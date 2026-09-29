from __future__ import annotations

from collections.abc import Callable
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


def _accrual_money(value: Any, *, required: bool = False) -> Decimal:
    # Не превращаем повреждённую сумму или другую валюту в рублёвую проводку.
    if value is None and not required:
        return Decimal("0")
    if not isinstance(value, dict) or value.get("currency") != "RUB":
        raise HTTPException(502, "Ozon accrual contains missing money or unsupported currency")
    try:
        amount = Decimal(str(value["amount"]))
    except (KeyError, InvalidOperation, ValueError):
        raise HTTPException(502, "Ozon accrual contains invalid amount")
    if not amount.is_finite():
        raise HTTPException(502, "Ozon accrual contains non-finite amount")
    return amount


def _normalize_finance_accrual(row: dict[str, Any], day: date) -> dict[str, Any]:
    # Приводим начисления нового API к дневному учёту, сохраняя прежние ключи записей.
    category = str(row.get("accrued_category") or "UNSPECIFIED")
    gross = Decimal("0")
    commission = Decimal("0")
    services: list[dict[str, Any]] = []
    posting = row.get("posting") or {}
    for product in posting.get("products") or []:
        product_commission = product.get("commission") or {}
        # Реализация уже учтена в sale_amount: баллы и софинансирование повторно не прибавляем.
        gross += _accrual_money(product_commission.get("sale_amount"))
        # Для выплаты нужна итоговая комиссия, а не комиссия по прайс-листу sale_commission.
        commission += _accrual_money(product_commission.get("commission"))
        delivery = product.get("delivery") or {}
        # Итог доставки уже включает услуги: не складываем его повторно с детализацией.
        services.append({"name": "delivery", "price": _accrual_money(delivery.get("total_accrued"))})

    fees = list((row.get("container_fees") or {}).get("fees") or [])
    for item in (row.get("item_fees") or {}).get("fees") or []:
        fees.extend(item.get("fees") or [])
    if row.get("non_item_fee"):
        fees.append(row["non_item_fee"])
    for fee in fees:
        services.append({"name": f"type_id:{fee.get('type_id')}", "price": _accrual_money(fee.get("accrued"), required=True)})

    # Дата запроса известна даже при пустой дате строки; чужой день не записываем в этот период.
    raw_date = row.get("date") or day.isoformat()
    if raw_date != day.isoformat():
        raise HTTPException(502, "Ozon accrual date differs from requested day")
    total = _accrual_money(row.get("total_amount"), required=True)
    # До записи сверяем разложение отправления с итогом API, чтобы новый формат не исказил выручку.
    if category == "POSTING":
        calculated_total = gross + commission + sum((service["price"] for service in services), Decimal("0"))
        if calculated_total.quantize(Decimal("0.01")) != total.quantize(Decimal("0.01")):
            raise HTTPException(502, "Ozon: сумма продажи, комиссий и услуг не совпадает с итогом начисления; требуется сверка формата API")
    return {
        "operation_id": row.get("accrual_id"),
        "operation_date": raw_date,
        "operation_type": category,
        "accruals_for_sale": gross,
        "sale_commission": commission,
        "amount": total,
        "posting": {"posting_number": row.get("unit_number") if category == "POSTING" else ""},
        "services": services,
        "report_type": "finance_accrual_by_day_v1",
    }


def fetch_ozon_finance_transactions(
    date_from: date,
    date_to: date,
    store_code: str = "asat",
    progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    # Старый transaction/list отключён: читаем каждый день через курсор нового API.
    if date_to < date_from:
        raise HTTPException(400, "date_to must be >= date_from")
    normalized_store_code = normalize_ozon_store_code(store_code)
    client_id = _required_store_env("CLIENT_ID", store_code=normalized_store_code)
    api_key = _required_store_env("API_KEY", store_code=normalized_store_code)
    base_url = str(os.getenv("OZON_SELLER_BASE_URL", OZON_SELLER_BASE_URL) or OZON_SELLER_BASE_URL).rstrip("/")
    timeout = max(5, _env_int("OZON_TIMEOUT_SEC", 60))
    max_pages = max(1, _env_int("OZON_TRANSACTION_MAX_PAGES", 1000))
    rows: list[dict[str, Any]] = []

    for offset in range((date_to - date_from).days + 1):
        day = date_from + timedelta(days=offset)
        last_id = ""
        seen_cursors: set[str] = set()
        for page in range(1, max_pages + 1):
            if progress:
                progress(f"Загружаем начисления Ozon {day.isoformat()}: страница {page}")
            data = _request_json(
                f"{base_url}/v1/finance/accrual/by-day",
                client_id=client_id,
                api_key=api_key,
                payload={"date": day.isoformat(), "last_id": last_id},
                timeout=timeout,
            )
            accruals = data.get("accruals")
            if not isinstance(accruals, list) or any(not isinstance(row, dict) for row in accruals):
                raise HTTPException(502, "Ozon Seller API response does not contain valid accruals")
            rows.extend(_normalize_finance_accrual(row, day) for row in accruals)
            next_id = data.get("last_id")
            if not isinstance(next_id, str):
                raise HTTPException(502, "Ozon accrual response does not contain last_id")
            if not next_id:
                break
            if next_id in seen_cursors:
                raise HTTPException(502, "Ozon accrual pagination did not advance")
            seen_cursors.add(next_id)
            last_id = next_id
        else:
            raise HTTPException(502, f"Ozon accrual list exceeded {max_pages} pages for {day.isoformat()}")
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

    def fetch_catalog_segment(visibility: str, label: str) -> list[dict[str, Any]]:
        # Читает отдельный сегмент, потому что Ozon не включает архивные товары в выборку ALL.
        segment_rows: list[dict[str, Any]] = []
        last_id = ""
        for page in range(1, max_pages + 1):
            if progress:
                progress(f"Загружаем {label} Ozon: страница {page}")
            data = _request_json(
                f"{base_url}/v3/product/list",
                client_id=client_id,
                api_key=api_key,
                payload={
                    "filter": {"offer_id": [], "product_id": [], "visibility": visibility},
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
            for item in items:
                if not isinstance(item, dict):
                    continue
                # Сохраняем признак явно: подробный ответ может не вернуть visibility архивной карточки.
                segment_rows.append({**item, "visibility": "ARCHIVED"} if visibility == "ARCHIVED" else item)
            next_last_id = str(result.get("last_id") or "").strip()
            if not next_last_id or not items:
                return segment_rows
            if next_last_id == last_id:
                raise HTTPException(502, "Ozon catalog pagination did not advance")
            last_id = next_last_id
        raise HTTPException(502, f"Ozon catalog exceeded {max_pages} pages")

    # ALL у Ozon возвращает рабочий каталог без архива, поэтому читаем оба сегмента и объединяем их.
    rows = fetch_catalog_segment("ALL", "каталог") + fetch_catalog_segment("ARCHIVED", "архив")

    details_by_product_id: dict[int, dict[str, Any]] = {}
    for offset in range(0, len(rows), 1000):
        product_ids = [
            int(item.get("product_id") or item.get("id"))
            for item in rows[offset:offset + 1000]
            if str(item.get("product_id") or item.get("id") or "").isdigit()
        ]
        if not product_ids:
            continue
        # Запрашиваем полные карточки отдельным методом: список Ozon не содержит названия и статуса.
        data = _request_json(
            f"{base_url}/v3/product/info/list",
            client_id=client_id,
            api_key=api_key,
            payload={"offer_id": [], "product_id": product_ids, "sku": []},
            timeout=timeout,
        )
        result = data.get("result") if isinstance(data.get("result"), dict) else {}
        info_items = data.get("items") if isinstance(data.get("items"), list) else result.get("items")
        if not isinstance(info_items, list):
            raise HTTPException(502, "Ozon product info response does not contain items")
        for item in info_items:
            if not isinstance(item, dict):
                continue
            raw_product_id = item.get("product_id") or item.get("id")
            if str(raw_product_id or "").isdigit():
                details_by_product_id[int(raw_product_id)] = item

    # Склеиваем короткий список и детали, сохраняя product_id из основного метода как стабильный ключ.
    enriched_rows = []
    for item in rows:
        raw_product_id = item.get("product_id") or item.get("id")
        details = details_by_product_id.get(int(raw_product_id)) if str(raw_product_id or "").isdigit() else None
        enriched = {**item, **(details or {})}
        if str(item.get("visibility") or "").upper() == "ARCHIVED":
            enriched["visibility"] = "ARCHIVED"
        enriched_rows.append(enriched)

    prices_by_product_id: dict[int, dict[str, Any]] = {}
    stocks_by_product_id: dict[int, list[dict[str, Any]]] = {}
    for offset in range(0, len(enriched_rows), 1000):
        product_ids = [
            int(item.get("product_id") or item.get("id"))
            for item in enriched_rows[offset:offset + 1000]
            if str(item.get("product_id") or item.get("id") or "").isdigit()
        ]
        if not product_ids:
            continue
        product_filter = {"offer_id": [], "product_id": product_ids, "visibility": "ALL"}
        # Берем цену отдельным методом Ozon: поле vat в нем означает ставку НДС, а не остаток.
        prices_data = _request_json(
            f"{base_url}/v5/product/info/prices",
            client_id=client_id,
            api_key=api_key,
            payload={"cursor": "", "filter": product_filter, "limit": len(product_ids)},
            timeout=timeout,
        )
        price_items = prices_data.get("items") if isinstance(prices_data.get("items"), list) else []
        for item in price_items:
            raw_product_id = item.get("product_id") if isinstance(item, dict) else None
            if str(raw_product_id or "").isdigit():
                prices_by_product_id[int(raw_product_id)] = item

        # Суммируем present по схемам FBO/FBS, чтобы показать фактический остаток, а не ставку НДС.
        stocks_data = _request_json(
            f"{base_url}/v4/product/info/stocks",
            client_id=client_id,
            api_key=api_key,
            payload={
                "cursor": "",
                "filter": {**product_filter, "with_quant": {"created": True, "exists": True}},
                "limit": len(product_ids),
            },
            timeout=timeout,
        )
        stock_items = stocks_data.get("items") if isinstance(stocks_data.get("items"), list) else []
        for item in stock_items:
            raw_product_id = item.get("product_id") if isinstance(item, dict) else None
            if not str(raw_product_id or "").isdigit():
                continue
            stocks = item.get("stocks") if isinstance(item.get("stocks"), list) else []
            stocks_by_product_id[int(raw_product_id)] = [stock for stock in stocks if isinstance(stock, dict)]

    def stock_rows_from_product_info(item: dict[str, Any]) -> list[dict[str, Any]]:
        # Берет запас из подробной карточки, потому что для цифровых товаров общий складской метод может вернуть пустой список.
        raw_stocks = item.get("stocks")
        if isinstance(raw_stocks, dict):
            raw_stocks = raw_stocks.get("stocks")
        if not isinstance(raw_stocks, list):
            return []
        return [stock for stock in raw_stocks if isinstance(stock, dict)]

    # Дополняем сохраненный снимок ценой и остатком, чтобы карточка UI не зависела от формата API Ozon.
    for item in enriched_rows:
        raw_product_id = item.get("product_id") or item.get("id")
        if not str(raw_product_id or "").isdigit():
            continue
        product_id = int(raw_product_id)
        price_item = prices_by_product_id.get(product_id, {})
        price = price_item.get("price") if isinstance(price_item.get("price"), dict) else {}
        item["ozon_price"] = price
        # Для цифровой карточки present приходит в product/info/list, а v4/product/info/stocks может быть пустым.
        item["ozon_stocks"] = stocks_by_product_id.get(product_id) or stock_rows_from_product_info(item)

    if progress:
        progress(f"Загружено карточек Ozon: {len(enriched_rows)}")
    return enriched_rows


def fetch_ozon_catalog_offer_id(product_id: int, store_code: str = "asat") -> str:
    # Запрашивает один артикул напрямую у Ozon, когда локальный снимок карточки оказался неполным.
    normalized_store_code = normalize_ozon_store_code(store_code)
    client_id = _required_store_env("CLIENT_ID", store_code=normalized_store_code)
    api_key = _required_store_env("API_KEY", store_code=normalized_store_code)
    base_url = str(os.getenv("OZON_SELLER_BASE_URL", OZON_SELLER_BASE_URL) or OZON_SELLER_BASE_URL).rstrip("/")
    timeout = max(5, _env_int("OZON_TIMEOUT_SEC", 60))
    data = _request_json(
        f"{base_url}/v3/product/info/list",
        client_id=client_id,
        api_key=api_key,
        payload={"offer_id": [], "product_id": [int(product_id)], "sku": []},
        timeout=timeout,
    )
    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    items = data.get("items") if isinstance(data.get("items"), list) else result.get("items")
    if not isinstance(items, list):
        raise HTTPException(502, "Ozon product info response does not contain items")
    for item in items:
        if not isinstance(item, dict):
            continue
        if int(item.get("product_id") or item.get("id") or 0) != int(product_id):
            continue
        offer_id = str(item.get("offer_id") or item.get("offer_code") or "").strip()
        if offer_id:
            return offer_id
    return ""


def update_ozon_digital_stock(
    offer_id: str,
    stock: int,
    store_code: str = "asat",
) -> dict[str, Any]:
    # Передает в Ozon только витринный остаток цифровой карточки, а не сами ключи.
    normalized_store_code = normalize_ozon_store_code(store_code)
    normalized_offer_id = str(offer_id or "").strip()
    if not normalized_offer_id:
        raise HTTPException(400, "Ozon offer_id is required for digital stock")
    if stock < 0:
        raise HTTPException(400, "Ozon digital stock must not be negative")
    client_id = _required_store_env("CLIENT_ID", store_code=normalized_store_code)
    api_key = _required_store_env("API_KEY", store_code=normalized_store_code)
    base_url = str(os.getenv("OZON_SELLER_BASE_URL", OZON_SELLER_BASE_URL) or OZON_SELLER_BASE_URL).rstrip("/")
    timeout = max(5, _env_int("OZON_TIMEOUT_SEC", 60))
    return _request_json(
        f"{base_url}/v1/product/digital/stocks/import",
        client_id=client_id,
        api_key=api_key,
        payload={"stocks": [{"offer_id": normalized_offer_id, "stock": int(stock)}]},
        timeout=timeout,
    )


def update_ozon_catalog_archive(
    product_id: int,
    archived: bool,
    store_code: str = "asat",
) -> dict[str, Any]:
    # Переносит карточку в архив или возвращает ее в продажу по стабильному ID Ozon.
    normalized_store_code = normalize_ozon_store_code(store_code)
    normalized_product_id = int(product_id or 0)
    if normalized_product_id <= 0:
        raise HTTPException(400, "Ozon product_id is required")
    client_id = _required_store_env("CLIENT_ID", store_code=normalized_store_code)
    api_key = _required_store_env("API_KEY", store_code=normalized_store_code)
    base_url = str(os.getenv("OZON_SELLER_BASE_URL", OZON_SELLER_BASE_URL) or OZON_SELLER_BASE_URL).rstrip("/")
    timeout = max(5, _env_int("OZON_TIMEOUT_SEC", 60))
    endpoint = "/v1/product/archive" if archived else "/v1/product/unarchive"
    return _request_json(
        f"{base_url}{endpoint}",
        client_id=client_id,
        api_key=api_key,
        payload={"product_id": [normalized_product_id]},
        timeout=timeout,
    )


def fetch_ozon_digital_postings(
    date_from: datetime,
    date_to: datetime,
    store_code: str = "asat",
) -> list[dict[str, Any]]:
    # Получает цифровые отправления постранично, чтобы оператор мог выдать ключ вручную.
    normalized_store_code = normalize_ozon_store_code(store_code)
    client_id = _required_store_env("CLIENT_ID", store_code=normalized_store_code)
    api_key = _required_store_env("API_KEY", store_code=normalized_store_code)
    base_url = str(os.getenv("OZON_SELLER_BASE_URL", OZON_SELLER_BASE_URL) or OZON_SELLER_BASE_URL).rstrip("/")
    timeout = max(5, _env_int("OZON_TIMEOUT_SEC", 60))
    # Метод цифровых отправлений принимает не больше 100 строк, это отдельный лимит Ozon.
    limit = min(100, max(1, _env_int("OZON_DIGITAL_POSTINGS_PAGE_SIZE", 100)))
    max_pages = max(1, _env_int("OZON_DIGITAL_POSTINGS_MAX_PAGES", 1000))
    cursor = ""
    postings: list[dict[str, Any]] = []
    since = date_from.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    to = date_to.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    for _page in range(max_pages):
        data = _request_json(
            f"{base_url}/v2/posting/digital/list",
            client_id=client_id,
            api_key=api_key,
            payload={
                "cursor": cursor,
                "filter": {"since": since, "to": to},
                "limit": limit,
                "sort_dir": "ASC",
            },
            timeout=timeout,
        )
        rows = data.get("postings") if isinstance(data.get("postings"), list) else []
        postings.extend(row for row in rows if isinstance(row, dict))
        if not data.get("has_next"):
            break
        next_cursor = str(data.get("cursor") or "").strip()
        if not next_cursor or next_cursor == cursor:
            raise HTTPException(502, "Ozon digital posting pagination did not advance")
        cursor = next_cursor
    else:
        raise HTTPException(502, f"Ozon digital postings exceeded {max_pages} pages")
    return postings


def upload_ozon_digital_codes(
    *,
    posting_number: str,
    sku: int,
    codes: list[str],
    store_code: str = "asat",
) -> dict[str, Any]:
    # Передает введенные оператором ключи в конкретное цифровое отправление Ozon.
    normalized_store_code = normalize_ozon_store_code(store_code)
    normalized_posting_number = str(posting_number or "").strip()
    cleaned_codes = [str(code or "").strip() for code in codes if str(code or "").strip()]
    if not normalized_posting_number:
        raise HTTPException(400, "Ozon posting_number is required")
    if sku <= 0:
        raise HTTPException(400, "Ozon SKU is required")
    if not cleaned_codes:
        raise HTTPException(400, "At least one digital code is required")
    client_id = _required_store_env("CLIENT_ID", store_code=normalized_store_code)
    api_key = _required_store_env("API_KEY", store_code=normalized_store_code)
    base_url = str(os.getenv("OZON_SELLER_BASE_URL", OZON_SELLER_BASE_URL) or OZON_SELLER_BASE_URL).rstrip("/")
    timeout = max(5, _env_int("OZON_TIMEOUT_SEC", 60))
    return _request_json(
        f"{base_url}/v1/posting/digital/codes/upload",
        client_id=client_id,
        api_key=api_key,
        payload={
            "posting_number": normalized_posting_number,
            "exemplars_by_sku": [
                {
                    "sku": int(sku),
                    "exemplar_qty": len(cleaned_codes),
                    "not_available_exemplar_qty": 0,
                    "exemplar_keys": cleaned_codes,
                }
            ],
        },
        timeout=timeout,
    )


def aggregate_ozon_finance_transactions(
    rows: list[dict[str, Any]],
    *,
    fallback_date: date,
    store_code: str = "asat",
) -> list[dict[str, Any]]:
    # Сворачиваем операции по дням; формат источника храним отдельно от стабильного ключа записи.
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
                "report_type": row.get("report_type") or "finance_transaction_list_v3",
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
                    "report_type": group["report_type"],
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
