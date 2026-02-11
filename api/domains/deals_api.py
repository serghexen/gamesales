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
    ensure_game_active,
    ensure_source_exists,
    ensure_account_allows_slot_type,
    get_platform_id,
    get_region_id,
    get_account_slot_free,
    ensure_customer,
    get_slot_type,
    ensure_game_exists,
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

    @app.post("/rentals")
    def create_rental(payload: RentalCreate, user=Depends(get_current_user)):
        if not payload.slot_type_code:
            raise HTTPException(400, "slot_type_code is required for rental")
        validate_date_in_range(payload.purchase_at, "purchase_at")
        validate_date_in_range(payload.start_at, "start_at")
        validate_date_in_range(payload.end_at, "end_at")
        validate_date_range(payload.start_at, payload.end_at, "end_at")
    
        start_at = payload.start_at or now_utc()
        end_at = payload.end_at
    
        with psycopg.connect(DB_DSN) as conn:
            # Получаем region_id и заодно проверяем существование аккаунта — один запрос вместо двух
            account_row = q1(conn, "SELECT region_id FROM app.accounts WHERE account_id=%s", (payload.account_id,))
            if not account_row:
                raise HTTPException(400, f"Unknown account_id: {payload.account_id}")
            region_id = int(account_row[0]) if account_row[0] is not None else None
            ensure_game_active(conn, payload.game_id)
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
    
            row_item = q1(conn, """
                INSERT INTO app.deal_items(
                  deal_id, account_id, game_id, platform_id,
                  qty, price, purchase_cost, start_at, end_at, slots_used, slot_type_code, purchase_at, notes, game_link
                )
                VALUES (%s, %s, %s, %s, 1, %s, 0, %s, %s, 1, %s, %s, %s, %s)
                RETURNING deal_item_id
            """, (
                deal_id, payload.account_id, payload.game_id, platform_id,
                payload.price, start_at, end_at, payload.slot_type_code, payload.purchase_at, None, None
            ))
            deal_item_id = int(row_item[0])
            exec1(
                conn,
                """
                INSERT INTO app.account_slot_assignments(
                  account_id, slot_type_code, customer_id, game_id, deal_id, deal_item_id, assigned_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (payload.account_id, payload.slot_type_code, customer_id, payload.game_id, deal_id, deal_item_id, user.username),
            )
            conn.commit()
    
            conn.commit()
    
            # return updated slots
            occ2, free2 = slots_summary(conn, payload.account_id, platform_id)
            return {"deal_id": deal_id, "account_id": payload.account_id, "occupied_slots": occ2, "free_slots": free2}
    
    @app.post("/deals")
    def create_deal(payload: DealCreate, user=Depends(get_current_user)):
        deal_type = payload.deal_type_code.strip().lower()
        if deal_type not in ("sale", "rental"):
            raise HTTPException(400, "deal_type_code must be sale or rental")
        # Для создания поддерживаем draft только для продаж.
        new_flow_status = (payload.flow_status_code or "pending").strip().lower()
        if new_flow_status == "draft" and deal_type != "sale":
            raise HTTPException(400, "flow_status_code draft is allowed only for sale deals")
        sale_is_draft = deal_type == "sale" and new_flow_status == "draft"
        if deal_type == "rental":
            if not payload.slot_type_code:
                raise HTTPException(400, "slot_type_code is required for rental")
            if not payload.account_id:
                raise HTTPException(400, "account_id is required for rental")
            if not payload.game_id:
                raise HTTPException(400, "game_id is required for rental")
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
            if deal_type == "rental":
                ensure_account_exists(conn, payload.account_id)
                ensure_game_active(conn, payload.game_id)
            ensure_source_exists(conn, payload.source_id)
            platform_id = None
            if deal_type == "rental":
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
    
            if deal_type == "rental":
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
    
            row_item = q1(conn, """
                INSERT INTO app.deal_items(
                  deal_id, account_id, game_id, platform_id,
                  qty, price, purchase_cost, fee, purchase_at, start_at, end_at, slots_used, slot_type_code, notes, game_link
                )
                VALUES (%s, %s, %s, %s, 1, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s)
                RETURNING deal_item_id
            """, (
                deal_id, payload.account_id, payload.game_id, platform_id,
                payload.price, payload.purchase_cost, payload.purchase_at, payload.start_at, payload.end_at,
                (0 if deal_type == "sale" else 1), payload.slot_type_code, payload.notes, payload.game_link
            ))
            deal_item_id = int(row_item[0])
            if deal_type == "rental":
                exec1(
                    conn,
                    """
                    INSERT INTO app.account_slot_assignments(
                      account_id, slot_type_code, customer_id, game_id, deal_id, deal_item_id, assigned_by
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (payload.account_id, payload.slot_type_code, customer_id, payload.game_id, deal_id, deal_item_id, user.username),
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
                  di.game_id,
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
                account_id, game_id, platform_id, price, purchase_cost, purchase_at, start_at, end_at, slots_used, slot_type_code, notes, game_link, returned_at = row
    
            deal_type = (payload.deal_type_code or current_type or "").strip().lower()
            if deal_type not in ("sale", "rental"):
                raise HTTPException(400, "deal_type_code must be sale or rental")
            new_flow_status = payload.flow_status_code if payload.flow_status_code is not None else flow_status_code
            if payload.flow_status_code is not None:
                row = q1(conn, "SELECT 1 FROM app.deal_flow_statuses WHERE code=%s", (payload.flow_status_code,))
                if not row:
                    raise HTTPException(400, "Unknown flow_status_code")
            # Черновик применяем только для продаж, чтобы не ломать правила шеринга.
            if new_flow_status == "draft" and deal_type != "sale":
                raise HTTPException(400, "flow_status_code draft is allowed only for sale deals")

            new_account_id = payload.account_id if payload.account_id is not None else account_id
            new_game_id = payload.game_id if payload.game_id is not None else game_id
            ensure_source_exists(conn, payload.source_id if payload.source_id is not None else None)
            if payload.region_code is not None:
                region_id = get_region_id(conn, payload.region_code)
    
            new_slot_type_code = payload.slot_type_code if payload.slot_type_code is not None else slot_type_code
            new_platform_id = platform_id
            slot_type_platform = None
            if deal_type == "rental":
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
            new_game_link = payload.game_link if payload.game_link is not None else game_link
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
            # Признак возврата можно менять только в pending, но неизменное значение пропускаем.
            if is_refund_changed and flow_status_code != "pending":
                raise HTTPException(400, "is_refund can be changed only for pending deals")
            if payload.is_refund and deal_type != "sale":
                raise HTTPException(400, "is_refund is allowed only for sale deals")
            # Проведение возврата в completed разрешено только владельцу или администратору.
            user_role = (getattr(user, "role", "") or "").strip().lower()
            is_completing_now = flow_status_code != "completed" and new_flow_status == "completed"
            if is_completing_now and new_is_refund and user_role not in {"admin", "owner"}:
                raise HTTPException(403, "не достаточно прав для проведения возврата")
            # Храним признак возврата через returned_at: timestamp при включении и null при выключении.
            new_returned_at = returned_at
            if is_refund_changed:
                if new_is_refund:
                    new_returned_at = returned_at or now_utc()
                else:
                    new_returned_at = None
            if deal_type == "sale":
                new_slots_used = 0
                new_account_id = None
                new_game_id = None
                new_platform_id = None
                new_slot_type_code = None
                # Для черновика продажи допускаем пустой регион.
                if new_flow_status != "draft" and region_id is None:
                    raise HTTPException(400, "region_code is required for sale")
                # Для не-черновика продажи покупатель обязателен, иначе сделку нельзя провести.
                if new_flow_status != "draft" and customer_id is None:
                    raise HTTPException(400, "customer_nickname is required for non-draft sale")
            if deal_type == "rental":
                new_slots_used = 1
                new_returned_at = None
            validate_date_range(new_start_at, new_end_at, "end_at")
    
            # check slots for rental
            if deal_type == "rental":
                if not new_account_id:
                    raise HTTPException(400, "account_id is required for rental")
                if not new_game_id:
                    raise HTTPException(400, "game_id is required for rental")
                ensure_account_exists(conn, new_account_id)
                ensure_game_exists(conn, new_game_id)
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
                    completed_at=CASE WHEN %s THEN %s ELSE completed_at END
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
                    completed_at_changed,
                    completed_at_value,
                    deal_id,
                ),
            )
    
            exec1(
                conn,
                """
                UPDATE app.deal_items
                SET account_id=%s,
                    game_id=%s,
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
                    new_game_id,
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
                    new_game_link,
                    deal_item_id,
                ),
            )
            if deal_type == "rental":
                row_assign = q1(
                    conn,
                    """
                    SELECT assignment_id, account_id, slot_type_code, customer_id, game_id
                    FROM app.account_slot_assignments
                    WHERE deal_item_id=%s AND released_at IS NULL
                    """,
                    (deal_item_id,),
                )
                current_assign = row_assign[0] if row_assign else None
                need_new_assign = (
                    (not row_assign)
                    or int(row_assign[1]) != int(new_account_id)
                    or row_assign[2] != new_slot_type_code
                    or (customer_id is not None and row_assign[3] != customer_id)
                    or (new_game_id is not None and row_assign[4] != new_game_id)
                )
                if need_new_assign and current_assign:
                    release_slot_assignment(conn, deal_item_id, user.username)
                if need_new_assign:
                    exec1(
                        conn,
                        """
                        INSERT INTO app.account_slot_assignments(
                          account_id, slot_type_code, customer_id, game_id, deal_id, deal_item_id, assigned_by
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (new_account_id, new_slot_type_code, customer_id, new_game_id, deal_id, deal_item_id, user.username),
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
        game_id: Optional[int] = None,
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
        game_q: Optional[str] = None,
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
                game_id,
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
                game_q,
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
            user_role = (getattr(user, "role", "") or "").strip().lower()
            user_name = (getattr(user, "username", "") or "").strip().lower()
            can_view_refunds = user_role in {"admin", "owner"} or user_name in {"admin", "owner"}
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
                LEFT JOIN app.game_titles g ON g.game_id = di.game_id
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
                  d.responsible_username,
                  COALESCE(rd.code, ra.code) as region_code,
                  di.account_id,
                  a.login_name,
                  dm.name as domain_name,
                  di.game_id,
                  g.title,
                  g.short_title,
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
                  di.game_link,
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
                LEFT JOIN app.game_titles g ON g.game_id = di.game_id
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
            # Поддерживаем оба формата: новый (с login/password) и старый (без них) для тестовых фикстур.
            has_customer_credentials = len(r) >= 29
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
                    game_id=r[12],
                    game_title=r[13],
                    game_short_title=r[14],
                    platform_code=r[15],
                    customer_nickname=r[16],
                    login=r[17] if has_customer_credentials else None,
                    password=r[18] if has_customer_credentials else None,
                    source_id=r[19] if has_customer_credentials else r[17],
                    price=float((r[20] if has_customer_credentials else r[18]) or 0),
                    purchase_cost=float((r[21] if has_customer_credentials else r[19]) or 0),
                    purchase_at=r[22] if has_customer_credentials else r[20],
                    created_at=r[23] if has_customer_credentials else r[21],
                    completed_at=r[24] if has_customer_credentials else r[22],
                    slots_used=r[25] if has_customer_credentials else r[23],
                    slot_type_code=r[26] if has_customer_credentials else r[24],
                    notes=r[27] if has_customer_credentials else r[25],
                    game_link=r[28] if has_customer_credentials else r[26],
                    is_refund=bool(r[29]) if has_customer_credentials and len(r) >= 30 else False,
                )
            )
    
        return DealListOut(total=total, items=items)
    
