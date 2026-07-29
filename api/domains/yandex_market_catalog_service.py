from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import os
import urllib.parse
from typing import Any

from fastapi import HTTPException

from .yandex_market_service import (
    YANDEX_MARKET_BASE_URL,
    _env_int,
    _env_store_bool,
    _env_store_int,
    _request_json,
    _required_store_env,
    normalize_yandex_market_store_code,
)


logger = logging.getLogger(__name__)


def _include_fake_yandex_market_orders(store_code: str | None = None) -> bool:
    # Включаем тестовые заказы только для явно выбранного кабинета Маркета.
    return _env_store_bool("INCLUDE_FAKE_ORDERS", store_code=store_code, default=False)


def yandex_market_sandbox_orders_enabled(store_code: str | None = None) -> bool:
    # Помечает снимок sandbox только для явно выбранного test-магазина с включенными fake-заказами.
    normalized_store_code = normalize_yandex_market_store_code(store_code)
    return normalized_store_code == "test" and _include_fake_yandex_market_orders(normalized_store_code)


def yandex_market_sandbox_actions_enabled(store_code: str | None = None) -> bool:
    # Разрешает локальную выдачу только после отдельного явного включения sandbox-действий.
    normalized_store_code = normalize_yandex_market_store_code(store_code)
    return yandex_market_sandbox_orders_enabled(normalized_store_code) and _env_store_bool(
        "SANDBOX_ACTIONS_ENABLED", store_code=normalized_store_code, default=False,
    )


def yandex_market_sandbox_market_delivery_enabled(store_code: str | None = None) -> bool:
    # Открывает внешнюю отправку кода только для test-магазина после отдельного явного разрешения.
    normalized_store_code = normalize_yandex_market_store_code(store_code)
    return yandex_market_sandbox_actions_enabled(normalized_store_code) and _env_store_bool(
        "SANDBOX_MARKET_DELIVERY_ENABLED", store_code=normalized_store_code, default=False,
    )


def _catalog_context(store_code: str | None) -> tuple[str, str, int, int, int]:
    # Собирает реквизиты кабинета и магазина до обращения к товарным методам Маркета.
    normalized_store_code = normalize_yandex_market_store_code(store_code)
    token = _required_store_env("TOKEN", store_code=normalized_store_code)
    business_id = _env_store_int("BUSINESS_ID", store_code=normalized_store_code)
    campaign_id = _env_store_int("CAMPAIGN_ID", store_code=normalized_store_code)
    if not business_id or not campaign_id:
        raise HTTPException(
            500,
            f"YANDEX_MARKET_{normalized_store_code.upper()}_BUSINESS_ID and "
            f"YANDEX_MARKET_{normalized_store_code.upper()}_CAMPAIGN_ID are required",
        )
    base_url = str(os.getenv("YANDEX_MARKET_BASE_URL", YANDEX_MARKET_BASE_URL) or YANDEX_MARKET_BASE_URL).rstrip("/")
    timeout = max(5, _env_int("YANDEX_MARKET_TIMEOUT_SEC", 30))
    return normalized_store_code, token, business_id, campaign_id, timeout


def find_yandex_market_store_code_by_campaign_id(campaign_id: int) -> str | None:
    # Находит локальный код магазина по campaignId из уведомления, чтобы читать заказ из нужного кабинета.
    target_campaign_id = int(campaign_id)
    suffix = "_CAMPAIGN_ID"
    scoped_prefix = "YANDEX_MARKET_"
    matched_codes: list[str] = []
    for env_name, env_value in os.environ.items():
        if not env_name.startswith(scoped_prefix) or not env_name.endswith(suffix):
            continue
        store_code = env_name[len(scoped_prefix) : -len(suffix)]
        if not store_code:
            continue
        try:
            configured_campaign_id = int(str(env_value or "").strip())
        except (TypeError, ValueError):
            continue
        if configured_campaign_id == target_campaign_id:
            matched_codes.append(normalize_yandex_market_store_code(store_code))
    if matched_codes:
        return sorted(set(matched_codes))[0]

    # Поддерживает основной магазин без суффикса, который исторически считается ASAT.
    try:
        default_campaign_id = int(str(os.getenv("YANDEX_MARKET_CAMPAIGN_ID", "")).strip())
    except (TypeError, ValueError):
        return None
    return "asat" if default_campaign_id == target_campaign_id else None


def _catalog_url(base_url: str, business_id: int, *, page_token: str = "") -> str:
    # Формирует постраничный адрес каталога без ручной склейки и потери спецсимволов токена страницы.
    query = {"language": "RU", "limit": "100"}
    if page_token:
        query["pageToken"] = page_token
    return f"{base_url}/v2/businesses/{business_id}/offer-mappings?{urllib.parse.urlencode(query)}"


def fetch_yandex_market_catalog_items(store_code: str | None = None) -> list[dict[str, Any]]:
    # Загружает активные и архивные карточки, чтобы интерфейс работал со снимком, а не с внешним API.
    normalized_store_code, token, business_id, campaign_id, timeout = _catalog_context(store_code)
    base_url = str(os.getenv("YANDEX_MARKET_BASE_URL", YANDEX_MARKET_BASE_URL) or YANDEX_MARKET_BASE_URL).rstrip("/")
    max_pages = max(1, _env_int("YANDEX_MARKET_CATALOG_MAX_PAGES", 1000))
    all_items: list[dict[str, Any]] = []

    for archived in (False, True):
        page_token = ""
        for _page in range(max_pages):
            data = _request_json(
                "POST",
                _catalog_url(base_url, business_id, page_token=page_token),
                token=token,
                payload={"archived": archived},
                timeout=timeout,
            )
            result = data.get("result") if isinstance(data.get("result"), dict) else {}
            rows = result.get("offerMappings") if isinstance(result.get("offerMappings"), list) else []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                offer = row.get("offer") if isinstance(row.get("offer"), dict) else {}
                campaigns = offer.get("campaigns") if isinstance(offer.get("campaigns"), list) else []
                campaign_ids = {
                    int(item.get("campaignId"))
                    for item in campaigns
                    if isinstance(item, dict) and str(item.get("campaignId") or "").isdigit()
                }
                # Берем только карточки выбранного DBS-магазина, а не соседнего FBY-канала того же кабинета.
                if campaign_ids and campaign_id not in campaign_ids:
                    continue
                all_items.append(row)
            paging = result.get("paging") if isinstance(result.get("paging"), dict) else {}
            next_page_token = str(paging.get("nextPageToken") or "").strip()
            if not next_page_token:
                break
            if next_page_token == page_token:
                raise HTTPException(502, "Yandex Market catalog pagination did not advance")
            page_token = next_page_token
        else:
            raise HTTPException(502, f"Yandex Market catalog exceeded {max_pages} pages for {normalized_store_code}")
    return all_items


def update_yandex_market_catalog_archive(
    offer_id: str,
    *,
    archived: bool,
    store_code: str | None = None,
) -> dict[str, Any]:
    # Переносит одну карточку в архив или возвращает её, сохраняя неизменный SKU продавца.
    normalized_offer_id = str(offer_id or "").strip()
    if not normalized_offer_id:
        raise HTTPException(400, "Yandex Market offer_id is required")
    _store_code, token, business_id, _campaign_id, timeout = _catalog_context(store_code)
    base_url = str(os.getenv("YANDEX_MARKET_BASE_URL", YANDEX_MARKET_BASE_URL) or YANDEX_MARKET_BASE_URL).rstrip("/")
    action = "archive" if archived else "unarchive"
    return _request_json(
        "POST",
        f"{base_url}/v2/businesses/{business_id}/offer-mappings/{action}",
        token=token,
        payload={"offerIds": [normalized_offer_id]},
        timeout=timeout,
    )


def update_yandex_market_stock(
    offer_id: str,
    stock: int,
    *,
    store_code: str | None = None,
) -> dict[str, Any]:
    # Передает витринный остаток DBS по точному SKU и не затрагивает выдачу цифровых ключей.
    normalized_offer_id = str(offer_id or "").strip()
    if not normalized_offer_id:
        raise HTTPException(400, "Yandex Market offer_id is required for stock")
    if int(stock) < 0:
        raise HTTPException(400, "Yandex Market stock must not be negative")
    _store_code, token, _business_id, campaign_id, timeout = _catalog_context(store_code)
    base_url = str(os.getenv("YANDEX_MARKET_BASE_URL", YANDEX_MARKET_BASE_URL) or YANDEX_MARKET_BASE_URL).rstrip("/")
    updated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return _request_json(
        "PUT",
        f"{base_url}/v2/campaigns/{campaign_id}/offers/stocks",
        token=token,
        payload={"skus": [{"sku": normalized_offer_id, "items": [{"count": int(stock), "updatedAt": updated_at}]}]},
        timeout=timeout,
    )


def deliver_yandex_market_digital_goods(
    order_id: int,
    *,
    item_id: int,
    codes: list[str],
    store_code: str | None = None,
) -> dict[str, Any]:
    # Передает полный комплект ключей одной позиции в test-Маркет по официальному DBS-методу.
    normalized_order_id = int(order_id)
    normalized_item_id = int(item_id)
    prepared_codes = [str(code or "").strip() for code in codes if str(code or "").strip()]
    if normalized_order_id <= 0 or normalized_item_id <= 0 or not prepared_codes:
        raise HTTPException(400, "Yandex Market digital delivery requires an order, item and at least one key")
    if len(prepared_codes) != len(set(prepared_codes)):
        raise HTTPException(400, "Yandex Market digital delivery codes must be unique")
    _store_code, token, _business_id, campaign_id, timeout = _catalog_context(store_code)
    base_url = str(os.getenv("YANDEX_MARKET_BASE_URL", YANDEX_MARKET_BASE_URL) or YANDEX_MARKET_BASE_URL).rstrip("/")
    return _request_json(
        "POST",
        f"{base_url}/v2/campaigns/{campaign_id}/orders/{normalized_order_id}/deliverDigitalGoods",
        token=token,
        payload={
            "items": [{
                "id": normalized_item_id,
                "codes": prepared_codes,
                "slip": "Активируйте код в PlayStation Store.",
                "activate_till": "2099-12-31",
            }],
        },
        timeout=timeout,
    )


def fetch_yandex_market_stock(
    offer_id: str,
    *,
    store_code: str | None = None,
) -> dict[str, Any]:
    # Читает доступный к продаже остаток одного SKU и не меняет данные в кабинете Маркета.
    normalized_offer_id = str(offer_id or "").strip()
    if not normalized_offer_id:
        raise HTTPException(400, "Yandex Market offer_id is required for stock")
    _store_code, token, _business_id, campaign_id, timeout = _catalog_context(store_code)
    base_url = str(os.getenv("YANDEX_MARKET_BASE_URL", YANDEX_MARKET_BASE_URL) or YANDEX_MARKET_BASE_URL).rstrip("/")
    data = _request_json(
        "POST",
        f"{base_url}/v2/campaigns/{campaign_id}/offers/stocks",
        token=token,
        payload={"offerIds": [normalized_offer_id], "withTurnover": False},
        timeout=timeout,
    )
    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    warehouses = result.get("warehouses") if isinstance(result.get("warehouses"), list) else []
    available_stock = 0
    updated_at = ""
    found = False
    for warehouse in warehouses:
        offers = warehouse.get("offers") if isinstance(warehouse, dict) and isinstance(warehouse.get("offers"), list) else []
        for offer in offers:
            if not isinstance(offer, dict) or str(offer.get("offerId") or "").strip() != normalized_offer_id:
                continue
            found = True
            updated_at = max(updated_at, str(offer.get("updatedAt") or "").strip())
            stocks = offer.get("stocks") if isinstance(offer.get("stocks"), list) else []
            for stock in stocks:
                if not isinstance(stock, dict) or str(stock.get("type") or "").upper() != "AVAILABLE":
                    continue
                try:
                    available_stock += max(0, int(stock.get("count") or 0))
                except (TypeError, ValueError):
                    continue
    return {"found": found, "available_stock": available_stock, "updated_at": updated_at}


def fetch_yandex_market_orders(
    store_code: str | None = None,
    *,
    updated_from: datetime | None = None,
) -> dict[str, Any]:
    # Читает новые и измененные заказы DBS без изменения статусов, остатков или выдачи ключей.
    normalized_store_code, token, business_id, campaign_id, timeout = _catalog_context(store_code)
    base_url = str(os.getenv("YANDEX_MARKET_BASE_URL", YANDEX_MARKET_BASE_URL) or YANDEX_MARKET_BASE_URL).rstrip("/")
    # На первом этапе не блокируем интерфейс обходом всей истории кабинета: берем до 250 свежих заказов.
    max_pages = max(1, _env_int("YANDEX_MARKET_ORDERS_MAX_PAGES", 5))
    orders: list[dict[str, Any]] = []
    page_token = ""
    pages_loaded = 0
    has_more = False

    payload: dict[str, Any] = {
        "campaignIds": [campaign_id],
        "programTypes": ["DBS"],
        "fake": _include_fake_yandex_market_orders(normalized_store_code),
    }
    if updated_from:
        # Повторяем последние пять минут, чтобы не потерять обновление, пришедшее на границе двух загрузок.
        checkpoint = updated_from.astimezone(timezone.utc) if updated_from.tzinfo else updated_from.replace(tzinfo=timezone.utc)
        payload["dates"] = {"updateDateFrom": (checkpoint - timedelta(minutes=5)).replace(microsecond=0).isoformat().replace("+00:00", "Z")}

    logger.info(
        "Yandex Market: начинаем чтение новых заказов магазина %s, максимум страниц: %s, от: %s",
        normalized_store_code,
        max_pages,
        payload.get("dates", {}).get("updateDateFrom", "последние 30 дней"),
    )

    for page_number in range(1, max_pages + 1):
        query = {"limit": "50"}
        if page_token:
            query["pageToken"] = page_token
        # Записываем в журнал номер страницы, чтобы было видно, что запрос не завис, а обрабатывает историю.
        logger.info("Yandex Market: запрашиваем страницу заказов %s", page_number)
        data = _request_json(
            "POST",
            f"{base_url}/v1/businesses/{business_id}/orders?{urllib.parse.urlencode(query)}",
            token=token,
            payload=payload,
            timeout=timeout,
        )
        result = data.get("result") if isinstance(data.get("result"), dict) else data
        rows = result.get("orders") if isinstance(result.get("orders"), list) else []
        pages_loaded = page_number
        for row in rows:
            if isinstance(row, dict) and str(row.get("campaignId") or "") == str(campaign_id):
                orders.append(row)
        paging = result.get("paging") if isinstance(result.get("paging"), dict) else {}
        next_page_token = str(paging.get("nextPageToken") or "").strip()
        logger.info(
            "Yandex Market: страница заказов %s получена, записей: %s, всего в снимке: %s",
            page_number,
            len(rows),
            len(orders),
        )
        if not next_page_token:
            break
        if next_page_token == page_token:
            raise HTTPException(502, "Yandex Market orders pagination did not advance")
        if page_number == max_pages:
            # Сохраняем полученную свежую часть истории, а не держим кнопку в ожидании десятков тысяч старых заказов.
            has_more = True
            logger.info("Yandex Market: достигнут лимит страниц, в Маркете есть более ранние заказы")
            break
        page_token = next_page_token
    logger.info(
        "Yandex Market: чтение заказов завершено, страниц: %s, заказов: %s, есть еще: %s",
        pages_loaded,
        len(orders),
        has_more,
    )
    return {"orders": orders, "pages_loaded": pages_loaded, "has_more": has_more}


def fetch_yandex_market_order(order_id: int, *, store_code: str | None = None) -> dict[str, Any]:
    # Запрашивает ровно один заказ для уведомления и не меняет его статус или выдачу в Маркете.
    normalized_order_id = int(order_id)
    normalized_store_code, token, business_id, campaign_id, timeout = _catalog_context(store_code)
    base_url = str(os.getenv("YANDEX_MARKET_BASE_URL", YANDEX_MARKET_BASE_URL) or YANDEX_MARKET_BASE_URL).rstrip("/")
    data = _request_json(
        "POST",
        f"{base_url}/v1/businesses/{business_id}/orders?limit=1",
        token=token,
        payload={
            "campaignIds": [campaign_id],
            "orderIds": [normalized_order_id],
            "programTypes": ["DBS"],
            "fake": _include_fake_yandex_market_orders(normalized_store_code),
        },
        timeout=timeout,
    )
    result = data.get("result") if isinstance(data.get("result"), dict) else data
    rows = result.get("orders") if isinstance(result, dict) and isinstance(result.get("orders"), list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_order_id = row.get("orderId", row.get("id"))
        if str(row_order_id or "") == str(normalized_order_id) and str(row.get("campaignId") or "") == str(campaign_id):
            return row
    raise HTTPException(404, f"Yandex Market order {normalized_order_id} was not found for {normalized_store_code}")
