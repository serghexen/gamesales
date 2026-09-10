from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
from typing import Any
from zoneinfo import ZoneInfo
import json

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from domains.interhub_stock_cache import STOCK_STATUS_LABELS


PRICE_TYPES = {"VOUCHER", "TOP_UP_FIXED"}


def collect_price_targets(services: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Собирает активные номиналы, для которых InterHub поддерживает calculate."""
    targets: list[dict[str, Any]] = []
    seen = set()
    for service in services:
        # Не опрашиваем выключенные услуги и не повторяем запросы для дублей каталога.
        raw = service.get('raw') or {}
        if str(raw.get('active', service.get('active', True))).lower() in {'false', '0', 'no', 'off'}:
            continue
        service_type = str(service.get("type") or "").upper()
        if service_type not in PRICE_TYPES:
            continue
        nominal_field = next(
            (field for field in service.get("fields") or [] if str(field.get("name") or "") == "nominal"),
            None,
        )
        if not nominal_field:
            continue
        for nominal in nominal_field.get("value_list") or []:
            if not isinstance(nominal, dict) or str(nominal.get('active', True)).lower() in {'false', '0', 'no', 'off'}:
                continue
            try:
                nominal_id = int(nominal.get("id"))
                service_id = int(service.get("service_id"))
            except (TypeError, ValueError):
                continue
            if service_id <= 0 or nominal_id <= 0:
                continue
            if (service_id, nominal_id) in seen:
                continue
            seen.add((service_id, nominal_id))
            targets.append(
                {
                    "service_id": service_id,
                    "service_title": str(service.get("title") or ""),
                    "category": str(service.get("category") or ""),
                    "service_type": service_type,
                    "nominal_id": nominal_id,
                    "nominal_title": str(nominal.get("title") or nominal_id),
                }
            )
    return targets


def build_interhub_prices_xlsx(prices: list[dict[str, Any]], errors: list[dict[str, Any]], stocks=None) -> bytes:
    """Создаёт отчёт из кэша цен и остатков; неизвестный остаток оставляет пустым, а не нулём."""
    workbook = Workbook()
    prices_sheet = workbook.active
    prices_sheet.title = "Закупочные цены"
    prices_sheet.append(["ID услуги", "Услуга", "Категория", "Тип", "ID номинала", "Номинал", "Закупочная цена, ₽", "Сумма для клиента (amount_in_currency)", "Розничная цена, ₽", "Рассчитано", "Полный ответ calculate (JSON)"])
    for row in prices:
        amount_in_currency = extract_response_number(row.get("provider_response"), "amount_in_currency")
        prices_sheet.append([
            row.get("service_id"), row.get("service_title"), row.get("category"), row.get("service_type"),
            row.get("nominal_id"), row.get("nominal_title"), row.get("fixed_amount"), amount_in_currency,
            calculate_retail_price(row.get("fixed_amount")), format_datetime(row.get("calculated_at")),
            format_provider_response(row.get("provider_response")),
        ])
    errors_sheet = workbook.create_sheet("Ошибки calculate")
    errors_sheet.append(["ID услуги", "Услуга", "Тип", "ID номинала", "Номинал", "Статус InterHub", "Сообщение", "Время", "Полный ответ calculate (JSON)"])
    for row in errors:
        errors_sheet.append([
            row.get("service_id"), row.get("service_title"), row.get("service_type"), row.get("nominal_id"),
            row.get("nominal_title"), row.get("provider_status"), row.get("provider_message"), format_datetime(row.get("calculated_at")),
            format_provider_response(row.get("provider_response")),
        ])
    for sheet in (prices_sheet, errors_sheet):
        style_sheet(sheet)
    prices_sheet.column_dimensions["G"].width = 22
    prices_sheet.column_dimensions["H"].width = 34
    prices_sheet.column_dimensions["I"].width = 22
    prices_sheet.column_dimensions["K"].width = 52
    errors_sheet.column_dimensions["I"].width = 52
    if stocks is not None:
        # Отдельный лист включает даже номиналы без успешной цены и ошибки ответа HTTP 200.
        stock_sheet = workbook.create_sheet('Остатки')
        stock_sheet.append(['ID услуги', 'Услуга', 'ID номинала', 'Номинал', 'Остаток, шт.',
                            'Проверено', 'Сопоставление', 'Название у поставщика', 'Сообщение',
                            'Полный ответ service/detail (JSON)'])
        for row in stocks:
            stock_sheet.append([row.get('service_id'), row.get('service_title'), row.get('nominal_id'),
                                row.get('nominal_title'), row.get('stock_count'), format_stock_datetime(row.get('checked_at')),
                                STOCK_STATUS_LABELS.get(row.get('match_status'), row.get('match_status')),
                                row.get('provider_name'), row.get('message'),
                                format_provider_response(row.get('provider_response'))])
        style_sheet(stock_sheet)
        stock_sheet.column_dimensions['F'].width = 24
        stock_sheet.column_dimensions['J'].width = 60
        stock_sheet.row_dimensions[1].height = 32
        for cells in stock_sheet.iter_rows(min_row=2):
            cells[4].number_format = '#,##0'
            # Текст поставщика не должен становиться исполняемой формулой в Excel.
            for cell in cells:
                if cell.data_type == 'f':
                    cell.data_type = 's'
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def format_datetime(value: Any) -> str:
    """Приводит дату из базы к читаемому виду в Excel."""
    if isinstance(value, datetime):
        return value.astimezone().strftime("%d.%m.%Y %H:%M:%S")
    return str(value or "")


def format_stock_datetime(value: Any) -> str:
    # Время проверки в выгрузке показываем по Москве независимо от часового пояса контейнера API.
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.astimezone(ZoneInfo('Europe/Moscow')).strftime('%d.%m.%Y %H:%M:%S')
    return format_datetime(value)


def format_provider_response(value: Any) -> str:
    """Сохраняет ответ поставщика в читаемом JSON без удаления неизвестных полей."""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return str(value or "")


def extract_response_number(value: Any, key: str) -> float:
    """Достаёт числовое поле из сохранённого JSON calculate для отдельной колонки отчёта."""
    response = value
    if isinstance(value, str):
        try:
            response = json.loads(value)
        except (TypeError, ValueError):
            response = {}
    try:
        return float(response.get(key) or 0) if isinstance(response, dict) else 0.0
    except (TypeError, ValueError):
        return 0.0


def calculate_retail_price(fixed_amount: Any) -> int:
    """Считает розницу от закупочной цены по согласованному коэффициенту без потери округления."""
    try:
        value = Decimal(str(fixed_amount or 0)) / Decimal("0.801024")
        return int(value.to_integral_value(rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError):
        return 0


def style_sheet(sheet) -> None:
    """Оформляет лист, чтобы отчёт было удобно фильтровать и читать."""
    header_fill = PatternFill("solid", fgColor="1F4E78")
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for column in range(1, sheet.max_column + 1):
        longest = max((len(str(sheet.cell(row, column).value or "")) for row in range(1, sheet.max_row + 1)), default=10)
        sheet.column_dimensions[get_column_letter(column)].width = min(max(longest + 2, 12), 42)
    for row in range(2, sheet.max_row + 1):
        sheet.cell(row, 7).alignment = Alignment(vertical="top", wrap_text=True)
        sheet.cell(row, sheet.max_column).alignment = Alignment(vertical="top", wrap_text=True)
