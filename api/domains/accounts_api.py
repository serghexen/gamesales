from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import Depends, HTTPException

from .accounts_models import (
    AccountCreate,
    AccountUpdate,
    AccountPlatformSlots,
    AccountSlotStatusOut,
    AccountOut,
    AccountListOut,
    AccountSecretIn,
    AccountSecretOut,
    AccountSecretsBatchIn,
    AccountSecretsBatchItem,
    SlotAvailabilityOut,
    AccountGamesIn,
    GameAccountOut,
    AccountSlotAssignmentOut,
)


def mount_accounts_routes(
    app,
    *,
    DB_DSN,
    psycopg,
    q1,
    qall,
    exec1,
    get_region_id,
    get_domain_id,
    get_platform_info,
    ensure_account_exists,
    ensure_game_exists,
    validate_date_not_future,
    get_account_platform_slots,
    get_account_slot_status,
    b64_encode,
    require_role,
    get_current_user,
    GameOut,
):
    @app.get("/accounts", response_model=AccountListOut)
    def list_accounts(
        q: Optional[str] = None,
        login_q: Optional[str] = None,
        game_q: Optional[str] = None,
        region_q: Optional[str] = None,
        status_q: Optional[str] = None,
        slots_q: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        sort_key: str = "login",
        sort_dir: str = "asc",
        page: int = 1,
        page_size: int = 50,
        all: bool = False,
        user=Depends(get_current_user),
    ):
        page = max(1, page)
        if all:
            page_size = 0
            offset = 0
        else:
            page_size = max(1, min(int(page_size or 50), 200))
            offset = (page - 1) * page_size
    
        sort_map = {
            "login": "login_name",
            "region": "region_code",
            "status": "status_code",
            "slots": "free_total",
            "games": "game_titles_text",
            "date": "account_date",
        }
        sort_col = sort_map.get(sort_key, "login_name")
        sort_dir = "desc" if str(sort_dir).lower() == "desc" else "asc"
    
        filters = []
        params = []
        if login_q:
            filters.append("(a.login_name ILIKE %s OR d.name ILIKE %s OR (a.login_name || '@' || d.name) ILIKE %s)")
            params.extend([f"%{login_q}%", f"%{login_q}%", f"%{login_q}%"])
        if q:
            filters.append("(a.login_name ILIKE %s OR d.name ILIKE %s OR (a.login_name || '@' || d.name) ILIKE %s OR r.code ILIKE %s OR g.title ILIKE %s)")
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"])
        if game_q:
            filters.append("g.title ILIKE %s")
            params.append(f"%{game_q}%")
        if region_q:
            filters.append("r.code ILIKE %s")
            params.append(f"%{region_q}%")
        if status_q:
            filters.append("a.status_code ILIKE %s")
            params.append(f"%{status_q}%")
        else:
            filters.append("a.status_code <> 'archived'")
        if date_from:
            filters.append("a.account_date >= %s")
            params.append(date_from)
        if date_to:
            filters.append("a.account_date <= %s")
            params.append(date_to)
    
        where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
    
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                f"""
                WITH account_platforms AS (
                  SELECT
                    aa.account_id,
                    BOOL_OR(p.code = 'ps4') AS has_ps4,
                    COALESCE(array_agg(DISTINCT p.code ORDER BY p.code) FILTER (WHERE p.code IS NOT NULL), '{{}}'::text[]) AS platform_codes
                  FROM app.account_assets aa
                  JOIN app.game_platforms gp ON gp.game_id = aa.game_id
                  JOIN app.platforms p ON p.platform_id = gp.platform_id
                  WHERE aa.asset_type_code = 'game'
                  GROUP BY aa.account_id
                ),
                base AS (
                  SELECT
                    a.account_id,
                    a.region_id,
                    a.status_code,
                    a.login_name,
                    a.domain_id,
                    a.account_date,
                    a.notes,
                    r.code as region_code,
                    d.name as domain_name,
                    COALESCE(array_agg(DISTINCT g.title ORDER BY g.title) FILTER (WHERE g.title IS NOT NULL), '{{}}'::text[]) as game_titles,
                    COALESCE(string_agg(DISTINCT g.title, ' · ' ORDER BY g.title), '') as game_titles_text,
                    ap.platform_codes,
                    COALESCE(SUM(s.free), 0) as free_total,
                    COALESCE(string_agg(st.code || ' ' || s.occupied || '/' || s.capacity, ' · ' ORDER BY st.code), '') as slots_text
                  FROM app.accounts a
                  LEFT JOIN app.regions r ON r.region_id = a.region_id
                  LEFT JOIN app.domains d ON d.domain_id = a.domain_id
                  LEFT JOIN account_platforms ap ON ap.account_id = a.account_id
                  LEFT JOIN app.account_assets aa ON aa.account_id = a.account_id AND aa.asset_type_code = 'game'
                  LEFT JOIN app.game_titles g ON g.game_id = aa.game_id
                  LEFT JOIN app.v_account_slot_status s
                    ON s.account_id = a.account_id
                   AND (COALESCE(ap.has_ps4, false) OR s.platform_code = 'ps5')
                  LEFT JOIN app.slot_types st ON st.code = s.slot_type_code
                  {where_sql}
                  GROUP BY a.account_id, a.region_id, a.status_code, a.login_name, a.domain_id, a.account_date, a.notes, r.code, d.name, ap.platform_codes
                ),
                filtered AS (
                  SELECT * FROM base
                  {"WHERE slots_text ILIKE %s" if slots_q else ""}
                ),
                page AS (
                  SELECT
                    filtered.*,
                    COUNT(*) OVER() AS total_count
                  FROM filtered
                  ORDER BY {sort_col} {sort_dir}, account_id DESC
                  {"" if all else "LIMIT %s OFFSET %s"}
                )
                SELECT
                  page.account_id,
                  page.region_code,
                  page.status_code,
                  page.login_name,
                  page.domain_name,
                  page.account_date,
                  page.notes,
                  page.game_titles,
                  page.platform_codes,
                  s.slot_type_code,
                  s.platform_code,
                  s.mode,
                  s.capacity,
                  s.occupied,
                  s.free,
                  page.total_count
                FROM page
                LEFT JOIN app.v_account_slot_status s ON s.account_id = page.account_id
                ORDER BY {sort_col} {sort_dir}, page.account_id DESC, s.slot_type_code
                """,
                params + ([f"%{slots_q}%"] if slots_q else []) + ([] if all else [page_size, offset]),
            )
    
        acc_map = {}
        acc_list = []
        total = 0
        for row in rows:
            if not total:
                total = int(row[15] or 0)
            account_id = row[0]
            if account_id not in acc_map:
                acc = AccountOut(
                    account_id=account_id,
                    region_code=row[1],
                    status=row[2],
                    login_name=row[3],
                    domain_code=row[4],
                    login_full=f"{row[3]}@{row[4]}" if row[3] and row[4] else None,
                    platform_slots=[],
                    slot_status=[],
                    game_titles=list(row[7] or []),
                    platform_codes=list(row[8] or []),
                    account_date=row[5],
                    notes=row[6],
                )
                acc_map[account_id] = acc
                acc_list.append(acc)
            slot_type_code = row[9]
            if slot_type_code:
                acc_map[account_id].slot_status.append(
                    AccountSlotStatusOut(
                        slot_type_code=slot_type_code,
                        platform_code=row[10],
                        mode=row[11],
                        capacity=int(row[12] or 0),
                        occupied=int(row[13] or 0),
                        free=int(row[14] or 0),
                    )
                )
        return {"total": total, "items": acc_list}
    
    @app.post("/accounts", response_model=AccountOut)
    def create_account(payload: AccountCreate, user=Depends(get_current_user)):
        if not payload.login_name or not payload.domain_code:
            raise HTTPException(400, "login_name and domain_code are required")
        validate_date_not_future(payload.account_date, "account_date")
        with psycopg.connect(DB_DSN) as conn:
            region_id = get_region_id(conn, payload.region_code)
            domain_id = get_domain_id(conn, payload.domain_code)
    
            row = q1(conn, """
                INSERT INTO app.accounts(login_name, domain_id, region_id, notes, account_date)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING account_id
            """, (payload.login_name, domain_id, region_id, payload.notes, payload.account_date))
            account_id = int(row[0])
    
            ps4_id, ps4_slots = get_platform_info(conn, "ps4")
            ps5_id, ps5_slots = get_platform_info(conn, "ps5")
            exec1(
                conn,
                """
                INSERT INTO app.account_platforms(account_id, platform_id, slot_capacity)
                VALUES (%s, %s, %s), (%s, %s, %s)
                ON CONFLICT (account_id, platform_id) DO UPDATE SET slot_capacity=excluded.slot_capacity
                """,
                (account_id, ps4_id, ps4_slots, account_id, ps5_id, ps5_slots),
            )
            conn.commit()
    
            platform_slots = get_account_platform_slots(conn, account_id)
            slot_status = get_account_slot_status(conn, account_id)
            return AccountOut(
                account_id=account_id,
                region_code=payload.region_code,
                status="active",
                login_name=payload.login_name,
                domain_code=payload.domain_code,
                login_full=f"{payload.login_name}@{payload.domain_code}" if payload.login_name and payload.domain_code else None,
                platform_slots=platform_slots,
                slot_status=slot_status,
                game_titles=None,
                account_date=payload.account_date,
                notes=payload.notes
            )
    
    @app.put("/accounts/{account_id}", response_model=AccountOut)
    def update_account(
        account_id: int,
        payload: AccountUpdate,
        user=Depends(require_role("admin")),
    ):
        validate_date_not_future(payload.account_date, "account_date")
        with psycopg.connect(DB_DSN) as conn:
            current = q1(
                conn,
                """
                SELECT login_name, domain_id, region_id, status_code, account_date, notes
                FROM app.accounts
                WHERE account_id=%s
                """,
                (account_id,),
            )
            if not current:
                raise HTTPException(404, "Account not found")
    
            region_id = get_region_id(conn, payload.region_code) if payload.region_code else current[2]
            domain_id = get_domain_id(conn, payload.domain_code) if payload.domain_code else current[1]
    
            new_login = payload.login_name if payload.login_name is not None else current[0]
            new_status = payload.status_code if payload.status_code is not None else current[3]
            new_date = payload.account_date if payload.account_date is not None else current[4]
            new_notes = payload.notes if payload.notes is not None else current[5]
    
            exec1(
                conn,
                """
                UPDATE app.accounts
                SET login_name=%s,
                    domain_id=%s,
                    region_id=%s,
                    status_code=%s,
                    notes=%s,
                    account_date=%s
                WHERE account_id=%s
                """,
                (
                    new_login,
                    domain_id,
                    region_id,
                    new_status,
                    new_notes,
                    new_date,
                    account_id,
                ),
            )
            conn.commit()
    
            row = q1(
                conn,
                """
                SELECT
                  a.account_id,
                  r.code as region_code,
                  a.status_code,
                  a.login_name,
                  d.name as domain_name,
                  a.account_date,
                  a.notes
                FROM app.accounts a
                LEFT JOIN app.regions r ON r.region_id = a.region_id
                LEFT JOIN app.domains d ON d.domain_id = a.domain_id
                WHERE a.account_id=%s
                """,
                (account_id,),
            )
            if not row:
                raise HTTPException(404, "Account not found")
    
            platform_slots = get_account_platform_slots(conn, row[0])
            slot_status = get_account_slot_status(conn, row[0])
            return AccountOut(
                account_id=row[0], region_code=row[1],
                status=row[2], login_name=row[3], domain_code=row[4],
                login_full=f"{row[3]}@{row[4]}" if row[3] and row[4] else None,
                platform_slots=platform_slots,
                slot_status=slot_status,
                game_titles=None,
                account_date=row[5],
                notes=row[6]
            )
    
    @app.delete("/accounts/{account_id}")
    def archive_account(account_id: int, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT 1 FROM app.accounts WHERE account_id=%s", (account_id,))
            if not row:
                raise HTTPException(404, "Account not found")
            exec1(conn, "UPDATE app.accounts SET status_code='archived' WHERE account_id=%s", (account_id,))
            conn.commit()
        return {"ok": True}
    
    @app.get("/accounts/{account_id}/secrets", response_model=List[AccountSecretOut])
    def list_account_secrets(account_id: int, user=Depends(require_role("admin"))):
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                """
                SELECT secret_key, secret_value, created_at
                FROM app.account_secrets
                WHERE account_id=%s
                ORDER BY secret_key
                """,
                (account_id,),
            )
        return [AccountSecretOut(secret_key=r0, secret_value_b64=r1, created_at=r2) for (r0, r1, r2) in rows]
    
    @app.post("/accounts/secrets/batch", response_model=List[AccountSecretsBatchItem])
    def list_account_secrets_batch(payload: AccountSecretsBatchIn, user=Depends(require_role("admin"))):
        account_ids = list({int(a) for a in (payload.account_ids or [])})
        if not account_ids:
            return []
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                """
                SELECT account_id, secret_key, secret_value, created_at
                FROM app.account_secrets
                WHERE account_id = ANY(%s)
                ORDER BY account_id, secret_key
                """,
                (account_ids,),
            )
        out_map = {aid: [] for aid in account_ids}
        for account_id, secret_key, secret_value, created_at in rows:
            out_map.setdefault(account_id, []).append(
                AccountSecretOut(
                    secret_key=secret_key,
                    secret_value_b64=secret_value,
                    created_at=created_at,
                )
            )
        return [AccountSecretsBatchItem(account_id=aid, secrets=out_map.get(aid, [])) for aid in account_ids]
    
    @app.post("/accounts/{account_id}/secrets", response_model=AccountSecretOut)
    def upsert_account_secret(
        account_id: int,
        payload: AccountSecretIn,
        user=Depends(require_role("admin")),
    ):
        value_b64 = b64_encode(payload.secret_value)
        with psycopg.connect(DB_DSN) as conn:
            q1(
                conn,
                """
                INSERT INTO app.account_secrets(account_id, secret_key, secret_value)
                VALUES (%s, %s, %s)
                ON CONFLICT (account_id, secret_key)
                DO UPDATE SET secret_value=excluded.secret_value
                RETURNING secret_key, secret_value, created_at
                """,
                (account_id, payload.secret_key, value_b64),
            )
            conn.commit()
            row = q1(
                conn,
                "SELECT secret_key, secret_value, created_at FROM app.account_secrets WHERE account_id=%s AND secret_key=%s",
                (account_id, payload.secret_key),
            )
        return AccountSecretOut(secret_key=row[0], secret_value_b64=row[1], created_at=row[2])
    
    @app.delete("/accounts/{account_id}/secrets/{secret_key}")
    def delete_account_secret(
        account_id: int,
        secret_key: str,
        user=Depends(require_role("admin")),
    ):
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                "DELETE FROM app.account_secrets WHERE account_id=%s AND secret_key=%s",
                (account_id, secret_key),
            )
            conn.commit()
        return {"ok": True}
    
    @app.get("/accounts/{account_id}/games", response_model=List[GameOut])
    def list_account_games(account_id: int, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            ensure_account_exists(conn, account_id)
            rows = qall(
                conn,
                """
                SELECT g.game_id, g.title, g.short_title, g.link, g.logo_url, g.text_lang, g.audio_lang, g.vr_support, r.code,
                       COALESCE(array_agg(p.code ORDER BY p.code) FILTER (WHERE p.code IS NOT NULL), '{}'::text[]) AS platform_codes
                FROM app.account_assets aa
                JOIN app.game_titles g ON g.game_id = aa.game_id
                LEFT JOIN app.regions r ON r.region_id = g.region_id
                LEFT JOIN app.game_platforms gp ON gp.game_id = g.game_id
                LEFT JOIN app.platforms p ON p.platform_id = gp.platform_id
                WHERE aa.account_id=%s AND aa.asset_type_code='game'
                GROUP BY g.game_id, g.title, g.short_title, g.link, g.logo_url, g.text_lang, g.audio_lang, g.vr_support, r.code
                ORDER BY g.title
                """,
                (account_id,),
            )
        return [
            GameOut(
                game_id=r0,
                title=r1,
                short_title=r2,
                link=r3,
                logo_url=r4,
                text_lang=r5,
                audio_lang=r6,
                vr_support=r7,
                platform_codes=list(r9 or []),
                region_code=r8,
            )
            for (r0, r1, r2, r3, r4, r5, r6, r7, r8, r9) in rows
        ]
    
    @app.get("/accounts/{account_id}/slot-status", response_model=List[AccountSlotStatusOut])
    def list_account_slot_status(account_id: int, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            ensure_account_exists(conn, account_id)
            rows = qall(
                conn,
                """
                SELECT s.slot_type_code, s.platform_code, s.mode, s.capacity, s.occupied, s.free
                FROM app.v_account_slot_status s
                LEFT JOIN (
                  SELECT
                    aa.account_id,
                    BOOL_OR(p.code = 'ps4') AS has_ps4
                  FROM app.account_assets aa
                  JOIN app.game_platforms gp ON gp.game_id = aa.game_id
                  JOIN app.platforms p ON p.platform_id = gp.platform_id
                  WHERE aa.asset_type_code = 'game' AND aa.account_id = %s
                  GROUP BY aa.account_id
                ) ap ON ap.account_id = s.account_id
                WHERE s.account_id=%s
                  AND (COALESCE(ap.has_ps4, false) OR s.platform_code = 'ps5')
                ORDER BY slot_type_code
                """,
                (account_id, account_id),
            )
        return [
            AccountSlotStatusOut(
                slot_type_code=r[0],
                platform_code=r[1],
                mode=r[2],
                capacity=int(r[3] or 0),
                occupied=int(r[4] or 0),
                free=int(r[5] or 0),
            )
            for r in rows
        ]
    
    @app.get("/accounts/{account_id}/slot-assignments", response_model=List[AccountSlotAssignmentOut])
    def list_account_slot_assignments(account_id: int, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            ensure_account_exists(conn, account_id)
            rows = qall(
                conn,
                """
                SELECT
                  asa.assignment_id,
                  asa.account_id,
                  a.login_name,
                  d.name as domain_name,
                  asa.slot_type_code,
                  asa.customer_id,
                  c.nickname,
                  asa.game_id,
                  g.title,
                  asa.deal_id,
                  asa.deal_item_id,
                  asa.assigned_at,
                  asa.released_at,
                  asa.assigned_by,
                  asa.released_by
                FROM app.account_slot_assignments asa
                LEFT JOIN app.accounts a ON a.account_id = asa.account_id
                LEFT JOIN app.domains d ON d.domain_id = a.domain_id
                LEFT JOIN app.customers c ON c.customer_id = asa.customer_id
                LEFT JOIN app.game_titles g ON g.game_id = asa.game_id
                WHERE asa.account_id=%s
                ORDER BY asa.released_at IS NULL DESC, asa.assigned_at DESC
                """,
                (account_id,),
            )
        return [
            AccountSlotAssignmentOut(
                assignment_id=r[0],
                account_id=r[1],
                account_login=f"{r[2]}@{r[3]}" if r[2] and r[3] else None,
                slot_type_code=r[4],
                customer_id=r[5],
                customer_nickname=r[6],
                game_id=r[7],
                game_title=r[8],
                deal_id=r[9],
                deal_item_id=r[10],
                assigned_at=r[11],
                released_at=r[12],
                assigned_by=r[13],
                released_by=r[14],
            )
            for r in rows
        ]
    
    @app.get("/accounts/for-deal", response_model=List[AccountOut])
    def list_accounts_for_deal(
        game_id: int,
        slot_type_code: Optional[str] = None,
        user=Depends(get_current_user),
    ):
        slot_type_code = (slot_type_code or "").strip() or None
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                """
                WITH account_platforms AS (
                  SELECT
                    aa.account_id,
                    BOOL_OR(p.code = 'ps4') AS has_ps4,
                    COALESCE(array_agg(DISTINCT p.code ORDER BY p.code) FILTER (WHERE p.code IS NOT NULL), '{}'::text[]) AS platform_codes
                  FROM app.account_assets aa
                  JOIN app.game_platforms gp ON gp.game_id = aa.game_id
                  JOIN app.platforms p ON p.platform_id = gp.platform_id
                  WHERE aa.asset_type_code = 'game'
                  GROUP BY aa.account_id
                ),
                base AS (
                  SELECT
                    a.account_id,
                    a.region_id,
                    a.status_code,
                    a.login_name,
                    a.domain_id,
                    a.account_date,
                    a.notes,
                    r.code as region_code,
                    d.name as domain_name,
                    ap.platform_codes,
                    COALESCE(ap.has_ps4, false) as has_ps4
                  FROM app.accounts a
                  LEFT JOIN app.regions r ON r.region_id = a.region_id
                  LEFT JOIN app.domains d ON d.domain_id = a.domain_id
                  LEFT JOIN account_platforms ap ON ap.account_id = a.account_id
                  JOIN app.account_assets aa
                    ON aa.account_id = a.account_id
                   AND aa.asset_type_code = 'game'
                   AND aa.game_id = %s
                  WHERE a.status_code <> 'archived'
                    AND EXISTS (
                    SELECT 1
                    FROM app.v_account_slot_status ss
                    WHERE ss.account_id = a.account_id
                      AND ss.free > 0
                      AND (COALESCE(ap.has_ps4, false) OR ss.platform_code = 'ps5')
                      AND (%s::text IS NULL OR ss.slot_type_code = %s)
                  )
                )
                SELECT
                  base.account_id,
                  base.region_code,
                  base.status_code,
                  base.login_name,
                  base.domain_name,
                  base.account_date,
                  base.notes,
                  base.platform_codes,
                  p.code as platform_code,
                  s.slot_capacity,
                  s.occupied_slots,
                  s.free_slots
                FROM base
                LEFT JOIN app.v_account_platform_slots s ON s.account_id = base.account_id
                LEFT JOIN app.platforms p ON p.platform_id = s.platform_id
                ORDER BY base.account_id DESC, p.code
                """,
                (game_id, slot_type_code, slot_type_code),
            )
    
        acc_map = {}
        acc_list = []
        for row in rows:
            account_id = row[0]
            if account_id not in acc_map:
                acc = AccountOut(
                    account_id=account_id,
                    region_code=row[1],
                    status=row[2],
                    login_name=row[3],
                    domain_code=row[4],
                    login_full=f"{row[3]}@{row[4]}" if row[3] and row[4] else None,
                    platform_slots=[],
                    platform_codes=list(row[7] or []),
                    account_date=row[5],
                    notes=row[6],
                )
                acc_map[account_id] = acc
                acc_list.append(acc)
            platform_code = row[8]
            if platform_code:
                acc_map[account_id].platform_slots.append(
                    AccountPlatformSlots(
                        platform_code=platform_code,
                        slot_capacity=int(row[9] or 0),
                        occupied_slots=int(row[10] or 0),
                        free_slots=int(row[11] or 0),
                    )
                )
        return acc_list
    
    @app.get("/accounts/for-deal/availability", response_model=List[SlotAvailabilityOut])
    def list_slot_availability_for_deal(
        game_id: int,
        user=Depends(get_current_user),
    ):
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                """
                WITH account_platforms AS (
                  SELECT
                    aa.account_id,
                    BOOL_OR(p.code = 'ps4') AS has_ps4
                  FROM app.account_assets aa
                  JOIN app.game_platforms gp ON gp.game_id = aa.game_id
                  JOIN app.platforms p ON p.platform_id = gp.platform_id
                  WHERE aa.asset_type_code = 'game'
                  GROUP BY aa.account_id
                ),
                base_accounts AS (
                  SELECT a.account_id
                  FROM app.accounts a
                  JOIN app.account_assets aa
                    ON aa.account_id = a.account_id
                   AND aa.asset_type_code = 'game'
                   AND aa.game_id = %s
                  WHERE a.status_code <> 'archived'
                )
                SELECT
                  st.code AS slot_type_code,
                  BOOL_OR(COALESCE(ss.free, 0) > 0) AS has_free
                FROM base_accounts ba
                LEFT JOIN account_platforms ap ON ap.account_id = ba.account_id
                JOIN app.slot_types st
                  ON (COALESCE(ap.has_ps4, false) OR st.platform_code = 'ps5')
                LEFT JOIN app.v_account_slot_status ss
                  ON ss.account_id = ba.account_id AND ss.slot_type_code = st.code
                GROUP BY st.code
                ORDER BY st.code
                """,
                (game_id,),
            )
        return [SlotAvailabilityOut(slot_type_code=r0, has_free=bool(r1)) for (r0, r1) in rows]
    
    @app.put("/accounts/{account_id}/games")
    def set_account_games(
        account_id: int,
        payload: AccountGamesIn,
        user=Depends(require_role("admin")),
    ):
        with psycopg.connect(DB_DSN) as conn:
            ensure_account_exists(conn, account_id)
            game_ids = list({int(g) for g in (payload.game_ids or [])})
            if game_ids:
                rows = qall(conn, "SELECT game_id FROM app.game_titles WHERE game_id = ANY(%s)", (game_ids,))
                valid_ids = [int(r[0]) for r in rows]
            else:
                valid_ids = []
    
            exec1(
                conn,
                "DELETE FROM app.account_assets WHERE account_id=%s AND asset_type_code='game'",
                (account_id,),
            )
            if valid_ids:
                with conn.cursor() as cur:
                    cur.executemany(
                        "INSERT INTO app.account_assets(account_id, game_id, asset_type_code) VALUES (%s, %s, 'game')",
                        [(account_id, gid) for gid in valid_ids],
                    )
            conn.commit()
        return {"ok": True}
    
    @app.get("/games/{game_id}/accounts", response_model=List[GameAccountOut])
    def list_game_accounts(game_id: int, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            ensure_game_exists(conn, game_id)
            rows = qall(
                conn,
                """
                SELECT
                  a.account_id,
                  a.login_name,
                  d.name as domain_name,
                  p.code as platform_code,
                  s.free_slots,
                  s.occupied_slots
                FROM (
                  SELECT DISTINCT ON (di.account_id, di.platform_id)
                    di.account_id,
                    di.platform_id
                  FROM app.deal_items di
                  WHERE di.game_id=%s
                    AND di.account_id IS NOT NULL
                    AND di.platform_id IS NOT NULL
                  ORDER BY di.account_id DESC, di.platform_id
                ) dg
                JOIN app.accounts a ON a.account_id = dg.account_id
                LEFT JOIN app.domains d ON d.domain_id = a.domain_id
                JOIN app.platforms p ON p.platform_id = dg.platform_id
                LEFT JOIN app.v_account_platform_slots s ON s.account_id = dg.account_id AND s.platform_id = dg.platform_id
                ORDER BY a.account_id DESC, p.code
                """,
                (game_id,),
            )
        return [
            GameAccountOut(
                account_id=r0,
                login_full=f"{r1}@{r2}" if r1 and r2 else None,
                platform_code=r3,
                free_slots=int(r4 or 0),
                occupied_slots=int(r5 or 0),
            )
            for (r0, r1, r2, r3, r4, r5) in rows
        ]
    
    @app.get("/games/{game_id}/slot-assignments", response_model=List[AccountSlotAssignmentOut])
    def list_game_slot_assignments(game_id: int, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            ensure_game_exists(conn, game_id)
            rows = qall(
                conn,
                """
                SELECT
                  asa.assignment_id,
                  asa.account_id,
                  a.login_name,
                  d.name as domain_name,
                  asa.slot_type_code,
                  asa.customer_id,
                  c.nickname,
                  asa.game_id,
                  g.title,
                  asa.deal_id,
                  asa.deal_item_id,
                  asa.assigned_at,
                  asa.released_at,
                  asa.assigned_by,
                  asa.released_by
                FROM app.account_slot_assignments asa
                LEFT JOIN app.accounts a ON a.account_id = asa.account_id
                LEFT JOIN app.domains d ON d.domain_id = a.domain_id
                LEFT JOIN app.customers c ON c.customer_id = asa.customer_id
                LEFT JOIN app.game_titles g ON g.game_id = asa.game_id
                WHERE asa.game_id=%s
                ORDER BY asa.released_at IS NULL DESC, asa.assigned_at DESC
                """,
                (game_id,),
            )
        return [
            AccountSlotAssignmentOut(
                assignment_id=r[0],
                account_id=r[1],
                account_login=f"{r[2]}@{r[3]}" if r[2] and r[3] else None,
                slot_type_code=r[4],
                customer_id=r[5],
                customer_nickname=r[6],
                game_id=r[7],
                game_title=r[8],
                deal_id=r[9],
                deal_item_id=r[10],
                assigned_at=r[11],
                released_at=r[12],
                assigned_by=r[13],
                released_by=r[14],
            )
            for r in rows
        ]
    
    @app.post("/slot-assignments/{assignment_id}/release")
    def release_slot_assignment_api(assignment_id: int, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                "SELECT assignment_id FROM app.account_slot_assignments WHERE assignment_id=%s AND released_at IS NULL",
                (assignment_id,),
            )
            if not row:
                return {"ok": True}
            exec1(
                conn,
                "UPDATE app.account_slot_assignments SET released_at=now(), released_by=%s WHERE assignment_id=%s",
                (user.username, assignment_id),
            )
            conn.commit()
        return {"ok": True}
    
