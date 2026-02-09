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
):
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
            ensure_account_exists(conn, payload.account_id)
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
            region_row = q1(conn, "SELECT region_id FROM app.accounts WHERE account_id=%s", (payload.account_id,))
            region_id = int(region_row[0]) if region_row and region_row[0] is not None else None
            deal_row = q1(conn, """
                INSERT INTO app.deals(deal_type_code, status_code, flow_status_code, region_id, customer_id, currency, total_amount)
                VALUES ('rental', 'confirmed', 'pending', %s, %s, 'RUB', %s)
                RETURNING deal_id
            """, (region_id, customer_id, payload.price))
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
        if deal_type == "rental":
            if not payload.slot_type_code:
                raise HTTPException(400, "slot_type_code is required for rental")
            if not payload.account_id:
                raise HTTPException(400, "account_id is required for rental")
            if not payload.game_id:
                raise HTTPException(400, "game_id is required for rental")
        if deal_type == "sale":
            if not payload.region_code:
                raise HTTPException(400, "region_code is required for sale")
        if deal_type == "sale":
            payload.slots_used = 0
            if not payload.purchase_at:
                payload.purchase_at = now_utc()
        validate_date_in_range(payload.purchase_at, "purchase_at")
        validate_date_in_range(payload.start_at, "start_at")
        validate_date_in_range(payload.end_at, "end_at")
        validate_date_range(payload.start_at, payload.end_at, "end_at")
    
        with psycopg.connect(DB_DSN) as conn:
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
    
            if deal_type == "rental":
                free = get_account_slot_free(conn, payload.account_id, payload.slot_type_code)
                if free < 1:
                    raise HTTPException(409, "Not enough free slots for selected slot type")
    
            deal_row = q1(conn, """
                INSERT INTO app.deals(deal_type_code, status_code, flow_status_code, region_id, customer_id, currency, total_amount)
                VALUES (%s, 'confirmed', 'pending', %s, %s, 'RUB', %s)
                RETURNING deal_id
            """, (deal_type, region_id, customer_id, payload.price))
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
                  di.game_link
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
    
            current_type, status_code, flow_status_code, region_id, customer_id, total_amount, deal_item_id, \
                account_id, game_id, platform_id, price, purchase_cost, purchase_at, start_at, end_at, slots_used, slot_type_code, notes, game_link = row
    
            deal_type = (payload.deal_type_code or current_type or "").strip().lower()
            if deal_type not in ("sale", "rental"):
                raise HTTPException(400, "deal_type_code must be sale or rental")
    
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
    
            new_price = payload.price if payload.price is not None else price
            new_purchase_cost = payload.purchase_cost if payload.purchase_cost is not None else purchase_cost
            new_purchase_at = payload.purchase_at if payload.purchase_at is not None else purchase_at
            new_start_at = payload.start_at if payload.start_at is not None else start_at
            new_end_at = payload.end_at if payload.end_at is not None else end_at
            new_notes = payload.notes if payload.notes is not None else notes
            new_game_link = payload.game_link if payload.game_link is not None else game_link
            new_slots_used = payload.slots_used if payload.slots_used is not None else slots_used
            new_flow_status = payload.flow_status_code if payload.flow_status_code is not None else flow_status_code
            if payload.flow_status_code is not None:
                row = q1(conn, "SELECT 1 FROM app.deal_flow_statuses WHERE code=%s", (payload.flow_status_code,))
                if not row:
                    raise HTTPException(400, "Unknown flow_status_code")
            if deal_type == "sale":
                new_slots_used = 0
                new_account_id = None
                new_game_id = None
                new_platform_id = None
                new_slot_type_code = None
                if region_id is None:
                    raise HTTPException(400, "region_code is required for sale")
            if deal_type == "rental":
                new_slots_used = 1
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
                    completed_at=CASE WHEN %s THEN %s ELSE completed_at END
                WHERE deal_id=%s
                """,
                (deal_type, customer_id, new_price, new_flow_status, region_id, completed_at_changed, completed_at_value, deal_id),
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
                  COALESCE(rd.code, ra.code) as region_code,
                  di.account_id,
                  a.login_name,
                  dm.name as domain_name,
                  di.game_id,
                  g.title,
                  g.short_title,
                  p.code as platform_code,
                  c.nickname,
                  c.source_id,
                  di.price,
                  di.purchase_cost,
                  di.purchase_at,
                  d.created_at,
                  di.slots_used,
                  di.slot_type_code,
                  di.notes,
                  di.game_link
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
            login_full = f"{r[8]}@{r[9]}" if r[8] and r[9] else None
            items.append(
                DealListItem(
                    deal_id=r[0],
                    deal_type=r[1],
                    deal_type_code=r[2],
                    status=r[3],
                    flow_status_code=r[4],
                    flow_status=r[5],
                    region_code=r[6],
                    account_id=r[7],
                    account_login=login_full,
                    game_id=r[10],
                    game_title=r[11],
                    game_short_title=r[12],
                    platform_code=r[13],
                    customer_nickname=r[14],
                    source_id=r[15],
                    price=float(r[16] or 0),
                    purchase_cost=float(r[17] or 0),
                    purchase_at=r[18],
                    created_at=r[19],
                    slots_used=r[20],
                    slot_type_code=r[21],
                    notes=r[22],
                    game_link=r[23],
                )
            )
    
        return DealListOut(total=total, items=items)
    
