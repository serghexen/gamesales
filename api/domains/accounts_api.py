from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import Depends, HTTPException, Query

from .accounts_models import (
    AccountCreate,
    AccountUpdate,
    AccountPlatformSlots,
    AccountSlotStatusOut,
    AccountOut,
    AccountListOut,
    AccountSecretIn,
    AccountSecretOut,
    AccountSecretsPatchIn,
    AccountSecretsBatchIn,
    AccountSecretsBatchItem,
    SlotAvailabilityOut,
    AccountProductsIn,
    AccountLabelOut,
    ProductAccountOut,
    ProductLinkedAccountOut,
    ProductSelectableAccountOut,
    AccountProductOut,
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
    validate_date_not_future,
    get_account_platform_slots,
    get_account_slot_status,
    b64_encode,
    require_role,
    get_current_user,
):
    # Безопасно читает значение из SQL-строки по индексу, даже если тест дает укороченный кортеж.
    def row_value(row, idx, default=None):
        return row[idx] if row is not None and len(row) > idx else default

    # Приводит datetime к UTC-aware виду для корректного сравнения сроков.
    def to_utc_aware(value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    # Валидирует товар для слотов: поддерживаем игры и подписки.
    def ensure_slot_product_supported(conn, product_id: Optional[int]) -> None:
        if product_id is None:
            raise HTTPException(400, "product_id is required")
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
        if type_code not in {"game", "subscription"}:
            raise HTTPException(400, "slot availability supports only products with type game or subscription")

    # Валидирует список product_ids для привязки к аккаунту (игры и подписки).
    def resolve_asset_links(conn, payload: AccountProductsIn) -> List[tuple[int, str]]:
        product_ids = list({int(p) for p in (payload.product_ids or [])})
        valid_links: List[tuple[int, str]] = []
        if product_ids:
            rows = qall(
                conn,
                """
                SELECT product_id, type_code, is_archived
                FROM app.products
                WHERE product_id = ANY(%s)
                """,
                (product_ids,),
            )
            rows_by_id = {int(r[0]): r for r in rows}
            for product_id in product_ids:
                row = rows_by_id.get(product_id)
                if not row:
                    raise HTTPException(400, f"Unknown product_id: {product_id}")
                type_code = str(row[1] or "").strip().lower()
                is_archived = bool(row[2]) if row[2] is not None else False
                if is_archived:
                    raise HTTPException(400, f"Product is archived: {product_id}")
                if type_code not in {"game", "subscription"}:
                    raise HTTPException(400, "account assets support only products with type game or subscription")
                valid_links.append((product_id, type_code))
            # Сохраняем порядок без дублей.
            out: List[tuple[int, str]] = []
            seen: set[int] = set()
            for product_id, type_code in valid_links:
                if product_id in seen:
                    continue
                seen.add(product_id)
                out.append((product_id, type_code))
            return out
        return []

    @app.get("/accounts", response_model=AccountListOut)
    def list_accounts(
        q: Optional[str] = None,
        login_q: Optional[str] = None,
        product_q: Optional[str] = None,
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
            "products": "product_titles_text",
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
            filters.append(
                """
                (
                  a.login_name ILIKE %s
                  OR d.name ILIKE %s
                  OR (a.login_name || '@' || d.name) ILIKE %s
                  OR r.code ILIKE %s
                  OR apa.product_titles_text ILIKE %s
                  OR EXISTS (
                    SELECT 1
                    FROM app.deal_items di_q
                    JOIN app.deals d_q ON d_q.deal_id = di_q.deal_id
                    JOIN app.customers c_q ON c_q.customer_id = d_q.customer_id
                    WHERE di_q.account_id = a.account_id
                      AND c_q.nickname ILIKE %s
                      AND d_q.status_code <> 'cancelled'
                  )
                )
                """
            )
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"])
        if product_q:
            filters.append("apa.product_titles_text ILIKE %s")
            params.append(f"%{product_q}%")
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
            # Строим список аккаунтов в strict product-first режиме без compatibility fallback.
            # Для подписок в выдаче добавляем дату окончания в подпись товара: "Название до DD/MM/YY".
            rows = qall(
                conn,
                f"""
                WITH account_platforms AS (
                  SELECT
                    aa.account_id,
                    BOOL_OR(p.code = 'ps4') AS has_ps4,
                    COALESCE(array_agg(DISTINCT p.code ORDER BY p.code) FILTER (WHERE p.code IS NOT NULL), '{{}}'::text[]) AS platform_codes
                  FROM app.account_assets aa
                  JOIN app.products pr ON pr.product_id = aa.product_id
                  JOIN app.product_platforms pp ON pp.product_id = pr.product_id
                  JOIN app.platforms p ON p.platform_id = pp.platform_id
                  WHERE aa.asset_type_code IN ('game', 'subscription')
                  GROUP BY aa.account_id
                ),
                account_products_linked AS (
                  -- Собираем товары аккаунта из прямых привязок и из сроков подписок (fallback для старых импортов).
                  SELECT aa.account_id, aa.product_id
                  FROM app.account_assets aa
                  WHERE aa.asset_type_code IN ('game', 'subscription')
                  UNION
                  SELECT st.account_id, st.product_id
                  FROM app.subscription_terms st
                  WHERE st.is_archived IS NOT TRUE
                ),
                subscription_terms_titles AS (
                  -- Предвычисляем подписи подписок по аккаунту, чтобы не запускать одинаковые подзапросы много раз.
                  SELECT
                    st.account_id,
                    st.product_id,
                    string_agg(
                      p.title || ' до ' || to_char(st.valid_until, 'DD/MM/YY'),
                      ' · '
                      ORDER BY st.valid_until
                    ) AS title_with_terms
                  FROM app.subscription_terms st
                  JOIN app.products p ON p.product_id = st.product_id
                  WHERE st.is_archived IS NOT TRUE
                  GROUP BY st.account_id, st.product_id
                ),
                account_products_resolved AS (
                  -- Единая "витрина" названий товаров аккаунта (игра или подписка + сроки).
                  SELECT
                    apl.account_id,
                    apl.product_id,
                    CASE
                      WHEN lower(p_id.type_code) = 'subscription' THEN
                        COALESCE(NULLIF(stt.title_with_terms, ''), p_id.title)
                      ELSE p_id.title
                    END AS display_title
                  FROM account_products_linked apl
                  JOIN app.products p_id ON p_id.product_id = apl.product_id
                  LEFT JOIN subscription_terms_titles stt
                    ON stt.account_id = apl.account_id
                   AND stt.product_id = apl.product_id
                ),
                account_products_agg AS (
                  -- Агрегируем подписи товаров отдельно, чтобы не перемножать строки со слотами.
                  SELECT
                    apr.account_id,
                    COALESCE(
                      array_agg(DISTINCT apr.display_title ORDER BY apr.display_title)
                        FILTER (WHERE apr.display_title IS NOT NULL),
                      '{{}}'::text[]
                    ) AS product_titles,
                    COALESCE(
                      string_agg(DISTINCT apr.display_title, ' · ' ORDER BY apr.display_title),
                      ''
                    ) AS product_titles_text
                  FROM account_products_resolved apr
                  GROUP BY apr.account_id
                ),
                account_slots_agg AS (
                  -- Агрегируем сводку слотов отдельно, чтобы базовый SELECT был "одна строка = один аккаунт".
                  SELECT
                    s.account_id,
                    COALESCE(SUM(s.free), 0) AS free_total,
                    COALESCE(string_agg(st.code || ' ' || s.occupied || '/' || s.capacity, ' · ' ORDER BY st.code), '') AS slots_text
                  FROM app.v_account_slot_status s
                  LEFT JOIN app.slot_types st ON st.code = s.slot_type_code
                  LEFT JOIN account_platforms ap ON ap.account_id = s.account_id
                  WHERE (COALESCE(ap.has_ps4, false) OR s.platform_code = 'ps5')
                  GROUP BY s.account_id
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
                    a.is_deactivated,
                    a.deactivated_at,
                    a.next_activation_at,
                    r.code as region_code,
                    d.name as domain_name,
                    COALESCE(apa.product_titles, '{{}}'::text[]) as product_titles,
                    COALESCE(apa.product_titles_text, '') as product_titles_text,
                    ap.platform_codes,
                    COALESCE(asa.free_total, 0) as free_total,
                    COALESCE(asa.slots_text, '') as slots_text
                  FROM app.accounts a
                  LEFT JOIN app.regions r ON r.region_id = a.region_id
                  LEFT JOIN app.domains d ON d.domain_id = a.domain_id
                  LEFT JOIN account_platforms ap ON ap.account_id = a.account_id
                  LEFT JOIN account_products_agg apa ON apa.account_id = a.account_id
                  LEFT JOIN account_slots_agg asa ON asa.account_id = a.account_id
                  {where_sql}
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
                  page.product_titles,
                  page.platform_codes,
                  s.slot_type_code,
                  s.platform_code,
                  s.mode,
                  s.capacity,
                  s.occupied,
                  s.free,
                  page.total_count,
                  page.is_deactivated,
                  page.deactivated_at,
                  page.next_activation_at
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
                    product_titles=list(row[7] or []),
                    platform_codes=list(row[8] or []),
                    account_date=row[5],
                    notes=row[6],
                    is_deactivated=bool(row_value(row, 16, False)),
                    deactivated_at=row_value(row, 17),
                    next_activation_at=row_value(row, 18),
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

    @app.get("/accounts/labels", response_model=List[AccountLabelOut])
    def list_account_labels(
        account_id: List[int] = Query(default=[]),
        user=Depends(get_current_user),
    ):
        # Легкий lookup для сделок: возвращает подписи только по запрошенным account_id.
        normalized_ids = []
        seen_ids = set()
        for raw_id in account_id:
            account_id_value = int(raw_id or 0)
            if account_id_value <= 0 or account_id_value in seen_ids:
                continue
            seen_ids.add(account_id_value)
            normalized_ids.append(account_id_value)
        if not normalized_ids:
            return []
        if len(normalized_ids) > 200:
            raise HTTPException(400, "too many account_id values")
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                """
                SELECT
                  a.account_id,
                  a.login_name,
                  d.name AS domain_name
                FROM app.accounts a
                LEFT JOIN app.domains d ON d.domain_id = a.domain_id
                WHERE a.account_id = ANY(%s)
                ORDER BY a.account_id ASC
                """,
                (normalized_ids,),
            )
        labels = []
        for row in rows:
            account_id_value = int(row[0])
            login_name = str(row[1]).strip() if row[1] is not None else None
            domain_code = str(row[2]).strip() if row[2] is not None else None
            login_full = f"{login_name}@{domain_code}" if login_name and domain_code else (login_name or str(account_id_value))
            labels.append(
                AccountLabelOut(
                    account_id=account_id_value,
                    login_name=login_name,
                    domain_code=domain_code,
                    login_full=login_full,
                )
            )
        return labels
    
    @app.post("/accounts", response_model=AccountOut)
    def create_account(payload: AccountCreate, user=Depends(get_current_user)):
        # Для создания аккаунта требуем базовые поля; регион можно не указывать.
        missing_fields = []
        if not payload.login_name:
            missing_fields.append("login_name")
        if not payload.domain_code:
            missing_fields.append("domain_code")
        if payload.account_date is None:
            missing_fields.append("account_date")
        if missing_fields:
            raise HTTPException(400, f"required fields are missing: {', '.join(missing_fields)}")
        validate_date_not_future(payload.account_date, "account_date")
        with psycopg.connect(DB_DSN) as conn:
            region_id = get_region_id(conn, payload.region_code) if payload.region_code else None
            domain_id = get_domain_id(conn, payload.domain_code)

            try:
                row = q1(conn, """
                    INSERT INTO app.accounts(login_name, domain_id, region_id, notes, account_date)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING account_id
                """, (payload.login_name, domain_id, region_id, payload.notes, payload.account_date))
            except Exception as exc:
                # 23505 = unique_violation (PostgreSQL), срабатывает и при proxy-обертке psycopg.
                if getattr(exc, "sqlstate", None) == "23505":
                    raise HTTPException(409, "Account already exists")
                raise
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
                product_titles=None,
                account_date=payload.account_date,
                notes=payload.notes,
                is_deactivated=False,
                deactivated_at=None,
                next_activation_at=None,
            )
    
    @app.put("/accounts/{account_id}", response_model=AccountOut)
    def update_account(
        account_id: int,
        payload: AccountUpdate,
        user=Depends(require_role("admin", "owner", "manager", "operator")),
    ):
        validate_date_not_future(payload.account_date, "account_date")
        with psycopg.connect(DB_DSN) as conn:
            current = q1(
                conn,
                """
                SELECT login_name, domain_id, region_id, status_code, account_date, notes, is_deactivated, deactivated_at, next_activation_at
                FROM app.accounts
                WHERE account_id=%s
                """,
                (account_id,),
            )
            if not current:
                raise HTTPException(404, "Account not found")

            current_login = row_value(current, 0, "")
            current_domain_id = row_value(current, 1)
            current_region_id = row_value(current, 2)
            current_status = row_value(current, 3, "active")
            current_account_date = row_value(current, 4)
            current_notes = row_value(current, 5)
            current_is_deactivated = bool(row_value(current, 6, False))
            current_deactivated_at = row_value(current, 7)
            current_next_activation_at = row_value(current, 8)
            user_role = str(getattr(user, "role", "") or "").strip().lower()

            region_id = get_region_id(conn, payload.region_code) if payload.region_code else current_region_id
            domain_id = get_domain_id(conn, payload.domain_code) if payload.domain_code else current_domain_id

            new_login = payload.login_name if payload.login_name is not None else current_login
            # Менеджер/оператор могут редактировать карточку, но не менять статус аккаунта.
            if user_role not in {"admin", "owner"} and payload.status_code is not None and payload.status_code != current_status:
                raise HTTPException(403, "Only admin can change account status")
            new_status = payload.status_code if payload.status_code is not None else current_status
            new_date = payload.account_date if payload.account_date is not None else current_account_date
            new_notes = payload.notes if payload.notes is not None else current_notes

            # Оператору запрещаем менять флаг деактивации, но статус он видит как обычно.
            if payload.is_deactivated is not None and user_role == "operator":
                requested_is_deactivated = bool(payload.is_deactivated)
                if requested_is_deactivated != current_is_deactivated:
                    raise HTTPException(403, "Operator cannot change account deactivation flag")

            # Обновляем деактивацию с правилом повторной активации не раньше чем через 183 дня.
            requested_is_deactivated = current_is_deactivated if payload.is_deactivated is None else bool(payload.is_deactivated)
            next_is_deactivated = requested_is_deactivated
            next_deactivated_at = current_deactivated_at
            next_activation_at = current_next_activation_at
            now_utc = datetime.now(timezone.utc)
            if requested_is_deactivated:
                if not current_is_deactivated:
                    next_deactivated_at = now_utc
                    next_activation_at = now_utc + timedelta(days=183)
                else:
                    if next_deactivated_at is None:
                        next_deactivated_at = now_utc
                    if next_activation_at is None:
                        next_activation_at = to_utc_aware(next_deactivated_at) + timedelta(days=183)
            else:
                # Флаг деактивации используется как визуальная пометка, без блокировок по сроку.
                next_deactivated_at = None
                next_activation_at = None
    
            exec1(
                conn,
                """
                UPDATE app.accounts
                SET login_name=%s,
                    domain_id=%s,
                    region_id=%s,
                    status_code=%s,
                    notes=%s,
                    account_date=%s,
                    is_deactivated=%s,
                    deactivated_at=%s,
                    next_activation_at=%s
                WHERE account_id=%s
                """,
                (
                    new_login,
                    domain_id,
                    region_id,
                    new_status,
                    new_notes,
                    new_date,
                    next_is_deactivated,
                    next_deactivated_at,
                    next_activation_at,
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
                  a.notes,
                  a.is_deactivated,
                  a.deactivated_at,
                  a.next_activation_at
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
                product_titles=None,
                account_date=row[5],
                notes=row[6],
                is_deactivated=bool(row_value(row, 7, False)),
                deactivated_at=row_value(row, 8),
                next_activation_at=row_value(row, 9),
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
    def list_account_secrets(account_id: int, user=Depends(require_role("admin", "owner", "manager", "operator"))):
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
    def list_account_secrets_batch(payload: AccountSecretsBatchIn, user=Depends(require_role("admin", "owner", "manager", "operator"))):
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
        user=Depends(require_role("admin", "owner", "manager", "operator")),
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

    @app.put("/accounts/{account_id}/secrets")
    def patch_account_secrets(
        account_id: int,
        payload: AccountSecretsPatchIn,
        user=Depends(require_role("admin", "owner", "manager", "operator")),
    ):
        # Обновляем и удаляем секреты в одной транзакции, чтобы не оставлять частично сохраненное состояние.
        with psycopg.connect(DB_DSN) as conn:
            ensure_account_exists(conn, account_id)
            upserts = payload.upserts or []
            delete_keys = [str(k or "").strip() for k in (payload.delete_keys or []) if str(k or "").strip()]

            # Если один и тот же ключ пришел несколько раз, оставляем последнее значение.
            upserts_map: dict[str, str] = {}
            for item in upserts:
                key = str(item.secret_key or "").strip()
                if not key:
                    raise HTTPException(400, "secret_key is required")
                upserts_map[key] = b64_encode(item.secret_value)

            if upserts_map:
                rows = [(account_id, key, value_b64) for key, value_b64 in upserts_map.items()]
                with conn.cursor() as cur:
                    cur.executemany(
                        """
                        INSERT INTO app.account_secrets(account_id, secret_key, secret_value)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (account_id, secret_key)
                        DO UPDATE SET secret_value=excluded.secret_value
                        """,
                        rows,
                    )

            if delete_keys:
                exec1(
                    conn,
                    """
                    DELETE FROM app.account_secrets
                    WHERE account_id=%s
                      AND secret_key = ANY(%s)
                    """,
                    (account_id, delete_keys),
                )

            conn.commit()
        return {"ok": True}
    
    @app.delete("/accounts/{account_id}/secrets/{secret_key}")
    def delete_account_secret(
        account_id: int,
        secret_key: str,
        user=Depends(require_role("admin", "owner", "manager", "operator")),
    ):
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                "DELETE FROM app.account_secrets WHERE account_id=%s AND secret_key=%s",
                (account_id, secret_key),
            )
            conn.commit()
        return {"ok": True}
    
    @app.get("/accounts/{account_id}/products", response_model=List[AccountProductOut])
    def list_account_products(account_id: int, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            ensure_account_exists(conn, account_id)
            # Отдаем товары аккаунта только по product_id без legacy fallback.
            # Для подписки возвращаем подпись со сроком, чтобы UI показывал "Название до DD/MM/YY".
            rows = qall(
                conn,
                """
                SELECT
                  p_id.product_id AS product_id,
                  p_id.type_code AS type_code,
                  CASE
                    WHEN lower(p_id.type_code) = 'subscription' THEN
                      COALESCE(
                        NULLIF(
                          (
                            SELECT string_agg(
                              p_id.title || ' до ' || to_char(st.valid_until, 'DD/MM/YY'),
                              ' · '
                              ORDER BY st.valid_until
                            )
                            FROM app.subscription_terms st
                            WHERE st.account_id = %s
                              AND st.product_id = p_id.product_id
                              AND st.is_archived IS NOT TRUE
                          ),
                          ''
                        ),
                        p_id.title
                      )
                    ELSE p_id.title
                  END AS title,
                  p_id.short_title AS short_title,
                  r.code AS region_code,
                  COALESCE(array_agg(pl.code ORDER BY pl.code) FILTER (WHERE pl.code IS NOT NULL), '{}'::text[]) AS platform_codes
                FROM (
                  -- Для карточки аккаунта учитываем и прямые привязки, и сроки подписок без прямой связи.
                  SELECT aa.product_id
                  FROM app.account_assets aa
                  WHERE aa.account_id=%s
                    AND aa.asset_type_code IN ('game', 'subscription')
                  UNION
                  SELECT st.product_id
                  FROM app.subscription_terms st
                  WHERE st.account_id=%s
                    AND st.is_archived IS NOT TRUE
                ) linked
                JOIN app.products p_id ON p_id.product_id = linked.product_id
                LEFT JOIN app.regions r ON r.region_id = p_id.region_id
                LEFT JOIN app.product_platforms pp ON pp.product_id = p_id.product_id
                LEFT JOIN app.platforms pl ON pl.platform_id = pp.platform_id
                WHERE p_id.is_archived IS NOT TRUE
                GROUP BY
                  p_id.product_id,
                  p_id.type_code,
                  p_id.title,
                  p_id.short_title,
                  r.code
                ORDER BY p_id.title
                """,
                (account_id, account_id, account_id),
            )
        return [
            AccountProductOut(
                product_id=int(r[0]),
                type_code=r[1],
                title=r[2],
                short_title=r[3],
                region_code=r[4],
                platform_codes=list(r[5] or []),
            )
            for r in rows
        ]
    
    @app.get("/accounts/{account_id}/slot-status", response_model=List[AccountSlotStatusOut])
    def list_account_slot_status(account_id: int, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            ensure_account_exists(conn, account_id)
            # Для статуса слотов используем только product-first связи аккаунта.
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
                  JOIN app.products pr ON pr.product_id = aa.product_id
                  JOIN app.product_platforms pp ON pp.product_id = pr.product_id
                  JOIN app.platforms p ON p.platform_id = pp.platform_id
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
            # Для slot-назначений отдаем только product-first записи.
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
                  asa.product_id AS product_id,
                  p_id.title AS product_title,
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
                LEFT JOIN app.products p_id ON p_id.product_id = asa.product_id
                WHERE asa.account_id=%s
                  AND asa.product_id IS NOT NULL
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
                product_id=r[7],
                product_title=r[8],
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
        product_id: int,
        slot_type_code: Optional[str] = None,
        user=Depends(get_current_user),
    ):
        slot_type_code = (slot_type_code or "").strip() or None
        with psycopg.connect(DB_DSN) as conn:
            # Эндпоинт strict product-first: работаем только по product_id.
            selected_product_id = int(product_id)
            ensure_slot_product_supported(conn, selected_product_id)

            rows = qall(
                conn,
                """
                WITH account_platforms AS (
                  SELECT
                    aa.account_id,
                    BOOL_OR(p.code = 'ps4') AS has_ps4,
                    COALESCE(array_agg(DISTINCT p.code ORDER BY p.code) FILTER (WHERE p.code IS NOT NULL), '{}'::text[]) AS platform_codes
                  FROM app.account_assets aa
                  JOIN app.products pr ON pr.product_id = aa.product_id
                  JOIN app.product_platforms pp ON pp.product_id = pr.product_id
                  JOIN app.platforms p ON p.platform_id = pp.platform_id
                  WHERE aa.asset_type_code IN ('game', 'subscription')
                  GROUP BY aa.account_id
                ),
                active_play_assignments AS (
                  SELECT
                    asa.account_id,
                    asa.slot_type_code,
                    COUNT(*) AS active_count,
                    MIN(COALESCE(asa.assigned_at, now())) AS first_assigned_at
                  FROM app.account_slot_assignments asa
                  JOIN app.slot_types st ON st.code = asa.slot_type_code
                  WHERE asa.released_at IS NULL
                    AND st.mode = 'play'
                  GROUP BY asa.account_id, asa.slot_type_code
                ),
                recent_duplicate_locks AS (
                  SELECT
                    asa.account_id,
                    asa.slot_type_code,
                    MAX(COALESCE(asa.assigned_at, now())) AS last_duplicate_assigned_at
                  FROM app.account_slot_assignments asa
                  JOIN app.slot_types st_dup ON st_dup.code = asa.slot_type_code
                  WHERE st_dup.mode = 'play'
                    AND COALESCE(asa.assigned_at, now()) > (now() - INTERVAL '2 months')
                    AND EXISTS (
                      SELECT 1
                      FROM app.account_slot_assignments prev
                      WHERE prev.account_id = asa.account_id
                        AND prev.slot_type_code = asa.slot_type_code
                        AND COALESCE(prev.assigned_at, now()) < COALESCE(asa.assigned_at, now())
                        AND COALESCE(prev.released_at, 'infinity'::timestamptz) > COALESCE(asa.assigned_at, now())
                    )
                  GROUP BY asa.account_id, asa.slot_type_code
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
                   AND aa.asset_type_code IN ('game', 'subscription')
                   AND aa.product_id = %s
                  WHERE a.status_code <> 'archived'
                    AND EXISTS (
                    SELECT 1
                    FROM app.v_account_slot_status ss
                    JOIN app.slot_types st_gate ON st_gate.code = ss.slot_type_code
                    LEFT JOIN active_play_assignments apa
                      ON apa.account_id = ss.account_id
                     AND apa.slot_type_code = ss.slot_type_code
                    LEFT JOIN recent_duplicate_locks rdl
                      ON rdl.account_id = ss.account_id
                     AND rdl.slot_type_code = ss.slot_type_code
                    WHERE ss.account_id = a.account_id
                      AND (
                        CASE
                          -- Если дубль по этому методу был менее 2 месяцев назад, новый дубль временно блокируем.
                          WHEN COALESCE(ss.capacity, 0) >= 2
                            AND rdl.last_duplicate_assigned_at IS NOT NULL
                          THEN 0
                          -- Для П2 не открываем второй слот сразу: ждем 2 месяца с первого активного занятия.
                          WHEN st_gate.name ILIKE 'П2%%'
                            AND COALESCE(ss.capacity, 0) >= 2
                            AND COALESCE(apa.active_count, 0) = 1
                            AND COALESCE(apa.first_assigned_at, now()) > (now() - INTERVAL '2 months')
                          THEN 0
                          ELSE COALESCE(ss.free, 0)
                        END
                      ) > 0
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
                (selected_product_id, slot_type_code, slot_type_code),
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
                    is_deactivated=False,
                    deactivated_at=None,
                    next_activation_at=None,
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
        product_id: int,
        user=Depends(get_current_user),
    ):
        with psycopg.connect(DB_DSN) as conn:
            # Эндпоинт strict product-first: работаем только по product_id.
            selected_product_id = int(product_id)
            ensure_slot_product_supported(conn, selected_product_id)

            rows = qall(
                conn,
                """
                WITH account_platforms AS (
                  SELECT
                    aa.account_id,
                    BOOL_OR(p.code = 'ps4') AS has_ps4
                  FROM app.account_assets aa
                  JOIN app.products pr ON pr.product_id = aa.product_id
                  JOIN app.product_platforms pp ON pp.product_id = pr.product_id
                  JOIN app.platforms p ON p.platform_id = pp.platform_id
                  WHERE aa.asset_type_code IN ('game', 'subscription')
                  GROUP BY aa.account_id
                ),
                active_play_assignments AS (
                  SELECT
                    asa.account_id,
                    asa.slot_type_code,
                    COUNT(*) AS active_count,
                    MIN(COALESCE(asa.assigned_at, now())) AS first_assigned_at
                  FROM app.account_slot_assignments asa
                  JOIN app.slot_types stp ON stp.code = asa.slot_type_code
                  WHERE asa.released_at IS NULL
                    AND stp.mode = 'play'
                  GROUP BY asa.account_id, asa.slot_type_code
                ),
                recent_duplicate_locks AS (
                  SELECT
                    asa.account_id,
                    asa.slot_type_code,
                    MAX(COALESCE(asa.assigned_at, now())) AS last_duplicate_assigned_at
                  FROM app.account_slot_assignments asa
                  JOIN app.slot_types st_dup ON st_dup.code = asa.slot_type_code
                  WHERE st_dup.mode = 'play'
                    AND COALESCE(asa.assigned_at, now()) > (now() - INTERVAL '2 months')
                    AND EXISTS (
                      SELECT 1
                      FROM app.account_slot_assignments prev
                      WHERE prev.account_id = asa.account_id
                        AND prev.slot_type_code = asa.slot_type_code
                        AND COALESCE(prev.assigned_at, now()) < COALESCE(asa.assigned_at, now())
                        AND COALESCE(prev.released_at, 'infinity'::timestamptz) > COALESCE(asa.assigned_at, now())
                    )
                  GROUP BY asa.account_id, asa.slot_type_code
                ),
                base_accounts AS (
                  SELECT a.account_id
                  FROM app.accounts a
                  JOIN app.account_assets aa
                    ON aa.account_id = a.account_id
                   AND aa.asset_type_code IN ('game', 'subscription')
                   AND aa.product_id = %s
                  WHERE a.status_code <> 'archived'
                )
                SELECT
                  st.code AS slot_type_code,
                  BOOL_OR(
                    (
                      CASE
                        -- Если дубль по этому методу был менее 2 месяцев назад, новый дубль временно блокируем.
                        WHEN COALESCE(ss.capacity, 0) >= 2
                          AND rdl.last_duplicate_assigned_at IS NOT NULL
                        THEN 0
                        -- Для П2 не открываем второй слот сразу: ждем 2 месяца с первого активного занятия.
                        WHEN st.name ILIKE 'П2%%'
                          AND COALESCE(ss.capacity, 0) >= 2
                          AND COALESCE(apa.active_count, 0) = 1
                          AND COALESCE(apa.first_assigned_at, now()) > (now() - INTERVAL '2 months')
                        THEN 0
                        ELSE COALESCE(ss.free, 0)
                      END
                    ) > 0
                  ) AS has_free
                FROM base_accounts ba
                LEFT JOIN account_platforms ap ON ap.account_id = ba.account_id
                JOIN app.slot_types st
                  ON (COALESCE(ap.has_ps4, false) OR st.platform_code = 'ps5')
                LEFT JOIN app.v_account_slot_status ss
                  ON ss.account_id = ba.account_id AND ss.slot_type_code = st.code
                LEFT JOIN active_play_assignments apa
                  ON apa.account_id = ba.account_id AND apa.slot_type_code = st.code
                LEFT JOIN recent_duplicate_locks rdl
                  ON rdl.account_id = ba.account_id AND rdl.slot_type_code = st.code
                GROUP BY st.code
                ORDER BY st.code
                """,
                (selected_product_id,),
            )
        return [SlotAvailabilityOut(slot_type_code=r0, has_free=bool(r1)) for (r0, r1) in rows]
    
    @app.put("/accounts/{account_id}/products")
    def set_account_products(
        account_id: int,
        payload: AccountProductsIn,
        user=Depends(require_role("admin", "owner", "manager", "operator")),
    ):
        with psycopg.connect(DB_DSN) as conn:
            ensure_account_exists(conn, account_id)
            # Обновляем привязки товаров аккаунта в product-first формате.
            valid_links = resolve_asset_links(conn, payload)
            exec1(
                conn,
                "DELETE FROM app.account_assets WHERE account_id=%s AND asset_type_code IN ('game', 'subscription')",
                (account_id,),
            )
            if valid_links:
                with conn.cursor() as cur:
                    cur.executemany(
                        """
                        INSERT INTO app.account_assets(account_id, product_id, asset_type_code)
                        VALUES (%s, %s, %s)
                        """,
                        [(account_id, product_id, type_code) for (product_id, type_code) in valid_links],
                    )
            conn.commit()
        return {"ok": True}

    @app.get("/products/{product_id}/accounts", response_model=List[ProductAccountOut])
    def list_product_accounts(product_id: int, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                "SELECT 1 FROM app.products WHERE product_id=%s AND is_archived IS NOT TRUE",
                (product_id,),
            )
            if not row:
                raise HTTPException(400, f"Unknown product_id: {product_id}")
            # Эндпоинт product-first: учитываем только сделки, где уже заполнен product_id.
            rows = qall(
                conn,
                """
                SELECT
                  di.deal_item_id,
                  a.account_id,
                  a.login_name,
                  d.name as domain_name,
                  c.nickname as customer_nickname,
                  COALESCE(di.purchase_at, dl.created_at) as deal_date
                FROM app.deal_items di
                JOIN app.deals dl ON dl.deal_id = di.deal_id
                JOIN app.accounts a ON a.account_id = di.account_id
                LEFT JOIN app.domains d ON d.domain_id = a.domain_id
                LEFT JOIN app.customers c ON c.customer_id = dl.customer_id
                WHERE di.product_id=%s
                  AND di.account_id IS NOT NULL
                ORDER BY COALESCE(di.purchase_at, dl.created_at) DESC, di.deal_item_id DESC
                """,
                (product_id,),
            )
        return [
            ProductAccountOut(
                deal_item_id=int(r0),
                account_id=int(r1),
                login_full=f"{r2}@{r3}" if r2 and r3 else (str(r2 or "") or None),
                customer_nickname=r4,
                deal_date=r5,
            )
            for (r0, r1, r2, r3, r4, r5) in rows
        ]

    @app.get("/products/{product_id}/linked-accounts", response_model=List[ProductLinkedAccountOut])
    def list_product_linked_accounts(product_id: int, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                "SELECT 1 FROM app.products WHERE product_id=%s AND is_archived IS NOT TRUE",
                (product_id,),
            )
            if not row:
                raise HTTPException(400, f"Unknown product_id: {product_id}")
            # Возвращаем прямые привязки товара к аккаунтам из account_assets.
            rows = qall(
                conn,
                """
                SELECT
                  a.account_id,
                  a.login_name,
                  COALESCE(d.name, '') AS domain_code
                FROM app.account_assets aa
                JOIN app.accounts a ON a.account_id = aa.account_id
                LEFT JOIN app.domains d ON d.domain_id = a.domain_id
                WHERE aa.product_id=%s
                ORDER BY a.login_name ASC, a.account_id ASC
                """,
                (product_id,),
            )
        return [
            ProductLinkedAccountOut(
                account_id=int(r0),
                login_name=str(r1 or ""),
                domain_code=str(r2 or ""),
                login_full=(f"{r1}@{r2}" if r1 and r2 else str(r1 or "")),
            )
            for (r0, r1, r2) in rows
        ]

    @app.get("/accounts/available-for-product", response_model=List[ProductSelectableAccountOut])
    def list_accounts_available_for_product(
        type_code: str,
        product_id: Optional[int] = None,
        user=Depends(get_current_user),
    ):
        normalized_type = str(type_code or "").strip().lower()
        if normalized_type not in ("game", "subscription"):
            raise HTTPException(400, "type_code must be game or subscription")
        with psycopg.connect(DB_DSN) as conn:
            if normalized_type == "subscription":
                # Для подписок показываем только полностью "пустые" аккаунты
                # (без привязок game/subscription) + текущие привязки этого товара.
                # Если редактируем конкретную подписку, сохраняем ее текущие привязки в списке.
                rows = qall(
                    conn,
                    """
                    WITH occupied_accounts AS (
                      SELECT DISTINCT aa.account_id
                      FROM app.account_assets aa
                      JOIN app.products p ON p.product_id = aa.product_id
                      WHERE p.type_code IN ('game', 'subscription')
                        AND p.is_archived IS NOT TRUE
                    )
                    SELECT
                      a.account_id,
                      a.login_name,
                      COALESCE(d.name, '') AS domain_code
                    FROM app.accounts a
                    LEFT JOIN app.domains d ON d.domain_id = a.domain_id
                    WHERE (
                        a.account_id NOT IN (SELECT oa.account_id FROM occupied_accounts oa)
                        OR (
                          %s::bigint IS NOT NULL
                          AND EXISTS (
                            SELECT 1
                            FROM app.account_assets aa_cur
                            WHERE aa_cur.account_id = a.account_id
                              AND aa_cur.product_id = %s::bigint
                          )
                        )
                      )
                    ORDER BY a.login_name ASC, a.account_id ASC
                    """,
                    (product_id, product_id),
                )
            else:
                # Для игр оставляем полный список аккаунтов.
                rows = qall(
                    conn,
                    """
                    SELECT
                      a.account_id,
                      a.login_name,
                      COALESCE(d.name, '') AS domain_code
                    FROM app.accounts a
                    LEFT JOIN app.domains d ON d.domain_id = a.domain_id
                    ORDER BY a.login_name ASC, a.account_id ASC
                    """,
                    (),
                )
        return [
            ProductSelectableAccountOut(
                account_id=int(r0),
                login_name=str(r1 or ""),
                domain_code=str(r2 or ""),
                login_full=(f"{r1}@{r2}" if r1 and r2 else str(r1 or "")),
            )
            for (r0, r1, r2) in rows
        ]

    @app.get("/products/{product_id}/slot-assignments", response_model=List[AccountSlotAssignmentOut])
    def list_product_slot_assignments(product_id: int, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                "SELECT 1 FROM app.products WHERE product_id=%s AND is_archived IS NOT TRUE",
                (product_id,),
            )
            if not row:
                raise HTTPException(400, f"Unknown product_id: {product_id}")
            # Отдаем только product-first назначения без compatibility fallback.
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
                  asa.product_id,
                  p_id.title AS product_title,
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
                LEFT JOIN app.products p_id ON p_id.product_id = asa.product_id
                WHERE asa.product_id=%s
                ORDER BY asa.released_at IS NULL DESC, asa.assigned_at DESC
                """,
                (product_id,),
            )
        return [
            AccountSlotAssignmentOut(
                assignment_id=r[0],
                account_id=r[1],
                account_login=f"{r[2]}@{r[3]}" if r[2] and r[3] else None,
                slot_type_code=r[4],
                customer_id=r[5],
                customer_nickname=r[6],
                product_id=r[7],
                product_title=r[8],
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
                """
                SELECT
                  asa.assignment_id,
                  asa.subscription_term_id,
                  p.type_code
                FROM app.account_slot_assignments asa
                LEFT JOIN app.products p ON p.product_id = asa.product_id
                WHERE asa.assignment_id=%s
                  AND asa.released_at IS NULL
                """,
                (assignment_id,),
            )
            if not row:
                return {"ok": True}
            # Подписочные назначения не снимаем вручную: это ломает логику сроков подписки.
            subscription_term_id = row[1]
            product_type_code = str(row[2] or "").strip().lower()
            if subscription_term_id is not None or product_type_code == "subscription":
                raise HTTPException(409, "subscription slot release is not allowed")
            exec1(
                conn,
                "UPDATE app.account_slot_assignments SET released_at=now(), released_by=%s WHERE assignment_id=%s",
                (user.username, assignment_id),
            )
            conn.commit()
        return {"ok": True}

    @app.post("/slot-assignments/{assignment_id}/restore")
    def restore_slot_assignment_api(assignment_id: int, user=Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                """
                SELECT
                  asa.assignment_id,
                  asa.account_id,
                  asa.slot_type_code,
                  asa.released_at,
                  asa.subscription_term_id,
                  p.type_code
                FROM app.account_slot_assignments asa
                LEFT JOIN app.products p ON p.product_id = asa.product_id
                WHERE asa.assignment_id=%s
                """,
                (assignment_id,),
            )
            if not row:
                return {"ok": True}
            # Для подписочных слотов восстановление вручную запрещаем: оно ломает сроковую модель.
            subscription_term_id = row[4]
            product_type_code = str(row[5] or "").strip().lower()
            if subscription_term_id is not None or product_type_code == "subscription":
                raise HTTPException(409, "subscription slot restore is not allowed")
            # Если слот уже активен, операция идемпотентна.
            if row[3] is None:
                return {"ok": True}

            account_id = int(row[1] or 0)
            slot_type_code = str(row[2] or "").strip()
            slot_row = q1(
                conn,
                """
                SELECT free
                FROM app.v_account_slot_status
                WHERE account_id=%s AND slot_type_code=%s
                """,
                (account_id, slot_type_code),
            )
            free_slots = int((slot_row[0] if slot_row else 0) or 0)
            if free_slots <= 0:
                raise HTTPException(409, "Not enough free slots for selected slot type")

            exec1(
                conn,
                """
                UPDATE app.account_slot_assignments
                SET released_at=NULL, released_by=NULL
                WHERE assignment_id=%s
                """,
                (assignment_id,),
            )
            conn.commit()
        return {"ok": True}
    
