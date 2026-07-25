from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import json

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .yandex_market_catalog_service import (
    fetch_yandex_market_catalog_items,
    fetch_yandex_market_orders,
    fetch_yandex_market_stock,
    normalize_yandex_market_store_code,
    update_yandex_market_catalog_archive,
    update_yandex_market_stock,
)


class YandexMarketCatalogItemOut(BaseModel):
    offer_id: str
    market_sku: str = ""
    title: str = ""
    archived: bool = False
    card_status: str = ""
    category_name: str = ""
    downloadable: bool = False
    price: str = ""
    currency_code: str = ""
    synced_at: datetime


class YandexMarketCatalogListOut(BaseModel):
    store_code: str
    items: list[YandexMarketCatalogItemOut] = Field(default_factory=list)


class YandexMarketCatalogSyncOut(BaseModel):
    store_code: str
    synced_items: int
    synced_at: datetime


class YandexMarketCatalogArchiveOut(BaseModel):
    offer_id: str
    archived: bool


class YandexMarketCatalogDetailsOut(YandexMarketCatalogItemOut):
    market_category_id: int | None = None
    primary_image: str = ""
    vendor: str = ""
    showcase_url: str = ""


class YandexMarketStockSettingsIn(BaseModel):
    manual_stock_limit: int = Field(default=0, ge=0, le=100000)


class YandexMarketStockSettingsOut(YandexMarketStockSettingsIn):
    offer_id: str
    published_stock: int = 0
    last_stock_sync_at: datetime | None = None
    market_available_stock: int | None = None
    market_stock_updated_at: datetime | None = None


class YandexMarketOrderOut(BaseModel):
    order_id: int
    item_id: int
    offer_id: str
    item_name: str = ""
    quantity: int = 0
    status: str = ""
    substatus: str = ""
    price: str = ""
    currency_code: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class YandexMarketOrdersOut(BaseModel):
    offer_id: str
    items: list[YandexMarketOrderOut] = Field(default_factory=list)


class YandexMarketOrdersSyncOut(BaseModel):
    imported_orders: int
    synced_at: datetime
    pages_loaded: int = 0
    has_more: bool = False
    updated_from: datetime | None = None


def mount_yandex_market_catalog_routes(
    app,
    *,
    DB_DSN,
    psycopg,
    q1,
    qall,
    exec1,
    require_role,
    yandex_market_live_enabled: bool = True,
):
    def require_yandex_market_live() -> None:
        # Не дает тестовому или подготовительному контуру изменить кабинет Маркета внешним запросом.
        if not yandex_market_live_enabled:
            raise HTTPException(503, "Интеграция Yandex Market отключена для этого окружения")

    def first_text(*values: Any) -> str:
        # Возвращает первое непустое текстовое поле из отличающихся версий ответа Маркета.
        for value in values:
            text = str(value or "").strip()
            if text:
                return text
        return ""

    def optional_int(value: Any) -> int | None:
        # Приводит идентификатор к числу, не подменяя отсутствующее значение нулем в карточке.
        try:
            result = int(value)
        except (TypeError, ValueError):
            return None
        return result if result > 0 else None

    def read_payload(value: Any) -> dict[str, Any]:
        # Приводит jsonb снимка к словарю, чтобы старые драйверы не влияли на ответы API.
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}

    def optional_datetime(value: Any) -> datetime | None:
        # Разбирает дату Маркета, не превращая неизвестный формат в ошибку синхронизации заказов.
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None

    def nonnegative_int(value: Any) -> int:
        # Приводит количество позиции к безопасному неотрицательному числу для списка заказов.
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0

    def normalize_catalog_item(item: dict[str, Any]) -> tuple[str, int | None, str, bool, str, str, dict[str, Any]]:
        # Выделяет из ответа Маркета поля для быстрого списка и сохраняет полный снимок для деталей.
        offer = item.get("offer") if isinstance(item.get("offer"), dict) else {}
        mapping = item.get("mapping") if isinstance(item.get("mapping"), dict) else {}
        offer_id = first_text(offer.get("offerId"), item.get("offerId"))
        if not offer_id:
            raise HTTPException(502, "Yandex Market catalog item does not contain offerId")
        market_sku = optional_int(mapping.get("marketSku"))
        title = first_text(offer.get("name"), mapping.get("marketSkuName"))
        archived = bool(offer.get("archived"))
        card_status = first_text(offer.get("cardStatus"))
        category_name = first_text(mapping.get("marketCategoryName"), offer.get("category"))
        return offer_id, market_sku, title, archived, card_status, category_name, item

    def make_catalog_item_out(row: tuple[Any, ...]) -> YandexMarketCatalogItemOut:
        # Формирует компактную карточку из сохраненного снимка без обращения к внешнему API.
        return YandexMarketCatalogItemOut(
            offer_id=str(row[0]),
            market_sku=str(row[1] or ""),
            title=str(row[2] or ""),
            archived=bool(row[3]),
            card_status=str(row[4] or ""),
            category_name=str(row[5] or ""),
            downloadable=bool(row[6]),
            price=str(row[7] or ""),
            currency_code=str(row[8] or ""),
            synced_at=row[9],
        )

    def make_order_out(row: tuple[Any, ...]) -> YandexMarketOrderOut:
        # Отдает только операционные поля заказа, не раскрывая покупателя и адрес доставки в интерфейсе.
        return YandexMarketOrderOut(
            order_id=int(row[0]),
            item_id=int(row[1]),
            offer_id=str(row[2]),
            item_name=str(row[3] or ""),
            quantity=nonnegative_int(row[4]),
            status=str(row[5] or ""),
            substatus=str(row[6] or ""),
            price=str(row[7] or ""),
            currency_code=str(row[8] or ""),
            created_at=row[9],
            updated_at=row[10],
        )

    def sync_yandex_market_orders(store_code: str) -> YandexMarketOrdersSyncOut:
        # Сохраняет только новые или измененные заказы локально и не вызывает методы выдачи или изменения статуса.
        with psycopg.connect(DB_DSN) as conn:
            checkpoint_row = q1(
                conn,
                "SELECT last_checked_at FROM app.marketplace_yandex_order_sync_state WHERE store_code=%s",
                (store_code,),
            )
        updated_from = optional_datetime(checkpoint_row[0]) if checkpoint_row else None
        # Фиксируем начало чтения, чтобы следующая загрузка с запасом подобрала изменения, пришедшие во время запроса.
        sync_started_at = datetime.now(timezone.utc)
        remote_snapshot = fetch_yandex_market_orders(store_code=store_code, updated_from=updated_from)
        remote_orders = remote_snapshot.get("orders") if isinstance(remote_snapshot, dict) else []
        synced_at = datetime.now(timezone.utc)
        imported_orders = 0
        with psycopg.connect(DB_DSN) as conn:
            for order in remote_orders:
                order_id = optional_int(order.get("orderId"))
                campaign_id = optional_int(order.get("campaignId"))
                if not order_id or not campaign_id:
                    continue
                items = order.get("items") if isinstance(order.get("items"), list) else []
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    item_id = optional_int(item.get("id"))
                    offer_id = first_text(item.get("offerId"))
                    if not item_id or not offer_id:
                        continue
                    prices = item.get("prices") if isinstance(item.get("prices"), dict) else {}
                    payment = prices.get("payment") if isinstance(prices.get("payment"), dict) else {}
                    exec1(
                        conn,
                        """
                        INSERT INTO app.marketplace_yandex_order_items(
                          store_code, order_id, item_id, campaign_id, offer_id, item_name, quantity,
                          status, substatus, price, currency_code, created_at, updated_at, synced_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (store_code, order_id, item_id) DO UPDATE
                        SET campaign_id=excluded.campaign_id,
                            offer_id=excluded.offer_id,
                            item_name=excluded.item_name,
                            quantity=excluded.quantity,
                            status=excluded.status,
                            substatus=excluded.substatus,
                            price=excluded.price,
                            currency_code=excluded.currency_code,
                            created_at=excluded.created_at,
                            updated_at=excluded.updated_at,
                            synced_at=excluded.synced_at
                        """,
                        (
                            store_code,
                            order_id,
                            item_id,
                            campaign_id,
                            offer_id,
                            first_text(item.get("offerName")),
                            nonnegative_int(item.get("count")),
                            first_text(order.get("status")),
                            first_text(order.get("substatus")),
                            first_text(payment.get("value")),
                            first_text(payment.get("currencyId")),
                            optional_datetime(order.get("creationDate")),
                            optional_datetime(order.get("updateDate")),
                            synced_at,
                        ),
                    )
                    imported_orders += 1
            # Храним отдельную отметку даже при нулевом результате, чтобы не перечитывать последние 30 дней снова.
            exec1(
                conn,
                """
                INSERT INTO app.marketplace_yandex_order_sync_state(store_code, last_checked_at, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (store_code) DO UPDATE
                SET last_checked_at=excluded.last_checked_at,
                    updated_at=excluded.updated_at
                """,
                (store_code, sync_started_at, synced_at),
            )
            conn.commit()
        return YandexMarketOrdersSyncOut(
            imported_orders=imported_orders,
            synced_at=synced_at,
            pages_loaded=nonnegative_int(remote_snapshot.get("pages_loaded")) if isinstance(remote_snapshot, dict) else 0,
            has_more=bool(remote_snapshot.get("has_more")) if isinstance(remote_snapshot, dict) else False,
            updated_from=updated_from,
        )

    def make_stock_settings_out(conn, store_code: str, offer_id: str) -> YandexMarketStockSettingsOut:
        # Возвращает локальный лимит и последнюю публикацию, не считая остатки из будущей очереди заказов.
        row = q1(
            conn,
            """
            SELECT manual_stock_limit, published_stock, last_stock_sync_at
            FROM app.marketplace_yandex_stock_settings
            WHERE store_code=%s AND offer_id=%s
            """,
            (store_code, offer_id),
        )
        if not row:
            return YandexMarketStockSettingsOut(offer_id=offer_id)
        return YandexMarketStockSettingsOut(
            offer_id=offer_id,
            manual_stock_limit=max(0, int(row[0] or 0)),
            published_stock=max(0, int(row[1] or 0)),
            last_stock_sync_at=row[2],
        )

    @app.post("/marketplaces/yandex/catalog/sync", response_model=YandexMarketCatalogSyncOut)
    def sync_yandex_market_catalog(store_code: str = "asat", user=Depends(require_role("owner"))):
        # Читает каталог кабинета и обновляет локальный снимок без изменения цен, ключей или заказов.
        require_yandex_market_live()
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        synced_at = datetime.now(timezone.utc)
        remote_items = fetch_yandex_market_catalog_items(store_code=normalized_store_code)
        normalized_items = [normalize_catalog_item(item) for item in remote_items]
        with psycopg.connect(DB_DSN) as conn:
            for offer_id, market_sku, title, archived, card_status, category_name, raw_payload in normalized_items:
                offer = raw_payload.get("offer") if isinstance(raw_payload.get("offer"), dict) else {}
                price = offer.get("basicPrice") if isinstance(offer.get("basicPrice"), dict) else {}
                exec1(
                    conn,
                    """
                    INSERT INTO app.marketplace_yandex_catalog_items(
                      store_code, offer_id, market_sku, title, archived, card_status, category_name,
                      downloadable, price, currency_code, raw_payload, synced_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (store_code, offer_id) DO UPDATE
                    SET market_sku=excluded.market_sku,
                        title=excluded.title,
                        archived=excluded.archived,
                        card_status=excluded.card_status,
                        category_name=excluded.category_name,
                        downloadable=excluded.downloadable,
                        price=excluded.price,
                        currency_code=excluded.currency_code,
                        raw_payload=excluded.raw_payload,
                        synced_at=excluded.synced_at
                    """,
                    (
                        normalized_store_code,
                        offer_id,
                        market_sku,
                        title,
                        archived,
                        card_status,
                        category_name,
                        bool(offer.get("downloadable")),
                        first_text(price.get("value")),
                        first_text(price.get("currencyId")),
                        json.dumps(raw_payload, ensure_ascii=False),
                        synced_at,
                    ),
                )
            conn.commit()
        return YandexMarketCatalogSyncOut(store_code=normalized_store_code, synced_items=len(normalized_items), synced_at=synced_at)

    @app.get("/marketplaces/yandex/catalog", response_model=YandexMarketCatalogListOut)
    def list_yandex_market_catalog(store_code: str = "asat", user=Depends(require_role("owner"))):
        # Отдает сохраненный снимок, чтобы открытие окна не зависело от доступности кабинета Маркета.
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                """
                SELECT offer_id, market_sku, title, archived, card_status, category_name,
                       downloadable, price, currency_code, synced_at
                FROM app.marketplace_yandex_catalog_items
                WHERE store_code=%s
                ORDER BY archived ASC, title ASC, offer_id ASC
                """,
                (normalized_store_code,),
            )
        return YandexMarketCatalogListOut(store_code=normalized_store_code, items=[make_catalog_item_out(row) for row in rows])

    @app.get("/marketplaces/yandex/catalog/{offer_id}", response_model=YandexMarketCatalogDetailsOut)
    def get_yandex_market_catalog_details(offer_id: str, store_code: str = "asat", user=Depends(require_role("owner"))):
        # Показывает полезные детали локальной карточки и не раскрывает сырой ответ Маркета браузеру.
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                """
                SELECT offer_id, market_sku, title, archived, card_status, category_name,
                       downloadable, price, currency_code, raw_payload, synced_at
                FROM app.marketplace_yandex_catalog_items
                WHERE store_code=%s AND offer_id=%s
                """,
                (normalized_store_code, offer_id),
            )
        if not row:
            raise HTTPException(404, "Карточка Yandex Market не найдена в сохраненном каталоге")
        payload = read_payload(row[9])
        offer = payload.get("offer") if isinstance(payload.get("offer"), dict) else {}
        mapping = payload.get("mapping") if isinstance(payload.get("mapping"), dict) else {}
        pictures = offer.get("pictures") if isinstance(offer.get("pictures"), list) else []
        showcase_urls = payload.get("showcaseUrls") if isinstance(payload.get("showcaseUrls"), list) else []
        showcase_url = ""
        for item in showcase_urls:
            if isinstance(item, dict) and first_text(item.get("showcaseUrl")):
                showcase_url = first_text(item.get("showcaseUrl"))
                break
        return YandexMarketCatalogDetailsOut(
            **make_catalog_item_out((*row[:9], row[10])).model_dump(),
            market_category_id=optional_int(mapping.get("marketCategoryId") or offer.get("marketCategoryId")),
            primary_image=first_text(*pictures),
            vendor=first_text(offer.get("vendor")),
            showcase_url=showcase_url,
        )

    @app.post("/marketplaces/yandex/catalog/{offer_id}/archive", response_model=YandexMarketCatalogArchiveOut)
    @app.post("/marketplaces/yandex/catalog/{offer_id}/unarchive", response_model=YandexMarketCatalogArchiveOut)
    def update_yandex_market_catalog_archive_route(
        offer_id: str,
        request: Request,
        store_code: str = "asat",
        user=Depends(require_role("owner")),
    ):
        # Передает изменение архива в Маркет и сразу синхронизирует признак в нашем снимке.
        require_yandex_market_live()
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        # Определяем действие по пути, потому что один обработчик обслуживает архив и восстановление.
        archived = request.url.path.endswith("/archive")
        update_yandex_market_catalog_archive(offer_id, archived=archived, store_code=normalized_store_code)
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                UPDATE app.marketplace_yandex_catalog_items
                SET archived=%s, synced_at=now()
                WHERE store_code=%s AND offer_id=%s
                """,
                (archived, normalized_store_code, offer_id),
            )
            conn.commit()
        return YandexMarketCatalogArchiveOut(offer_id=offer_id, archived=archived)

    @app.get("/marketplaces/yandex/catalog/{offer_id}/orders", response_model=YandexMarketOrdersOut)
    def list_yandex_market_orders(offer_id: str, store_code: str = "asat", user=Depends(require_role("owner"))):
        # Показывает уже сохраненную историю позиции без обращения к внешнему API при открытии раздела.
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                """
                SELECT order_id, item_id, offer_id, item_name, quantity, status, substatus,
                       price, currency_code, created_at, updated_at
                FROM app.marketplace_yandex_order_items
                WHERE store_code=%s AND offer_id=%s
                ORDER BY created_at DESC NULLS LAST, order_id DESC, item_id DESC
                """,
                (normalized_store_code, offer_id),
            )
        return YandexMarketOrdersOut(offer_id=offer_id, items=[make_order_out(row) for row in rows])

    @app.post("/marketplaces/yandex/catalog/{offer_id}/orders/sync", response_model=YandexMarketOrdersSyncOut)
    def sync_yandex_market_orders_for_catalog_item(offer_id: str, store_code: str = "asat", user=Depends(require_role("owner"))):
        # Обновляет общий снимок заказов DBS вручную; offer_id нужен интерфейсу и не меняет данные Маркета.
        require_yandex_market_live()
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        return sync_yandex_market_orders(normalized_store_code)

    @app.get("/marketplaces/yandex/catalog/{offer_id}/stock-settings", response_model=YandexMarketStockSettingsOut)
    def get_yandex_market_stock_settings(offer_id: str, store_code: str = "asat", user=Depends(require_role("owner"))):
        # Совмещает локальный лимит с безопасным чтением текущего доступного остатка из Маркета.
        require_yandex_market_live()
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        market_stock = fetch_yandex_market_stock(offer_id, store_code=normalized_store_code)
        with psycopg.connect(DB_DSN) as conn:
            settings = make_stock_settings_out(conn, normalized_store_code, offer_id)
        if not market_stock["found"]:
            return settings
        updated_at = str(market_stock.get("updated_at") or "").strip()
        try:
            market_stock_updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00")) if updated_at else None
        except ValueError:
            market_stock_updated_at = None
        return settings.model_copy(update={
            "market_available_stock": int(market_stock["available_stock"]),
            "market_stock_updated_at": market_stock_updated_at,
        })

    @app.put("/marketplaces/yandex/catalog/{offer_id}/stock-settings", response_model=YandexMarketStockSettingsOut)
    def save_yandex_market_stock_settings(
        offer_id: str,
        payload: YandexMarketStockSettingsIn,
        publish_stock: bool = False,
        store_code: str = "asat",
        user=Depends(require_role("owner")),
    ):
        # Сохраняет лимит отдельно и публикует его только по явной команде оператора.
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                INSERT INTO app.marketplace_yandex_stock_settings(store_code, offer_id, manual_stock_limit, updated_at)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (store_code, offer_id) DO UPDATE
                SET manual_stock_limit=excluded.manual_stock_limit, updated_at=now()
                """,
                (normalized_store_code, offer_id, payload.manual_stock_limit),
            )
            conn.commit()
        if publish_stock:
            require_yandex_market_live()
            update_yandex_market_stock(offer_id, payload.manual_stock_limit, store_code=normalized_store_code)
            with psycopg.connect(DB_DSN) as conn:
                exec1(
                    conn,
                    """
                    UPDATE app.marketplace_yandex_stock_settings
                    SET published_stock=%s, last_stock_sync_at=now(), updated_at=now()
                    WHERE store_code=%s AND offer_id=%s
                    """,
                    (payload.manual_stock_limit, normalized_store_code, offer_id),
                )
                result = make_stock_settings_out(conn, normalized_store_code, offer_id)
                conn.commit()
                return result
        with psycopg.connect(DB_DSN) as conn:
            return make_stock_settings_out(conn, normalized_store_code, offer_id)
