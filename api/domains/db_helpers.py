from dataclasses import dataclass
from datetime import date
from typing import Callable, Optional


@dataclass
class DbHelpers:
    get_platform_id: Callable
    get_platform_info: Callable
    get_region_id: Callable
    get_domain_id: Callable
    get_platform_id_optional: Callable
    ensure_account_exists: Callable
    ensure_customer: Callable
    ensure_source_exists: Callable
    build_deals_filters: Callable
    slots_summary: Callable
    get_account_platform_slots: Callable
    get_account_slot_status: Callable
    normalize_platform_codes: Callable
    get_game_platform_codes: Callable
    get_account_platform_codes: Callable
    account_has_ps4: Callable
    ensure_account_allows_slot_type: Callable
    get_slot_type: Callable
    get_account_slot_free: Callable
    release_slot_assignment: Callable


def build_db_helpers(
    *,
    q1,
    qall,
    exec1,
    HTTPException,
    AccountPlatformSlots,
    AccountSlotStatusOut,
) -> DbHelpers:
    def get_platform_id(conn, code: str) -> int:
        row = q1(conn, "SELECT platform_id FROM app.platforms WHERE code=%s AND is_archived IS NOT TRUE", (code,))
        if not row:
            raise HTTPException(400, f"Unknown platform_code: {code}")
        return int(row[0])

    def get_platform_info(conn, code: str) -> tuple[int, int]:
        row = q1(conn, "SELECT platform_id, slot_capacity FROM app.platforms WHERE code=%s AND is_archived IS NOT TRUE", (code,))
        if not row:
            raise HTTPException(400, f"Unknown platform_code: {code}")
        return int(row[0]), int(row[1] or 0)

    def get_region_id(conn, code: Optional[str]) -> Optional[int]:
        if not code:
            return None
        row = q1(conn, "SELECT region_id FROM app.regions WHERE code=%s AND is_archived IS NOT TRUE", (code,))
        if not row:
            raise HTTPException(400, f"Unknown region_code: {code}")
        return int(row[0])

    def get_domain_id(conn, code: Optional[str]) -> Optional[int]:
        if not code:
            return None
        row = q1(conn, "SELECT domain_id FROM app.domains WHERE name=%s AND is_archived IS NOT TRUE", (code,))
        if not row:
            raise HTTPException(400, f"Unknown domain: {code}")
        return int(row[0])

    def get_platform_id_optional(conn, code: Optional[str]) -> Optional[int]:
        if not code:
            return None
        row = q1(conn, "SELECT platform_id FROM app.platforms WHERE code=%s AND is_archived IS NOT TRUE", (code,))
        if not row:
            raise HTTPException(400, f"Unknown platform_code: {code}")
        return int(row[0])

    def ensure_account_exists(conn, account_id: int):
        row = q1(conn, "SELECT 1 FROM app.accounts WHERE account_id=%s", (account_id,))
        if not row:
            raise HTTPException(400, f"Unknown account_id: {account_id}")

    def ensure_customer(conn, nickname: Optional[str], source_id: Optional[int]) -> Optional[int]:
        if not nickname:
            return None
        row = q1(conn, "SELECT customer_id, source_id FROM app.customers WHERE nickname=%s", (nickname,))
        if row:
            customer_id = int(row[0])
            if source_id and row[1] != source_id:
                exec1(conn, "UPDATE app.customers SET source_id=%s WHERE customer_id=%s", (source_id, customer_id))
            return customer_id
        row = q1(
            conn,
            "INSERT INTO app.customers(nickname, source_id) VALUES (%s, %s) RETURNING customer_id",
            (nickname, source_id),
        )
        return int(row[0])

    def ensure_source_exists(conn, source_id: Optional[int]):
        if not source_id:
            return
        row = q1(conn, "SELECT 1 FROM app.sources WHERE source_id=%s AND is_archived IS NOT TRUE", (source_id,))
        if not row:
            raise HTTPException(400, f"Unknown source_id: {source_id}")

    # Разбирает строку фильтра "a,b,c" в список значений без пустых элементов.
    def parse_multi_filter_values(raw_value: Optional[str]) -> list[str]:
        if not raw_value:
            return []
        parts = [str(part or "").strip() for part in str(raw_value).split(",")]
        return [part for part in parts if part]

    # Разбирает фильтр ответственных из строки в список значений.
    def parse_responsible_filter_values(raw_value: Optional[str]) -> list[str]:
        return parse_multi_filter_values(raw_value)

    # Разбирает фильтр статусов сделки из строки "a,b,c" в список кодов.
    def parse_flow_status_filter_values(raw_value: Optional[str]) -> list[str]:
        return parse_multi_filter_values(raw_value)

    def build_deals_filters(
        account_id: Optional[int],
        platform_code: Optional[str],
        q: Optional[str],
        deal_type_code: Optional[str],
        status_code: Optional[str],
        flow_status_code: Optional[str],
        customer_q: Optional[str],
        responsible_q: Optional[str],
        source_id: Optional[int],
        purchase_from: Optional[date],
        purchase_to: Optional[date],
        price_min: Optional[float],
        price_max: Optional[float],
        notes_q: Optional[str],
        account_q: Optional[str],
        region_q: Optional[str],
        product_q: Optional[str],
        platform_q: Optional[str],
        type_q: Optional[str],
        status_q: Optional[str],
        flow_status_q: Optional[str],
        source_q: Optional[str],
        date_q: Optional[str],
        price_q: Optional[str],
    ) -> tuple[str, list]:
        where = []
        params: list = []
        if account_id:
            where.append("di.account_id = %s")
            params.append(account_id)
        if platform_code:
            where.append("p.code = %s")
            params.append(platform_code)
        if q:
            where.append("""
              (
                c.nickname ILIKE %s
                OR d.responsible_username ILIKE %s
                OR COALESCE(rd.code, ra.code) ILIKE %s
                OR dt.name ILIKE %s
                OR dt.code ILIKE %s
                OR fs.name ILIKE %s
                OR fs.code ILIKE %s
                OR COALESCE(di.purchase_at, d.created_at)::text ILIKE %s
              )
            """)
            like = f"%{q}%"
            params.extend([like, like, like, like, like, like, like, like])
        if deal_type_code:
            where.append("d.deal_type_code = %s")
            params.append(deal_type_code)
        if status_code:
            where.append("d.status_code = %s")
            params.append(status_code)
        if flow_status_code:
            where.append("d.flow_status_code = %s")
            params.append(flow_status_code)
        if customer_q:
            where.append("c.nickname ILIKE %s")
            params.append(f"%{customer_q}%")
        if responsible_q:
            responsible_values = parse_responsible_filter_values(responsible_q)
            if responsible_values:
                responsible_where = " OR ".join(["d.responsible_username ILIKE %s"] * len(responsible_values))
                where.append(f"({responsible_where})")
                params.extend([f"%{value}%" for value in responsible_values])
        if source_id:
            where.append("c.source_id = %s")
            params.append(source_id)
        if notes_q:
            where.append("di.notes ILIKE %s")
            params.append(f"%{notes_q}%")
        if account_q:
            like = f"%{account_q}%"
            where.append("(a.login_name ILIKE %s OR dm.name ILIKE %s)")
            params.extend([like, like])
        if region_q:
            region_values = parse_multi_filter_values(region_q)
            if len(region_values) > 1:
                # Для множественного выбора регионов используем точное сравнение кодов.
                region_where = " OR ".join(["COALESCE(rd.code, ra.code) = %s"] * len(region_values))
                where.append(f"({region_where})")
                params.extend(region_values)
            else:
                like = f"%{region_q}%"
                where.append("COALESCE(rd.code, ra.code) ILIKE %s")
                params.append(like)
        if product_q:
            # Фильтруем по названию товара в product-first режиме.
            where.append("pr.title ILIKE %s")
            params.append(f"%{product_q}%")
        if platform_q:
            like = f"%{platform_q}%"
            where.append("(p.code ILIKE %s OR p.name ILIKE %s)")
            params.extend([like, like])
        if type_q:
            type_values = parse_multi_filter_values(type_q)
            if len(type_values) > 1:
                # Для множественного выбора типов фильтруем по точным кодам.
                type_where = " OR ".join(["dt.code = %s"] * len(type_values))
                where.append(f"({type_where})")
                params.extend(type_values)
            else:
                like = f"%{type_q}%"
                where.append("(dt.code ILIKE %s OR dt.name ILIKE %s)")
                params.extend([like, like])
        if status_q:
            status_values = parse_multi_filter_values(status_q)
            if len(status_values) > 1:
                # Для множественного выбора статусов используем точное сравнение кодов.
                status_where = " OR ".join(["ds.code = %s"] * len(status_values))
                where.append(f"({status_where})")
                params.extend(status_values)
            else:
                like = f"%{status_q}%"
                where.append("(ds.code ILIKE %s OR ds.name ILIKE %s)")
                params.extend([like, like])
        if flow_status_q:
            flow_values = parse_flow_status_filter_values(flow_status_q)
            if len(flow_values) > 1:
                # Для списка статусов фильтруем по точным кодам, чтобы корректно поддержать pending,draft.
                flow_where = " OR ".join(["fs.code = %s"] * len(flow_values))
                where.append(f"({flow_where})")
                params.extend(flow_values)
            else:
                like = f"%{flow_status_q}%"
                where.append("(fs.code ILIKE %s OR fs.name ILIKE %s)")
                params.extend([like, like])
        if source_q:
            like = f"%{source_q}%"
            where.append("(src.code ILIKE %s OR src.name ILIKE %s)")
            params.extend([like, like])
        if date_q:
            where.append("COALESCE(di.purchase_at, d.created_at)::text ILIKE %s")
            params.append(f"%{date_q}%")
        if price_q:
            where.append("di.price::text ILIKE %s")
            params.append(f"%{price_q}%")
        if purchase_from:
            where.append("COALESCE(di.purchase_at, d.created_at)::date >= %s")
            params.append(purchase_from)
        if purchase_to:
            where.append("COALESCE(di.purchase_at, d.created_at)::date <= %s")
            params.append(purchase_to)
        if price_min is not None:
            where.append("di.price >= %s")
            params.append(price_min)
        if price_max is not None:
            where.append("di.price <= %s")
            params.append(price_max)
        where_sql = "WHERE " + " AND ".join(where) if where else ""
        return where_sql, params

    def slots_summary(conn, account_id: int, platform_id: int):
        row = q1(
            conn,
            """
            SELECT occupied_slots, free_slots
            FROM app.v_account_platform_slots
            WHERE account_id=%s AND platform_id=%s
            """,
            (account_id, platform_id),
        )
        if not row:
            return (0, 0)
        return int(row[0]), int(row[1])

    def get_account_platform_slots(conn, account_id: int):
        rows = qall(
            conn,
            """
            SELECT p.code, s.slot_capacity, s.occupied_slots, s.free_slots
            FROM app.v_account_platform_slots s
            JOIN app.platforms p ON p.platform_id = s.platform_id
            WHERE s.account_id=%s
            ORDER BY p.code
            """,
            (account_id,),
        )
        return [
            AccountPlatformSlots(
                platform_code=r0,
                slot_capacity=int(r1 or 0),
                occupied_slots=int(r2 or 0),
                free_slots=int(r3 or 0),
            )
            for (r0, r1, r2, r3) in rows
        ]

    def get_account_slot_status(conn, account_id: int):
        rows = qall(
            conn,
            """
            SELECT slot_type_code, platform_code, mode, capacity, occupied, free
            FROM app.v_account_slot_status
            WHERE account_id=%s
            ORDER BY slot_type_code
            """,
            (account_id,),
        )
        return [
            AccountSlotStatusOut(
                slot_type_code=r0,
                platform_code=r1,
                mode=r2,
                capacity=int(r3 or 0),
                occupied=int(r4 or 0),
                free=int(r5 or 0),
            )
            for (r0, r1, r2, r3, r4, r5) in rows
        ]

    def normalize_platform_codes(codes: Optional[list[str]]) -> list[str]:
        if not codes:
            return []
        uniq = []
        seen = set()
        for code in codes:
            if not code:
                continue
            val = str(code).strip().lower()
            if not val or val in seen:
                continue
            seen.add(val)
            uniq.append(val)
        return uniq

    # Возвращает платформы товара через нейтральную связку product_platforms.
    def get_game_platform_codes(conn, product_id: int) -> list[str]:
        rows = qall(
            conn,
            """
            SELECT p.code
            FROM app.product_platforms pp
            JOIN app.platforms p ON p.platform_id = pp.platform_id
            WHERE pp.product_id=%s
            ORDER BY p.code
            """,
            (product_id,),
        )
        return [r[0] for r in rows]

    def get_account_platform_codes(conn, account_id: int) -> list[str]:
        rows = qall(
            conn,
            """
            SELECT DISTINCT p.code
            FROM app.account_assets aa
            JOIN app.product_platforms pp ON pp.product_id = aa.product_id
            JOIN app.platforms p ON p.platform_id = pp.platform_id
            WHERE aa.account_id=%s AND aa.asset_type_code='game'
            ORDER BY p.code
            """,
            (account_id,),
        )
        return [r[0] for r in rows]

    def account_has_ps4(conn, account_id: int) -> bool:
        row = q1(
            conn,
            """
            SELECT 1
            FROM app.account_assets aa
            JOIN app.product_platforms pp ON pp.product_id = aa.product_id
            JOIN app.platforms p ON p.platform_id = pp.platform_id
            WHERE aa.account_id=%s AND aa.asset_type_code='game' AND p.code='ps4'
            LIMIT 1
            """,
            (account_id,),
        )
        return bool(row)

    def get_slot_type(conn, slot_type_code: str):
        row = q1(
            conn,
            "SELECT code, platform_code, mode, capacity FROM app.slot_types WHERE code=%s",
            (slot_type_code,),
        )
        if not row:
            raise HTTPException(400, "Unknown slot_type_code")
        return row

    def ensure_account_allows_slot_type(conn, account_id: int, slot_type_code: str):
        slot_type = get_slot_type(conn, slot_type_code)
        platform_code = slot_type[1]
        if platform_code == "ps4" and not account_has_ps4(conn, account_id):
            raise HTTPException(400, "Account does not support PS4 slot type")
        return slot_type

    def get_account_slot_free(conn, account_id: int, slot_type_code: str) -> int:
        row = q1(
            conn,
            """
            SELECT free
            FROM app.v_account_slot_status
            WHERE account_id=%s AND slot_type_code=%s
            """,
            (account_id, slot_type_code),
        )
        return int(row[0] or 0) if row else 0

    def release_slot_assignment(conn, deal_item_id: int, released_by: Optional[str]):
        exec1(
            conn,
            """
            UPDATE app.account_slot_assignments
            SET released_at=now(), released_by=%s
            WHERE deal_item_id=%s AND released_at IS NULL
            """,
            (released_by, deal_item_id),
        )

    return DbHelpers(
        get_platform_id=get_platform_id,
        get_platform_info=get_platform_info,
        get_region_id=get_region_id,
        get_domain_id=get_domain_id,
        get_platform_id_optional=get_platform_id_optional,
        ensure_account_exists=ensure_account_exists,
        ensure_customer=ensure_customer,
        ensure_source_exists=ensure_source_exists,
        build_deals_filters=build_deals_filters,
        slots_summary=slots_summary,
        get_account_platform_slots=get_account_platform_slots,
        get_account_slot_status=get_account_slot_status,
        normalize_platform_codes=normalize_platform_codes,
        get_game_platform_codes=get_game_platform_codes,
        get_account_platform_codes=get_account_platform_codes,
        account_has_ps4=account_has_ps4,
        ensure_account_allows_slot_type=ensure_account_allows_slot_type,
        get_slot_type=get_slot_type,
        get_account_slot_free=get_account_slot_free,
        release_slot_assignment=release_slot_assignment,
    )
