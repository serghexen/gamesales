from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import Depends, HTTPException

from .deals_models import RentalCreate, DealCreate, DealUpdate, DealListItem, DealListOut


def mount_deals_routes(
    app,
    *,
    DB_DSN,
    psycopg,
    q1,
    qall,
    exec1,
    now_utc,
    validate_date_in_range,
    validate_date_range,
    ensure_account_exists,
    ensure_source_exists,
    ensure_account_allows_slot_type,
    get_platform_id,
    get_region_id,
    get_account_slot_free,
    ensure_customer,
    get_slot_type,
    account_has_ps4,
    release_slot_assignment,
    build_deals_filters,
    slots_summary,
    get_current_user,
    publish_deal_event=None,
):
    # Нормализуем текстовые поля клиента, чтобы в БД не попадали пустые строки.
    def normalize_customer_field(value: Optional[str]) -> Optional[str]:
        normalized = (value or "").strip()
        return normalized or None

    # Проверяет привилегии пользователя для операций с завершенными/возвратными сделками.
    def has_completed_deal_access(user) -> bool:
        role = (getattr(user, "role", "") or "").strip().lower()
        username = (getattr(user, "username", "") or "").strip().lower()
        return role in {"admin", "administrator", "owner"} or username in {"admin", "owner"}

    # Находит owner и возвращает отображаемое имя для поля "Ответственный".
    def resolve_owner_responsible_name(conn) -> str:
        row = q1(
            conn,
            """
            SELECT name, username
            FROM app.users
            WHERE lower(role_code)='owner'
            ORDER BY user_id ASC
            LIMIT 1
            """,
        )
        owner_name = str(row[0]).strip() if row and row[0] is not None else ""
        owner_username = str(row[1]).strip() if row and len(row) > 1 and row[1] is not None else ""
        resolved_name = owner_name or owner_username
        if not resolved_name:
            raise HTTPException(400, "owner user not found")
        return resolved_name

    # Обновляем дополнительные поля клиента только когда пришли непустые значения.
    def update_customer_credentials(conn, customer_id: Optional[int], login: Optional[str], password: Optional[str]):
        if not customer_id:
            return
        customer_login = normalize_customer_field(login)
        customer_password = normalize_customer_field(password)
        if customer_login is None and customer_password is None:
            return
        updates = []
        params = []
        if customer_login is not None:
            updates.append("customer_login=%s")
            params.append(customer_login)
        if customer_password is not None:
            updates.append("customer_password=%s")
            params.append(customer_password)
        if not updates:
            return
        params.append(customer_id)
        exec1(conn, f"UPDATE app.customers SET {', '.join(updates)} WHERE customer_id=%s", tuple(params))

    # Проверяет уникальность номера заказа для market-источников в связке (source_id, order_number).
    def validate_market_order_number_unique(
        conn,
        source_id: Optional[int],
        order_number: Optional[str],
        exclude_deal_id: Optional[int] = None,
    ):
        normalized_order = (order_number or "").strip()
        if not source_id or not normalized_order:
            return
        source_row = q1(
            conn,
            "SELECT code FROM app.sources WHERE source_id=%s AND is_archived IS NOT TRUE",
            (source_id,),
        )
        source_code = str(source_row[0] or "") if source_row else ""
        # Правило включается только для источников, где код содержит market.
        if "market" not in source_code.lower():
            return
        # Разделяем запросы на две ветки, чтобы Postgres не получал "безтиповый" NULL-параметр.
        if exclude_deal_id is None:
            conflict_row = q1(
                conn,
                """
                SELECT d.deal_id
                FROM app.deals d
                JOIN app.customers c ON c.customer_id = d.customer_id
                WHERE c.source_id=%s
                  AND lower(btrim(COALESCE(d.order_number, ''))) = lower(btrim(%s))
                LIMIT 1
                """,
                (source_id, normalized_order),
            )
        else:
            conflict_row = q1(
                conn,
                """
                SELECT d.deal_id
                FROM app.deals d
                JOIN app.customers c ON c.customer_id = d.customer_id
                WHERE c.source_id=%s
                  AND lower(btrim(COALESCE(d.order_number, ''))) = lower(btrim(%s))
                  AND d.deal_id <> %s
                LIMIT 1
                """,
                (source_id, normalized_order, exclude_deal_id),
            )
        if conflict_row:
            raise HTTPException(409, "order_number must be unique for market source")

    # Валидирует product_id и тип товара для операций со сделками.
    def validate_deal_product_id(
        conn,
        *,
        product_id: Optional[int],
        for_rental: bool,
        must_be_active: bool,
    ) -> Optional[int]:
        if product_id is None:
            return None
        # Параметр оставлен для совместимости сигнатуры в текущем этапе миграции.
        _ = must_be_active
        row = q1(
            conn,
            """
            SELECT type_code, is_archived
            FROM app.products
            WHERE product_id=%s
            """,
            (product_id,),
        )
        if not row:
            raise HTTPException(400, f"Unknown product_id: {product_id}")
        type_code = str(row[0] or "").strip().lower()
        is_archived = bool(row[1]) if row[1] is not None else False
        if is_archived:
            raise HTTPException(400, f"Product is archived: {product_id}")
        if for_rental and type_code != "game":
            raise HTTPException(400, "rental supports only products with type game")
        return None

    @app.post("/rentals")
    def create_rental(payload: RentalCreate, user=Depends(get_current_user)):
        if not payload.slot_type_code:
            raise HTTPException(400, "slot_type_code is required for rental")
        if not payload.product_id:
            raise HTTPException(400, "product_id is required for rental")
        validate_date_in_range(payload.purchase_at, "purchase_at")
        validate_date_in_range(payload.start_at, "start_at")
        validate_date_in_range(payload.end_at, "end_at")
        validate_date_range(payload.start_at, payload.end_at, "end_at")
    
        start_at = payload.start_at or now_utc()
        end_at = payload.end_at
    
        with psycopg.connect(DB_DSN) as conn:
            # Валидируем product_id для rental в product-first режиме.
            validate_deal_product_id(
                conn,
                product_id=payload.product_id,
                for_rental=True,
                must_be_active=True,
            )
            # Получаем region_id и заодно проверяем существование аккаунта — один запрос вместо двух
            account_row = q1(conn, "SELECT region_id FROM app.accounts WHERE account_id=%s", (payload.account_id,))
            if not account_row:
                raise HTTPException(400, f"Unknown account_id: {payload.account_id}")
            region_id = int(account_row[0]) if account_row[0] is not None else None
            ensure_source_exists(conn, payload.source_id)
            slot_type = ensure_account_allows_slot_type(conn, payload.account_id, payload.slot_type_code)
            platform_id = get_platform_id(conn, slot_type[1])
            # ensure customer exists
            row = q1(conn, "SELECT customer_id, source_id FROM app.customers WHERE nickname=%s", (payload.customer_nickname,))
            if row:
                customer_id = int(row[0])
                if payload.source_id and not row[1]:
                    exec1(
                        conn,
                        "UPDATE app.customers SET source_id=%s WHERE customer_id=%s",
                        (payload.source_id, customer_id),
                    )
            else:
                row = q1(
                    conn,
                    "INSERT INTO app.customers(nickname, source_id) VALUES (%s, %s) RETURNING customer_id",
                    (payload.customer_nickname, payload.source_id),
                )
                customer_id = int(row[0])
    
            # check slots
            free = get_account_slot_free(conn, payload.account_id, payload.slot_type_code)
            if free < 1:
                raise HTTPException(409, "Not enough free slots for selected slot type")
    
            # create deal + item
            deal_row = q1(conn, """
                INSERT INTO app.deals(
                  deal_type_code, status_code, flow_status_code, region_id, customer_id, currency, total_amount, responsible_username
                )
                VALUES ('rental', 'confirmed', 'pending', %s, %s, 'RUB', %s, %s)
                RETURNING deal_id
            """, (region_id, customer_id, payload.price, user.username))
            deal_id = int(deal_row[0])
    
            # Для новых строк аренды сохраняем только product_id.
            row_item = q1(conn, """
                INSERT INTO app.deal_items(
                  deal_id, account_id, product_id, platform_id,
                  qty, price, purchase_cost, start_at, end_at, slots_used, slot_type_code, purchase_at, notes, game_link
                )
                VALUES (
                  %s, %s, %s, %s,
                  1, %s, 0, %s, %s, 1, %s, %s, %s, %s
                )
                RETURNING deal_item_id
            """, (
                deal_id, payload.account_id, payload.product_id, platform_id,
                payload.price, start_at, end_at, payload.slot_type_code, payload.purchase_at, None, None
            ))
            deal_item_id = int(row_item[0])
            exec1(
                conn,
                """
                INSERT INTO app.account_slot_assignments(
                  account_id, slot_type_code, customer_id, product_id, deal_id, deal_item_id, assigned_by
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    payload.account_id,
                    payload.slot_type_code,
                    customer_id,
                    payload.product_id,
                    deal_id,
                    deal_item_id,
                    user.username,
                ),
            )
            conn.commit()

            # return updated slots
            occ2, free2 = slots_summary(conn, payload.account_id, platform_id)
            return {"deal_id": deal_id, "account_id": payload.account_id, "occupied_slots": occ2, "free_slots": free2}
    
    @app.post("/deals")
    def create_deal(payload: DealCreate, user=Depends(get_current_user)):
        deal_type = payload.deal_type_code.strip().lower()
        if deal_type not in ("sale", "rental"):
            raise HTTPException(400, "deal_type_code must be sale or rental")
        # Для создания поддерживаем draft и для продаж, и для шеринга.
        new_flow_status = (payload.flow_status_code or "pending").strip().lower()
        sale_is_draft = deal_type == "sale" and new_flow_status == "draft"
        rental_is_draft = deal_type == "rental" and new_flow_status == "draft"
        if deal_type == "rental" and not rental_is_draft:
            if not payload.slot_type_code:
                raise HTTPException(400, "slot_type_code is required for rental")
            if not payload.account_id:
                raise HTTPException(400, "account_id is required for rental")
            if not payload.product_id:
                raise HTTPException(400, "product_id is required for rental")
        if deal_type == "sale" and not sale_is_draft:
            if not (payload.customer_nickname or "").strip():
                raise HTTPException(400, "customer_nickname is required for non-draft sale")
            if not payload.region_code:
                raise HTTPException(400, "region_code is required for sale")
        if deal_type == "sale":
            payload.slots_used = 0
            if not payload.purchase_at and not sale_is_draft:
                payload.purchase_at = now_utc()
        validate_date_in_range(payload.purchase_at, "purchase_at")
        validate_date_in_range(payload.start_at, "start_at")
        validate_date_in_range(payload.end_at, "end_at")
        validate_date_range(payload.start_at, payload.end_at, "end_at")
    
        with psycopg.connect(DB_DSN) as conn:
            # Нормализуем поля "номер заказа" и "ответственный", чтобы не хранить служебные значения.
            order_number = (payload.order_number or "").strip() or None
            responsible_username = (payload.responsible_username or "").strip() or None
            if responsible_username == "current_user":
                responsible_username = user.username
            if payload.flow_status_code is not None:
                row = q1(conn, "SELECT 1 FROM app.deal_flow_statuses WHERE code=%s", (new_flow_status,))
                if not row:
                    raise HTTPException(400, "Unknown flow_status_code")
            # Для rental работаем только по product_id.
            if payload.product_id is not None:
                # Проверяем product_id заранее, чтобы вернуть понятную 4xx ошибку вместо SQL-ошибки.
                validate_deal_product_id(
                    conn,
                    product_id=payload.product_id,
                    for_rental=(deal_type == "rental"),
                    must_be_active=(deal_type == "rental" and not rental_is_draft),
                )
            if deal_type == "rental" and not rental_is_draft:
                ensure_account_exists(conn, payload.account_id)
            ensure_source_exists(conn, payload.source_id)
            platform_id = None
            if deal_type == "rental" and not rental_is_draft:
                slot_type = ensure_account_allows_slot_type(conn, payload.account_id, payload.slot_type_code)
                platform_id = get_platform_id(conn, slot_type[1])
            region_id = get_region_id(conn, payload.region_code)
            if region_id is None:
                if payload.account_id:
                    region_row = q1(conn, "SELECT region_id FROM app.accounts WHERE account_id=%s", (payload.account_id,))
                    region_id = int(region_row[0]) if region_row and region_row[0] is not None else None

            customer_id = None
            customer_nickname = (payload.customer_nickname or "").strip()
            if customer_nickname:
                row = q1(conn, "SELECT customer_id, source_id FROM app.customers WHERE nickname=%s", (customer_nickname,))
                if row:
                    customer_id = int(row[0])
                    if payload.source_id and not row[1]:
                        exec1(
                            conn,
                            "UPDATE app.customers SET source_id=%s WHERE customer_id=%s",
                            (payload.source_id, customer_id),
                        )
                else:
                    row = q1(
                        conn,
                        """
                        INSERT INTO app.customers(nickname, source_id, customer_login, customer_password)
                        VALUES (%s, %s, %s, %s)
                        RETURNING customer_id
                        """,
                        (
                            customer_nickname,
                            payload.source_id,
                            normalize_customer_field(payload.login),
                            normalize_customer_field(payload.password),
                        ),
                    )
                    customer_id = int(row[0])
                # Для уже существующего клиента обновляем логин/пароль, если они реально переданы.
                update_customer_credentials(conn, customer_id, payload.login, payload.password)
            # Проверяем уникальность только когда номер заказа действительно заполнен.
            if order_number and customer_id is not None:
                customer_row = q1(conn, "SELECT source_id FROM app.customers WHERE customer_id=%s", (customer_id,))
                customer_source_id = int(customer_row[0]) if customer_row and customer_row[0] is not None else None
                validate_market_order_number_unique(conn, customer_source_id, order_number)
    
            if deal_type == "rental" and not rental_is_draft:
                free = get_account_slot_free(conn, payload.account_id, payload.slot_type_code)
                if free < 1:
                    raise HTTPException(409, "Not enough free slots for selected slot type")
    
            deal_row = q1(conn, """
                INSERT INTO app.deals(
                  deal_type_code, status_code, flow_status_code, region_id, customer_id, currency, total_amount, order_number, responsible_username
                )
                VALUES (%s, 'confirmed', %s, %s, %s, 'RUB', %s, %s, %s)
                RETURNING deal_id
            """, (deal_type, new_flow_status, region_id, customer_id, payload.price, order_number, responsible_username))
            deal_id = int(deal_row[0])
    
            # Для новых сделок (sale/rental) храним только product_id.
            product_link = payload.product_link
            if deal_type == "rental" and not rental_is_draft:
                row_item = q1(conn, """
                    INSERT INTO app.deal_items(
                      deal_id, account_id, product_id, platform_id,
                      qty, price, purchase_cost, fee, purchase_at, start_at, end_at, slots_used, slot_type_code, notes, game_link
                    )
                    VALUES (
                      %s, %s, %s, %s,
                      1, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING deal_item_id
                """, (
                    deal_id, payload.account_id, payload.product_id, platform_id,
                    payload.price, payload.purchase_cost, payload.purchase_at, payload.start_at, payload.end_at,
                    1, payload.slot_type_code, payload.notes, product_link
                ))
            else:
                row_item = q1(conn, """
                    INSERT INTO app.deal_items(
                      deal_id, account_id, product_id, platform_id,
                      qty, price, purchase_cost, fee, purchase_at, start_at, end_at, slots_used, slot_type_code, notes, game_link
                    )
                    VALUES (
                      %s, %s, %s, %s,
                      1, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING deal_item_id
                """, (
                    deal_id, payload.account_id, payload.product_id, platform_id,
                    payload.price, payload.purchase_cost, payload.purchase_at, payload.start_at, payload.end_at,
                    0, payload.slot_type_code, payload.notes, product_link
                ))
            deal_item_id = int(row_item[0])
            if deal_type == "rental" and not rental_is_draft:
                exec1(
                conn,
                """
                INSERT INTO app.account_slot_assignments(
                      account_id, slot_type_code, customer_id, product_id, deal_id, deal_item_id, assigned_by
                    )
                    VALUES (
                      %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        payload.account_id,
                        payload.slot_type_code,
                        customer_id,
                        payload.product_id,
                        deal_id,
                        deal_item_id,
                        user.username,
                    ),
                )
            conn.commit()
            # После фиксации публикуем событие, чтобы клиенты могли обновить список сделок в реальном времени.
            if publish_deal_event:
                try:
                    publish_deal_event("deal_created", deal_id, user.username)
                except Exception:
                    # Ошибка нотификации не должна ломать сохранение сделки.
                    pass
    
            return {"deal_id": deal_id}
    
    @app.put("/deals/{deal_id}")
    def update_deal(deal_id: int, payload: DealUpdate, user=Depends(get_current_user)):
        if payload.purchase_at is not None:
            validate_date_in_range(payload.purchase_at, "purchase_at")
        if payload.created_at is not None:
            validate_date_in_range(payload.created_at, "created_at")
        if payload.completed_at is not None:
            validate_date_in_range(payload.completed_at, "completed_at")
        if payload.start_at is not None:
            validate_date_in_range(payload.start_at, "start_at")
        if payload.end_at is not None:
            validate_date_in_range(payload.end_at, "end_at")
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.user', %s, true)", (user.username,))
            row = q1(
                conn,
                """
                SELECT
                  d.deal_type_code,
                  d.status_code,
                  d.flow_status_code,
                  d.region_id,
                  d.customer_id,
                  d.total_amount,
                  d.order_number,
                  d.responsible_username,
                  di.deal_item_id,
                  di.account_id,
                  di.platform_id,
                  di.price,
                  di.purchase_cost,
                  di.purchase_at,
                  di.start_at,
                  di.end_at,
                  di.slots_used,
                  di.slot_type_code,
                  di.notes,
                  di.game_link,
                  di.returned_at
                FROM app.deals d
                JOIN app.deal_items di ON di.deal_id = d.deal_id
                WHERE d.deal_id=%s
                ORDER BY di.deal_item_id ASC
                LIMIT 1
                """,
                (deal_id,),
            )
            if not row:
                raise HTTPException(404, "Deal not found")
    
            current_type, status_code, flow_status_code, region_id, customer_id, total_amount, order_number, responsible_username, deal_item_id, \
                account_id, platform_id, price, purchase_cost, purchase_at, start_at, end_at, slots_used, slot_type_code, notes, game_link, returned_at = row
            user_role = (getattr(user, "role", "") or "").strip().lower()
            can_edit_completed = has_completed_deal_access(user)
            # Завершенные сделки редактируют только admin/owner; для возврата есть отдельный endpoint.
            if str(flow_status_code or "").strip().lower() == "completed" and not can_edit_completed:
                raise HTTPException(403, "editing completed deal is allowed only for admin/owner")
            # Ручные правки системных дат разрешаем только для admin/owner у завершенной сделки.
            has_manual_system_dates = payload.created_at is not None or payload.completed_at is not None
            if has_manual_system_dates and (str(flow_status_code or "").strip().lower() != "completed" or not can_edit_completed):
                raise HTTPException(403, "editing completed deal is allowed only for admin/owner")
    
            deal_type = (payload.deal_type_code or current_type or "").strip().lower()
            if deal_type not in ("sale", "rental"):
                raise HTTPException(400, "deal_type_code must be sale or rental")
            new_flow_status = payload.flow_status_code if payload.flow_status_code is not None else flow_status_code
            if payload.flow_status_code is not None:
                row = q1(conn, "SELECT 1 FROM app.deal_flow_statuses WHERE code=%s", (payload.flow_status_code,))
                if not row:
                    raise HTTPException(400, "Unknown flow_status_code")
            # Черновик нельзя переводить сразу в completed из формы редактирования.
            if str(flow_status_code or "").strip().lower() == "draft" and str(new_flow_status or "").strip().lower() == "completed":
                raise HTTPException(400, "draft deal cannot be completed directly")
            # Черновик допускаем и для продаж, и для шеринга.
            rental_is_draft = deal_type == "rental" and new_flow_status == "draft"

            new_account_id = payload.account_id if payload.account_id is not None else account_id
            ensure_source_exists(conn, payload.source_id if payload.source_id is not None else None)
            if payload.product_id is not None and deal_type != "rental":
                # Для продажи валидируем только product_id.
                validate_deal_product_id(
                    conn,
                    product_id=payload.product_id,
                    for_rental=False,
                    must_be_active=False,
                )
            if payload.region_code is not None:
                region_id = get_region_id(conn, payload.region_code)
    
            new_slot_type_code = payload.slot_type_code if payload.slot_type_code is not None else slot_type_code
            new_platform_id = platform_id
            slot_type_platform = None
            if deal_type == "rental" and not rental_is_draft:
                if not new_slot_type_code:
                    raise HTTPException(400, "slot_type_code is required for rental")
                slot_type = get_slot_type(conn, new_slot_type_code)
                slot_type_platform = slot_type[1]
                new_platform_id = get_platform_id(conn, slot_type[1])
    
            # customer update
            cust_nickname = payload.customer_nickname
            cust_source = payload.source_id if payload.source_id is not None else None
            if cust_nickname:
                customer_id = ensure_customer(conn, cust_nickname, cust_source)
            # Если передали логин/пароль, обновляем их у текущего клиента сделки.
            update_customer_credentials(conn, customer_id, payload.login, payload.password)
    
            new_price = payload.price if payload.price is not None else price
            new_purchase_cost = payload.purchase_cost if payload.purchase_cost is not None else purchase_cost
            new_purchase_at = payload.purchase_at if payload.purchase_at is not None else purchase_at
            new_start_at = payload.start_at if payload.start_at is not None else start_at
            new_end_at = payload.end_at if payload.end_at is not None else end_at
            new_notes = payload.notes if payload.notes is not None else notes
            new_product_link = (
                payload.product_link
                if payload.product_link is not None
                else game_link
            )
            new_order_number = order_number if payload.order_number is None else ((payload.order_number or "").strip() or None)
            if payload.responsible_username is None:
                new_responsible_username = responsible_username
            else:
                normalized_responsible = (payload.responsible_username or "").strip()
                if normalized_responsible == "current_user":
                    normalized_responsible = user.username
                new_responsible_username = normalized_responsible or None
            # Для update проверяем правило только если пользователь менял номер заказа или источник.
            if (payload.order_number is not None or payload.source_id is not None) and new_order_number:
                customer_row = q1(conn, "SELECT source_id FROM app.customers WHERE customer_id=%s", (customer_id,))
                customer_source_id = int(customer_row[0]) if customer_row and customer_row[0] is not None else None
                validate_market_order_number_unique(conn, customer_source_id, new_order_number, exclude_deal_id=deal_id)
            new_slots_used = payload.slots_used if payload.slots_used is not None else slots_used
            current_is_refund = returned_at is not None
            new_is_refund = current_is_refund if payload.is_refund is None else bool(payload.is_refund)
            is_refund_changed = new_is_refund != current_is_refund
            # Признак возврата можно менять в pending для всех, а в completed только для admin/owner.
            allow_refund_change = flow_status_code == "pending" or (flow_status_code == "completed" and can_edit_completed)
            if is_refund_changed and not allow_refund_change:
                raise HTTPException(400, "is_refund can be changed only for pending deals")
            if payload.is_refund and deal_type != "sale":
                raise HTTPException(400, "is_refund is allowed only for sale deals")
            # Проведение возврата в completed разрешено только владельцу или администратору.
            is_completing_now = flow_status_code != "completed" and new_flow_status == "completed"
            if is_completing_now and new_is_refund and user_role not in {"admin", "administrator", "owner"}:
                raise HTTPException(403, "не достаточно прав для проведения возврата")
            # Храним признак возврата через returned_at: timestamp при включении и null при выключении.
            new_returned_at = returned_at
            if is_refund_changed:
                if new_is_refund:
                    new_returned_at = returned_at or now_utc()
                else:
                    new_returned_at = None
            if deal_type == "sale" and new_is_refund:
                # Для возвратной продажи всегда назначаем owner ответственным.
                new_responsible_username = resolve_owner_responsible_name(conn)
            if deal_type == "sale":
                new_slots_used = 0
                new_account_id = None
                new_platform_id = None
                new_slot_type_code = None
                # Для черновика продажи допускаем пустой регион.
                if new_flow_status != "draft" and region_id is None:
                    raise HTTPException(400, "region_code is required for sale")
                # Для не-черновика продажи покупатель обязателен, иначе сделку нельзя провести.
                if new_flow_status != "draft" and customer_id is None:
                    raise HTTPException(400, "customer_nickname is required for non-draft sale")
            if deal_type == "rental":
                new_slots_used = 0 if rental_is_draft else 1
                new_returned_at = None
            validate_date_range(new_start_at, new_end_at, "end_at")
    
            # check slots for rental
            if deal_type == "rental" and not rental_is_draft:
                # Для rental валидируем продукт в product-first режиме.
                if payload.product_id is None:
                    raise HTTPException(400, "product_id is required for rental")
                validate_deal_product_id(
                    conn,
                    product_id=payload.product_id,
                    for_rental=True,
                    must_be_active=False,
                )
                if not new_account_id:
                    raise HTTPException(400, "account_id is required for rental")
                ensure_account_exists(conn, new_account_id)
                # Проверяем поддержку PS4 по product-first привязкам аккаунта.
                if slot_type_platform == "ps4" and not account_has_ps4(conn, new_account_id):
                    raise HTTPException(400, "Account does not support PS4 slot type")
                free = get_account_slot_free(conn, new_account_id, new_slot_type_code)
                row_assign = q1(
                    conn,
                    """
                    SELECT account_id, slot_type_code
                    FROM app.account_slot_assignments
                    WHERE deal_item_id=%s AND released_at IS NULL
                    """,
                    (deal_item_id,),
                )
                same_assignment = row_assign and int(row_assign[0]) == int(new_account_id) and row_assign[1] == new_slot_type_code
                free_adjusted = free + (1 if same_assignment else 0)
                if free_adjusted < 1:
                    raise HTTPException(409, "Not enough free slots for selected slot type")
    
            completed_at_changed = flow_status_code != new_flow_status
            completed_at_value = None
            if completed_at_changed:
                completed_at_value = now_utc() if new_flow_status == "completed" else None
            created_at_override = payload.created_at is not None
            created_at_override_value = payload.created_at if created_at_override else None
            completed_at_override = payload.completed_at is not None
            completed_at_override_value = payload.completed_at if completed_at_override else None

            exec1(
                conn,
                """
                UPDATE app.deals
                SET deal_type_code=%s,
                    customer_id=%s,
                    total_amount=%s,
                    flow_status_code=%s,
                    region_id=%s,
                    order_number=%s,
                    responsible_username=%s,
                    created_at=CASE WHEN %s THEN %s ELSE created_at END,
                    completed_at=CASE
                        WHEN %s THEN %s
                        WHEN %s THEN %s
                        ELSE completed_at
                    END
                WHERE deal_id=%s
                """,
                (
                    deal_type,
                    customer_id,
                    new_price,
                    new_flow_status,
                    region_id,
                    new_order_number,
                    new_responsible_username,
                    created_at_override,
                    created_at_override_value,
                    completed_at_override,
                    completed_at_override_value,
                    completed_at_changed,
                    completed_at_value,
                    deal_id,
                ),
            )
    
            # Для rental обновляем строку в product-first режиме через product_id.
            if deal_type == "rental":
                exec1(
                    conn,
                    """
                    UPDATE app.deal_items
                    SET account_id=%s,
                        product_id=%s,
                        platform_id=%s,
                        price=%s,
                        purchase_cost=%s,
                        purchase_at=%s,
                        start_at=%s,
                        end_at=%s,
                        returned_at=%s,
                        slots_used=%s,
                        slot_type_code=%s,
                        notes=%s,
                        game_link=%s
                    WHERE deal_item_id=%s
                    """,
                    (
                        new_account_id,
                        payload.product_id,
                        new_platform_id,
                        new_price,
                        new_purchase_cost,
                        new_purchase_at,
                        new_start_at,
                        new_end_at,
                        new_returned_at,
                        new_slots_used,
                        new_slot_type_code,
                        new_notes,
                        new_product_link,
                        deal_item_id,
                    ),
                )
            else:
                exec1(
                    conn,
                    """
                    UPDATE app.deal_items
                    SET account_id=%s,
                        product_id=COALESCE(%s, product_id),
                        platform_id=%s,
                        price=%s,
                        purchase_cost=%s,
                        purchase_at=%s,
                        start_at=%s,
                        end_at=%s,
                        returned_at=%s,
                        slots_used=%s,
                        slot_type_code=%s,
                        notes=%s,
                        game_link=%s
                    WHERE deal_item_id=%s
                    """,
                    (
                        new_account_id,
                        payload.product_id,
                        new_platform_id,
                        new_price,
                        new_purchase_cost,
                        new_purchase_at,
                        new_start_at,
                        new_end_at,
                        new_returned_at,
                        new_slots_used,
                        new_slot_type_code,
                        new_notes,
                        new_product_link,
                        deal_item_id,
                    ),
                )
            if deal_type == "rental":
                if rental_is_draft:
                    # При переводе шеринга в черновик снимаем активное назначение слота.
                    release_slot_assignment(conn, deal_item_id, user.username)
                else:
                    row_assign = q1(
                        conn,
                        """
                        SELECT assignment_id, account_id, slot_type_code, customer_id, product_id
                        FROM app.account_slot_assignments
                        WHERE deal_item_id=%s AND released_at IS NULL
                        """,
                        (deal_item_id,),
                    )
                    current_assign = row_assign[0] if row_assign else None
                    # Сравниваем назначение только по product_id.
                    assigned_product_id = int(row_assign[4]) if row_assign and row_assign[4] is not None else None
                    need_new_assign = (
                        (not row_assign)
                        or int(row_assign[1]) != int(new_account_id)
                        or row_assign[2] != new_slot_type_code
                        or (customer_id is not None and row_assign[3] != customer_id)
                        or (assigned_product_id != int(payload.product_id))
                    )
                    if need_new_assign and current_assign:
                        release_slot_assignment(conn, deal_item_id, user.username)
                    if need_new_assign:
                        exec1(
                            conn,
                            """
                            INSERT INTO app.account_slot_assignments(
                              account_id, slot_type_code, customer_id, product_id, deal_id, deal_item_id, assigned_by
                            )
                            VALUES (
                              %s, %s, %s, %s, %s, %s, %s
                            )
                            """,
                            (
                                new_account_id,
                                new_slot_type_code,
                                customer_id,
                                payload.product_id,
                                deal_id,
                                deal_item_id,
                                user.username,
                            ),
                        )
            conn.commit()
            # После успешного update отправляем событие об изменении сделки.
            if publish_deal_event:
                try:
                    publish_deal_event("deal_updated", deal_id, user.username)
                except Exception:
                    # Ошибка нотификации не должна ломать update сделки.
                    pass
    
        return {"ok": True}

    @app.post("/deals/{deal_id}/return")
    def return_completed_sale_to_pending(deal_id: int, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.user', %s, true)", (user.username,))
            # Берем текущее состояние сделки, чтобы безопасно выполнить возврат только для нужного кейса.
            row = q1(
                conn,
                """
                SELECT d.deal_type_code, d.flow_status_code, di.returned_at
                FROM app.deals d
                JOIN app.deal_items di ON di.deal_id = d.deal_id
                WHERE d.deal_id=%s
                ORDER BY di.deal_item_id ASC
                LIMIT 1
                """,
                (deal_id,),
            )
            if not row:
                raise HTTPException(404, "Deal not found")
            deal_type_code, flow_status_code, returned_at = row
            if str(deal_type_code or "").strip().lower() != "sale":
                raise HTTPException(400, "return is allowed only for sale deals")
            if str(flow_status_code or "").strip().lower() != "completed":
                raise HTTPException(400, "return is allowed only for completed deals")
            if returned_at is not None:
                raise HTTPException(400, "deal is already marked as refund")

            owner_responsible = resolve_owner_responsible_name(conn)
            returned_at_value = now_utc()
            # Переводим сделку обратно в pending, очищаем дату завершения и назначаем owner ответственным.
            exec1(
                conn,
                """
                UPDATE app.deals
                SET flow_status_code='pending',
                    responsible_username=%s,
                    completed_at=NULL
                WHERE deal_id=%s
                """,
                (owner_responsible, deal_id),
            )
            # Признак возврата храним в returned_at: ставим timestamp для всех позиций сделки.
            exec1(
                conn,
                "UPDATE app.deal_items SET returned_at=%s WHERE deal_id=%s",
                (returned_at_value, deal_id),
            )
            conn.commit()
            if publish_deal_event:
                try:
                    publish_deal_event("deal_updated", deal_id, user.username)
                except Exception:
                    # Ошибка нотификации не должна ломать успешный возврат.
                    pass
        return {"ok": True}

    @app.delete("/deals/{deal_id}")
    def delete_deal(deal_id: int, user=Depends(get_current_user)):
        # Мягкое удаление: оставляем запись в БД, меняем только статус.
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT flow_status_code FROM app.deals WHERE deal_id=%s", (deal_id,))
            if not row:
                raise HTTPException(404, "Deal not found")
            if row[0] != "draft":
                raise HTTPException(400, "delete is allowed only for draft deals")
            exec1(conn, "UPDATE app.deals SET status_code='cancelled' WHERE deal_id=%s", (deal_id,))
            conn.commit()
            if publish_deal_event:
                try:
                    publish_deal_event("deal_deleted", deal_id, user.username)
                except Exception:
                    # Ошибка нотификации не должна ломать удаление сделки.
                    pass
        return {"ok": True}
    
    @app.get("/deals", response_model=DealListOut)
    def list_deals(
        account_id: Optional[int] = None,
        platform_code: Optional[str] = None,
        q: Optional[str] = None,
        deal_type_code: Optional[str] = None,
        status_code: Optional[str] = None,
        flow_status_code: Optional[str] = None,
        customer_q: Optional[str] = None,
        responsible_q: Optional[str] = None,
        source_id: Optional[int] = None,
        purchase_from: Optional[date] = None,
        purchase_to: Optional[date] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        notes_q: Optional[str] = None,
        account_q: Optional[str] = None,
        region_q: Optional[str] = None,
        product_q: Optional[str] = None,
        platform_q: Optional[str] = None,
        type_q: Optional[str] = None,
        status_q: Optional[str] = None,
        flow_status_q: Optional[str] = None,
        source_q: Optional[str] = None,
        date_q: Optional[str] = None,
        price_q: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        user=Depends(get_current_user),
    ):
        if page < 1:
            raise HTTPException(400, "page must be >= 1")
        if page_size < 1 or page_size > 200:
            raise HTTPException(400, "page_size must be between 1 and 200")
        offset = (page - 1) * page_size
    
        with psycopg.connect(DB_DSN) as conn:
            where_sql, params = build_deals_filters(
                account_id,
                platform_code,
                q,
                deal_type_code,
                status_code,
                flow_status_code,
                customer_q,
                responsible_q,
                source_id,
                purchase_from,
                purchase_to,
                price_min,
                price_max,
                notes_q,
                account_q,
                region_q,
                product_q,
                platform_q,
                type_q,
                status_q,
                flow_status_q,
                source_q,
                date_q,
                price_q,
            )
            # Удаленные (cancelled) сделки скрываем из рабочего списка.
            if where_sql:
                where_sql = f"{where_sql} AND d.status_code <> 'cancelled'"
            else:
                where_sql = "WHERE d.status_code <> 'cancelled'"
            # Возвратные сделки в списке видят только admin/owner.
            can_view_refunds = has_completed_deal_access(user)
            if not can_view_refunds:
                if where_sql:
                    where_sql = f"{where_sql} AND di.returned_at IS NULL"
                else:
                    where_sql = "WHERE di.returned_at IS NULL"
                # Для не-привилегированных ролей старые завершенные сделки скрываем.
                today = now_utc().date()
                completed_today_clause = "(d.flow_status_code <> 'completed' OR COALESCE(d.completed_at, di.purchase_at, d.created_at)::date = %s)"
                if where_sql:
                    where_sql = f"{where_sql} AND {completed_today_clause}"
                else:
                    where_sql = f"WHERE {completed_today_clause}"
                params.append(today)

            total_row = q1(conn, f"""
                SELECT COUNT(*)
                FROM app.deal_items di
                JOIN app.deals d ON d.deal_id = di.deal_id
                LEFT JOIN app.accounts a ON a.account_id = di.account_id
                LEFT JOIN app.domains dm ON dm.domain_id = a.domain_id
                LEFT JOIN app.regions ra ON ra.region_id = a.region_id
                LEFT JOIN app.regions rd ON rd.region_id = d.region_id
                LEFT JOIN app.products pr ON pr.product_id = di.product_id
                LEFT JOIN app.platforms p ON p.platform_id = di.platform_id
                LEFT JOIN app.customers c ON c.customer_id = d.customer_id
                LEFT JOIN app.sources src ON src.source_id = c.source_id
                LEFT JOIN app.deal_flow_statuses fs ON fs.code = d.flow_status_code
                LEFT JOIN app.deal_statuses ds ON ds.code = d.status_code
                LEFT JOIN app.deal_types dt ON dt.code = d.deal_type_code
                {where_sql}
            """, params)
            total = int(total_row[0]) if total_row else 0
    
            rows = qall(conn, f"""
                SELECT
                  d.deal_id,
                  dt.name as deal_type_name,
                  dt.code as deal_type_code,
                  ds.name as status_name,
                  d.flow_status_code,
                  fs.name as flow_status_name,
                  d.order_number,
                  COALESCE(
                    (
                      SELECT NULLIF(btrim(u.name), '')
                      FROM app.users u
                      WHERE lower(u.username) = lower(d.responsible_username)
                      ORDER BY u.user_id ASC
                      LIMIT 1
                    ),
                    d.responsible_username
                  ) as responsible_username,
                  COALESCE(rd.code, ra.code) as region_code,
                  di.account_id,
                  a.login_name,
                  dm.name as domain_name,
                  di.product_id,
                  pr.title as product_title,
                  pr.short_title as product_short_title,
                  p.code as platform_code,
                  c.nickname,
                  c.customer_login,
                  c.customer_password,
                  c.source_id,
                  di.price,
                  di.purchase_cost,
                  di.purchase_at,
                  d.created_at,
                  d.completed_at,
                  di.slots_used,
                  di.slot_type_code,
                  di.notes,
                  di.game_link as product_link,
                  (di.returned_at IS NOT NULL) as is_refund
                FROM app.deal_items di
                JOIN app.deals d ON d.deal_id = di.deal_id
                LEFT JOIN app.deal_types dt ON dt.code = d.deal_type_code
                LEFT JOIN app.deal_statuses ds ON ds.code = d.status_code
                LEFT JOIN app.deal_flow_statuses fs ON fs.code = d.flow_status_code
                LEFT JOIN app.accounts a ON a.account_id = di.account_id
                LEFT JOIN app.domains dm ON dm.domain_id = a.domain_id
                LEFT JOIN app.regions ra ON ra.region_id = a.region_id
                LEFT JOIN app.regions rd ON rd.region_id = d.region_id
                LEFT JOIN app.products pr ON pr.product_id = di.product_id
                LEFT JOIN app.platforms p ON p.platform_id = di.platform_id
                LEFT JOIN app.customers c ON c.customer_id = d.customer_id
                LEFT JOIN app.sources src ON src.source_id = c.source_id
                {where_sql}
                ORDER BY d.created_at DESC
                LIMIT %s OFFSET %s
            """, params + [page_size, offset])
    
        items = []
        for r in rows:
            login_full = f"{r[10]}@{r[11]}" if r[10] and r[11] else None
            # Разбираем единый product-first формат строки из SQL списка сделок.
            product_id = r[12]
            product_title = r[13]
            product_short_title = r[14]
            platform_code = r[15]
            customer_nickname = r[16]
            login = r[17]
            password = r[18]
            source_id = r[19]
            price_value = r[20]
            purchase_cost_value = r[21]
            purchase_at = r[22]
            created_at = r[23]
            completed_at = r[24]
            slots_used = r[25]
            slot_type_code = r[26]
            notes = r[27]
            product_link = r[28]
            is_refund = bool(r[29])
            items.append(
                DealListItem(
                    deal_id=r[0],
                    deal_type=r[1],
                    deal_type_code=r[2],
                    status=r[3],
                    flow_status_code=r[4],
                    flow_status=r[5],
                    order_number=r[6],
                    responsible_username=r[7],
                    region_code=r[8],
                    account_id=r[9],
                    account_login=login_full,
                    product_id=product_id,
                    product_title=product_title,
                    product_short_title=product_short_title,
                    platform_code=platform_code,
                    customer_nickname=customer_nickname,
                    login=login,
                    password=password,
                    source_id=source_id,
                    price=float(price_value or 0),
                    purchase_cost=float(purchase_cost_value or 0),
                    purchase_at=purchase_at,
                    created_at=created_at,
                    completed_at=completed_at,
                    slots_used=slots_used,
                    slot_type_code=slot_type_code,
                    notes=notes,
                    product_link=product_link,
                    is_refund=is_refund,
                )
            )
    
        return DealListOut(total=total, items=items)
    
