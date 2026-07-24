from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import json
import uuid

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from .ozon_service import (
    fetch_ozon_catalog_offer_id,
    fetch_ozon_catalog_items,
    fetch_ozon_digital_postings,
    normalize_ozon_store_code,
    update_ozon_catalog_archive,
    update_ozon_digital_stock,
    upload_ozon_digital_codes,
)


class OzonCatalogItemOut(BaseModel):
    external_product_id: int
    offer_id: str = ""
    sku: str = ""
    title: str = ""
    visibility: str = ""
    state: str = ""
    synced_at: datetime


class OzonCatalogListOut(BaseModel):
    store_code: str
    items: list[OzonCatalogItemOut] = Field(default_factory=list)


class OzonCatalogSyncOut(BaseModel):
    store_code: str
    synced_items: int
    synced_at: datetime


class OzonCatalogArchiveOut(BaseModel):
    external_product_id: int
    archived: bool


class OzonCatalogDetailsOut(BaseModel):
    external_product_id: int
    offer_id: str = ""
    sku: str = ""
    title: str = ""
    primary_image: str = ""
    barcodes: list[str] = Field(default_factory=list)
    category_id: int | None = None
    fbo_sku: str = ""
    fbs_sku: str = ""
    price: str = ""
    price_currency_code: str = ""
    available_stock: int = 0
    synced_at: datetime


class OzonDigitalSettingsIn(BaseModel):
    offer_id: str = Field(default="", max_length=255)
    manual_stock_limit: int = Field(default=0, ge=0, le=100000)
    auto_issue_enabled: bool = False
    activation_instruction: str = Field(default="", max_length=5000)
    support_error_message: str = Field(default="", max_length=2000)
    interhub_service_id: int | None = Field(default=None, gt=0)
    interhub_nominal_id: str = Field(default="", max_length=255)
    interhub_enabled: bool = False


class OzonDigitalSupplierOut(BaseModel):
    provider_code: str
    priority: int
    enabled: bool
    service_id: int
    nominal_id: str = ""


class OzonDigitalSettingsOut(OzonDigitalSettingsIn):
    external_product_id: int
    offer_id: str = ""
    published_stock: int = 0
    available_stock: int = 0
    pending_orders: int = 0
    delivered_orders: int = 0
    last_stock_sync_at: datetime | None = None
    last_orders_sync_at: datetime | None = None
    suppliers: list[OzonDigitalSupplierOut] = Field(default_factory=list)


class OzonDigitalOrderOut(BaseModel):
    id: int
    posting_number: str
    order_number: str = ""
    product_name: str = ""
    sku: int
    required_qty: int = 1
    collected_qty: int = 0
    remaining_qty: int = 1
    status: str
    ozon_status: str = ""
    waiting_deadline_at: datetime | None = None
    created_at: datetime | None = None
    delivered_at: datetime | None = None
    last_error: str = ""
    delivery_source: str = ""
    delivered_codes_masked: list[str] = Field(default_factory=list)


class OzonDigitalOrdersOut(BaseModel):
    items: list[OzonDigitalOrderOut] = Field(default_factory=list)


class OzonDigitalOrderCodesOut(BaseModel):
    id: int
    codes: list[str] = Field(default_factory=list)


class OzonDigitalSupplierOperationOut(BaseModel):
    order_id: int
    provider_code: str
    agent_transaction_id: str
    provider_transaction_id: str = ""
    service_id: int
    nominal_id: str = ""
    service_title: str = ""
    nominal_title: str = ""
    amount: float | None = None
    state: str
    provider_status: int = 0
    provider_message: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OzonDigitalSyncOut(BaseModel):
    imported_orders: int = 0
    available_stock: int = 0
    last_orders_sync_at: datetime


class OzonDigitalDeliveryIn(BaseModel):
    codes: list[str] = Field(default_factory=list, min_length=1, max_length=100)


def mount_marketplaces_routes(
    app,
    *,
    DB_DSN,
    psycopg,
    q1,
    qall,
    exec1,
    get_current_user,
    require_role,
    interhub_calculate=None,
    interhub_check=None,
    interhub_pay=None,
    interhub_check_status=None,
):
    def ensure_marketplaces_schema(conn) -> None:
        # Создает локальный снимок карточек, не меняя каталог или остатки в кабинете Ozon.
        exec1(
            conn,
            """
            CREATE TABLE IF NOT EXISTS app.marketplace_ozon_catalog_items (
              store_code text NOT NULL,
              external_product_id bigint NOT NULL,
              offer_id text NOT NULL DEFAULT '',
              title text NOT NULL DEFAULT '',
              visibility text NOT NULL DEFAULT '',
              state text NOT NULL DEFAULT '',
              raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
              synced_at timestamptz NOT NULL DEFAULT now(),
              PRIMARY KEY (store_code, external_product_id)
            )
            """,
        )
        exec1(
            conn,
            """
            CREATE INDEX IF NOT EXISTS idx_marketplace_ozon_catalog_offer
            ON app.marketplace_ozon_catalog_items(store_code, offer_id)
            """,
        )
        exec1(
            conn,
            """
            CREATE TABLE IF NOT EXISTS app.marketplace_ozon_digital_settings (
              store_code text NOT NULL,
              external_product_id bigint NOT NULL,
              offer_id text NOT NULL DEFAULT '',
              manual_stock_limit integer NOT NULL DEFAULT 0,
              auto_issue_enabled boolean NOT NULL DEFAULT false,
              activation_instruction text NOT NULL DEFAULT '',
              support_error_message text NOT NULL DEFAULT '',
              published_stock integer NOT NULL DEFAULT 0,
              last_stock_sync_at timestamptz,
              last_orders_sync_at timestamptz,
              updated_at timestamptz NOT NULL DEFAULT now(),
              PRIMARY KEY (store_code, external_product_id)
            )
            """,
        )
        exec1(
            conn,
            """
            CREATE TABLE IF NOT EXISTS app.marketplace_ozon_digital_orders (
              id bigserial PRIMARY KEY,
              store_code text NOT NULL,
              external_product_id bigint NOT NULL,
              posting_number text NOT NULL,
              order_number text NOT NULL DEFAULT '',
              product_name text NOT NULL DEFAULT '',
              sku bigint NOT NULL,
              required_qty integer NOT NULL DEFAULT 1,
              status text NOT NULL DEFAULT 'manual_required',
              ozon_status text NOT NULL DEFAULT '',
              waiting_deadline_at timestamptz,
              created_at timestamptz,
              delivered_at timestamptz,
              delivered_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
              last_error text NOT NULL DEFAULT '',
              updated_at timestamptz NOT NULL DEFAULT now(),
              UNIQUE (store_code, posting_number, sku)
            )
            """,
        )
        exec1(
            conn,
            # Добавляет исходный статус Ozon в уже созданные таблицы без потери истории заказов.
            "ALTER TABLE app.marketplace_ozon_digital_orders ADD COLUMN IF NOT EXISTS ozon_status text NOT NULL DEFAULT ''",
        )
        exec1(
            conn,
            """
            CREATE INDEX IF NOT EXISTS idx_marketplace_ozon_digital_orders_product
            ON app.marketplace_ozon_digital_orders(store_code, external_product_id, status, created_at DESC)
            """,
        )
        exec1(
            conn,
            """
            CREATE TABLE IF NOT EXISTS app.marketplace_ozon_digital_suppliers (
              id bigserial PRIMARY KEY,
              store_code text NOT NULL,
              external_product_id bigint NOT NULL,
              provider_code text NOT NULL,
              priority integer NOT NULL DEFAULT 1,
              enabled boolean NOT NULL DEFAULT false,
              service_id integer NOT NULL,
              nominal_id text NOT NULL DEFAULT '',
              params jsonb NOT NULL DEFAULT '{}'::jsonb,
              updated_at timestamptz NOT NULL DEFAULT now(),
              UNIQUE (store_code, external_product_id, provider_code, priority)
            )
            """,
        )
        exec1(
            conn,
            """
            CREATE TABLE IF NOT EXISTS app.marketplace_ozon_digital_supplier_attempts (
              id bigserial PRIMARY KEY,
              order_id bigint NOT NULL REFERENCES app.marketplace_ozon_digital_orders(id) ON DELETE CASCADE,
              supplier_id bigint NOT NULL REFERENCES app.marketplace_ozon_digital_suppliers(id) ON DELETE RESTRICT,
              agent_transaction_id text NOT NULL UNIQUE,
              state text NOT NULL DEFAULT 'processing',
              provider_status integer NOT NULL DEFAULT 0,
              provider_message text NOT NULL DEFAULT '',
              provider_response jsonb NOT NULL DEFAULT '{}'::jsonb,
              next_status_check_at timestamptz,
              created_at timestamptz NOT NULL DEFAULT now(),
              updated_at timestamptz NOT NULL DEFAULT now()
            )
            """,
        )
        exec1(
            conn,
            """
            DO $$
            DECLARE constraint_name text;
            BEGIN
              SELECT constraint_row.conname INTO constraint_name
              FROM pg_constraint AS constraint_row
              JOIN pg_attribute AS attribute_row
                ON attribute_row.attrelid=constraint_row.conrelid
               AND attribute_row.attnum=ANY(constraint_row.conkey)
              WHERE constraint_row.conrelid='app.marketplace_ozon_digital_supplier_attempts'::regclass
                AND constraint_row.contype='u'
              GROUP BY constraint_row.conname, constraint_row.conkey
              HAVING array_agg(attribute_row.attname::text ORDER BY array_position(constraint_row.conkey, attribute_row.attnum))
                = ARRAY['order_id', 'supplier_id']
              LIMIT 1;
              IF constraint_name IS NOT NULL THEN
                EXECUTE format('ALTER TABLE app.marketplace_ozon_digital_supplier_attempts DROP CONSTRAINT %%I', constraint_name);
              END IF;
            END $$
            """,
        )
        exec1(
            conn,
            """
            CREATE INDEX IF NOT EXISTS idx_marketplace_ozon_digital_supplier_attempts_pending
            ON app.marketplace_ozon_digital_supplier_attempts(state, next_status_check_at)
            """,
        )
        exec1(
            conn,
            """
            CREATE INDEX IF NOT EXISTS idx_marketplace_ozon_digital_supplier_attempts_order_supplier
            ON app.marketplace_ozon_digital_supplier_attempts(order_id, supplier_id, updated_at DESC)
            """,
        )

    def prepare_marketplaces_schema() -> None:
        # Выполняет изменения структуры один раз при запуске API, чтобы рабочие запросы не блокировали таблицы DDL-командами.
        with psycopg.connect(DB_DSN) as conn:
            exec1(conn, "SELECT pg_advisory_xact_lock(hashtext('gamesales_marketplaces_schema'))")
            ensure_marketplaces_schema(conn)
            conn.commit()

    def normalize_catalog_item(item: dict[str, Any]) -> tuple[int, str, str, str, str]:
        # Выбирает стабильные поля карточки из ответа Ozon и отбрасывает неполные элементы.
        raw_product_id = item.get("product_id") or item.get("id")
        try:
            external_product_id = int(raw_product_id)
        except (TypeError, ValueError):
            raise HTTPException(502, "Ozon catalog item does not contain product_id")
        offer_id = first_text(item.get("offer_id"), item.get("offer_code"))
        title = str(item.get("name") or item.get("title") or "").strip()
        visibility = str(item.get("visibility") or "").strip()
        if bool(item.get("archived")) or visibility.upper() == "ARCHIVED":
            visibility = "ARCHIVED"
        status = item.get("status") if isinstance(item.get("status"), dict) else {}
        state = str(status.get("state") or item.get("state") or "").strip()
        return external_product_id, offer_id, title, visibility, state

    def read_catalog_payload(value: Any) -> dict[str, Any]:
        # Приводит jsonb из PostgreSQL к словарю, чтобы не отдавать UI необработанный ответ Ozon.
        if isinstance(value, dict):
            return value
        if not isinstance(value, str):
            return {}
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def catalog_item_sku(raw_payload: Any) -> str:
        # Берет основной SKU Ozon, а для старых ответов использует SKU источника или схемы поставки.
        payload = read_catalog_payload(raw_payload)
        sources = payload.get("sources") if isinstance(payload.get("sources"), list) else []
        source_skus = [source.get("sku") for source in sources if isinstance(source, dict)]
        return first_text(payload.get("sku"), source_skus, payload.get("fbs_sku"), payload.get("fbo_sku"))

    def first_text(*values: Any) -> str:
        # Берет первое непустое текстовое значение, в том числе из массивов ссылок или штрихкодов.
        for value in values:
            candidates = value if isinstance(value, list) else [value]
            for candidate in candidates:
                text = str("" if candidate is None else candidate).strip()
                if text:
                    return text
        return ""

    def optional_int(value: Any) -> int | None:
        # Не дает пустым или нестандартным числам из внешнего API сломать открытие карточки.
        try:
            return int(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None

    def make_catalog_details(product_id: int, payload: dict[str, Any], synced_at: datetime) -> OzonCatalogDetailsOut:
        # Оставляет для оператора только полезные реквизиты из детального ответа Ozon без дублей таблицы.
        raw_barcodes = payload.get("barcodes") if isinstance(payload.get("barcodes"), list) else []
        barcode = first_text(payload.get("barcode"))
        barcodes = [str(value).strip() for value in raw_barcodes if str(value or "").strip()]
        if barcode and barcode not in barcodes:
            barcodes.insert(0, barcode)
        price = payload.get("ozon_price") if isinstance(payload.get("ozon_price"), dict) else {}
        stock_rows = payload.get("ozon_stocks") if isinstance(payload.get("ozon_stocks"), list) else []
        if not stock_rows:
            # Поддерживаем снимки, где цифровой остаток Ozon лежит внутри подробной карточки, а не в отдельном поле.
            native_stocks = payload.get("stocks")
            if isinstance(native_stocks, dict):
                native_stocks = native_stocks.get("stocks")
            stock_rows = native_stocks if isinstance(native_stocks, list) else []
        available_stock = sum(optional_int(stock.get("present")) or 0 for stock in stock_rows if isinstance(stock, dict))
        return OzonCatalogDetailsOut(
            external_product_id=product_id,
            offer_id=first_text(payload.get("offer_id"), payload.get("offer_code")),
            sku=catalog_item_sku(payload),
            title=first_text(payload.get("name"), payload.get("title")),
            primary_image=first_text(payload.get("primary_image"), payload.get("images")),
            barcodes=barcodes,
            category_id=optional_int(payload.get("category_id")),
            fbo_sku=first_text(payload.get("fbo_sku")),
            fbs_sku=first_text(payload.get("fbs_sku")),
            price=first_text(price.get("price")),
            price_currency_code=first_text(price.get("currency_code")),
            available_stock=available_stock,
            synced_at=synced_at,
        )

    def catalog_offer_id(conn, store_code: str, product_id: int, fallback_offer_id: str = "") -> str:
        # Берет артикул из снимка или сырого ответа, чтобы старые синхронизации тоже могли публиковать остаток.
        row = q1(
            conn,
            """
            SELECT offer_id, raw_payload
            FROM app.marketplace_ozon_catalog_items
            WHERE store_code=%s AND external_product_id=%s
            """,
            (store_code, product_id),
        )
        offer_id = str(row[0] or "").strip() if row else ""
        if not offer_id and row:
            payload = read_catalog_payload(row[1])
            offer_id = first_text(payload.get("offer_id"), payload.get("offer_code"))
        if not offer_id:
            # Восстанавливает артикул из Ozon, чтобы неполный старый снимок не блокировал первую публикацию остатка.
            offer_id = fetch_ozon_catalog_offer_id(product_id, store_code=store_code)
            if offer_id and row:
                exec1(
                    conn,
                    "UPDATE app.marketplace_ozon_catalog_items SET offer_id=%s WHERE store_code=%s AND external_product_id=%s",
                    (offer_id, store_code, product_id),
                )
        if not offer_id:
            # Использует артикул уже открытой карточки как последний безопасный резерв при сохранении настроек.
            offer_id = str(fallback_offer_id or "").strip()
        if not offer_id:
            raise HTTPException(400, "Ozon не вернул артикул продавца для этой карточки. Проверьте артикул в кабинете Ozon.")
        return offer_id

    def settings_row(conn, store_code: str, product_id: int):
        # Читает только настройки выбранной карточки, не смешивая их с настройками других товаров.
        return q1(
            conn,
            """
            SELECT offer_id, manual_stock_limit, auto_issue_enabled, activation_instruction,
                   support_error_message, published_stock, last_stock_sync_at, last_orders_sync_at
            FROM app.marketplace_ozon_digital_settings
            WHERE store_code=%s AND external_product_id=%s
            """,
            (store_code, product_id),
        )

    def supplier_rows(conn, store_code: str, product_id: int, *, enabled_only: bool = False):
        # Читает цепочку поставщиков в заданном порядке, чтобы позже добавить второго без переделки заказов.
        condition = "AND enabled=true" if enabled_only else ""
        return qall(
            conn,
            f"""
            SELECT id, provider_code, priority, enabled, service_id, nominal_id, params
            FROM app.marketplace_ozon_digital_suppliers
            WHERE store_code=%s AND external_product_id=%s {condition}
            ORDER BY priority ASC, id ASC
            """,
            (store_code, product_id),
        )

    def make_supplier_out(row) -> OzonDigitalSupplierOut:
        # Не возвращает технические параметры поставщика в UI, оставляя только выбранную услугу и номинал.
        return OzonDigitalSupplierOut(
            provider_code=str(row[1] or ""),
            priority=int(row[2] or 1),
            enabled=bool(row[3]),
            service_id=int(row[4] or 0),
            nominal_id=str(row[5] or ""),
        )

    def get_order_counters(conn, store_code: str, product_id: int) -> tuple[int, int, int]:
        # Считает зарезервированные и выданные единицы, чтобы не продавать поверх уже пришедших заказов.
        row = q1(
            conn,
            """
            SELECT
              COALESCE(SUM(required_qty) FILTER (WHERE status IN ('manual_required', 'supplier_processing', 'delivering', 'delivered')), 0),
              COALESCE(SUM(required_qty) FILTER (WHERE status='manual_required'), 0),
              COALESCE(SUM(required_qty) FILTER (WHERE status='delivered'), 0)
            FROM app.marketplace_ozon_digital_orders
            WHERE store_code=%s AND external_product_id=%s
            """,
            (store_code, product_id),
        )
        if not row:
            return 0, 0, 0
        reserved = int(row[0] or 0)
        pending = int(row[1] or 0)
        delivered = int(row[2] or 0)
        return reserved, pending, delivered

    def make_digital_settings_out(conn, store_code: str, product_id: int) -> OzonDigitalSettingsOut:
        # Собирает настройки и счетчики в один ответ, удобный для экрана ручной выдачи.
        row = settings_row(conn, store_code, product_id)
        if not row:
            offer_id = catalog_offer_id(conn, store_code, product_id)
            return OzonDigitalSettingsOut(external_product_id=product_id, offer_id=offer_id)
        _reserved_units, pending_orders, delivered_orders = get_order_counters(conn, store_code, product_id)
        suppliers = [make_supplier_out(item) for item in supplier_rows(conn, store_code, product_id)]
        interhub = next((item for item in suppliers if item.provider_code == "interhub" and item.priority == 1), None)
        manual_stock_limit = int(row[1] or 0)
        return OzonDigitalSettingsOut(
            external_product_id=product_id,
            offer_id=str(row[0] or ""),
            manual_stock_limit=manual_stock_limit,
            auto_issue_enabled=bool(row[2]),
            activation_instruction=str(row[3] or ""),
            support_error_message=str(row[4] or ""),
            published_stock=int(row[5] or 0),
            # Оператор задаёт точный остаток для Ozon: заказы не меняют его без нового ручного сохранения.
            available_stock=manual_stock_limit,
            pending_orders=pending_orders,
            delivered_orders=delivered_orders,
            last_stock_sync_at=row[6],
            last_orders_sync_at=row[7],
            interhub_service_id=interhub.service_id if interhub else None,
            interhub_nominal_id=interhub.nominal_id if interhub else "",
            interhub_enabled=interhub.enabled if interhub else False,
            suppliers=suppliers,
        )

    def update_local_published_stock(conn, store_code: str, product_id: int, stock: int, synced_at: datetime) -> None:
        # Запоминает подтвержденный Ozon остаток, чтобы оператор видел, что витрина уже обновлена.
        exec1(
            conn,
            """
            UPDATE app.marketplace_ozon_digital_settings
            SET published_stock=%s, last_stock_sync_at=%s, updated_at=now()
            WHERE store_code=%s AND external_product_id=%s
            """,
            (stock, synced_at, store_code, product_id),
        )

    def publish_available_stock(conn, store_code: str, product_id: int) -> OzonDigitalSettingsOut:
        # Отправляет в Ozon ровно введенный оператором остаток и только после успеха обновляет локальный статус.
        settings = make_digital_settings_out(conn, store_code, product_id)
        response = update_ozon_digital_stock(settings.offer_id, settings.available_stock, store_code=store_code)
        statuses = response.get("status") if isinstance(response.get("status"), list) else []
        if not any(isinstance(item, dict) and item.get("updated") for item in statuses):
            messages = [str(error.get("message") or "") for item in statuses if isinstance(item, dict) for error in (item.get("errors") or []) if isinstance(error, dict)]
            raise HTTPException(502, f"Ozon не подтвердил обновление остатка. {'; '.join(message for message in messages if message) or 'Проверьте карточку и настройки цифрового товара.'}")
        update_local_published_stock(conn, store_code, product_id, settings.available_stock, datetime.now(timezone.utc))
        return make_digital_settings_out(conn, store_code, product_id)

    def local_digital_order_status(ozon_status: str) -> str:
        # Переводит финальные статусы Ozon в наши, чтобы отмененный заказ не оставался в обработке.
        normalized_status = str(ozon_status or "").strip().lower()
        if "cancel" in normalized_status:
            return "cancelled"
        if normalized_status == "done":
            return "delivered"
        return "manual_required"

    def cancel_missing_digital_orders(store_code: str, product_id: int, active_postings: set[str]) -> None:
        # Ozon исключает отмененные digital-отправления из списка, поэтому закрываем отсутствующие незавершенные заказы.
        with psycopg.connect(DB_DSN) as conn:
            known_orders = qall(
                conn,
                """
                SELECT id, posting_number
                FROM app.marketplace_ozon_digital_orders
                WHERE store_code=%s
                  AND external_product_id=%s
                  AND status NOT IN ('delivered', 'cancelled')
                ORDER BY id ASC
                """,
                (store_code, product_id),
            )
            for known_order in known_orders:
                order_id = int(known_order[0])
                posting_number = str(known_order[1] or "").strip()
                if not posting_number or posting_number in active_postings:
                    continue
                exec1(
                    conn,
                    """
                    UPDATE app.marketplace_ozon_digital_orders
                    SET ozon_status='cancelled',
                        status='cancelled',
                        updated_at=now()
                    WHERE id=%s
                    """,
                    (order_id,),
                )
            conn.commit()

    def provider_state(result: dict[str, Any]) -> str:
        # Приводит ответ Interhub к трем состояниям, от которых зависит дальнейшая выдача заказа.
        if bool(result.get("success")) and int(result.get("status") or 0) == 1:
            return "processing"
        if bool(result.get("success")) and int(result.get("status") or 0) == 0:
            return "paid"
        return "failed"

    def delivered_codes_from_row(value: Any) -> list[str]:
        # Приводит сохраненный JSON с кодами к списку строк, не допуская служебные значения в ответ API.
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = []
        return [str(code or "").strip() for code in value] if isinstance(value, list) else []

    def mask_digital_code(code: str) -> str:
        # Оставляет только последние символы ключа, чтобы история помогала сверке, но не раскрывала секрет.
        normalized = str(code or "").strip()
        if not normalized:
            return ""
        return f"••••{normalized[-4:]}" if len(normalized) > 4 else "••••"

    def make_order_out(row) -> OzonDigitalOrderOut:
        # Собирает единый ответ заказа после ручной или автоматической выдачи, не раскрывая сам ключ.
        delivered_codes = delivered_codes_from_row(row[13] if len(row) > 13 else [])
        required_qty = int(row[5] or 1)
        collected_qty = min(len(delivered_codes), required_qty)
        delivery_source = str(row[12] or "").strip() if len(row) > 12 else ""
        if not delivery_source and delivered_codes:
            delivery_source = "manual"
        return OzonDigitalOrderOut(
            id=int(row[0]),
            posting_number=str(row[1] or ""),
            order_number=str(row[2] or ""),
            product_name=str(row[3] or ""),
            sku=int(row[4] or 0),
            required_qty=required_qty,
            collected_qty=collected_qty,
            remaining_qty=max(0, required_qty - collected_qty),
            status=str(row[6] or "manual_required"),
            ozon_status=str(row[7] or ""),
            waiting_deadline_at=row[8],
            created_at=row[9],
            delivered_at=row[10],
            last_error=str(row[11] or ""),
            delivery_source=delivery_source,
            delivered_codes_masked=[mask_digital_code(code) for code in delivered_codes],
        )

    def read_order_out(conn, order_id: int) -> OzonDigitalOrderOut:
        # Читает безопасный срез заказа для UI после изменения его статуса.
        row = q1(
            conn,
            """
            SELECT orders.id, orders.posting_number, orders.order_number, orders.product_name, orders.sku,
                   orders.required_qty, orders.status, orders.ozon_status, orders.waiting_deadline_at,
                   orders.created_at, orders.delivered_at, orders.last_error,
                   COALESCE((
                     SELECT supplier.provider_code
                     FROM app.marketplace_ozon_digital_supplier_attempts AS attempt
                     JOIN app.marketplace_ozon_digital_suppliers AS supplier ON supplier.id=attempt.supplier_id
                     WHERE attempt.order_id=orders.id AND attempt.state='paid'
                     ORDER BY attempt.updated_at DESC, attempt.id DESC
                     LIMIT 1
                   ), ''),
                   orders.delivered_codes
            FROM app.marketplace_ozon_digital_orders AS orders WHERE orders.id=%s
            """,
            (order_id,),
        )
        if not row:
            raise HTTPException(404, "Цифровой заказ Ozon не найден")
        return make_order_out(row)

    def is_ozon_posting_done_error(error: HTTPException) -> bool:
        # Распознает финальный статус Ozon после отправки ключа, когда ответ на повторный запрос уже не принимает коды.
        message = str(error.detail or "").lower()
        return "статусе done" in message or "status done" in message

    def finish_ozon_delivery(order_id: int, order_row, codes: list[str]) -> OzonDigitalOrderOut:
        # Фиксирует выдачу локально, а резерв Ozon уменьшает сам без повторной публикации остатка.
        delivered_at = datetime.now(timezone.utc)
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                UPDATE app.marketplace_ozon_digital_orders
                SET status='delivered', delivered_at=%s, delivered_codes=%s::jsonb, last_error='', updated_at=now()
                WHERE id=%s
                """,
                (delivered_at, json.dumps(codes, ensure_ascii=False), order_id),
            )
            delivered_order = read_order_out(conn, order_id)
            conn.commit()
        return delivered_order

    def deliver_ozon_codes(order_id: int, codes: list[str]) -> OzonDigitalOrderOut:
        # Объединяет сохраненные и новые коды, чтобы заказ из нескольких единиц ушел в Ozon одной выдачей.
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                """
                SELECT store_code, external_product_id, posting_number, sku, required_qty, status, delivered_codes
                FROM app.marketplace_ozon_digital_orders WHERE id=%s
                """,
                (order_id,),
            )
            if not row:
                raise HTTPException(404, "Цифровой заказ Ozon не найден")
            if str(row[5] or "") == "delivered":
                raise HTTPException(409, "Ключ для этого заказа уже отправлен в Ozon")
            if str(row[5] or "") == "cancelled":
                raise HTTPException(409, "Отмененному заказу нельзя отправить ключ")
            saved_codes = delivered_codes_from_row(row[6])
            new_codes = [str(code or "").strip() for code in codes if str(code or "").strip()]
            all_codes = list(saved_codes)
            for code in new_codes:
                if code not in all_codes:
                    all_codes.append(code)
            required_qty = int(row[4] or 1)
            if len(all_codes) > required_qty:
                raise HTTPException(400, f"Для этого заказа можно передать не больше ключей: {required_qty}")
            if len(all_codes) != required_qty:
                raise HTTPException(400, f"Для этого заказа осталось передать ключей: {required_qty - len(all_codes)}")
            exec1(conn, "UPDATE app.marketplace_ozon_digital_orders SET status='delivering', last_error='', updated_at=now() WHERE id=%s", (order_id,))
            conn.commit()

        try:
            response = upload_ozon_digital_codes(posting_number=str(row[2]), sku=int(row[3]), codes=all_codes, store_code=str(row[0]))
            results = response.get("exemplars_by_sku") if isinstance(response.get("exemplars_by_sku"), list) else []
            delivered = next((item for item in results if isinstance(item, dict) and int(item.get("sku") or 0) == int(row[3])), None)
            if not delivered or int(delivered.get("received_qty") or 0) != len(all_codes) or int(delivered.get("rejected_qty") or 0) != 0:
                raise HTTPException(502, "Ozon не подтвердил передачу всех ключей для заказа")
        except HTTPException as exc:
            if is_ozon_posting_done_error(exc):
                # Ozon мог успеть принять ключ до ответа: Done для цифрового отправления считаем подтвержденной выдачей.
                return finish_ozon_delivery(order_id, row, all_codes)
            with psycopg.connect(DB_DSN) as conn:
                exec1(conn, "UPDATE app.marketplace_ozon_digital_orders SET status='manual_required', last_error=%s, updated_at=now() WHERE id=%s", (str(exc.detail)[:2000], order_id))
                conn.commit()
            raise

        return finish_ozon_delivery(order_id, row, all_codes)

    def save_collected_supplier_code(order_id: int, gift_code: str) -> tuple[int, int, bool]:
        # Сохраняет каждый полученный код до следующей покупки у поставщика, чтобы частичная выдача не терялась.
        normalized_code = str(gift_code or "").strip()
        if not normalized_code:
            raise HTTPException(502, "Поставщик не вернул ключ")
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                "SELECT required_qty, delivered_codes FROM app.marketplace_ozon_digital_orders WHERE id=%s FOR UPDATE",
                (order_id,),
            )
            if not row:
                raise HTTPException(404, "Цифровой заказ Ozon не найден")
            codes = delivered_codes_from_row(row[1])
            duplicate = normalized_code in codes
            if not duplicate:
                codes.append(normalized_code)
                exec1(
                    conn,
                    "UPDATE app.marketplace_ozon_digital_orders SET delivered_codes=%s::jsonb, status='supplier_processing', last_error='', updated_at=now() WHERE id=%s",
                    (json.dumps(codes, ensure_ascii=False), order_id),
                )
            conn.commit()
        return len(codes), int(row[0] or 1), duplicate

    def mark_order_for_manual_delivery(order_id: int, message: str) -> None:
        # Оставляет заказ оператору, только когда поставщики не дали пригодный ключ без списания дубля.
        with psycopg.connect(DB_DSN) as conn:
            exec1(conn, "UPDATE app.marketplace_ozon_digital_orders SET status='manual_required', last_error=%s, updated_at=now() WHERE id=%s", (message[:2000], order_id))
            conn.commit()

    def save_auto_interhub_check(order_id: int, request: dict[str, Any], amount: float, result: dict[str, Any]) -> None:
        # Добавляет автоматическую проверку в общий журнал Interhub, чтобы она была видна рядом с ручными платежами.
        state = "checked" if bool(result.get("success")) else "failed"
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                INSERT INTO app.interhub_transactions(
                  agent_transaction_id, service_id, account, amount, request_params, state,
                  provider_status, provider_message, provider_transaction_id, provider_response, created_by, ozon_order_id, updated_at
                )
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s::jsonb, 'ozon-auto', %s, now())
                ON CONFLICT (agent_transaction_id) DO UPDATE
                SET state=excluded.state,
                    amount=excluded.amount,
                    request_params=excluded.request_params,
                    provider_status=excluded.provider_status,
                    provider_message=excluded.provider_message,
                    provider_transaction_id=excluded.provider_transaction_id,
                    provider_response=excluded.provider_response,
                    ozon_order_id=excluded.ozon_order_id,
                    updated_at=now()
                """,
                (
                    str(request["agent_transaction_id"]), int(request["service_id"]), str(request.get("account") or ""), amount,
                    json.dumps(request.get("params") or {}), state, int(result.get("status") or 0), str(result.get("message") or ""),
                    str(result.get("transaction_id") or ""), json.dumps(result.get("raw") or {}), order_id,
                ),
            )
            conn.commit()

    def save_auto_interhub_result(agent_transaction_id: str, result: dict[str, Any]) -> None:
        # Обновляет общий журнал результатом pay или check_status, не сохраняя ключ в отдельном месте вне Interhub-истории.
        state = provider_state(result)
        params = result.get("params") if isinstance(result.get("params"), dict) else {}
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                UPDATE app.interhub_transactions
                SET state=%s, provider_status=%s, provider_message=%s,
                    provider_transaction_id=COALESCE(NULLIF(%s, ''), provider_transaction_id),
                    gift_code=COALESCE(NULLIF(%s, ''), gift_code), provider_response=%s::jsonb,
                    updated_at=now()
                WHERE agent_transaction_id=%s
                """,
                (
                    state, int(result.get("status") or 0), str(result.get("message") or ""),
                    str(result.get("transaction_id") or ""), str(params.get("gift_code") or ""),
                    json.dumps(result.get("raw") or {}), agent_transaction_id,
                ),
            )
            conn.commit()

    def process_order_with_suppliers(order_id: int) -> None:
        # Покупает ключи по одному до количества заказа, а после частичной ошибки оставляет только недостающее оператору.
        if not interhub_calculate or not interhub_check or not interhub_pay:
            mark_order_for_manual_delivery(order_id, "Автовыдача Interhub пока недоступна на сервере.")
            return
        suppliers = []
        failed_suppliers: set[int] = set()
        with psycopg.connect(DB_DSN) as conn:
            order = q1(
                conn,
                """
                SELECT store_code, external_product_id, required_qty, status, delivered_codes
                FROM app.marketplace_ozon_digital_orders WHERE id=%s
                """,
                (order_id,),
            )
            if not order or str(order[3] or "") not in {"manual_required", "supplier_processing"}:
                # Явно завершаем даже транзакцию только на чтение, чтобы пул не возвращал ее с удержанной блокировкой.
                conn.commit()
                return
            required_qty = int(order[2] or 1)
            collected_codes = delivered_codes_from_row(order[4])
            suppliers = supplier_rows(conn, str(order[0]), int(order[1]), enabled_only=True)
            attempt_rows = qall(
                conn,
                """
                SELECT DISTINCT ON (supplier_id) supplier_id, state
                FROM app.marketplace_ozon_digital_supplier_attempts
                WHERE order_id=%s
                ORDER BY supplier_id, updated_at DESC, id DESC
                """,
                (order_id,),
            )
            if any(str(row[1] or "") == "processing" for row in attempt_rows):
                # Ждем незавершенную оплату, чтобы повторный опрос не оплатил еще один код.
                conn.commit()
                return
            failed_suppliers = {int(row[0]) for row in attempt_rows if str(row[1] or "") == "failed"}
            # Завершаем транзакцию чтения до внешних вызовов, чтобы она не удерживала блокировку таблицы.
            conn.commit()

        if len(collected_codes) >= required_qty:
            try:
                deliver_ozon_codes(order_id, [])
            except HTTPException:
                pass
            return

        for supplier in suppliers:
            supplier_id = int(supplier[0])
            if supplier_id in failed_suppliers:
                continue
            if str(supplier[1] or "") != "interhub":
                continue
            # Создаем отдельную операцию Interhub на каждый ключ, сохраняя старые операции в общем журнале.
            transaction_id = f"gamesales-check-{int(datetime.now(timezone.utc).timestamp() * 1000)}-{uuid.uuid4().hex[:12]}"
            params = read_catalog_payload(supplier[6])
            nominal_id = str(supplier[5] or "").strip()
            if nominal_id:
                params["nominal"] = nominal_id
            request = {"service_id": int(supplier[4]), "account": "", "agent_transaction_id": transaction_id, "params": params}
            with psycopg.connect(DB_DSN) as conn:
                # Резервируем одну попытку до вызова поставщика, чтобы повторная синхронизация не создала двойную оплату.
                exec1(conn, "UPDATE app.marketplace_ozon_digital_orders SET status='supplier_processing', last_error='', updated_at=now() WHERE id=%s", (order_id,))
                exec1(
                    conn,
                    """
                    INSERT INTO app.marketplace_ozon_digital_supplier_attempts(order_id, supplier_id, agent_transaction_id, state)
                    VALUES (%s, %s, %s, 'processing')
                    """,
                    (order_id, supplier_id, transaction_id),
                )
                conn.commit()
            try:
                # Сначала получаем цену ваучера: Interhub требует её в обязательном поле amount на check.
                calculated = interhub_calculate({**request, "agent_transaction_id": f"{transaction_id}-calculate"})
                amount = float(calculated.get("fixed_amount") or 0)
                if not bool(calculated.get("success")) or amount <= 0:
                    raise HTTPException(502, str(calculated.get("message") or "Interhub не вернул цену для выдачи ключа"))
                checked = interhub_check({**request, "amount": amount})
                save_auto_interhub_check(order_id, request, amount, checked)
                if not bool(checked.get("success")):
                    raise HTTPException(502, str(checked.get("message") or "Interhub не подтвердил выдачу ключа"))
                paid = interhub_pay({"agent_transaction_id": transaction_id})
            except Exception as exc:
                message = str(getattr(exc, "detail", exc))
                with psycopg.connect(DB_DSN) as conn:
                    exec1(conn, "UPDATE app.marketplace_ozon_digital_supplier_attempts SET state='failed', provider_message=%s, updated_at=now() WHERE agent_transaction_id=%s", (message[:2000], transaction_id))
                    conn.commit()
                continue
            state = provider_state(paid)
            provider_message = str(paid.get("message") or "")
            save_auto_interhub_result(transaction_id, paid)
            with psycopg.connect(DB_DSN) as conn:
                exec1(
                    conn,
                    """
                    UPDATE app.marketplace_ozon_digital_supplier_attempts
                    SET state=%s, provider_status=%s, provider_message=%s, provider_response=%s::jsonb,
                        next_status_check_at=CASE WHEN %s='processing' THEN now() + interval '1 minute' ELSE NULL END,
                        updated_at=now()
                    WHERE agent_transaction_id=%s
                    """,
                    (state, int(paid.get("status") or 0), provider_message, json.dumps(paid.get("raw") or {}), state, transaction_id),
                )
                conn.commit()
            if state == "processing":
                return
            if state == "paid":
                gift_code = str((paid.get("params") or {}).get("gift_code") or "").strip()
                if not gift_code:
                    mark_order_for_manual_delivery(order_id, "Interhub подтвердил оплату, но не вернул ключ. Проверьте операцию у поставщика.")
                    return
                try:
                    _collected_qty, _required_qty, duplicate = save_collected_supplier_code(order_id, gift_code)
                except HTTPException:
                    return
                if duplicate:
                    mark_order_for_manual_delivery(order_id, "Interhub вернул повторный ключ. Добавьте недостающий ключ вручную.")
                    return
                process_order_with_suppliers(order_id)
                return

        mark_order_for_manual_delivery(order_id, "Поставщики не выдали ключ. Вставьте ключ вручную или обратитесь в поддержку.")

    def refresh_supplier_attempts() -> None:
        # Проверяет отложенные оплаты Interhub в фоне и не требует от оператора повторно открывать заказ.
        if not interhub_check_status:
            return
        with psycopg.connect(DB_DSN) as conn:
            attempts = qall(
                conn,
                """
                SELECT attempt.id, attempt.order_id, attempt.agent_transaction_id
                FROM app.marketplace_ozon_digital_supplier_attempts AS attempt
                WHERE attempt.state='processing' AND attempt.next_status_check_at <= now()
                ORDER BY attempt.next_status_check_at ASC
                LIMIT 50
                """,
            )
            # Освобождаем блокировку чтения до опроса поставщика, который может отвечать долго.
            conn.commit()
        for attempt in attempts:
            attempt_id, order_id, transaction_id = int(attempt[0]), int(attempt[1]), str(attempt[2])
            try:
                result = interhub_check_status({"agent_transaction_id": transaction_id})
            except Exception as exc:
                result = {"success": False, "status": -1, "message": str(getattr(exc, "detail", exc)), "raw": {}}
            state = provider_state(result)
            message = str(result.get("message") or "")
            save_auto_interhub_result(transaction_id, result)
            with psycopg.connect(DB_DSN) as conn:
                exec1(
                    conn,
                    """
                    UPDATE app.marketplace_ozon_digital_supplier_attempts
                    SET state=%s, provider_status=%s, provider_message=%s, provider_response=%s::jsonb,
                        next_status_check_at=CASE WHEN %s='processing' THEN now() + interval '5 minutes' ELSE NULL END,
                        updated_at=now()
                    WHERE id=%s
                    """,
                    (state, int(result.get("status") or 0), message[:2000], json.dumps(result.get("raw") or {}), state, attempt_id),
                )
                conn.commit()
            if state == "processing":
                continue
            if state == "paid":
                gift_code = str((result.get("params") or {}).get("gift_code") or "").strip()
                if gift_code:
                    try:
                        _collected_qty, _required_qty, duplicate = save_collected_supplier_code(order_id, gift_code)
                    except HTTPException:
                        pass
                    else:
                        if duplicate:
                            mark_order_for_manual_delivery(order_id, "Interhub вернул повторный ключ. Добавьте недостающий ключ вручную.")
                        else:
                            process_order_with_suppliers(order_id)
                else:
                    mark_order_for_manual_delivery(order_id, "Interhub подтвердил оплату, но не вернул ключ. Проверьте операцию у поставщика.")
                continue
            # После финального отказа этой попытки следующий поставщик пробуется с тем же заказом.
            process_order_with_suppliers(order_id)

    def refresh_ozon_digital_supplier_orders() -> None:
        # Раз в минуту забирает заказы только у карточек с включенной авто-выдачей и продолжает ответы поставщика.
        with psycopg.connect(DB_DSN) as conn:
            active_products = qall(
                conn,
                """
                SELECT settings.store_code, settings.external_product_id
                FROM app.marketplace_ozon_digital_settings AS settings
                WHERE settings.auto_issue_enabled=true
                  AND EXISTS (
                    SELECT 1 FROM app.marketplace_ozon_digital_suppliers AS supplier
                    WHERE supplier.store_code=settings.store_code
                      AND supplier.external_product_id=settings.external_product_id
                      AND supplier.enabled=true
                  )
                """,
            )
            # Закрываем транзакцию до сетевых запросов к Ozon и Interhub.
            conn.commit()
        for store_code, product_id in active_products:
            try:
                # Переиспользуем тот же импорт, что и кнопка «Проверить Ozon», чтобы правила сопоставления были одни.
                sync_ozon_digital_orders(int(product_id), store_code=str(store_code))
            except Exception:
                continue
        refresh_supplier_attempts()

    @app.post("/marketplaces/ozon/catalog/sync", response_model=OzonCatalogSyncOut)
    def sync_ozon_catalog(store_code: str = "asat", user=Depends(require_role("admin", "owner"))):
        # Читает карточки Ozon и сохраняет снимок для последующего ручного сопоставления с товарами.
        normalized_store_code = normalize_ozon_store_code(store_code)
        remote_items = fetch_ozon_catalog_items(normalized_store_code)
        synced_at = datetime.now(timezone.utc)

        with psycopg.connect(DB_DSN) as conn:
            for item in remote_items:
                product_id, offer_id, title, visibility, state = normalize_catalog_item(item)
                exec1(
                    conn,
                    """
                    INSERT INTO app.marketplace_ozon_catalog_items(
                      store_code, external_product_id, offer_id, title, visibility, state, raw_payload, synced_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (store_code, external_product_id) DO UPDATE
                    SET offer_id=excluded.offer_id,
                        title=excluded.title,
                        visibility=excluded.visibility,
                        state=excluded.state,
                        raw_payload=excluded.raw_payload,
                        synced_at=excluded.synced_at
                    """,
                    (normalized_store_code, product_id, offer_id, title, visibility, state, json.dumps(item, ensure_ascii=False), synced_at),
                )
            conn.commit()

        return OzonCatalogSyncOut(store_code=normalized_store_code, synced_items=len(remote_items), synced_at=synced_at)

    @app.get("/marketplaces/ozon/catalog", response_model=OzonCatalogListOut)
    def list_ozon_catalog(store_code: str = "asat", user=Depends(get_current_user)):
        # Отдает последний локальный снимок, чтобы UI не дергал Ozon при каждом открытии экрана.
        normalized_store_code = normalize_ozon_store_code(store_code)
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                """
                SELECT external_product_id, offer_id, title, visibility, state, raw_payload, synced_at
                FROM app.marketplace_ozon_catalog_items
                WHERE store_code=%s
                ORDER BY title ASC, external_product_id ASC
                """,
                (normalized_store_code,),
            )
        return OzonCatalogListOut(
            store_code=normalized_store_code,
            items=[
                OzonCatalogItemOut(
                    external_product_id=int(row[0]),
                    offer_id=str(row[1] or ""),
                    sku=catalog_item_sku(row[5]),
                    title=str(row[2] or ""),
                    visibility=str(row[3] or ""),
                    state=str(row[4] or ""),
                    synced_at=row[6],
                )
                for row in rows
            ],
        )

    @app.get("/marketplaces/ozon/catalog/{product_id}", response_model=OzonCatalogDetailsOut)
    def get_ozon_catalog_details(product_id: int, store_code: str = "asat", user=Depends(get_current_user)):
        # Возвращает важные поля уже сохраненного ответа, не повторяя запрос к Ozon при клике в UI.
        normalized_store_code = normalize_ozon_store_code(store_code)
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                """
                SELECT raw_payload, synced_at
                FROM app.marketplace_ozon_catalog_items
                WHERE store_code=%s AND external_product_id=%s
                """,
                (normalized_store_code, product_id),
            )
        if not row:
            raise HTTPException(404, "Ozon catalog item is not found")
        return make_catalog_details(product_id, read_catalog_payload(row[0]), row[1])

    def set_ozon_catalog_archive(product_id: int, archived: bool, store_code: str) -> OzonCatalogArchiveOut:
        # Сначала меняет статус у Ozon, затем помечает локальный снимок для мгновенного обновления интерфейса.
        normalized_store_code = normalize_ozon_store_code(store_code)
        update_ozon_catalog_archive(product_id, archived=archived, store_code=normalized_store_code)
        local_visibility = "ARCHIVED" if archived else "VISIBLE"
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                UPDATE app.marketplace_ozon_catalog_items
                SET visibility=%s
                WHERE store_code=%s AND external_product_id=%s
                """,
                (local_visibility, normalized_store_code, product_id),
            )
            conn.commit()
        return OzonCatalogArchiveOut(external_product_id=product_id, archived=archived)

    @app.post("/marketplaces/ozon/catalog/{product_id}/archive", response_model=OzonCatalogArchiveOut)
    def archive_ozon_catalog_item(product_id: int, store_code: str = "asat", user=Depends(require_role("admin", "owner"))):
        # Переносит выбранную карточку в архив, чтобы ее нельзя было использовать в текущей витрине.
        return set_ozon_catalog_archive(product_id, archived=True, store_code=store_code)

    @app.post("/marketplaces/ozon/catalog/{product_id}/unarchive", response_model=OzonCatalogArchiveOut)
    def unarchive_ozon_catalog_item(product_id: int, store_code: str = "asat", user=Depends(require_role("admin", "owner"))):
        # Возвращает карточку из архива, не меняя ее цену и настройки выдачи ключей.
        return set_ozon_catalog_archive(product_id, archived=False, store_code=store_code)

    @app.get("/marketplaces/ozon/catalog/{product_id}/digital-settings", response_model=OzonDigitalSettingsOut)
    def get_ozon_digital_settings(product_id: int, store_code: str = "asat", user=Depends(get_current_user)):
        # Отдает настройки ручной выдачи до публикации остатка, чтобы карточку можно было подготовить безопасно.
        normalized_store_code = normalize_ozon_store_code(store_code)
        with psycopg.connect(DB_DSN) as conn:
            return make_digital_settings_out(conn, normalized_store_code, product_id)

    @app.put("/marketplaces/ozon/catalog/{product_id}/digital-settings", response_model=OzonDigitalSettingsOut)
    def save_ozon_digital_settings(
        product_id: int,
        payload: OzonDigitalSettingsIn,
        store_code: str = "asat",
        user=Depends(require_role("admin", "owner")),
    ):
        # Сохраняет ручной лимит и сразу публикует безопасный остаток только в выбранную цифровую карточку.
        normalized_store_code = normalize_ozon_store_code(store_code)
        with psycopg.connect(DB_DSN) as conn:
            offer_id = catalog_offer_id(conn, normalized_store_code, product_id, payload.offer_id)
            exec1(
                conn,
                """
                INSERT INTO app.marketplace_ozon_digital_settings(
                  store_code, external_product_id, offer_id, manual_stock_limit, auto_issue_enabled,
                  activation_instruction, support_error_message, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (store_code, external_product_id) DO UPDATE
                SET offer_id=excluded.offer_id,
                    manual_stock_limit=excluded.manual_stock_limit,
                    auto_issue_enabled=excluded.auto_issue_enabled,
                    activation_instruction=excluded.activation_instruction,
                    support_error_message=excluded.support_error_message,
                    updated_at=now()
                """,
                (
                    normalized_store_code,
                    product_id,
                    offer_id,
                    payload.manual_stock_limit,
                    payload.auto_issue_enabled,
                    payload.activation_instruction.strip(),
                    payload.support_error_message.strip(),
                ),
            )
            if payload.interhub_service_id:
                # Связывает карточку с услугой Interhub, но не делает оплату во время сохранения формы.
                exec1(
                    conn,
                    """
                    INSERT INTO app.marketplace_ozon_digital_suppliers(
                      store_code, external_product_id, provider_code, priority, enabled, service_id, nominal_id, updated_at
                    )
                    VALUES (%s, %s, 'interhub', 1, %s, %s, %s, now())
                    ON CONFLICT (store_code, external_product_id, provider_code, priority) DO UPDATE
                    SET enabled=excluded.enabled,
                        service_id=excluded.service_id,
                        nominal_id=excluded.nominal_id,
                        updated_at=now()
                    """,
                    (
                        normalized_store_code,
                        product_id,
                        payload.interhub_enabled,
                        payload.interhub_service_id,
                        payload.interhub_nominal_id.strip(),
                    ),
                )
            else:
                # Отключает прежнюю связку, если оператор очистил услугу, не удаляя историю попыток.
                exec1(
                    conn,
                    """
                    UPDATE app.marketplace_ozon_digital_suppliers
                    SET enabled=false, updated_at=now()
                    WHERE store_code=%s AND external_product_id=%s AND provider_code='interhub' AND priority=1
                    """,
                    (normalized_store_code, product_id),
                )
            conn.commit()

        with psycopg.connect(DB_DSN) as conn:
            settings = publish_available_stock(conn, normalized_store_code, product_id)
            conn.commit()
            return settings

    @app.get("/marketplaces/ozon/catalog/{product_id}/digital-orders", response_model=OzonDigitalOrdersOut)
    def list_ozon_digital_orders(product_id: int, store_code: str = "asat", user=Depends(get_current_user)):
        # Показывает только заказы выбранной карточки и никогда не возвращает введенные ключи обратно в браузер.
        normalized_store_code = normalize_ozon_store_code(store_code)
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                """
                SELECT orders.id, orders.posting_number, orders.order_number, orders.product_name, orders.sku,
                       orders.required_qty, orders.status, orders.ozon_status, orders.waiting_deadline_at,
                       orders.created_at, orders.delivered_at, orders.last_error,
                       COALESCE((
                         SELECT supplier.provider_code
                         FROM app.marketplace_ozon_digital_supplier_attempts AS attempt
                         JOIN app.marketplace_ozon_digital_suppliers AS supplier ON supplier.id=attempt.supplier_id
                         WHERE attempt.order_id=orders.id AND attempt.state='paid'
                         ORDER BY attempt.updated_at DESC, attempt.id DESC
                         LIMIT 1
                       ), ''),
                       orders.delivered_codes
                FROM app.marketplace_ozon_digital_orders AS orders
                WHERE orders.store_code=%s AND orders.external_product_id=%s
                ORDER BY CASE WHEN orders.status='manual_required' THEN 0 ELSE 1 END, orders.created_at DESC NULLS LAST, orders.id DESC
                """,
                (normalized_store_code, product_id),
            )
        return OzonDigitalOrdersOut(
            items=[
                make_order_out(row)
                for row in rows
            ]
        )

    @app.get("/marketplaces/ozon/digital-orders/{order_id}/codes", response_model=OzonDigitalOrderCodesOut)
    def get_ozon_digital_order_codes(
        order_id: int,
        store_code: str = "asat",
        user=Depends(require_role("admin", "owner")),
    ):
        # Возвращает полный ключ только привилегированному пользователю и только после явного запроса из истории.
        normalized_store_code = normalize_ozon_store_code(store_code)
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                """
                SELECT id, delivered_codes
                FROM app.marketplace_ozon_digital_orders
                WHERE id=%s AND store_code=%s
                """,
                (order_id, normalized_store_code),
            )
        if not row:
            raise HTTPException(404, "Цифровой заказ Ozon не найден")
        codes = delivered_codes_from_row(row[1])
        if not codes:
            raise HTTPException(409, "Для этого заказа ключ еще не был отправлен")
        return OzonDigitalOrderCodesOut(id=int(row[0]), codes=codes)

    @app.get("/marketplaces/ozon/digital-orders/{order_id}/supplier-operation", response_model=OzonDigitalSupplierOperationOut)
    def get_ozon_digital_order_supplier_operation(
        order_id: int,
        store_code: str = "asat",
        user=Depends(require_role("admin", "owner")),
    ):
        # Возвращает операцию поставщика, которая действительно выдала ключ для выбранного заказа Ozon.
        normalized_store_code = normalize_ozon_store_code(store_code)
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                """
                SELECT attempt.order_id, supplier.provider_code, attempt.agent_transaction_id,
                       COALESCE(transaction.provider_transaction_id, ''), supplier.service_id, supplier.nominal_id,
                       transaction.amount, attempt.state, attempt.provider_status, attempt.provider_message,
                       attempt.created_at, attempt.updated_at,
                       COALESCE(calculation.service_title, ''), COALESCE(calculation.nominal_title, '')
                FROM app.marketplace_ozon_digital_supplier_attempts AS attempt
                JOIN app.marketplace_ozon_digital_suppliers AS supplier ON supplier.id=attempt.supplier_id
                JOIN app.marketplace_ozon_digital_orders AS orders ON orders.id=attempt.order_id
                LEFT JOIN app.interhub_transactions AS transaction
                  ON transaction.agent_transaction_id=attempt.agent_transaction_id
                LEFT JOIN LATERAL (
                  -- Берём последнюю успешную цену calculate, чтобы в истории показать названия услуги и номинала.
                  SELECT prices.service_title, prices.nominal_title
                  FROM app.interhub_price_calculations AS prices
                  WHERE prices.success=true
                    AND prices.service_id=supplier.service_id
                    AND prices.nominal_id=CASE
                      WHEN supplier.nominal_id ~ '^[0-9]+$' THEN supplier.nominal_id::integer
                      ELSE NULL
                    END
                  ORDER BY prices.calculated_at DESC, prices.id DESC
                  LIMIT 1
                ) AS calculation ON supplier.provider_code='interhub'
                WHERE attempt.order_id=%s
                  AND orders.store_code=%s
                  AND attempt.state='paid'
                ORDER BY attempt.updated_at DESC, attempt.id DESC
                LIMIT 1
                """,
                (order_id, normalized_store_code),
            )
        if not row:
            raise HTTPException(404, "Операция поставщика для этого заказа не найдена")
        return OzonDigitalSupplierOperationOut(
            order_id=int(row[0]),
            provider_code=str(row[1] or ""),
            agent_transaction_id=str(row[2] or ""),
            provider_transaction_id=str(row[3] or ""),
            service_id=int(row[4] or 0),
            nominal_id=str(row[5] or ""),
            service_title=str(row[12] or ""),
            nominal_title=str(row[13] or ""),
            amount=float(row[6]) if row[6] is not None else None,
            state=str(row[7] or ""),
            provider_status=int(row[8] or 0),
            provider_message=str(row[9] or ""),
            created_at=row[10],
            updated_at=row[11],
        )

    @app.post("/marketplaces/ozon/catalog/{product_id}/digital-orders/sync", response_model=OzonDigitalSyncOut)
    def sync_ozon_digital_orders(product_id: int, store_code: str = "asat", user=Depends(require_role("admin", "owner"))):
        # Забирает заказы только выбранной карточки, чтобы работа из окна товара не затрагивала другие ключи.
        selected_product_id = int(product_id)
        normalized_store_code = normalize_ozon_store_code(store_code)
        synced_at = datetime.now(timezone.utc)
        remote_postings = fetch_ozon_digital_postings(synced_at - timedelta(days=14), synced_at, store_code=normalized_store_code)
        active_posting_numbers = {
            str(posting.get("posting_number") or "").strip()
            for posting in remote_postings
            if str(posting.get("posting_number") or "").strip()
        }
        imported_orders = 0

        with psycopg.connect(DB_DSN) as conn:
            settings_rows = qall(
                conn,
                """
                SELECT settings.external_product_id, settings.offer_id, catalog.raw_payload
                FROM app.marketplace_ozon_digital_settings AS settings
                LEFT JOIN app.marketplace_ozon_catalog_items AS catalog
                  ON catalog.store_code=settings.store_code
                 AND catalog.external_product_id=settings.external_product_id
                WHERE settings.store_code=%s AND settings.external_product_id=%s
                """,
                (normalized_store_code, selected_product_id),
            )
            products_by_offer: dict[str, int] = {}
            products_by_sku: dict[int, int] = {}
            for row in settings_rows:
                setting_product_id = int(row[0])
                payload = read_catalog_payload(row[2]) if len(row) > 2 else {}
                for candidate in (row[1], payload.get("offer_id"), payload.get("offer_code")):
                    normalized_offer_id = str(candidate or "").strip()
                    if normalized_offer_id:
                        products_by_offer[normalized_offer_id] = setting_product_id
                for candidate in (payload.get("sku"), payload.get("fbs_sku"), payload.get("fbo_sku")):
                    catalog_sku = optional_int(candidate)
                    if catalog_sku:
                        products_by_sku[catalog_sku] = setting_product_id
            for posting in remote_postings:
                posting_number = str(posting.get("posting_number") or "").strip()
                if not posting_number:
                    continue
                remote_status = str(posting.get("status") or "").strip().lower()
                # Финальный статус Ozon сразу отражаем в нашей очереди, чтобы не предлагать выдачу по отмене.
                local_status = local_digital_order_status(remote_status)
                products = posting.get("products") if isinstance(posting.get("products"), list) else []
                for product in products:
                    if not isinstance(product, dict):
                        continue
                    offer_id = str(product.get("offer_id") or "").strip()
                    sku = optional_int(product.get("sku")) or 0
                    # Сначала сопоставляет по артикулу, а при его смене в Ozon — по стабильному SKU товара.
                    matched_product_id = products_by_offer.get(offer_id) or products_by_sku.get(sku)
                    required_qty = max(1, optional_int(product.get("required_qty_for_digital_code")) or optional_int(product.get("quantity")) or 1)
                    if not matched_product_id or not sku:
                        continue
                    exec1(
                        conn,
                        """
                        INSERT INTO app.marketplace_ozon_digital_orders(
                          store_code, external_product_id, posting_number, order_number, product_name, sku,
                          required_qty, status, ozon_status, waiting_deadline_at, created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (store_code, posting_number, sku) DO UPDATE
                        SET order_number=excluded.order_number,
                            product_name=excluded.product_name,
                            required_qty=excluded.required_qty,
                            ozon_status=excluded.ozon_status,
                            waiting_deadline_at=excluded.waiting_deadline_at,
                            created_at=excluded.created_at,
                            status=CASE
                              WHEN excluded.status='cancelled' THEN 'cancelled'
                              WHEN app.marketplace_ozon_digital_orders.status='delivered' OR excluded.status='delivered' THEN 'delivered'
                              WHEN app.marketplace_ozon_digital_orders.status IN ('supplier_processing', 'delivering') THEN app.marketplace_ozon_digital_orders.status
                              ELSE excluded.status
                            END,
                            delivered_at=CASE
                              WHEN excluded.status='delivered' THEN COALESCE(app.marketplace_ozon_digital_orders.delivered_at, now())
                              ELSE app.marketplace_ozon_digital_orders.delivered_at
                            END,
                            updated_at=now()
                        """,
                        (
                            normalized_store_code,
                            matched_product_id,
                            posting_number,
                            str(posting.get("order_number") or ""),
                            str(product.get("name") or ""),
                            sku,
                            required_qty,
                            local_status,
                            remote_status,
                            posting.get("waiting_deadline_for_digital_code") or None,
                            posting.get("created_at") or None,
                        ),
                    )
                    imported_orders += 1
            exec1(
                conn,
                """
                UPDATE app.marketplace_ozon_digital_settings
                SET last_orders_sync_at=%s, updated_at=now()
                WHERE store_code=%s AND external_product_id=%s
                """,
                (synced_at, normalized_store_code, selected_product_id),
            )
            conn.commit()

        cancel_missing_digital_orders(normalized_store_code, selected_product_id, active_posting_numbers)

        with psycopg.connect(DB_DSN) as conn:
            # Берем только неиспытанные новые заказы: ручной резерв не будет внезапно списывать средства у поставщика.
            queued_rows = qall(
                conn,
                """
                SELECT orders.id
                FROM app.marketplace_ozon_digital_orders AS orders
                JOIN app.marketplace_ozon_digital_settings AS settings
                  ON settings.store_code=orders.store_code
                 AND settings.external_product_id=orders.external_product_id
                WHERE orders.store_code=%s
                  AND orders.external_product_id=%s
                  AND orders.status='manual_required'
                  AND settings.auto_issue_enabled=true
                  AND EXISTS (
                    SELECT 1 FROM app.marketplace_ozon_digital_suppliers AS supplier
                    WHERE supplier.store_code=orders.store_code
                      AND supplier.external_product_id=orders.external_product_id
                      AND supplier.enabled=true
                  )
                  AND NOT EXISTS (
                    SELECT 1 FROM app.marketplace_ozon_digital_supplier_attempts AS attempt
                    WHERE attempt.order_id=orders.id
                  )
                ORDER BY orders.id ASC
                """,
                (normalized_store_code, selected_product_id),
            )
            # Не держим транзакцию, пока ниже запускается автовыдача через внешнего поставщика.
            conn.commit()
        for queued_row in queued_rows:
            process_order_with_suppliers(int(queued_row[0]))

        available_stock = 0
        with psycopg.connect(DB_DSN) as conn:
            # После заказа Ozon сам держит единицу в резерве, поэтому только пересчитываем локальный показатель.
            settings = make_digital_settings_out(conn, normalized_store_code, selected_product_id)
            available_stock = settings.available_stock
        return OzonDigitalSyncOut(imported_orders=imported_orders, available_stock=available_stock, last_orders_sync_at=synced_at)

    @app.post("/marketplaces/ozon/digital-orders/{order_id}/deliver", response_model=OzonDigitalOrderOut)
    def deliver_ozon_digital_order(
        order_id: int,
        payload: OzonDigitalDeliveryIn,
        user=Depends(require_role("admin", "owner")),
    ):
        # Передает вручную введенный ключ через общий безопасный путь выдачи поставщика или оператора.
        codes = [str(code or "").strip() for code in payload.codes if str(code or "").strip()]
        return deliver_ozon_codes(order_id, codes)

    # Передаем стартеру отдельную миграцию, не меняя контракт фоновой функции опроса.
    refresh_ozon_digital_supplier_orders.prepare_schema = prepare_marketplaces_schema
    return refresh_ozon_digital_supplier_orders
