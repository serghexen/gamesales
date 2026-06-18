from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import HTTPException


WILDBERRIES_FINANCE_BASE_URL = "https://finance-api.wildberries.ru"
WILDBERRIES_STATISTICS_BASE_URL = "https://statistics-api.wildberries.ru"
_REPORT_REQUEST_LOCK = threading.Lock()
_REPORT_LAST_ATTEMPT: dict[str, float] = {}
_REPORT_FIELDS = [
    "rrdId",
    "reportId",
    "rrDate",
    "docTypeName",
    "sellerOperName",
    "retailAmount",
    "forPay",
    "deliveryService",
    "paidStorage",
    "paidAcceptance",
    "deduction",
    "penalty",
    "additionalPayment",
    "acquiringFee",
    "ppvzSalesCommission",
    "orderId",
    "srid",
    "nmId",
    "vendorCode",
    "sku",
]


def _env_int(name: str, default: int) -> int:
    # Читаем числовую настройку WB и сразу показываем понятную ошибку конфигурации.
    raw = str(os.getenv(name, "") or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise HTTPException(500, f"{name} must be integer")


def normalize_wildberries_store_code(value: str | None) -> str:
    # Приводим код магазина к безопасному env-префиксу для выбора токена и источника.
    normalized = str(value or "asat").strip().lower().replace("-", "_")
    if not normalized:
        return "asat"
    if not normalized.replace("_", "").isalnum():
        raise HTTPException(400, "Wildberries store_code must contain only letters, digits, underscore or dash")
    return normalized


def _store_env_name(store_code: str, key: str) -> str:
    # Собираем имя настройки магазина, например WILDBERRIES_SPS_TOKEN.
    return f"WILDBERRIES_{normalize_wildberries_store_code(store_code).upper()}_{key}"


def _store_env_value(store_code: str, key: str, default: str = "") -> str:
    # Читаем настройку магазина, а для ASAT поддерживаем старые общие переменные.
    normalized = normalize_wildberries_store_code(store_code)
    scoped = str(os.getenv(_store_env_name(normalized, key), "") or "").strip()
    if scoped:
        return scoped
    if normalized in {"asat", "default"}:
        return str(os.getenv(f"WILDBERRIES_{key}", default) or "").strip()
    return default


def _required_token(store_code: str) -> str:
    # Проверяем токен выбранного магазина до сетевого запроса и не раскрываем его значение.
    token = _store_env_value(store_code, "TOKEN")
    if not token:
        raise HTTPException(500, f"{_store_env_name(store_code, 'TOKEN')} is not configured")
    return token


def _ssl_context() -> ssl.SSLContext:
    # Создаем стандартный SSL-контекст и используем certifi, когда пакет доступен.
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _sleep_with_progress(seconds: int, progress: Callable[[str], None] | None, prefix: str) -> None:
    # Показываем оставшееся ожидание по секундам, чтобы UI не выглядел зависшим.
    for remaining in range(max(0, int(seconds)), 0, -1):
        if progress:
            progress(f"{prefix}: {remaining} сек.")
        time.sleep(1)


def _wait_for_report_slot(rate_key: str, progress: Callable[[str], None] | None = None) -> None:
    # Ждем локальный лимит WB внутри фоновой задачи и продолжаем без ошибки для пользователя.
    interval_seconds = max(0, _env_int("WILDBERRIES_REQUEST_INTERVAL_SEC", 61))
    if interval_seconds <= 0:
        return
    while True:
        now = time.monotonic()
        with _REPORT_REQUEST_LOCK:
            last_attempt = _REPORT_LAST_ATTEMPT.get(rate_key, 0.0)
            remaining = interval_seconds - (now - last_attempt)
            if last_attempt <= 0 or remaining <= 0:
                _REPORT_LAST_ATTEMPT[rate_key] = now
                return
        wait_seconds = int(max(1, remaining + 0.999))
        _sleep_with_progress(wait_seconds, progress, "Ждем лимит Wildberries")


def _request_report_page(
    url: str,
    *,
    token: str,
    payload: dict[str, Any],
    timeout: int,
    rate_key: str,
    progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]] | None:
    # Загружает одну страницу финансового отчета; ответ 204 означает конец пагинации.
    body = ""
    max_attempts = max(1, _env_int("WILDBERRIES_RATE_LIMIT_ATTEMPTS", 4))
    retry_buffer_seconds = max(0, _env_int("WILDBERRIES_RATE_LIMIT_BUFFER_SEC", 5))
    for attempt in range(max_attempts):
        _wait_for_report_slot(rate_key, progress)
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={"Authorization": token, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
                if response.status == 204:
                    return None
                body = response.read().decode("utf-8")
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 204:
                return None
            error_text = exc.read().decode("utf-8", errors="replace")
            retry_header = ""
            if exc.headers:
                retry_header = str(exc.headers.get("X-Ratelimit-Retry") or exc.headers.get("Retry-After") or "").strip()
            retry_seconds = int(retry_header) if retry_header.isdigit() else 60
            if exc.code == 429 and retry_seconds > 300:
                raise HTTPException(429, f"Wildberries Finance API недоступен еще {retry_seconds} сек.")
            if exc.code == 429 and attempt < max_attempts - 1:
                wait_seconds = retry_seconds + retry_buffer_seconds
                _sleep_with_progress(wait_seconds, progress, "Wildberries ограничил запрос, повторяем через")
                continue
            if exc.code == 429:
                raise HTTPException(429, "Wildberries Finance API повторно отклонил запрос по лимиту")
            raise HTTPException(exc.code, f"Wildberries Finance API error: {error_text[:1000]}")
        except urllib.error.URLError as exc:
            raise HTTPException(502, f"Wildberries Finance API unavailable: {exc}")

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(502, "Wildberries Finance API returned invalid JSON")
    if not isinstance(data, list):
        raise HTTPException(502, "Wildberries Finance API returned unexpected report format")
    return [row for row in data if isinstance(row, dict)]


def _normalize_legacy_row(row: dict[str, Any]) -> dict[str, Any]:
    # Приводим поля старого отчета WB к формату нового Finance API для общей агрегации.
    return {
        "rrdId": row.get("rrd_id"),
        "reportId": row.get("realizationreport_id"),
        "rrDate": row.get("rr_dt"),
        "docTypeName": row.get("doc_type_name"),
        "sellerOperName": row.get("supplier_oper_name"),
        "retailAmount": row.get("retail_amount"),
        "forPay": row.get("ppvz_for_pay"),
        "deliveryService": row.get("delivery_rub"),
        "paidStorage": row.get("storage_fee"),
        "paidAcceptance": row.get("acceptance"),
        "deduction": row.get("deduction"),
        "penalty": row.get("penalty"),
        "additionalPayment": row.get("additional_payment"),
        "acquiringFee": row.get("acquiring_fee"),
        "ppvzSalesCommission": row.get("ppvz_sales_commission"),
        "orderId": row.get("order_uid") or row.get("shk_id"),
        "srid": row.get("srid"),
        "nmId": row.get("nm_id"),
        "vendorCode": row.get("sa_name"),
        "sku": row.get("barcode"),
    }


def _fetch_legacy_sales_report(
    date_from: date,
    date_to: date,
    *,
    token: str,
    timeout: int,
    progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    # Загружает старый отчет реализации как временный fallback для Basic-токенов WB.
    base_url = str(os.getenv("WILDBERRIES_STATISTICS_BASE_URL", WILDBERRIES_STATISTICS_BASE_URL) or WILDBERRIES_STATISTICS_BASE_URL).rstrip("/")
    limit = min(100000, max(1, _env_int("WILDBERRIES_REPORT_LIMIT", 100000)))
    rows: list[dict[str, Any]] = []
    rrd_id = 0
    for page_no in range(1, max(1, _env_int("WILDBERRIES_REPORT_MAX_PAGES", 100)) + 1):
        if progress:
            progress(f"Загружаем резервный отчет Wildberries: страница {page_no}")
        query = urllib.parse.urlencode(
            {
                "dateFrom": date_from.isoformat(),
                "dateTo": date_to.isoformat(),
                "limit": limit,
                "rrdid": rrd_id,
            }
        )
        request = urllib.request.Request(
            f"{base_url}/api/v5/supplier/reportDetailByPeriod?{query}",
            method="GET",
            headers={"Authorization": token},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error_text = exc.read().decode("utf-8", errors="replace")
            if exc.code == 429:
                retry_header = str(exc.headers.get("X-Ratelimit-Retry") or exc.headers.get("Retry-After") or "") if exc.headers else ""
                retry_seconds = int(retry_header) if retry_header.isdigit() else 60
                raise HTTPException(429, f"Лимит Wildberries для текущего токена. Повторите примерно через {retry_seconds} сек.")
            raise HTTPException(exc.code, f"Wildberries legacy report error: {error_text[:1000]}")
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise HTTPException(502, f"Wildberries legacy report unavailable: {exc}")
        if not isinstance(data, list):
            raise HTTPException(502, "Wildberries legacy report returned unexpected format")
        page = [_normalize_legacy_row(row) for row in data if isinstance(row, dict)]
        rows.extend(page)
        if len(page) < limit:
            return rows
        try:
            next_rrd_id = int(page[-1].get("rrdId"))
        except (TypeError, ValueError):
            raise HTTPException(502, "Wildberries legacy report page does not contain a valid rrd_id")
        if next_rrd_id <= rrd_id:
            raise HTTPException(502, "Wildberries legacy report pagination did not advance")
        rrd_id = next_rrd_id
        _sleep_with_progress(61, progress, "Ждем лимит резервного отчета Wildberries")
    raise HTTPException(502, "Wildberries legacy report exceeded page limit")


def _parse_money(value: Any) -> Decimal:
    # Приводим денежное поле WB к Decimal, чтобы дневные суммы не теряли копейки.
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value).replace(" ", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _parse_date(value: Any, fallback: date) -> date:
    # Приводим дату финансового отчета WB к дню учета.
    text = str(value or "").strip()
    if not text:
        return fallback
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return fallback


def aggregate_wildberries_report_rows(
    rows: list[dict[str, Any]],
    *,
    fallback_date: date,
    store_code: str = "asat",
) -> list[dict[str, Any]]:
    # Сворачиваем детализацию WB по rrDate и сохраняем разбивку расходов для сверки с кабинетом.
    normalized_store_code = normalize_wildberries_store_code(store_code)
    groups: dict[date, dict[str, Any]] = {}
    for row in rows:
        biz_date = _parse_date(row.get("rrDate"), fallback_date)
        group = groups.setdefault(
            biz_date,
            {
                "biz_date": biz_date,
                "gross_sales": Decimal("0"),
                "returns": Decimal("0"),
                "for_pay": Decimal("0"),
                "delivery": Decimal("0"),
                "storage": Decimal("0"),
                "acceptance": Decimal("0"),
                "deduction": Decimal("0"),
                "penalty": Decimal("0"),
                "additional_payment": Decimal("0"),
                "acquiring": Decimal("0"),
                "sales_commission": Decimal("0"),
                "rows_count": 0,
                "report_ids": set(),
                "rrd_ids": [],
                "order_ids": [],
                "srids": [],
            },
        )
        doc_type = str(row.get("docTypeName") or "").strip().lower()
        retail_amount = abs(_parse_money(row.get("retailAmount")))
        is_return = "возврат" in doc_type or "return" in doc_type
        if is_return:
            group["returns"] += retail_amount
            group["for_pay"] -= abs(_parse_money(row.get("forPay")))
        else:
            group["gross_sales"] += retail_amount
            group["for_pay"] += _parse_money(row.get("forPay"))
        # Сервисные поля суммируем в net-виде, потому что WB может прислать сторно.
        group["delivery"] += _parse_money(row.get("deliveryService"))
        group["storage"] += _parse_money(row.get("paidStorage"))
        group["acceptance"] += _parse_money(row.get("paidAcceptance"))
        group["deduction"] += _parse_money(row.get("deduction"))
        group["penalty"] += _parse_money(row.get("penalty"))
        group["additional_payment"] += _parse_money(row.get("additionalPayment"))
        group["acquiring"] += _parse_money(row.get("acquiringFee"))
        group["sales_commission"] += _parse_money(row.get("ppvzSalesCommission"))
        group["rows_count"] += 1
        if row.get("reportId") not in (None, ""):
            group["report_ids"].add(str(row.get("reportId")))
        if row.get("rrdId") not in (None, ""):
            group["rrd_ids"].append(str(row.get("rrdId")))
        if row.get("orderId") not in (None, ""):
            group["order_ids"].append(str(row.get("orderId")))
        if row.get("srid") not in (None, ""):
            group["srids"].append(str(row.get("srid")))

    result: list[dict[str, Any]] = []
    for biz_date, group in sorted(groups.items()):
        # Повторяем формулу ЛК WB: из суммы к перечислению вычитаются сервисы и штрафы.
        service_expenses = group["delivery"] + group["storage"] + group["acceptance"] + group["deduction"] + group["penalty"]
        goods_net = group["for_pay"]
        payout = goods_net - service_expenses + group["additional_payment"]
        direct_expense = group["gross_sales"] - payout
        result.append(
            {
                "biz_date": biz_date,
                "gross_amount": group["gross_sales"],
                "expense_amount": direct_expense,
                "payout_amount": payout,
                "external_key_base": f"wildberries:{normalized_store_code}:sales-reports:daily:{biz_date.isoformat()}",
                "comment": f"Wildberries {normalized_store_code.upper()}; отчет реализации за {biz_date.isoformat()}; строк {group['rows_count']}",
                "payload_json": {
                    "provider": "wildberries",
                    "store_code": normalized_store_code,
                    "report_type": "sales_reports_detailed",
                    "aggregation": "daily",
                    "biz_date": biz_date.isoformat(),
                    "rows_count": group["rows_count"],
                    "report_ids": sorted(group["report_ids"]),
                    "rrd_ids": sorted(set(group["rrd_ids"])),
                    "order_ids": sorted(set(group["order_ids"])),
                    "srids": sorted(set(group["srids"])),
                    "gross_sales": str(group["gross_sales"]),
                    "returns": str(group["returns"]),
                    "for_pay": str(group["for_pay"]),
                    "delivery": str(group["delivery"]),
                    "storage": str(group["storage"]),
                    "acceptance": str(group["acceptance"]),
                    "deduction": str(group["deduction"]),
                    "penalty": str(group["penalty"]),
                    "additional_payment": str(group["additional_payment"]),
                    "acquiring": str(group["acquiring"]),
                    "sales_commission": str(group["sales_commission"]),
                    "payout_amount": str(payout),
                    "direct_expense": str(direct_expense),
                },
            }
        )
    return result


def fetch_wildberries_sales_report(
    date_from: date,
    date_to: date,
    store_code: str = "asat",
    progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    # Загружает все страницы нового финансового отчета WB за выбранный период.
    normalized_store_code = normalize_wildberries_store_code(store_code)
    token = _required_token(normalized_store_code)
    rate_key = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    base_url = str(os.getenv("WILDBERRIES_FINANCE_BASE_URL", WILDBERRIES_FINANCE_BASE_URL) or WILDBERRIES_FINANCE_BASE_URL).rstrip("/")
    timeout = max(5, _env_int("WILDBERRIES_TIMEOUT_SEC", 60))
    limit = min(100000, max(1, _env_int("WILDBERRIES_REPORT_LIMIT", 100000)))
    max_pages = max(1, _env_int("WILDBERRIES_REPORT_MAX_PAGES", 100))
    url = f"{base_url}/api/finance/v1/sales-reports/detailed"
    rows: list[dict[str, Any]] = []
    rrd_id = 0

    for page_no in range(1, max_pages + 1):
        if progress:
            progress(f"Загружаем отчет Wildberries: страница {page_no}")
        try:
            page = _request_report_page(
                url,
                token=token,
                payload={
                    "dateFrom": date_from.isoformat(),
                    "dateTo": date_to.isoformat(),
                    "limit": limit,
                    "rrdId": rrd_id,
                    "period": "daily",
                    "fields": _REPORT_FIELDS,
                },
                timeout=timeout,
                rate_key=rate_key,
                progress=progress,
            )
        except HTTPException as exc:
            if exc.status_code != 429 or page_no != 1 or rows:
                raise
            if progress:
                progress("Переключаемся на резервный отчет Wildberries")
            return _fetch_legacy_sales_report(date_from, date_to, token=token, timeout=timeout, progress=progress)
        if not page:
            return rows
        rows.extend(page)
        if len(page) < limit:
            return rows
        next_rrd_id = page[-1].get("rrdId")
        try:
            next_rrd_id = int(next_rrd_id)
        except (TypeError, ValueError):
            raise HTTPException(502, "Wildberries report page does not contain a valid rrdId")
        if next_rrd_id <= rrd_id:
            raise HTTPException(502, "Wildberries report pagination did not advance")
        rrd_id = next_rrd_id

    raise HTTPException(502, f"Wildberries report exceeded {max_pages} pages")
