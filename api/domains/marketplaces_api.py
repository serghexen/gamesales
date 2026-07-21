from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import json

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from .ozon_service import fetch_ozon_catalog_items, normalize_ozon_store_code


class OzonCatalogItemOut(BaseModel):
    external_product_id: int
    offer_id: str = ""
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


class OzonCatalogDetailsOut(BaseModel):
    external_product_id: int
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

    def normalize_catalog_item(item: dict[str, Any]) -> tuple[int, str, str, str, str]:
        # Выбирает стабильные поля карточки из ответа Ozon и отбрасывает неполные элементы.
        raw_product_id = item.get("product_id") or item.get("id")
        try:
            external_product_id = int(raw_product_id)
        except (TypeError, ValueError):
            raise HTTPException(502, "Ozon catalog item does not contain product_id")
        offer_id = str(item.get("offer_id") or "").strip()
        title = str(item.get("name") or item.get("title") or "").strip()
        visibility = str(item.get("visibility") or "").strip()
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
        available_stock = sum(optional_int(stock.get("present")) or 0 for stock in stock_rows if isinstance(stock, dict))
        return OzonCatalogDetailsOut(
            external_product_id=product_id,
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

    @app.post("/marketplaces/ozon/catalog/sync", response_model=OzonCatalogSyncOut)
    def sync_ozon_catalog(store_code: str = "asat", user=Depends(require_role("admin", "owner"))):
        # Читает карточки Ozon и сохраняет снимок для последующего ручного сопоставления с товарами.
        normalized_store_code = normalize_ozon_store_code(store_code)
        remote_items = fetch_ozon_catalog_items(normalized_store_code)
        synced_at = datetime.now(timezone.utc)

        with psycopg.connect(DB_DSN) as conn:
            ensure_marketplaces_schema(conn)
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
            ensure_marketplaces_schema(conn)
            rows = qall(
                conn,
                """
                SELECT external_product_id, offer_id, title, visibility, state, synced_at
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
                    title=str(row[2] or ""),
                    visibility=str(row[3] or ""),
                    state=str(row[4] or ""),
                    synced_at=row[5],
                )
                for row in rows
            ],
        )

    @app.get("/marketplaces/ozon/catalog/{product_id}", response_model=OzonCatalogDetailsOut)
    def get_ozon_catalog_details(product_id: int, store_code: str = "asat", user=Depends(get_current_user)):
        # Возвращает важные поля уже сохраненного ответа, не повторяя запрос к Ozon при клике в UI.
        normalized_store_code = normalize_ozon_store_code(store_code)
        with psycopg.connect(DB_DSN) as conn:
            ensure_marketplaces_schema(conn)
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
