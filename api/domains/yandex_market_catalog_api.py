from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
from typing import Any
import json
import os

from fastapi import Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .yandex_market_catalog_service import (
    fetch_yandex_market_catalog_items,
    deliver_yandex_market_digital_goods,
    fetch_yandex_market_orders,
    fetch_yandex_market_stock,
    normalize_yandex_market_store_code,
    yandex_market_sandbox_actions_enabled,
    yandex_market_sandbox_market_delivery_enabled,
    yandex_market_sandbox_orders_enabled,
    update_yandex_market_catalog_archive,
    update_yandex_market_stock,
)
from .yandex_market_order_storage import save_yandex_market_order_snapshot
from .yandex_market_sales_limit import YandexMarketSalesLimitManager


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
    sales_limit: int | None = Field(default=None, ge=1, le=1000000)
    activation_instruction: str = Field(default="", max_length=5000)
    support_error_message: str = Field(default="", max_length=2000)
    auto_issue_enabled: bool = False
    pool_issue_enabled: bool = False
    support_message_delivery_enabled: bool = False
    interhub_service_id: int | None = Field(default=None, gt=0)
    interhub_nominal_id: str = Field(default="", max_length=255)
    interhub_enabled: bool = False


class YandexMarketStockSettingsOut(YandexMarketStockSettingsIn):
    offer_id: str
    published_stock: int = 0
    last_stock_sync_at: datetime | None = None
    market_available_stock: int | None = None
    market_stock_updated_at: datetime | None = None
    sales_limit_used: int = 0
    sales_limit_reserved: int = 0
    sales_limit_remaining: int | None = None
    sales_limit_daily_extra: int = 0
    sales_limit_effective: int | None = None
    sales_limit_day: date | None = None
    archived_by_sales_limit: bool = False
    sales_limit_exhausted_at: datetime | None = None


class YandexMarketDailyLimitAdditionIn(BaseModel):
    units: int = Field(ge=1, le=1000000)


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
    sandbox_delivery_status: str = ""


class YandexMarketOrdersOut(BaseModel):
    offer_id: str
    items: list[YandexMarketOrderOut] = Field(default_factory=list)


class YandexMarketOrdersSyncOut(BaseModel):
    imported_orders: int
    synced_at: datetime
    pages_loaded: int = 0
    has_more: bool = False
    updated_from: datetime | None = None


class YandexMarketSandboxDeliveryIn(BaseModel):
    codes: list[str] = Field(min_length=1, max_length=100)


class YandexMarketSandboxDeliveryOut(BaseModel):
    order_id: int
    item_id: int
    offer_id: str
    issued_qty: int
    delivery_source: str
    status: str


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
    sales_limit_manager=None,
):
    if sales_limit_manager is None:
        # Использует единый расчет лимита и для ручной кнопки, и для production-выдачи.
        sales_limit_manager = YandexMarketSalesLimitManager(
            DB_DSN=DB_DSN,
            psycopg=psycopg,
            q1=q1,
            qall=qall,
            exec1=exec1,
            update_stock=lambda offer_id, stock, *, store_code: update_yandex_market_stock(
                offer_id, stock, store_code=store_code,
            ),
            update_archive=lambda offer_id, *, archived, store_code: update_yandex_market_catalog_archive(
                offer_id, archived=archived, store_code=store_code,
            ),
        )

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
            sandbox_delivery_status=str(row[11] or "") if len(row) > 11 else "",
        )

    def sandbox_pool_secret() -> str:
        # Использует тот же отдельный секрет пула, чтобы ручной код не хранился открытым даже в sandbox.
        secret = str(os.getenv("MARKETPLACE_KEY_POOL_SECRET", "")).strip()
        if len(secret) < 32:
            raise HTTPException(503, "Для sandbox-выдачи задайте MARKETPLACE_KEY_POOL_SECRET длиной не менее 32 символов")
        return secret

    def sandbox_code_hash(code: str) -> str:
        # Создает тот же отпечаток, что и общий пул: вручную введенный код нельзя потом загрузить повторно.
        return sha256(f"marketplace-manual-key:v1:{code}".encode("utf-8")).hexdigest()

    def sandbox_order_ref(store_code: str, order_id: int, item_id: int) -> str:
        # Связывает ключ с одной позицией fake-заказа и не смешивает одинаковые номера разных магазинов.
        return f"yandex-sandbox:{store_code}:{order_id}:{item_id}"

    def require_yandex_market_sandbox(store_code: str) -> None:
        # Останавливает локальную выдачу вне test-магазина до любых изменений в базе и без внешнего запроса.
        if not yandex_market_sandbox_actions_enabled(store_code):
            raise HTTPException(403, "Локальная выдача доступна только для fake-заказов test-магазина при включенном sandbox-флаге")

    def require_yandex_market_sandbox_market_delivery(store_code: str) -> None:
        # Не дает отправить ключ во внешний API без отдельного флага именно для test-кабинета.
        if not yandex_market_sandbox_market_delivery_enabled(store_code):
            raise HTTPException(403, "Передача ключа в test-Маркет выключена отдельным sandbox-флагом")

    def sandbox_order_for_delivery(conn, store_code: str, order_id: int, item_id: int):
        # Блокирует одну сохраненную fake-позицию, чтобы две вкладки не выдали ей разные ключи.
        row = q1(
            conn,
            """
            SELECT offer_id, quantity, status, is_sandbox
            FROM app.marketplace_yandex_order_items
            WHERE store_code=%s AND order_id=%s AND item_id=%s
            FOR UPDATE
            """,
            (store_code, order_id, item_id),
        )
        if not row:
            raise HTTPException(404, "Fake-заказ Яндекс Маркета не найден в локальном снимке")
        if not bool(row[3]):
            raise HTTPException(409, "Локально можно выдавать ключи только сохраненным fake-заказам")
        if str(row[2] or "").upper() in {"CANCELLED", "DELIVERED"}:
            raise HTTPException(409, "Для отмененного или завершенного fake-заказа ключ не выдается")
        required_qty = nonnegative_int(row[1])
        if required_qty <= 0:
            raise HTTPException(409, "У fake-заказа не указано положительное количество ключей")
        existing = q1(
            conn,
            """
            SELECT status FROM app.marketplace_yandex_sandbox_deliveries
            WHERE store_code=%s AND order_id=%s AND item_id=%s
            FOR UPDATE
            """,
            (store_code, order_id, item_id),
        )
        if existing:
            raise HTTPException(409, "Ключи для этой позиции fake-заказа уже локально зафиксированы")
        return str(row[0]), required_qty

    def finalize_sandbox_delivery(conn, *, store_code: str, order_id: int, item_id: int, offer_id: str, required_qty: int, source: str) -> YandexMarketSandboxDeliveryOut:
        # Фиксирует только локальный результат; этот блок не вызывает API Маркета и не меняет статус заказа в кабинете.
        exec1(
            conn,
            """
            INSERT INTO app.marketplace_yandex_sandbox_deliveries(
              store_code, order_id, item_id, offer_id, required_qty, delivery_source, status, issued_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'locally_issued', now(), now())
            """,
            (store_code, order_id, item_id, offer_id, required_qty, source),
        )
        return YandexMarketSandboxDeliveryOut(
            order_id=order_id,
            item_id=item_id,
            offer_id=offer_id,
            issued_qty=required_qty,
            delivery_source=source,
            status="locally_issued",
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
        # Используем единое сохранение и для ручной загрузки, и для заказа из уведомления Маркета.
        imported_orders = save_yandex_market_order_snapshot(
            DB_DSN=DB_DSN,
            psycopg=psycopg,
            exec1=exec1,
            store_code=store_code,
            orders=remote_orders if isinstance(remote_orders, list) else [],
            is_sandbox=yandex_market_sandbox_orders_enabled(store_code),
            synced_at=synced_at,
        )
        with psycopg.connect(DB_DSN) as conn:
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
        # Возвращает локальные настройки вместе с проданными, зарезервированными и оставшимися единицами лимита.
        sales_state = sales_limit_manager.read_state(conn, store_code, offer_id)
        row = q1(
            conn,
            """
            SELECT manual_stock_limit, activation_instruction, support_error_message, auto_issue_enabled,
                   pool_issue_enabled, support_message_delivery_enabled, published_stock, last_stock_sync_at,
                   (SELECT service_id FROM app.marketplace_yandex_digital_suppliers supplier WHERE supplier.store_code=settings.store_code AND supplier.offer_id=settings.offer_id AND supplier.provider_code='interhub' AND supplier.priority=1),
                   (SELECT nominal_id FROM app.marketplace_yandex_digital_suppliers supplier WHERE supplier.store_code=settings.store_code AND supplier.offer_id=settings.offer_id AND supplier.provider_code='interhub' AND supplier.priority=1),
                   COALESCE((SELECT enabled FROM app.marketplace_yandex_digital_suppliers supplier WHERE supplier.store_code=settings.store_code AND supplier.offer_id=settings.offer_id AND supplier.provider_code='interhub' AND supplier.priority=1), false)
            FROM app.marketplace_yandex_stock_settings
            AS settings
            WHERE store_code=%s AND offer_id=%s
            """,
            (store_code, offer_id),
        )
        if not row:
            return YandexMarketStockSettingsOut(offer_id=offer_id, **{
                key: sales_state[key]
                for key in (
                    "sales_limit", "sales_limit_used", "sales_limit_reserved", "sales_limit_remaining",
                    "sales_limit_daily_extra", "sales_limit_effective", "sales_limit_day",
                    "archived_by_sales_limit", "sales_limit_exhausted_at",
                )
            })
        return YandexMarketStockSettingsOut(
            offer_id=offer_id,
            manual_stock_limit=max(0, int(row[0] or 0)),
            activation_instruction=str(row[1] or ""), support_error_message=str(row[2] or ""),
            auto_issue_enabled=bool(row[3]), pool_issue_enabled=bool(row[4]), support_message_delivery_enabled=bool(row[5]),
            published_stock=max(0, int(row[6] or 0)), last_stock_sync_at=row[7],
            interhub_service_id=int(row[8]) if len(row) > 8 and row[8] else None,
            interhub_nominal_id=str(row[9] or "") if len(row) > 9 else "",
            interhub_enabled=bool(row[10]) if len(row) > 10 else False,
            sales_limit=sales_state["sales_limit"],
            sales_limit_used=sales_state["sales_limit_used"],
            sales_limit_reserved=sales_state["sales_limit_reserved"],
            sales_limit_remaining=sales_state["sales_limit_remaining"],
            sales_limit_daily_extra=sales_state["sales_limit_daily_extra"],
            sales_limit_effective=sales_state["sales_limit_effective"],
            sales_limit_day=sales_state["sales_limit_day"],
            archived_by_sales_limit=sales_state["archived_by_sales_limit"],
            sales_limit_exhausted_at=sales_state["sales_limit_exhausted_at"],
        )

    @app.post("/marketplaces/yandex/catalog/sync", response_model=YandexMarketCatalogSyncOut)
    def sync_yandex_market_catalog(
        store_code: str = Query(..., min_length=1, max_length=64),
        user=Depends(require_role("owner")),
    ):
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
    def list_yandex_market_catalog(
        store_code: str = Query(..., min_length=1, max_length=64),
        user=Depends(require_role("owner")),
    ):
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
    def get_yandex_market_catalog_details(
        offer_id: str,
        store_code: str = Query(..., min_length=1, max_length=64),
        user=Depends(require_role("owner")),
    ):
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
        store_code: str = Query(..., min_length=1, max_length=64),
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
            exec1(
                conn,
                """
                UPDATE app.marketplace_yandex_stock_settings
                SET archived_by_sales_limit=false, updated_at=now()
                WHERE store_code=%s AND offer_id=%s
                """,
                (normalized_store_code, offer_id),
            )
            conn.commit()
        return YandexMarketCatalogArchiveOut(offer_id=offer_id, archived=archived)

    @app.get("/marketplaces/yandex/catalog/{offer_id}/orders", response_model=YandexMarketOrdersOut)
    def list_yandex_market_orders(
        offer_id: str,
        store_code: str = Query(..., min_length=1, max_length=64),
        user=Depends(require_role("owner")),
    ):
        # Показывает уже сохраненную историю позиции без обращения к внешнему API при открытии раздела.
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                """
                SELECT orders.order_id, orders.item_id, orders.offer_id, orders.item_name, orders.quantity, orders.status, orders.substatus,
                       orders.price, orders.currency_code, orders.created_at, orders.updated_at, COALESCE(deliveries.status, '')
                FROM app.marketplace_yandex_order_items AS orders
                LEFT JOIN app.marketplace_yandex_sandbox_deliveries AS deliveries
                  ON deliveries.store_code=orders.store_code
                 AND deliveries.order_id=orders.order_id
                 AND deliveries.item_id=orders.item_id
                WHERE orders.store_code=%s AND orders.offer_id=%s
                ORDER BY orders.created_at DESC NULLS LAST, orders.order_id DESC, orders.item_id DESC
                """,
                (normalized_store_code, offer_id),
            )
        return YandexMarketOrdersOut(offer_id=offer_id, items=[make_order_out(row) for row in rows])

    @app.post("/marketplaces/yandex/catalog/{offer_id}/orders/sync", response_model=YandexMarketOrdersSyncOut)
    def sync_yandex_market_orders_for_catalog_item(
        offer_id: str,
        store_code: str = Query(..., min_length=1, max_length=64),
        user=Depends(require_role("owner")),
    ):
        # Обновляет общий снимок заказов DBS вручную; offer_id нужен интерфейсу и не меняет данные Маркета.
        require_yandex_market_live()
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        return sync_yandex_market_orders(normalized_store_code)

    @app.post(
        "/marketplaces/yandex/sandbox/orders/{order_id}/items/{item_id}/deliver",
        response_model=YandexMarketSandboxDeliveryOut,
    )
    def deliver_yandex_market_sandbox_order_manually(
        order_id: int,
        item_id: int,
        payload: YandexMarketSandboxDeliveryIn,
        store_code: str = "test",
        user=Depends(require_role("owner")),
    ):
        # Шифрует ручные коды и фиксирует их только в локальном sandbox, не отправляя их в Маркет.
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        require_yandex_market_sandbox(normalized_store_code)
        prepared_codes: list[str] = []
        seen_codes: set[str] = set()
        for raw_code in payload.codes:
            code = str(raw_code or "").strip()
            if not code or len(code) > 1024:
                raise HTTPException(400, "Каждый ручной ключ должен быть непустым и короче 1025 символов")
            if code in seen_codes:
                raise HTTPException(400, "Один и тот же ручной ключ нельзя указать дважды")
            seen_codes.add(code)
            prepared_codes.append(code)
        secret = sandbox_pool_secret()
        order_ref = sandbox_order_ref(normalized_store_code, order_id, item_id)
        with psycopg.connect(DB_DSN) as conn:
            offer_id, required_qty = sandbox_order_for_delivery(conn, normalized_store_code, order_id, item_id)
            if len(prepared_codes) != required_qty:
                raise HTTPException(400, f"Для этой позиции нужно ключей: {required_qty}")
            pool = q1(
                conn,
                """
                INSERT INTO app.marketplace_manual_key_pools(marketplace, store_code, product_key)
                VALUES ('yandex_market', %s, %s)
                ON CONFLICT (marketplace, store_code, product_key)
                DO UPDATE SET updated_at=now()
                RETURNING id
                """,
                (normalized_store_code, offer_id),
            )
            pool_id = int(pool[0])
            existing_keys: list[tuple[int, str]] = []
            for code in prepared_codes:
                existing = q1(
                    conn,
                    """
                    SELECT id, pool_id, status, expires_at
                    FROM app.marketplace_manual_keys
                    WHERE code_hash=%s
                    FOR UPDATE
                    """,
                    (sandbox_code_hash(code),),
                )
                if not existing:
                    continue
                if int(existing[1]) != pool_id:
                    raise HTTPException(409, "Ручной ключ уже находится в другом пуле и не может быть выдан повторно")
                if str(existing[2] or "") != "free":
                    raise HTTPException(409, "Ручной ключ уже зарезервирован или выдан")
                if existing[3] is not None and existing[3] < datetime.now(timezone.utc).date():
                    raise HTTPException(409, "Ручной ключ уже истек и не может быть выдан")
                existing_keys.append((int(existing[0]), code))
            for key_id, _code in existing_keys:
                exec1(
                    conn,
                    """
                    UPDATE app.marketplace_manual_keys
                    SET status='delivered', issued_order_ref=%s, issued_at=now(), updated_at=now()
                    WHERE id=%s AND status='free'
                    """,
                    (order_ref, key_id),
                )
            existing_code_ids = {code for _key_id, code in existing_keys}
            for code in prepared_codes:
                if code in existing_code_ids:
                    continue
                exec1(
                    conn,
                    """
                    INSERT INTO app.marketplace_manual_keys(
                      pool_id, code_ciphertext, code_hash, code_suffix, status, issued_order_ref, issued_at
                    )
                    VALUES (%s, pgp_sym_encrypt(%s, %s, 'cipher-algo=aes256, compress-algo=0'), %s, %s, 'delivered', %s, now())
                    """,
                    (pool_id, code, secret, sandbox_code_hash(code), code[-4:], order_ref),
                )
            result = finalize_sandbox_delivery(
                conn,
                store_code=normalized_store_code,
                order_id=order_id,
                item_id=item_id,
                offer_id=offer_id,
                required_qty=required_qty,
                source="manual",
            )
            conn.commit()
        return result

    @app.post(
        "/marketplaces/yandex/sandbox/orders/{order_id}/items/{item_id}/issue-from-pool",
        response_model=YandexMarketSandboxDeliveryOut,
    )
    def issue_yandex_market_sandbox_order_from_pool(
        order_id: int,
        item_id: int,
        store_code: str = "test",
        user=Depends(require_role("owner")),
    ):
        # Берет точное число свободных ключей с блокировкой и отмечает выдачу только в локальной истории.
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        require_yandex_market_sandbox(normalized_store_code)
        order_ref = sandbox_order_ref(normalized_store_code, order_id, item_id)
        with psycopg.connect(DB_DSN) as conn:
            offer_id, required_qty = sandbox_order_for_delivery(conn, normalized_store_code, order_id, item_id)
            pool = q1(
                conn,
                """
                SELECT id
                FROM app.marketplace_manual_key_pools
                WHERE marketplace='yandex_market' AND store_code=%s AND product_key=%s
                """,
                (normalized_store_code, offer_id),
            )
            if not pool:
                raise HTTPException(409, "Для этой карточки нет ручного пула ключей")
            keys = qall(
                conn,
                """
                SELECT id
                FROM app.marketplace_manual_keys
                WHERE pool_id=%s
                  AND status='free'
                  AND (expires_at IS NULL OR expires_at >= current_date)
                ORDER BY created_at ASC, id ASC
                FOR UPDATE SKIP LOCKED
                LIMIT %s
                """,
                (int(pool[0]), required_qty),
            )
            if len(keys) != required_qty:
                raise HTTPException(409, f"В ручном пуле недостаточно свободных ключей: нужно {required_qty}, найдено {len(keys)}")
            key_ids = [int(row[0]) for row in keys]
            updated = exec1(
                conn,
                """
                UPDATE app.marketplace_manual_keys
                SET status='delivered', issued_order_ref=%s, issued_at=now(), updated_at=now()
                WHERE id=ANY(%s) AND status='free'
                """,
                (order_ref, key_ids),
            )
            if updated is not None and int(updated) != len(key_ids):
                raise HTTPException(409, "Часть ключей уже занята другой выдачей; повторите попытку")
            result = finalize_sandbox_delivery(
                conn,
                store_code=normalized_store_code,
                order_id=order_id,
                item_id=item_id,
                offer_id=offer_id,
                required_qty=required_qty,
                source="pool",
            )
            conn.commit()
        return result

    @app.post(
        "/marketplaces/yandex/sandbox/orders/{order_id}/items/{item_id}/send-to-market",
        response_model=YandexMarketSandboxDeliveryOut,
    )
    def send_yandex_market_sandbox_order_to_market(
        order_id: int,
        item_id: int,
        store_code: str = "test",
        user=Depends(require_role("owner")),
    ):
        # Отправляет уже закрепленные ключи только в fake-заказ test-Маркета после явной команды оператора.
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        require_yandex_market_live()
        require_yandex_market_sandbox_market_delivery(normalized_store_code)
        secret = sandbox_pool_secret()
        order_ref = sandbox_order_ref(normalized_store_code, order_id, item_id)
        offer_id = ""
        required_qty = 0
        delivery_source = ""
        with psycopg.connect(DB_DSN) as conn:
            delivery = q1(
                conn,
                """
                SELECT delivery.offer_id, delivery.required_qty, delivery.delivery_source, delivery.status, orders.status, orders.is_sandbox,
                       settings.activation_instruction
                FROM app.marketplace_yandex_sandbox_deliveries AS delivery
                JOIN app.marketplace_yandex_order_items AS orders
                  ON orders.store_code=delivery.store_code AND orders.order_id=delivery.order_id AND orders.item_id=delivery.item_id
                LEFT JOIN app.marketplace_yandex_stock_settings AS settings
                  ON settings.store_code=delivery.store_code AND settings.offer_id=delivery.offer_id
                WHERE delivery.store_code=%s AND delivery.order_id=%s AND delivery.item_id=%s
                FOR UPDATE
                """,
                (normalized_store_code, order_id, item_id),
            )
            if not delivery or not bool(delivery[5]):
                raise HTTPException(404, "Локальная выдача fake-заказа не найдена")
            if str(delivery[4] or "").upper() != "PROCESSING":
                raise HTTPException(409, "Передать ключ в Маркет можно только для fake-заказа в статусе PROCESSING")
            if str(delivery[3] or "") != "locally_issued":
                raise HTTPException(409, "Эта локальная выдача уже отправляется или была отправлена в Маркет")
            instruction = str(delivery[6] or "").strip()
            if not instruction:
                raise HTTPException(409, "Заполните инструкцию покупателю: она будет передана в slip Яндекс Маркета")
            offer_id, required_qty, delivery_source = str(delivery[0]), int(delivery[1]), str(delivery[2])
            rows = qall(
                conn,
                """
                SELECT pgp_sym_decrypt(key.code_ciphertext, %s)
                FROM app.marketplace_manual_keys AS key
                JOIN app.marketplace_manual_key_pools AS pool ON pool.id=key.pool_id
                WHERE pool.marketplace='yandex_market'
                  AND pool.store_code=%s
                  AND pool.product_key=%s
                  AND key.issued_order_ref=%s
                  AND key.status='delivered'
                ORDER BY key.issued_at ASC, key.id ASC
                FOR UPDATE
                """,
                (secret, normalized_store_code, offer_id, order_ref),
            )
            codes = [str(row[0] or "").strip() for row in rows if str(row[0] or "").strip()]
            if len(codes) != required_qty:
                raise HTTPException(409, "Не найден полный локально закрепленный комплект ключей для отправки в Маркет")
            exec1(
                conn,
                """
                UPDATE app.marketplace_yandex_sandbox_deliveries
                SET status='market_sending', last_error='', updated_at=now()
                WHERE store_code=%s AND order_id=%s AND item_id=%s
                """,
                (normalized_store_code, order_id, item_id),
            )
            conn.commit()
        try:
            deliver_yandex_market_digital_goods(
                order_id,
                item_id=item_id,
                codes=codes,
                slip=instruction,
                store_code=normalized_store_code,
            )
        except HTTPException as error:
            # При сетевой/серверной ошибке ответ мог потеряться после приема Маркетом, поэтому повтор блокируется.
            definite_rejection = 400 <= int(error.status_code) < 500
            next_status = "locally_issued" if definite_rejection else "market_unknown"
            with psycopg.connect(DB_DSN) as conn:
                exec1(
                    conn,
                    """
                    UPDATE app.marketplace_yandex_sandbox_deliveries
                    SET status=%s, last_error=%s, updated_at=now()
                    WHERE store_code=%s AND order_id=%s AND item_id=%s
                    """,
                    (next_status, str(error.detail)[:2000], normalized_store_code, order_id, item_id),
                )
                conn.commit()
            raise
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                UPDATE app.marketplace_yandex_sandbox_deliveries
                SET status='market_submitted', market_submitted_at=now(), last_error='', updated_at=now()
                WHERE store_code=%s AND order_id=%s AND item_id=%s
                """,
                (normalized_store_code, order_id, item_id),
            )
            conn.commit()
        return YandexMarketSandboxDeliveryOut(
            order_id=order_id, item_id=item_id, offer_id=offer_id, issued_qty=required_qty,
            delivery_source=delivery_source, status="market_submitted",
        )

    @app.get("/marketplaces/yandex/catalog/{offer_id}/stock-settings", response_model=YandexMarketStockSettingsOut)
    def get_yandex_market_stock_settings(
        offer_id: str,
        store_code: str = Query(..., min_length=1, max_length=64),
        user=Depends(require_role("owner")),
    ):
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
        store_code: str = Query(..., min_length=1, max_length=64),
        user=Depends(require_role("owner")),
    ):
        # Сохраняет лимит отдельно и публикует его только по явной команде оператора.
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        if payload.support_message_delivery_enabled and not payload.support_error_message.strip():
            # Не включает заглушку без текста, чтобы заказ не получил пустой код вместо понятного сообщения.
            raise HTTPException(400, "Введите сообщение покупателю для выдачи через поддержку")
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                INSERT INTO app.marketplace_yandex_stock_settings(
                  store_code, offer_id, manual_stock_limit, activation_instruction, support_error_message,
                  auto_issue_enabled, pool_issue_enabled, support_message_delivery_enabled,
                  sales_limit, sales_limit_revision, sales_limit_day, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,
                        CASE WHEN %s IS NULL THEN 0 ELSE 1 END, %s, now())
                ON CONFLICT (store_code, offer_id) DO UPDATE
                SET manual_stock_limit=excluded.manual_stock_limit,
                    activation_instruction=excluded.activation_instruction,
                    support_error_message=excluded.support_error_message,
                    auto_issue_enabled=CASE WHEN %s THEN excluded.auto_issue_enabled ELSE marketplace_yandex_stock_settings.auto_issue_enabled END,
                    pool_issue_enabled=CASE WHEN %s THEN excluded.pool_issue_enabled ELSE marketplace_yandex_stock_settings.pool_issue_enabled END,
                    support_message_delivery_enabled=CASE WHEN %s THEN excluded.support_message_delivery_enabled ELSE marketplace_yandex_stock_settings.support_message_delivery_enabled END,
                    sales_limit_revision=CASE
                      WHEN excluded.sales_limit IS NOT NULL
                       AND (marketplace_yandex_stock_settings.sales_limit IS NULL
                            OR marketplace_yandex_stock_settings.sales_limit_day < excluded.sales_limit_day)
                      THEN marketplace_yandex_stock_settings.sales_limit_revision + 1
                      ELSE marketplace_yandex_stock_settings.sales_limit_revision
                    END,
                    sales_limit_daily_extra=CASE
                      WHEN excluded.sales_limit IS NULL
                        OR marketplace_yandex_stock_settings.sales_limit_day < excluded.sales_limit_day
                      THEN 0
                      ELSE marketplace_yandex_stock_settings.sales_limit_daily_extra
                    END,
                    sales_limit_day=excluded.sales_limit_day,
                    sales_limit_rollover_pending=CASE
                      WHEN excluded.sales_limit IS NULL THEN false
                      WHEN marketplace_yandex_stock_settings.sales_limit_day < excluded.sales_limit_day
                      THEN true
                      ELSE marketplace_yandex_stock_settings.sales_limit_rollover_pending
                    END,
                    sales_limit=excluded.sales_limit,
                    sales_limit_exhausted_at=CASE
                      WHEN excluded.sales_limit IS NULL
                        OR marketplace_yandex_stock_settings.sales_limit_day < excluded.sales_limit_day
                      THEN NULL
                      ELSE marketplace_yandex_stock_settings.sales_limit_exhausted_at
                    END,
                    updated_at=now()
                """,
                (
                    normalized_store_code,
                    offer_id,
                    payload.manual_stock_limit,
                    payload.activation_instruction.strip(),
                    payload.support_error_message.strip(),
                    payload.auto_issue_enabled,
                    payload.pool_issue_enabled,
                    payload.support_message_delivery_enabled,
                    payload.sales_limit,
                    payload.sales_limit,
                    sales_limit_manager.current_day(),
                    not publish_stock,
                    not publish_stock,
                    not publish_stock,
                ),
            )
            if payload.interhub_service_id:
                # Связывает SKU с Interhub без оплаты: покупка возможна только из включенного webhook-обработчика.
                exec1(conn, """INSERT INTO app.marketplace_yandex_digital_suppliers(store_code, offer_id, provider_code, priority, enabled, service_id, nominal_id, updated_at) VALUES (%s, %s, 'interhub', 1, %s, %s, %s, now()) ON CONFLICT (store_code, offer_id, provider_code, priority) DO UPDATE SET enabled=excluded.enabled, service_id=excluded.service_id, nominal_id=excluded.nominal_id, updated_at=now()""", (normalized_store_code, offer_id, payload.interhub_enabled, payload.interhub_service_id, payload.interhub_nominal_id.strip()))
            else:
                # Не удаляет историю попыток, а выключает поставщика при очистке настройки.
                exec1(conn, "UPDATE app.marketplace_yandex_digital_suppliers SET enabled=false, updated_at=now() WHERE store_code=%s AND offer_id=%s AND provider_code='interhub' AND priority=1", (normalized_store_code, offer_id))
            if publish_stock and payload.sales_limit is not None:
                # Фоновый цикл повторит конечный остаток, если явная публикация временно не пройдет во внешний API.
                exec1(
                    conn,
                    "UPDATE app.marketplace_yandex_stock_settings SET sales_limit_rollover_pending=true, updated_at=now() WHERE store_code=%s AND offer_id=%s",
                    (normalized_store_code, offer_id),
                )
            conn.commit()
        if publish_stock:
            require_yandex_market_live()
            sales_limit_manager.sync_target_stock(normalized_store_code, offer_id)
            with psycopg.connect(DB_DSN) as conn:
                result = make_stock_settings_out(conn, normalized_store_code, offer_id)
                conn.commit()
                return result
        with psycopg.connect(DB_DSN) as conn:
            return make_stock_settings_out(conn, normalized_store_code, offer_id)

    @app.post("/marketplaces/yandex/catalog/{offer_id}/daily-limit/add", response_model=YandexMarketStockSettingsOut)
    def add_yandex_market_daily_limit(
        offer_id: str,
        payload: YandexMarketDailyLimitAdditionIn,
        store_code: str = Query(..., min_length=1, max_length=64),
        user=Depends(require_role("owner")),
    ):
        # Добавляет единицы только к текущему дню и сразу публикует увеличившийся доступный остаток.
        require_yandex_market_live()
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        try:
            sales_limit_manager.add_daily_units(normalized_store_code, offer_id, payload.units)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        with psycopg.connect(DB_DSN) as conn:
            return make_stock_settings_out(conn, normalized_store_code, offer_id)
