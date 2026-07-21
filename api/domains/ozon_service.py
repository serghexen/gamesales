from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import json
import os
import ssl
import urllib.error
import urllib.request
from typing import Any

from fastapi import HTTPException


OZON_SELLER_BASE_URL = "https://api-seller.ozon.ru"


def normalize_ozon_store_code(value: str | None) -> str:
    # Разрешаем только существующий кабинет ASAT, чтобы не создавать фиктивные источники Ozon.
    normalized = str(value or "asat").strip().lower().replace("-", "_")
    if normalized in {"", "default"}:
        return "asat"
    if not normalized.replace("_", "").isalnum():
        raise HTTPException(400, "Ozon store_code must contain only letters, digits, underscore or dash")
    if normalized != "asat":
        raise HTTPException(400, "Ozon store_code must be asat")
    return "asat"


def _store_env_name(store_code: str | None, key: str) -> str:
    # Собираем имя настройки кабинета ASAT, например OZON_ASAT_API_KEY.
    return f"OZON_{normalize_ozon_store_code(store_code).upper()}_{key}"


def _env_value(key: str, *, store_code: str | None = None, default: str = "") -> str:
    # Читаем настройку магазина, оставляя общий env как fallback только для ASAT.
    normalized_store_code = normalize_ozon_store_code(store_code)
    scoped = str(os.getenv(_store_env_name(normalized_store_code, key), "") or "").strip()
    if scoped:
        return scoped
    if normalized_store_code in {"asat", "default"}:
        return str(os.getenv(f"OZON_{key}", default) or "").strip()
    return default


def _required_store_env(key: str, *, store_code: str | None = None) -> str:
    # Проверяем обязательный идентификатор или ключ до запроса к внешнему API.
    value = _env_value(key, store_code=store_code)
    if value:
        return value
    raise HTTPException(500, f"{_store_env_name(store_code, key)} is not configured")


def _env_int(name: str, default: int) -> int:
    # Читаем числовую настройку Ozon и возвращаем понятную ошибку при опечатке.
    raw = str(os.getenv(name, "") or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise HTTPException(500, f"{name} must be integer")


def _env_bool(name: str, default: bool = True) -> bool:
    # Читаем переключатель проверки SSL для локальной диагностики цепочки сертификатов.
    raw = str(os.getenv(name, "") or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _ssl_context() -> ssl.SSLContext:
    # Создаем SSL-контекст как у Yandex и разрешаем явно указать корпоративный CA.
    if not _env_bool("OZON_SSL_VERIFY", True):
        return ssl._create_unverified_context()

    ca_cert_path = str(os.getenv("OZON_CA_CERT_PATH", "") or "").strip()
    if ca_cert_path:
        return ssl.create_default_context(cafile=ca_cert_path)

    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _request_json(
    url: str,
    *,
    client_id: str,
    api_key: str,
    payload: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    # Выполняем авторизованный JSON-запрос и нормализуем ошибки Ozon для фоновой задачи.
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Client-Id": client_id,
            "Api-Key": api_key,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
            response_text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_text = exc.read().decode("utf-8", errors="replace")
        if exc.code == 429:
            retry_after = str(exc.headers.get("Retry-After") or "").strip()
            suffix = f" Повторите через {retry_after} сек." if retry_after.isdigit() else ""
            raise HTTPException(429, f"Лимит Ozon Seller API.{suffix}".strip())
        raise HTTPException(exc.code, f"Ozon Seller API error: {error_text[:1000]}")
    except urllib.error.URLError as exc:
        raise HTTPException(502, f"Ozon Seller API unavailable: {exc}")

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        raise HTTPException(502, "Ozon Seller API returned invalid JSON")
    if not isinstance(data, dict):
        raise HTTPException(502, "Ozon Seller API returned unexpected response format")
    return data


def _iter_date_chunks(date_from: date, date_to: date, chunk_days: int = 30) -> Iterator[tuple[date, date]]:
    # Делим длинный период на интервалы до 30 дней, чтобы соблюдать ограничение финансового метода Ozon.
    cursor = date_from
    while cursor <= date_to:
        chunk_to = min(date_to, cursor + timedelta(days=max(1, chunk_days) - 1))
        yield cursor, chunk_to
        cursor = chunk_to + timedelta(days=1)


def _ozon_timestamp(value: date, *, end_of_day: bool = False) -> str:
    # Формируем UTC-время начала или конца дня в формате фильтра Seller API.
    moment = datetime.combine(value, datetime.max.time() if end_of_day else datetime.min.time(), tzinfo=timezone.utc)
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_money(value: Any) -> Decimal:
    # Преобразуем денежное поле Ozon в Decimal без потери копеек.
    text = str(value if value not in (None, "") else "0").strip().replace(" ", "").replace(",", ".")
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _parse_date(value: Any, fallback: date) -> date:
    # Берем день операции Ozon, а при пустом значении используем начало запрошенного периода.
    text = str(value or "").strip()
    if not text:
        return fallback
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return fallback


def fetch_ozon_finance_transactions(
    date_from: date,
    date_to: date,
    store_code: str = "asat",
    progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    # Загружаем все финансовые операции Ozon по страницам и месячным интервалам.
    if date_to < date_from:
        raise HTTPException(400, "date_to must be >= date_from")
    normalized_store_code = normalize_ozon_store_code(store_code)
    client_id = _required_store_env("CLIENT_ID", store_code=normalized_store_code)
    api_key = _required_store_env("API_KEY", store_code=normalized_store_code)
    base_url = str(os.getenv("OZON_SELLER_BASE_URL", OZON_SELLER_BASE_URL) or OZON_SELLER_BASE_URL).rstrip("/")
    timeout = max(5, _env_int("OZON_TIMEOUT_SEC", 60))
    page_size = min(1000, max(1, _env_int("OZON_TRANSACTION_PAGE_SIZE", 1000)))
    max_pages = max(1, _env_int("OZON_TRANSACTION_MAX_PAGES", 1000))
    rows: list[dict[str, Any]] = []

    for chunk_from, chunk_to in _iter_date_chunks(date_from, date_to):
        for page in range(1, max_pages + 1):
            if progress:
                progress(f"Загружаем операции Ozon {chunk_from.isoformat()} - {chunk_to.isoformat()}: страница {page}")
            data = _request_json(
                f"{base_url}/v3/finance/transaction/list",
                client_id=client_id,
                api_key=api_key,
                payload={
                    "filter": {
                        "date": {
                            "from": _ozon_timestamp(chunk_from),
                            "to": _ozon_timestamp(chunk_to, end_of_day=True),
                        },
                        "operation_type": [],
                        "posting_number": "",
                        "transaction_type": "all",
                    },
                    "page": page,
                    "page_size": page_size,
                },
                timeout=timeout,
            )
            result = data.get("result")
            if not isinstance(result, dict):
                raise HTTPException(502, "Ozon Seller API response does not contain result")
            operations = result.get("operations")
            if not isinstance(operations, list):
                raise HTTPException(502, "Ozon Seller API response does not contain operations")
            rows.extend(row for row in operations if isinstance(row, dict))
            page_count = int(result.get("page_count") or 0)
            if not operations or (page_count > 0 and page >= page_count) or len(operations) < page_size:
                break
        else:
            raise HTTPException(502, f"Ozon transaction list exceeded {max_pages} pages")
    return rows


def fetch_ozon_catalog_items(
    store_code: str = "asat",
    progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    # Загружает карточки кабинета Ozon, чтобы локально сопоставить их с будущими номиналами ключей.
    normalized_store_code = normalize_ozon_store_code(store_code)
    client_id = _required_store_env("CLIENT_ID", store_code=normalized_store_code)
    api_key = _required_store_env("API_KEY", store_code=normalized_store_code)
    base_url = str(os.getenv("OZON_SELLER_BASE_URL", OZON_SELLER_BASE_URL) or OZON_SELLER_BASE_URL).rstrip("/")
    timeout = max(5, _env_int("OZON_TIMEOUT_SEC", 60))
    page_size = min(1000, max(1, _env_int("OZON_CATALOG_PAGE_SIZE", 1000)))
    max_pages = max(1, _env_int("OZON_CATALOG_MAX_PAGES", 1000))
    rows: list[dict[str, Any]] = []
    last_id = ""

    for page in range(1, max_pages + 1):
        if progress:
            progress(f"Загружаем каталог Ozon: страница {page}")
        data = _request_json(
            f"{base_url}/v2/product/list",
            client_id=client_id,
            api_key=api_key,
            payload={
                "filter": {"offer_id": [], "product_id": [], "visibility": "ALL"},
                "last_id": last_id,
                "limit": page_size,
            },
            timeout=timeout,
        )
        result = data.get("result")
        if not isinstance(result, dict):
            raise HTTPException(502, "Ozon catalog response does not contain result")
        items = result.get("items")
        if not isinstance(items, list):
            raise HTTPException(502, "Ozon catalog response does not contain items")
        rows.extend(item for item in items if isinstance(item, dict))
        next_last_id = str(result.get("last_id") or "").strip()
        if not next_last_id or not items:
            break
        if next_last_id == last_id:
            raise HTTPException(502, "Ozon catalog pagination did not advance")
        last_id = next_last_id
    else:
        raise HTTPException(502, f"Ozon catalog exceeded {max_pages} pages")

    if progress:
        progress(f"Загружено карточек Ozon: {len(rows)}")
    return rows


def aggregate_ozon_finance_transactions(
    rows: list[dict[str, Any]],
    *,
    fallback_date: date,
    store_code: str = "asat",
) -> list[dict[str, Any]]:
    # Сворачиваем операции Ozon по дням и сохраняем расшифровку удержаний для сверки с кабинетом.
    normalized_store_code = normalize_ozon_store_code(store_code)
    groups: dict[date, dict[str, Any]] = {}
    for row in rows:
        biz_date = _parse_date(row.get("operation_date"), fallback_date)
        group = groups.setdefault(
            biz_date,
            {
                "gross_sales": Decimal("0"),
                "returns": Decimal("0"),
                "net_amount": Decimal("0"),
                "sale_commission": Decimal("0"),
                "sale_commission_expense": Decimal("0"),
                "delivery_charge": Decimal("0"),
                "return_delivery_charge": Decimal("0"),
                "service_expenses": Decimal("0"),
                "service_income": Decimal("0"),
                "rows_count": 0,
                "operation_ids": [],
                "posting_numbers": [],
                "operation_types": set(),
                "service_breakdown": {},
            },
        )
        accrual = _parse_money(row.get("accruals_for_sale"))
        if accrual >= 0:
            group["gross_sales"] += accrual
        else:
            group["returns"] += abs(accrual)
        group["net_amount"] += _parse_money(row.get("amount"))
        sale_commission = _parse_money(row.get("sale_commission"))
        group["sale_commission"] += sale_commission
        group["sale_commission_expense"] += abs(min(sale_commission, Decimal("0")))
        group["delivery_charge"] += abs(_parse_money(row.get("delivery_charge")))
        group["return_delivery_charge"] += abs(_parse_money(row.get("return_delivery_charge")))
        group["rows_count"] += 1

        operation_id = row.get("operation_id")
        if operation_id not in (None, ""):
            group["operation_ids"].append(str(operation_id))
        operation_type = str(row.get("operation_type") or row.get("type") or "").strip()
        if operation_type:
            group["operation_types"].add(operation_type)
        posting = row.get("posting") if isinstance(row.get("posting"), dict) else {}
        posting_number = str(posting.get("posting_number") or "").strip()
        if posting_number:
            group["posting_numbers"].append(posting_number)

        services = row.get("services") if isinstance(row.get("services"), list) else []
        for service in services:
            if not isinstance(service, dict):
                continue
            name = str(service.get("name") or "unknown").strip() or "unknown"
            price = _parse_money(service.get("price"))
            group["service_breakdown"][name] = group["service_breakdown"].get(name, Decimal("0")) + price
            if price < 0:
                group["service_expenses"] += abs(price)
            else:
                group["service_income"] += price

    result: list[dict[str, Any]] = []
    for biz_date, group in sorted(groups.items()):
        product_gross = group["gross_sales"]
        payout = group["net_amount"]
        other_income = max(Decimal("0"), payout - product_gross)
        gross_amount = product_gross + other_income
        expense_amount = gross_amount - payout
        result.append(
            {
                "biz_date": biz_date,
                "gross_amount": gross_amount,
                "expense_amount": expense_amount,
                "payout_amount": payout,
                "external_key_base": f"ozon:{normalized_store_code}:finance-transactions:daily:{biz_date.isoformat()}",
                "comment": f"Ozon {normalized_store_code.upper()}; финансовые операции за {biz_date.isoformat()}; строк {group['rows_count']}",
                "payload_json": {
                    "provider": "ozon",
                    "store_code": normalized_store_code,
                    "report_type": "finance_transaction_list_v3",
                    "aggregation": "daily",
                    "biz_date": biz_date.isoformat(),
                    "rows_count": group["rows_count"],
                    "operation_ids": sorted(set(group["operation_ids"])),
                    "posting_numbers": sorted(set(group["posting_numbers"])),
                    "operation_types": sorted(group["operation_types"]),
                    "gross_sales": str(product_gross),
                    "returns": str(group["returns"]),
                    "sale_commission": str(group["sale_commission"]),
                    "sale_commission_expense": str(group["sale_commission_expense"]),
                    "delivery_charge": str(group["delivery_charge"]),
                    "return_delivery_charge": str(group["return_delivery_charge"]),
                    "service_expenses": str(group["service_expenses"]),
                    "service_income": str(group["service_income"]),
                    "other_income": str(other_income),
                    "payout_amount": str(payout),
                    "direct_expense": str(expense_amount),
                    "service_breakdown": {name: str(value) for name, value in sorted(group["service_breakdown"].items())},
                },
            }
        )
    return result
