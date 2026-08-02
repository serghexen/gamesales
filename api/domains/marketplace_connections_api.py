from __future__ import annotations

import os
import json
from datetime import date, datetime, timedelta

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field


class MarketplaceConnectionCreateIn(BaseModel):
    provider_code: str
    display_name: str = Field(min_length=1, max_length=120)
    token: str = Field(min_length=8, max_length=4096)
    client_id: str = Field(default="", max_length=128)
    business_id: int | None = Field(default=None, gt=0)
    campaign_id: int | None = Field(default=None, gt=0)


class MarketplaceConnectionDiscoverIn(BaseModel):
    provider_code: str
    token: str = Field(min_length=8, max_length=4096)
    client_id: str = Field(default="", max_length=128)


class MarketplaceConnectionCandidateOut(BaseModel):
    business_id: int
    campaign_id: int
    display_name: str


class MarketplaceConnectionDiscoverOut(BaseModel):
    provider_code: str
    items: list[MarketplaceConnectionCandidateOut]


class MarketplaceConnectionOut(BaseModel):
    id: int
    provider_code: str
    display_name: str
    client_id: str = ""
    business_id: int | None = None
    campaign_id: int | None = None
    token_masked: str
    status: str
    last_checked_at: datetime | None = None
    last_error: str = ""
    created_at: datetime


class MarketplaceConnectionListOut(BaseModel):
    workspace_name: str
    items: list[MarketplaceConnectionOut]


class MarketplaceCatalogItemOut(BaseModel):
    external_product_id: str
    offer_id: str = ""
    sku: str = ""
    title: str = ""
    status: str = ""
    synced_at: datetime


class MarketplaceCatalogOut(BaseModel):
    connection_id: int
    items: list[MarketplaceCatalogItemOut]


class MarketplaceCatalogSyncOut(BaseModel):
    connection_id: int
    synced_items: int
    synced_at: datetime


class MarketplaceWorkspaceCatalogItemOut(MarketplaceCatalogItemOut):
    connection_id: int
    connection_name: str
    provider_code: str


class MarketplaceWorkspaceCatalogOut(BaseModel):
    items: list[MarketplaceWorkspaceCatalogItemOut]


class MarketplaceOrderItemOut(BaseModel):
    external_order_id: str
    external_item_id: str
    offer_id: str = ""
    sku: str = ""
    title: str = ""
    quantity: int = 1
    status: str = ""
    substatus: str = ""
    normalized_status: str = "problem"
    delivery_type: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    synced_at: datetime


class MarketplaceWorkspaceOrderItemOut(MarketplaceOrderItemOut):
    connection_id: int
    connection_name: str
    provider_code: str


class MarketplaceWorkspaceOrdersOut(BaseModel):
    items: list[MarketplaceWorkspaceOrderItemOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class MarketplaceOrdersSyncOut(BaseModel):
    connection_id: int
    synced_items: int
    synced_at: datetime


def mount_marketplace_connection_routes(
    app, *, DB_DSN, psycopg, q1, qall, get_current_user,
    verify_ozon_connection, discover_yandex_market_stores, fetch_marketplace_catalog, fetch_marketplace_orders,
    normalize_marketplace_order_status,
):
    def credentials_secret() -> str:
        # Берет отдельный ключ шифрования реквизитов, чтобы токен магазина не хранился в открытом виде.
        secret = str(os.getenv("MARKETPLACE_CREDENTIALS_SECRET", "")).strip()
        if len(secret) < 32:
            raise HTTPException(503, "Для подключения магазинов задайте MARKETPLACE_CREDENTIALS_SECRET длиной не менее 32 символов")
        return secret

    def normalize_provider(value: str) -> str:
        # Ограничивает подключение известными адаптерами, не создавая записи для неподдерживаемых маркетплейсов.
        provider_code = str(value or "").strip().lower()
        if provider_code not in {"ozon", "yandex_market"}:
            raise HTTPException(400, "Поддерживаются только Ozon и Яндекс Маркет")
        return provider_code

    def token_mask(value: str) -> str:
        # Отдает в браузер только конец токена, достаточный для распознавания нужного подключения.
        suffix = str(value or "").strip()[-4:]
        return f"••••{suffix}" if suffix else "••••"

    def current_workspace(conn, username: str) -> tuple[int, str]:
        # Создает персональное пространство при первом входе и возвращает только пространство текущего пользователя.
        user_row = q1(conn, "SELECT user_id FROM app.users WHERE username=%s", (username,))
        if not user_row:
            raise HTTPException(401, "Пользователь не найден")
        user_id = int(user_row[0])
        member_row = q1(
            conn,
            """
            SELECT workspace.id, workspace.name
            FROM marketplace.workspace_members AS member
            JOIN marketplace.workspaces AS workspace ON workspace.id=member.workspace_id
            WHERE member.user_id=%s
            ORDER BY CASE member.role_code WHEN 'owner' THEN 0 ELSE 1 END, workspace.id
            LIMIT 1
            """,
            (user_id,),
        )
        if member_row:
            return int(member_row[0]), str(member_row[1])
        workspace_row = q1(
            conn,
            """
            INSERT INTO marketplace.workspaces(name, owner_user_id)
            VALUES (%s, %s)
            RETURNING id, name
            """,
            (f"{username} — Marketplace", user_id),
        )
        workspace_id, workspace_name = int(workspace_row[0]), str(workspace_row[1])
        q1(
            conn,
            """
            INSERT INTO marketplace.workspace_members(workspace_id, user_id, role_code)
            VALUES (%s, %s, 'owner')
            ON CONFLICT (workspace_id, user_id) DO NOTHING
            RETURNING workspace_id
            """,
            (workspace_id, user_id),
        )
        return workspace_id, workspace_name

    def connection_out(row) -> MarketplaceConnectionOut:
        # Преобразует строку подключения в безопасный контракт, не раскрывая зашифрованный токен.
        return MarketplaceConnectionOut(
            id=int(row[0]),
            provider_code=str(row[1]),
            display_name=str(row[2]),
            client_id=str(row[3] or ""),
            business_id=row[4],
            campaign_id=row[5],
            token_masked=token_mask(str(row[6] or "")),
            status=str(row[7]),
            last_checked_at=row[8],
            last_error=str(row[9] or ""),
            created_at=row[10],
        )

    def catalog_payload_fields(provider_code: str, payload: dict) -> tuple[str, str, str, str, str]:
        # Выбирает стабильные поля карточки из ответов разных маркетплейсов перед сохранением локального снимка.
        if provider_code == "ozon":
            product_id = str(payload.get("product_id") or payload.get("id") or "").strip()
            sources = payload.get("sources") if isinstance(payload.get("sources"), list) else []
            source_skus = [source.get("sku") for source in sources if isinstance(source, dict)]
            sku = next((str(value).strip() for value in [payload.get("sku"), *source_skus, payload.get("fbs_sku"), payload.get("fbo_sku")] if str(value or "").strip()), "")
            return product_id, str(payload.get("offer_id") or ""), sku, str(payload.get("name") or payload.get("product_name") or ""), str(payload.get("visibility") or "")
        offer = payload.get("offer") if isinstance(payload.get("offer"), dict) else {}
        mapping = payload.get("mapping") if isinstance(payload.get("mapping"), dict) else {}
        offer_id = str(offer.get("offerId") or offer.get("offer_id") or "").strip()
        product_id = str(mapping.get("marketSku") or mapping.get("market_sku") or offer_id).strip()
        return product_id, offer_id, offer_id, str(mapping.get("name") or offer.get("name") or ""), str(mapping.get("status") or "")

    def optional_datetime(value: object) -> datetime | None:
        # Приводит дату внешнего API к единому виду и пропускает неизвестные форматы без падения синхронизации.
        text = str(value or "").strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.astimezone() if parsed.tzinfo else parsed.astimezone()

    def first_text(*values: object) -> str:
        # Берет первое непустое значение из различающихся контрактов Ozon и Яндекс Маркета.
        return next((str(value).strip() for value in values if str(value or "").strip()), "")

    def order_item_fields(provider_code: str, payload: dict) -> list[dict[str, object]]:
        # Нормализует только безопасные поля позиций заказа, не сохраняя покупателя или адрес доставки.
        if provider_code == "ozon":
            order_id = first_text(payload.get("posting_number"), payload.get("order_number"), payload.get("order_id"))
            products = payload.get("products") if isinstance(payload.get("products"), list) else []
            rows: list[dict[str, object]] = []
            for index, product in enumerate(products, start=1):
                if not isinstance(product, dict) or not order_id:
                    continue
                offer_id = first_text(product.get("offer_id"))
                sku = first_text(product.get("sku"))
                rows.append({
                    "external_order_id": order_id,
                    "external_item_id": first_text(product.get("id"), sku, offer_id, index),
                    "offer_id": offer_id,
                    "sku": sku,
                    "title": first_text(product.get("name"), product.get("product_name"), offer_id),
                    "quantity": max(0, int(product.get("quantity") or 1)),
                    "status": first_text(payload.get("status")),
                    "substatus": first_text(payload.get("substatus")),
                    "delivery_type": first_text(payload.get("__marketplace_source"), "DIGITAL"),
                    "created_at": optional_datetime(first_text(payload.get("in_process_at"), payload.get("created_at"))),
                    "updated_at": optional_datetime(first_text(payload.get("updated_at"), payload.get("status_updated_at"))),
                })
            return rows
        order_id = first_text(payload.get("orderId"), payload.get("id"))
        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        rows = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict) or not order_id:
                continue
            digital_delivery = item.get("digitalDelivery") if isinstance(item.get("digitalDelivery"), dict) else {}
            offer_id = first_text(item.get("offerId"), item.get("offer_id"))
            sku = first_text(item.get("sku"), item.get("marketSku"))
            rows.append({
                "external_order_id": order_id,
                "external_item_id": first_text(item.get("id"), sku, offer_id, index),
                "offer_id": offer_id,
                "sku": sku,
                "title": first_text(item.get("offerName"), item.get("name"), offer_id),
                "quantity": max(0, int(item.get("count") or item.get("quantity") or 1)),
                "status": first_text(payload.get("status")),
                "substatus": first_text(payload.get("substatus")),
                "delivery_type": first_text(item.get("deliveryType"), digital_delivery.get("type"), payload.get("deliveryType")),
                "created_at": optional_datetime(first_text(payload.get("creationDate"), payload.get("created_at"))),
                "updated_at": optional_datetime(first_text(payload.get("updateDate"), payload.get("updatedAt"))),
            })
        return rows

    def read_connection_for_workspace(conn, *, connection_id: int, workspace_id: int, secret: str):
        # Расшифровывает токен только внутри API перед read-only запросом выбранного магазина текущего пользователя.
        row = q1(conn, """
            SELECT id, provider_code, client_id, business_id, campaign_id, pgp_sym_decrypt(token_ciphertext, %s)
            FROM marketplace.connections
            WHERE id=%s AND workspace_id=%s AND status='active'
        """, (secret, connection_id, workspace_id))
        if not row:
            raise HTTPException(404, "Активный подключенный магазин не найден")
        return row

    @app.post("/marketplace/connections/discover", response_model=MarketplaceConnectionDiscoverOut)
    def discover_marketplace_connection(payload: MarketplaceConnectionDiscoverIn, user=Depends(get_current_user)):
        # Проверяет реквизиты до сохранения: Ozon подтверждает пару ключей, Маркет возвращает доступные магазины.
        provider_code = normalize_provider(payload.provider_code)
        token = str(payload.token or "").strip()
        client_id = str(payload.client_id or "").strip()
        if provider_code == "ozon":
            if not client_id:
                raise HTTPException(400, "Для Ozon укажите Client ID кабинета")
            verify_ozon_connection(client_id=client_id, token=token)
            return MarketplaceConnectionDiscoverOut(provider_code=provider_code, items=[])
        stores = discover_yandex_market_stores(token=token)
        return MarketplaceConnectionDiscoverOut(
            provider_code=provider_code,
            items=[MarketplaceConnectionCandidateOut(**store) for store in stores],
        )

    @app.get("/marketplace/connections", response_model=MarketplaceConnectionListOut)
    def list_marketplace_connections(user=Depends(get_current_user)):
        # Показывает пользователю только его рабочее пространство и подключенные в нем кабинеты.
        with psycopg.connect(DB_DSN) as conn:
            workspace_id, workspace_name = current_workspace(conn, str(user.username))
            rows = qall(
                conn,
                """
                SELECT id, provider_code, display_name, client_id, business_id, campaign_id, token_suffix, status, last_checked_at, last_error, created_at
                FROM marketplace.connections
                WHERE workspace_id=%s
                ORDER BY created_at DESC, id DESC
                """,
                (workspace_id,),
            )
            conn.commit()
        return MarketplaceConnectionListOut(workspace_name=workspace_name, items=[connection_out(row) for row in rows])

    @app.post("/marketplace/connections", response_model=MarketplaceConnectionOut, status_code=201)
    def create_marketplace_connection(payload: MarketplaceConnectionCreateIn, user=Depends(get_current_user)):
        # Сохраняет только проверенные реквизиты магазина, не включая автосинхронизацию и выдачу ключей.
        provider_code = normalize_provider(payload.provider_code)
        display_name = str(payload.display_name or "").strip()
        token = str(payload.token or "").strip()
        client_id = str(payload.client_id or "").strip()
        if provider_code == "ozon" and not client_id:
            raise HTTPException(400, "Для Ozon укажите Client ID кабинета")
        if provider_code == "ozon":
            verify_ozon_connection(client_id=client_id, token=token)
        if provider_code == "yandex_market" and (not payload.business_id or not payload.campaign_id):
            raise HTTPException(400, "Сначала выберите магазин Яндекс Маркета из найденных кабинетов")
        if provider_code == "yandex_market":
            discovered_stores = discover_yandex_market_stores(token=token)
            selected = {
                (int(store["business_id"]), int(store["campaign_id"]))
                for store in discovered_stores
            }
            if (int(payload.business_id), int(payload.campaign_id)) not in selected:
                raise HTTPException(400, "Выбранный магазин больше не доступен этому API-Key")
        secret = credentials_secret()
        with psycopg.connect(DB_DSN) as conn:
            workspace_id, _workspace_name = current_workspace(conn, str(user.username))
            user_row = q1(conn, "SELECT user_id FROM app.users WHERE username=%s", (str(user.username),))
            if provider_code == "ozon":
                row = q1(conn, """
                    INSERT INTO marketplace.connections(workspace_id, provider_code, display_name, client_id, token_ciphertext, token_suffix, status, last_checked_at, created_by_user_id)
                    VALUES (%s, %s, %s, %s, pgp_sym_encrypt(%s, %s, 'cipher-algo=aes256, compress-algo=0'), %s, 'active', now(), %s)
                    ON CONFLICT (workspace_id, provider_code, client_id) WHERE provider_code='ozon'
                    DO UPDATE SET display_name=excluded.display_name, token_ciphertext=excluded.token_ciphertext, token_suffix=excluded.token_suffix, status='active', last_checked_at=now(), last_error='', updated_at=now()
                    RETURNING id, provider_code, display_name, client_id, business_id, campaign_id, token_suffix, status, last_checked_at, last_error, created_at
                """, (workspace_id, provider_code, display_name, client_id, token, secret, token[-4:], int(user_row[0])))
            else:
                row = q1(conn, """
                    INSERT INTO marketplace.connections(workspace_id, provider_code, display_name, client_id, business_id, campaign_id, token_ciphertext, token_suffix, status, last_checked_at, created_by_user_id)
                    VALUES (%s, %s, %s, '', %s, %s, pgp_sym_encrypt(%s, %s, 'cipher-algo=aes256, compress-algo=0'), %s, 'active', now(), %s)
                    ON CONFLICT (workspace_id, provider_code, campaign_id) WHERE campaign_id IS NOT NULL
                    DO UPDATE SET display_name=excluded.display_name, business_id=excluded.business_id, token_ciphertext=excluded.token_ciphertext, token_suffix=excluded.token_suffix, status='active', last_checked_at=now(), last_error='', updated_at=now()
                    RETURNING id, provider_code, display_name, client_id, business_id, campaign_id, token_suffix, status, last_checked_at, last_error, created_at
                """, (workspace_id, provider_code, display_name, int(payload.business_id), int(payload.campaign_id), token, secret, token[-4:], int(user_row[0])))
            conn.commit()
        return connection_out(row)

    @app.delete("/marketplace/connections/{connection_id}", status_code=204)
    def delete_marketplace_connection(connection_id: int, user=Depends(get_current_user)):
        # Отключает только кабинет текущего пространства и никогда не принимает идентификатор чужого клиента.
        with psycopg.connect(DB_DSN) as conn:
            workspace_id, _workspace_name = current_workspace(conn, str(user.username))
            removed = q1(
                conn,
                "DELETE FROM marketplace.connections WHERE id=%s AND workspace_id=%s RETURNING id",
                (connection_id, workspace_id),
            )
            conn.commit()
        if not removed:
            raise HTTPException(404, "Подключенный магазин не найден")

    @app.get("/marketplace/connections/{connection_id}/catalog", response_model=MarketplaceCatalogOut)
    def list_marketplace_catalog(connection_id: int, user=Depends(get_current_user)):
        # Отдает последний локальный снимок каталога без нового запроса к внешнему маркетплейсу.
        with psycopg.connect(DB_DSN) as conn:
            workspace_id, _workspace_name = current_workspace(conn, str(user.username))
            exists = q1(conn, "SELECT id FROM marketplace.connections WHERE id=%s AND workspace_id=%s", (connection_id, workspace_id))
            if not exists:
                raise HTTPException(404, "Подключенный магазин не найден")
            rows = qall(conn, """
                SELECT external_product_id, offer_id, sku, title, status, synced_at
                FROM marketplace.catalog_items WHERE connection_id=%s
                ORDER BY title, external_product_id
            """, (connection_id,))
        return MarketplaceCatalogOut(connection_id=connection_id, items=[MarketplaceCatalogItemOut(external_product_id=str(row[0]), offer_id=str(row[1] or ""), sku=str(row[2] or ""), title=str(row[3] or ""), status=str(row[4] or ""), synced_at=row[5]) for row in rows])

    @app.get("/marketplace/catalog", response_model=MarketplaceWorkspaceCatalogOut)
    def list_workspace_marketplace_catalog(
        query: str = "",
        connection_id: int | None = None,
        user=Depends(get_current_user),
    ):
        # Собирает единый снимок каталога пространства, чтобы поиск не требовал заходить в каждый магазин отдельно.
        search_query = str(query or "").strip()[:200]
        filters = ["connection.workspace_id=%s"]
        params: list[object] = []
        with psycopg.connect(DB_DSN) as conn:
            workspace_id, _workspace_name = current_workspace(conn, str(user.username))
            params.append(workspace_id)
            if connection_id is not None:
                filters.append("item.connection_id=%s")
                params.append(connection_id)
            if search_query:
                filters.append("(item.title ILIKE %s OR item.offer_id ILIKE %s OR item.sku ILIKE %s OR item.external_product_id ILIKE %s)")
                params.extend([f"%{search_query}%"] * 4)
            rows = qall(conn, f"""
                SELECT item.external_product_id, item.offer_id, item.sku, item.title, item.status, item.synced_at,
                       connection.id, connection.display_name, connection.provider_code
                FROM marketplace.catalog_items AS item
                JOIN marketplace.connections AS connection ON connection.id=item.connection_id
                WHERE {' AND '.join(filters)}
                ORDER BY item.title, item.offer_id, item.external_product_id
                LIMIT 1000
            """, tuple(params))
        return MarketplaceWorkspaceCatalogOut(items=[
            MarketplaceWorkspaceCatalogItemOut(
                external_product_id=str(row[0]),
                offer_id=str(row[1] or ""),
                sku=str(row[2] or ""),
                title=str(row[3] or ""),
                status=str(row[4] or ""),
                synced_at=row[5],
                connection_id=int(row[6]),
                connection_name=str(row[7]),
                provider_code=str(row[8]),
            )
            for row in rows
        ])

    @app.post("/marketplace/connections/{connection_id}/catalog/sync", response_model=MarketplaceCatalogSyncOut)
    def sync_marketplace_catalog(connection_id: int, user=Depends(get_current_user)):
        # Читает каталог во внешнем API и сохраняет снимок, не вызывая ни одного метода изменения маркетплейса.
        secret = credentials_secret()
        with psycopg.connect(DB_DSN) as conn:
            workspace_id, _workspace_name = current_workspace(conn, str(user.username))
            connection = read_connection_for_workspace(conn, connection_id=connection_id, workspace_id=workspace_id, secret=secret)
            provider_code, client_id, business_id, token = str(connection[1]), str(connection[2] or ""), connection[3], str(connection[5])
        remote_items = fetch_marketplace_catalog(provider_code=provider_code, token=token, client_id=client_id, business_id=business_id)
        synced_at = datetime.now().astimezone()
        saved_count = 0
        with psycopg.connect(DB_DSN) as conn:
            for payload in remote_items:
                external_product_id, offer_id, sku, title, status = catalog_payload_fields(provider_code, payload)
                if not external_product_id:
                    continue
                q1(conn, """
                    INSERT INTO marketplace.catalog_items(connection_id, external_product_id, offer_id, sku, title, status, raw_payload, synced_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (connection_id, external_product_id) DO UPDATE SET offer_id=excluded.offer_id, sku=excluded.sku, title=excluded.title, status=excluded.status, raw_payload=excluded.raw_payload, synced_at=excluded.synced_at
                    RETURNING external_product_id
                """, (connection_id, external_product_id, offer_id, sku, title, status, json.dumps(payload, ensure_ascii=False), synced_at))
                saved_count += 1
            conn.commit()
        return MarketplaceCatalogSyncOut(connection_id=connection_id, synced_items=saved_count, synced_at=synced_at)

    @app.get("/marketplace/orders", response_model=MarketplaceWorkspaceOrdersOut)
    def list_workspace_marketplace_orders(
        query: str = "",
        connection_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        status: str = "",
        page: int = 1,
        page_size: int = 20,
        user=Depends(get_current_user),
    ):
        # Показывает отфильтрованный локальный снимок заказов без запроса во внешний API.
        search_query = str(query or "").strip()[:200]
        normalized_status = str(status or "").strip().lower()
        supported_statuses = {"processing", "in_delivery", "delivered", "cancelled", "problem"}
        if normalized_status and normalized_status not in supported_statuses:
            raise HTTPException(422, "Неизвестный статус заказа")
        if date_from and date_to and date_from > date_to:
            raise HTTPException(422, "Дата начала периода не может быть позже даты окончания")
        if page < 1 or not 1 <= page_size <= 50:
            raise HTTPException(422, "Некорректные параметры страницы заказов")
        filters = ["connection.workspace_id=%s"]
        params: list[object] = []
        with psycopg.connect(DB_DSN) as conn:
            workspace_id, _workspace_name = current_workspace(conn, str(user.username))
            params.append(workspace_id)
            if connection_id is not None:
                filters.append("item.connection_id=%s")
                params.append(connection_id)
            if search_query:
                filters.append("(item.external_order_id ILIKE %s OR item.title ILIKE %s OR item.offer_id ILIKE %s OR item.sku ILIKE %s)")
                params.extend([f"%{search_query}%"] * 4)
            if normalized_status:
                filters.append("item.normalized_status=%s")
                params.append(normalized_status)
            if date_from:
                filters.append("item.created_at >= %s")
                params.append(date_from)
            if date_to:
                # Верхняя граница берется как начало следующего дня, чтобы выбранная дата входила целиком.
                filters.append("item.created_at < %s")
                params.append(date_to + timedelta(days=1))
            where_sql = " AND ".join(filters)
            total_row = q1(conn, f"""
                SELECT COUNT(*)
                FROM marketplace.order_items AS item
                JOIN marketplace.connections AS connection ON connection.id=item.connection_id
                WHERE {where_sql}
            """, tuple(params))
            total = max(0, int(total_row[0] if total_row else 0))
            offset = (page - 1) * page_size
            rows = qall(conn, f"""
                SELECT item.external_order_id, item.external_item_id, item.offer_id, item.sku, item.title,
                       item.quantity, item.status, item.substatus, item.normalized_status, item.delivery_type,
                       item.created_at, item.updated_at, item.synced_at, connection.id, connection.display_name, connection.provider_code
                FROM marketplace.order_items AS item
                JOIN marketplace.connections AS connection ON connection.id=item.connection_id
                WHERE {where_sql}
                ORDER BY item.created_at DESC NULLS LAST, item.synced_at DESC, item.external_order_id DESC
                LIMIT %s OFFSET %s
            """, (*params, page_size, offset))
        return MarketplaceWorkspaceOrdersOut(items=[
            MarketplaceWorkspaceOrderItemOut(
                external_order_id=str(row[0]), external_item_id=str(row[1]), offer_id=str(row[2] or ""),
                sku=str(row[3] or ""), title=str(row[4] or ""), quantity=max(0, int(row[5] or 0)),
                status=str(row[6] or ""), substatus=str(row[7] or ""), normalized_status=str(row[8] or "problem"),
                delivery_type=str(row[9] or ""), created_at=row[10], updated_at=row[11], synced_at=row[12],
                connection_id=int(row[13]), connection_name=str(row[14]), provider_code=str(row[15]),
            )
            for row in rows
        ], total=total, page=page, page_size=page_size, total_pages=max(1, (total + page_size - 1) // page_size))

    @app.post("/marketplace/connections/{connection_id}/orders/sync", response_model=MarketplaceOrdersSyncOut)
    def sync_marketplace_orders(connection_id: int, user=Depends(get_current_user)):
        # Читает заказы внешнего API и сохраняет снимок, не вызывая выдачу, чат или подтверждение доставки.
        secret = credentials_secret()
        with psycopg.connect(DB_DSN) as conn:
            workspace_id, _workspace_name = current_workspace(conn, str(user.username))
            connection = read_connection_for_workspace(conn, connection_id=connection_id, workspace_id=workspace_id, secret=secret)
            provider_code, client_id, business_id, campaign_id, token = (
                str(connection[1]), str(connection[2] or ""), connection[3], connection[4], str(connection[5]),
            )
        remote_orders = fetch_marketplace_orders(
            provider_code=provider_code, token=token, client_id=client_id,
            business_id=business_id, campaign_id=campaign_id,
        )
        synced_at = datetime.now().astimezone()
        saved_count = 0
        with psycopg.connect(DB_DSN) as conn:
            for payload in remote_orders:
                for item in order_item_fields(provider_code, payload):
                    normalized_status = normalize_marketplace_order_status(
                        provider_code=provider_code, status=str(item["status"]), substatus=str(item["substatus"]),
                    )
                    q1(conn, """
                        INSERT INTO marketplace.order_items(
                          connection_id, external_order_id, external_item_id, offer_id, sku, title, quantity,
                          status, substatus, normalized_status, delivery_type, created_at, updated_at, synced_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (connection_id, external_order_id, external_item_id) DO UPDATE
                        SET offer_id=excluded.offer_id, sku=excluded.sku, title=excluded.title,
                            quantity=excluded.quantity, status=excluded.status, substatus=excluded.substatus,
                            normalized_status=excluded.normalized_status, delivery_type=excluded.delivery_type, created_at=excluded.created_at,
                            updated_at=excluded.updated_at, synced_at=excluded.synced_at
                        RETURNING external_order_id
                    """, (
                        connection_id, item["external_order_id"], item["external_item_id"], item["offer_id"],
                        item["sku"], item["title"], item["quantity"], item["status"], item["substatus"], normalized_status,
                        item["delivery_type"], item["created_at"], item["updated_at"], synced_at,
                    ))
                    saved_count += 1
            conn.commit()
        return MarketplaceOrdersSyncOut(connection_id=connection_id, synced_items=saved_count, synced_at=synced_at)
