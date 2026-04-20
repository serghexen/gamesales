from datetime import datetime, timezone
from typing import List, Optional

from fastapi import Body, Depends, HTTPException


def mount_products_routes(
    app,
    *,
    DB_DSN,
    psycopg,
    q1,
    qall,
    exec1,
    normalize_platform_codes,
    find_game_title_platform_conflicts,
    get_platform_id,
    get_region_id,
    get_game_platform_codes,
    get_current_user,
    ProductCreate,
    ProductUpdate,
    ProductOut,
    ProductListOut,
    SubscriptionTermCreate,
    SubscriptionTermUpdate,
    SubscriptionTermOut,
    SlotTypeOut,
    UserOut,
):
    # Проверяет, что товар существует и относится к подпискам.
    def ensure_subscription_product(conn, product_id: int):
        row = q1(
            conn,
            """
            SELECT 1
            FROM app.products
            WHERE product_id=%s
              AND is_archived IS NOT TRUE
              AND lower(type_code)='subscription'
            """,
            (product_id,),
        )
        if not row:
            raise HTTPException(400, f"Unknown subscription product_id: {product_id}")

    @app.get("/products/subscriptions/free-by-slot", response_model=List[int])
    def list_subscription_products_with_free_slot(
        slot_type_code: str,
        user: UserOut = Depends(get_current_user),
    ):
        # Возвращает id подписок, где есть хотя бы один срок с доступным выбранным слотом.
        normalized_slot_type_code = str(slot_type_code or "").strip()
        if not normalized_slot_type_code:
            raise HTTPException(400, "slot_type_code is required")

        with psycopg.connect(DB_DSN) as conn:
            slot_row = q1(
                conn,
                "SELECT code FROM app.slot_types WHERE code=%s",
                (normalized_slot_type_code,),
            )
            if not slot_row:
                raise HTTPException(400, f"Unknown slot_type_code: {normalized_slot_type_code}")

            rows = qall(
                conn,
                """
                WITH target_slot AS (
                  SELECT st.code, st.mode, st.capacity
                  FROM app.slot_types st
                  WHERE st.code = %s
                ),
                term_usage AS (
                  SELECT
                    asa.subscription_term_id,
                    COUNT(*) FILTER (
                      WHERE asa.released_at IS NULL
                        AND asa.slot_type_code = %s
                    ) AS used_exact_slot,
                    COUNT(*) FILTER (
                      WHERE asa.released_at IS NULL
                        AND st2.mode = 'activate'
                    ) AS used_activate_any
                  FROM app.account_slot_assignments asa
                  JOIN app.slot_types st2 ON st2.code = asa.slot_type_code
                  WHERE asa.subscription_term_id IS NOT NULL
                  GROUP BY asa.subscription_term_id
                )
                SELECT DISTINCT p.product_id
                FROM app.products p
                WHERE p.is_archived IS NOT TRUE
                  AND lower(p.type_code) = 'subscription'
                  AND EXISTS (
                    SELECT 1
                    FROM app.subscription_terms st
                    JOIN app.accounts a ON a.account_id = st.account_id
                    CROSS JOIN target_slot ts
                    LEFT JOIN term_usage tu ON tu.subscription_term_id = st.term_id
                    WHERE st.product_id = p.product_id
                      AND st.is_archived IS NOT TRUE
                      AND a.status_code <> 'archived'
                      AND (
                        (ts.mode = 'activate' AND COALESCE(tu.used_activate_any, 0) < 1)
                        OR
                        (ts.mode <> 'activate' AND COALESCE(tu.used_exact_slot, 0) < ts.capacity)
                      )
                  )
                ORDER BY p.product_id
                """,
                (normalized_slot_type_code, normalized_slot_type_code),
            )
        return [int(row[0]) for row in rows]

    @app.get("/products/subscriptions/{product_id}/terms", response_model=List[SubscriptionTermOut])
    def list_subscription_terms(product_id: int, user: UserOut = Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            ensure_subscription_product(conn, product_id)
            try:
                rows = qall(
                    conn,
                    """
                    SELECT
                      st.term_id,
                      st.product_id,
                      st.account_id,
                      a.login_name,
                      d.name AS domain_code,
                      st.valid_until,
                      st.notes,
                      st.is_archived,
                      st.created_at,
                      EXISTS (
                        SELECT 1
                        FROM app.account_slot_assignments asa
                        WHERE asa.subscription_term_id = st.term_id
                          AND asa.released_at IS NULL
                      ) AS occupied
                    FROM app.subscription_terms st
                    JOIN app.accounts a ON a.account_id = st.account_id
                    LEFT JOIN app.domains d ON d.domain_id = a.domain_id
                    WHERE st.product_id=%s
                    ORDER BY st.is_archived ASC, st.valid_until ASC, st.term_id ASC
                    """,
                    (product_id,),
                )
            except Exception as exc:
                # Для старой схемы БД без created_at не падаем, а возвращаем корректный список сроков.
                if "created_at" not in str(exc).lower():
                    raise
                rows = qall(
                    conn,
                    """
                    SELECT
                      st.term_id,
                      st.product_id,
                      st.account_id,
                      a.login_name,
                      d.name AS domain_code,
                      st.valid_until,
                      st.notes,
                      st.is_archived,
                      timezone('utc', now()) AS created_at,
                      EXISTS (
                        SELECT 1
                        FROM app.account_slot_assignments asa
                        WHERE asa.subscription_term_id = st.term_id
                          AND asa.released_at IS NULL
                      ) AS occupied
                    FROM app.subscription_terms st
                    JOIN app.accounts a ON a.account_id = st.account_id
                    LEFT JOIN app.domains d ON d.domain_id = a.domain_id
                    WHERE st.product_id=%s
                    ORDER BY st.is_archived ASC, st.valid_until ASC, st.term_id ASC
                    """,
                    (product_id,),
                )
        items: List[SubscriptionTermOut] = []
        for (r0, r1, r2, r3, r4, r5, r6, r7, r8, r9) in rows:
            # Старые/грязные строки не должны ломать весь эндпоинт 500-ошибкой.
            if not r5:
                continue
            created_at = r8 or datetime.now(timezone.utc)
            items.append(
                SubscriptionTermOut(
                    term_id=int(r0),
                    product_id=int(r1),
                    account_id=int(r2),
                    account_login=str(r3 or ""),
                    domain_code=str(r4 or ""),
                    login_full=(f"{r3}@{r4}" if r3 and r4 else str(r3 or "")),
                    valid_until=r5,
                    notes=r6,
                    is_archived=bool(r7) if r7 is not None else False,
                    created_at=created_at,
                    occupied=bool(r9),
                )
            )
        return items

    @app.post("/products/subscriptions/{product_id}/terms", response_model=SubscriptionTermOut)
    def create_subscription_term(
        product_id: int,
        payload: SubscriptionTermCreate = Body(...),
        user: UserOut = Depends(get_current_user),
    ):
        with psycopg.connect(DB_DSN) as conn:
            ensure_subscription_product(conn, product_id)
            account_row = q1(conn, "SELECT login_name, domain_id FROM app.accounts WHERE account_id=%s", (payload.account_id,))
            if not account_row:
                raise HTTPException(400, f"Unknown account_id: {payload.account_id}")
            row = q1(
                conn,
                """
                INSERT INTO app.subscription_terms(product_id, account_id, valid_until, notes)
                VALUES (%s, %s, %s, %s)
                RETURNING term_id, product_id, account_id, valid_until, notes, is_archived, created_at
                """,
                (product_id, payload.account_id, payload.valid_until, payload.notes),
            )
            # Синхронизируем прямую привязку подписки к аккаунту, чтобы карточки аккаунтов показывали товар.
            exec1(
                conn,
                """
                INSERT INTO app.account_assets(account_id, product_id, asset_type_code)
                VALUES (%s, %s, 'subscription')
                ON CONFLICT (account_id, product_id, asset_type_code) DO NOTHING
                """,
                (payload.account_id, product_id),
            )
            conn.commit()
            domain_row = q1(conn, "SELECT name FROM app.domains WHERE domain_id=%s", (account_row[1],))
        login_name = str(account_row[0] or "")
        domain_code = str(domain_row[0] or "") if domain_row else ""
        return SubscriptionTermOut(
            term_id=int(row[0]),
            product_id=int(row[1]),
            account_id=int(row[2]),
            account_login=login_name,
            domain_code=domain_code,
            login_full=(f"{login_name}@{domain_code}" if login_name and domain_code else login_name),
            valid_until=row[3],
            notes=row[4],
            is_archived=bool(row[5]),
            created_at=row[6],
            occupied=False,
        )

    @app.put("/products/subscription-terms/{term_id}", response_model=SubscriptionTermOut)
    def update_subscription_term(
        term_id: int,
        payload: SubscriptionTermUpdate = Body(...),
        user: UserOut = Depends(get_current_user),
    ):
        with psycopg.connect(DB_DSN) as conn:
            current = q1(
                conn,
                """
                SELECT term_id, product_id, account_id, valid_until, notes, is_archived, created_at
                FROM app.subscription_terms
                WHERE term_id=%s
                """,
                (term_id,),
            )
            if not current:
                raise HTTPException(404, "Subscription term not found")
            account_id = int(payload.account_id) if payload.account_id is not None else int(current[2])
            valid_until = payload.valid_until if payload.valid_until is not None else current[3]
            notes = payload.notes if payload.notes is not None else current[4]
            is_archived = bool(payload.is_archived) if payload.is_archived is not None else bool(current[5])
            account_row = q1(conn, "SELECT login_name, domain_id FROM app.accounts WHERE account_id=%s", (account_id,))
            if not account_row:
                raise HTTPException(400, f"Unknown account_id: {account_id}")
            exec1(
                conn,
                """
                UPDATE app.subscription_terms
                SET account_id=%s,
                    valid_until=%s,
                    notes=%s,
                    is_archived=%s
                WHERE term_id=%s
                """,
                (account_id, valid_until, notes, is_archived, term_id),
            )
            occupied = q1(
                conn,
                """
                SELECT 1
                FROM app.account_slot_assignments
                WHERE subscription_term_id=%s AND released_at IS NULL
                LIMIT 1
                """,
                (term_id,),
            )
            conn.commit()
            domain_row = q1(conn, "SELECT name FROM app.domains WHERE domain_id=%s", (account_row[1],))
        login_name = str(account_row[0] or "")
        domain_code = str(domain_row[0] or "") if domain_row else ""
        return SubscriptionTermOut(
            term_id=int(current[0]),
            product_id=int(current[1]),
            account_id=account_id,
            account_login=login_name,
            domain_code=domain_code,
            login_full=(f"{login_name}@{domain_code}" if login_name and domain_code else login_name),
            valid_until=valid_until,
            notes=notes,
            is_archived=is_archived,
            created_at=current[6],
            occupied=bool(occupied),
        )

    @app.get("/products/subscriptions/{product_id}/terms/available", response_model=List[SubscriptionTermOut])
    def list_available_subscription_terms(
        product_id: int,
        slot_type_code: str,
        user: UserOut = Depends(get_current_user),
    ):
        normalized_slot_type_code = str(slot_type_code or "").strip()
        if not normalized_slot_type_code:
            raise HTTPException(400, "slot_type_code is required")
        with psycopg.connect(DB_DSN) as conn:
            ensure_subscription_product(conn, product_id)
            slot_row = q1(conn, "SELECT 1 FROM app.slot_types WHERE code=%s", (normalized_slot_type_code,))
            if not slot_row:
                raise HTTPException(400, f"Unknown slot_type_code: {normalized_slot_type_code}")
            rows = qall(
                conn,
                """
                WITH target_slot AS (
                  SELECT st.code, st.mode, st.capacity
                  FROM app.slot_types st
                  WHERE st.code = %s
                ),
                term_usage AS (
                  SELECT
                    asa.subscription_term_id,
                    COUNT(*) FILTER (
                      WHERE asa.released_at IS NULL
                        AND asa.slot_type_code = %s
                    ) AS used_exact_slot,
                    COUNT(*) FILTER (
                      WHERE asa.released_at IS NULL
                        AND st2.mode = 'activate'
                    ) AS used_activate_any
                  FROM app.account_slot_assignments asa
                  JOIN app.slot_types st2 ON st2.code = asa.slot_type_code
                  WHERE asa.subscription_term_id IS NOT NULL
                  GROUP BY asa.subscription_term_id
                )
                SELECT
                  st.term_id,
                  st.product_id,
                  st.account_id,
                  a.login_name,
                  d.name AS domain_code,
                  st.valid_until,
                  st.notes,
                  st.is_archived,
                  st.created_at,
                  ts.mode,
                  ts.capacity,
                  COALESCE(tu.used_exact_slot, 0) AS used_exact_slot,
                  COALESCE(tu.used_activate_any, 0) AS used_activate_any
                FROM app.subscription_terms st
                JOIN app.accounts a ON a.account_id = st.account_id
                LEFT JOIN app.domains d ON d.domain_id = a.domain_id
                CROSS JOIN target_slot ts
                LEFT JOIN term_usage tu ON tu.subscription_term_id = st.term_id
                WHERE st.product_id=%s
                  AND st.is_archived IS NOT TRUE
                  AND a.status_code <> 'archived'
                  AND (
                    (ts.mode = 'activate' AND COALESCE(tu.used_activate_any, 0) < 1)
                    OR
                    (ts.mode <> 'activate' AND COALESCE(tu.used_exact_slot, 0) < ts.capacity)
                  )
                ORDER BY st.valid_until ASC, st.term_id ASC
                """,
                (normalized_slot_type_code, normalized_slot_type_code, product_id),
            )
        items: List[SubscriptionTermOut] = []
        for row in rows:
            if not row[5]:
                continue
            created_at = row[8] or datetime.now(timezone.utc)
            items.append(
                SubscriptionTermOut(
                    term_id=int(row[0]),
                    product_id=int(row[1]),
                    account_id=int(row[2]),
                    account_login=str(row[3] or ""),
                    domain_code=str(row[4] or ""),
                    login_full=(f"{row[3]}@{row[4]}" if row[3] and row[4] else str(row[3] or "")),
                    valid_until=row[5],
                    notes=row[6],
                    is_archived=bool(row[7]) if row[7] is not None else False,
                    created_at=created_at,
                    occupied=False,
                )
            )
        return items

    @app.get("/products/subscriptions/terms/available-for-deal")
    def list_available_subscription_terms_for_deal(
        slot_type_code: str,
        user: UserOut = Depends(get_current_user),
    ):
        # Возвращает плоский список доступных сроков подписок для выбранного слота.
        normalized_slot_type_code = str(slot_type_code or "").strip()
        if not normalized_slot_type_code:
            raise HTTPException(400, "slot_type_code is required")
        with psycopg.connect(DB_DSN) as conn:
            slot_row = q1(conn, "SELECT 1 FROM app.slot_types WHERE code=%s", (normalized_slot_type_code,))
            if not slot_row:
                raise HTTPException(400, f"Unknown slot_type_code: {normalized_slot_type_code}")
            rows = qall(
                conn,
                """
                WITH target_slot AS (
                  SELECT st.code, st.mode, st.capacity
                  FROM app.slot_types st
                  WHERE st.code = %s
                ),
                term_usage AS (
                  SELECT
                    asa.subscription_term_id,
                    COUNT(*) FILTER (
                      WHERE asa.released_at IS NULL
                        AND asa.slot_type_code = %s
                    ) AS used_exact_slot,
                    COUNT(*) FILTER (
                      WHERE asa.released_at IS NULL
                        AND st2.mode = 'activate'
                    ) AS used_activate_any
                  FROM app.account_slot_assignments asa
                  JOIN app.slot_types st2 ON st2.code = asa.slot_type_code
                  WHERE asa.subscription_term_id IS NOT NULL
                  GROUP BY asa.subscription_term_id
                )
                SELECT
                  st.term_id,
                  st.product_id,
                  p.title AS product_title,
                  st.account_id,
                  a.login_name,
                  d.name AS domain_code,
                  st.valid_until,
                  st.created_at
                FROM app.subscription_terms st
                JOIN app.products p ON p.product_id = st.product_id
                JOIN app.accounts a ON a.account_id = st.account_id
                LEFT JOIN app.domains d ON d.domain_id = a.domain_id
                CROSS JOIN target_slot ts
                LEFT JOIN term_usage tu ON tu.subscription_term_id = st.term_id
                WHERE st.is_archived IS NOT TRUE
                  AND p.is_archived IS NOT TRUE
                  AND lower(p.type_code) = 'subscription'
                  AND a.status_code <> 'archived'
                  AND (
                    (ts.mode = 'activate' AND COALESCE(tu.used_activate_any, 0) < 1)
                    OR
                    (ts.mode <> 'activate' AND COALESCE(tu.used_exact_slot, 0) < ts.capacity)
                  )
                ORDER BY st.valid_until DESC, st.term_id DESC
                """,
                (normalized_slot_type_code, normalized_slot_type_code),
            )
        result = []
        for row in rows:
            login_name = str(row[4] or "")
            domain_code = str(row[5] or "")
            login_full = f"{login_name}@{domain_code}" if login_name and domain_code else login_name
            result.append(
                {
                    "term_id": int(row[0]),
                    "product_id": int(row[1]),
                    "product_title": str(row[2] or ""),
                    "account_id": int(row[3]),
                    "login_full": login_full,
                    "valid_until": row[6],
                    "created_at": row[7],
                }
            )
        return result

    @app.get("/slot-types", response_model=List[SlotTypeOut])
    def list_slot_types(user: UserOut = Depends(get_current_user)):
        # Возвращает справочник типов слотов для модалки сделок.
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                """
                SELECT st.code, st.name, st.platform_code, st.mode, st.capacity
                FROM app.slot_types st
                ORDER BY st.platform_code, st.capacity, st.code
                """,
            )
        return [SlotTypeOut(code=r[0], name=r[1], platform_code=r[2], mode=r[3], capacity=int(r[4] or 0)) for r in rows]

    # Собирает карточку товара из общей и типовой таблиц.
    def load_product(conn, product_id: int):
        row = q1(
            conn,
            """
            SELECT
              p.product_id,
              p.type_code,
              p.title,
              p.short_title,
              r.code AS region_code,
              gp.link,
              gp.text_lang,
              gp.audio_lang,
              gp.vr_support,
              sp.provider,
              sp.billing_period,
              sp.notes
            FROM app.products p
            LEFT JOIN app.regions r ON r.region_id = p.region_id
            LEFT JOIN app.game_products gp ON gp.product_id = p.product_id
            LEFT JOIN app.subscription_products sp ON sp.product_id = p.product_id
            WHERE p.product_id=%s
            """,
            (product_id,),
        )
        if not row:
            return None
        # Платформы читаем через нейтральную связку product_platforms для всех типов товара.
        platform_codes = get_game_platform_codes(conn, int(row[0]))
        return ProductOut(
            product_id=int(row[0]),
            type_code=row[1],
            title=row[2],
            short_title=row[3],
            region_code=row[4],
            link=row[5],
            text_lang=row[6],
            audio_lang=row[7],
            vr_support=row[8],
            platform_codes=platform_codes,
            provider=row[9],
            billing_period=row[10],
            subscription_notes=row[11],
        )

    @app.get("/products", response_model=ProductListOut)
    def list_products(
        q: Optional[str] = None,
        type_code: Optional[str] = None,
        platform_code: Optional[str] = None,
        region_code: Optional[str] = None,
        sort_key: str = "id",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = 50,
        all: bool = False,
        user: UserOut = Depends(get_current_user),
    ):
        # Возвращаем единый список товаров с фильтрами и пагинацией.
        page = max(1, page)
        if all:
            page_size = 0
            offset = 0
        else:
            page_size = max(1, min(int(page_size or 50), 200))
            offset = (page - 1) * page_size

        sort_map = {
            "id": "product_id",
            "title": "title",
            "type": "type_code",
            "platform": "platform_sort",
            "region": "region_code",
        }
        sort_col = sort_map.get(sort_key, "b.product_id")
        sort_dir = "desc" if str(sort_dir).lower() == "desc" else "asc"

        filters = ["p.is_archived IS NOT TRUE"]
        params = []
        if q:
            filters.append("(p.title ILIKE %s OR p.short_title ILIKE %s)")
            params.extend([f"%{q}%", f"%{q}%"])
        if type_code:
            filters.append("lower(p.type_code) = lower(%s)")
            params.append(type_code)
        if region_code:
            filters.append("r.code ILIKE %s")
            params.append(f"%{region_code}%")
        if platform_code:
            filters.append(
                """
                EXISTS (
                  SELECT 1
                  FROM app.product_platforms pp2
                  JOIN app.platforms p2 ON p2.platform_id = pp2.platform_id
                  WHERE pp2.product_id = p.product_id
                    AND lower(p2.code) = lower(%s)
                )
                """
            )
            params.append(platform_code)

        where_sql = f"WHERE {' AND '.join(filters)}"

        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                f"""
                WITH base AS (
                  SELECT
                    p.product_id,
                    p.type_code,
                    p.title,
                    p.short_title,
                    r.code AS region_code,
                    gp.link,
                    gp.text_lang,
                    gp.audio_lang,
                    gp.vr_support,
                    sp.provider,
                    sp.billing_period,
                    sp.notes,
                    MIN(pl.code) AS platform_sort
                  FROM app.products p
                  LEFT JOIN app.regions r ON r.region_id = p.region_id
                  LEFT JOIN app.game_products gp ON gp.product_id = p.product_id
                  LEFT JOIN app.subscription_products sp ON sp.product_id = p.product_id
                  LEFT JOIN app.product_platforms gpl ON gpl.product_id = p.product_id
                  LEFT JOIN app.platforms pl ON pl.platform_id = gpl.platform_id
                  {where_sql}
                  GROUP BY
                    p.product_id,
                    p.type_code,
                    p.title,
                    p.short_title,
                    r.code,
                    gp.link,
                    gp.text_lang,
                    gp.audio_lang,
                    gp.vr_support,
                    sp.provider,
                    sp.billing_period,
                    sp.notes
                ),
                total AS (
                  SELECT COUNT(*) AS total_count FROM base
                ),
                page_rows AS (
                  SELECT * FROM base
                  ORDER BY {sort_col} {sort_dir}, product_id DESC
                  {"" if all else "LIMIT %s OFFSET %s"}
                )
                SELECT
                  b.product_id,
                  b.type_code,
                  b.title,
                  b.short_title,
                  b.region_code,
                  b.link,
                  b.text_lang,
                  b.audio_lang,
                  b.vr_support,
                  b.provider,
                  b.billing_period,
                  b.notes,
                  COALESCE(array_agg(pl2.code ORDER BY pl2.code) FILTER (WHERE pl2.code IS NOT NULL), '{{}}'::text[]) AS platform_codes,
                  (SELECT total_count FROM total) AS total_count
                FROM page_rows b
                LEFT JOIN app.product_platforms gpl2 ON gpl2.product_id = b.product_id
                LEFT JOIN app.platforms pl2 ON pl2.platform_id = gpl2.platform_id
                GROUP BY
                  b.product_id,
                  b.type_code,
                  b.title,
                  b.short_title,
                  b.region_code,
                  b.link,
                  b.text_lang,
                  b.audio_lang,
                  b.vr_support,
                  b.provider,
                  b.billing_period,
                  b.notes
                ORDER BY {sort_col} {sort_dir}, b.product_id DESC
                """,
                params + ([] if all else [page_size, offset]),
            )

        items = []
        total = 0
        for row in rows:
            total = int(row[13] or 0)
            items.append(
                ProductOut(
                    product_id=int(row[0]),
                    type_code=row[1],
                    title=row[2],
                    short_title=row[3],
                    region_code=row[4],
                    link=row[5],
                    text_lang=row[6],
                    audio_lang=row[7],
                    vr_support=row[8],
                    provider=row[9],
                    billing_period=row[10],
                    subscription_notes=row[11],
                    platform_codes=list(row[12] or []),
                )
            )

        if not rows:
            with psycopg.connect(DB_DSN) as conn:
                total_row = q1(
                    conn,
                    f"""
                    SELECT COUNT(*)
                    FROM app.products p
                    LEFT JOIN app.regions r ON r.region_id = p.region_id
                    {where_sql}
                    """,
                    params,
                )
                total = int(total_row[0] or 0) if total_row else 0

        return {"total": total, "items": items}

    @app.post("/products", response_model=ProductOut)
    # Создаём товар в product-first формате; платформы пишем в product_platforms.
    def create_product(payload: ProductCreate = Body(...), user: UserOut = Depends(get_current_user)):
        type_code = (payload.type_code or "").strip().lower()
        if not type_code:
            raise HTTPException(400, "type_code is required")
        if not (payload.title or "").strip():
            raise HTTPException(400, "title is required")

        with psycopg.connect(DB_DSN) as conn:
            type_row = q1(
                conn,
                "SELECT 1 FROM app.product_types WHERE code=%s AND is_archived IS NOT TRUE",
                (type_code,),
            )
            if not type_row:
                raise HTTPException(400, f"Unknown type_code: {type_code}")

            region_id = get_region_id(conn, payload.region_code)

            if type_code == "game":
                platform_codes = normalize_platform_codes(payload.platform_codes)
                conflicts = find_game_title_platform_conflicts(conn, payload.title, platform_codes)
                if conflicts:
                    raise HTTPException(409, f"Product already exists for platforms: {', '.join(conflicts)}")

                if platform_codes:
                    platform_ids = [get_platform_id(conn, code) for code in platform_codes]
                else:
                    platform_ids = []

                product_row = q1(
                    conn,
                    """
                    INSERT INTO app.products(type_code, title, short_title, region_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING product_id
                    """,
                    (type_code, payload.title, payload.short_title, region_id),
                )
                product_id = int(product_row[0])

                if platform_ids:
                    # Платформы сохраняем в нейтральную таблицу связей товара.
                    with conn.cursor() as cur:
                        cur.executemany(
                            "INSERT INTO app.product_platforms(product_id, platform_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                            [(product_id, pid) for pid in platform_ids],
                        )

                exec1(
                    conn,
                    """
                    INSERT INTO app.game_products(product_id, link, text_lang, audio_lang, vr_support)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (product_id) DO UPDATE
                    SET link=EXCLUDED.link,
                        text_lang=EXCLUDED.text_lang,
                        audio_lang=EXCLUDED.audio_lang,
                        vr_support=EXCLUDED.vr_support
                    """,
                    (
                        product_id,
                        payload.link,
                        payload.text_lang,
                        payload.audio_lang,
                        payload.vr_support,
                    ),
                )
            elif type_code == "subscription":
                platform_codes = normalize_platform_codes(payload.platform_codes)
                platform_ids = [get_platform_id(conn, code) for code in platform_codes] if platform_codes else []
                product_row = q1(
                    conn,
                    """
                    INSERT INTO app.products(type_code, title, short_title, region_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING product_id
                    """,
                    (type_code, payload.title, payload.short_title, region_id),
                )
                product_id = int(product_row[0])
                exec1(
                    conn,
                    """
                    INSERT INTO app.subscription_products(product_id, provider, billing_period, notes)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (product_id) DO NOTHING
                    """,
                    (product_id, payload.provider, payload.billing_period, payload.subscription_notes),
                )
                if platform_ids:
                    # Для подписок тоже сохраняем платформы в общей связке product_platforms.
                    with conn.cursor() as cur:
                        cur.executemany(
                            "INSERT INTO app.product_platforms(product_id, platform_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                            [(product_id, pid) for pid in platform_ids],
                        )
            else:
                product_row = q1(
                    conn,
                    """
                    INSERT INTO app.products(type_code, title, short_title, region_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING product_id
                    """,
                    (type_code, payload.title, payload.short_title, region_id),
                )
                product_id = int(product_row[0])

            conn.commit()

        with psycopg.connect(DB_DSN) as conn:
            item = load_product(conn, product_id)
        if not item:
            raise HTTPException(500, "Failed to load created product")
        return item

    @app.put("/products/{product_id}", response_model=ProductOut)
    # Обновляем товар и синхронизируем связанные игровые/подписочные атрибуты.
    def update_product(product_id: int, payload: ProductUpdate = Body(...), user: UserOut = Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                """
                SELECT p.type_code, p.title, p.short_title, p.region_id,
                       gp.link, gp.text_lang, gp.audio_lang, gp.vr_support,
                       sp.provider, sp.billing_period, sp.notes
                FROM app.products p
                LEFT JOIN app.game_products gp ON gp.product_id = p.product_id
                LEFT JOIN app.subscription_products sp ON sp.product_id = p.product_id
                WHERE p.product_id=%s
                """,
                (product_id,),
            )
            if not row:
                raise HTTPException(404, "Product not found")

            type_code = row[0]
            if payload.type_code is not None and payload.type_code.strip().lower() != type_code:
                raise HTTPException(400, "type_code cannot be changed")

            new_title = payload.title if payload.title is not None else row[1]
            if not (new_title or "").strip():
                raise HTTPException(400, "title is required")
            new_short = payload.short_title if payload.short_title is not None else row[2]
            new_region_id = get_region_id(conn, payload.region_code) if payload.region_code is not None else row[3]
            exec1(
                conn,
                """
                UPDATE app.products
                SET title=%s,
                    short_title=%s,
                    region_id=%s
                WHERE product_id=%s
                """,
                (new_title, new_short, new_region_id, product_id),
            )

            if type_code == "game":
                old_platform_codes = get_game_platform_codes(conn, product_id)
                platform_codes = normalize_platform_codes(payload.platform_codes) if payload.platform_codes is not None else old_platform_codes
                conflicts = find_game_title_platform_conflicts(conn, new_title, platform_codes, exclude_product_id=product_id)
                if conflicts:
                    raise HTTPException(409, f"Product already exists for platforms: {', '.join(conflicts)}")

                new_link = payload.link if payload.link is not None else row[4]
                new_text_lang = payload.text_lang if payload.text_lang is not None else row[5]
                new_audio_lang = payload.audio_lang if payload.audio_lang is not None else row[6]
                new_vr_support = payload.vr_support if payload.vr_support is not None else row[7]

                exec1(
                    conn,
                    """
                    INSERT INTO app.game_products(product_id, link, text_lang, audio_lang, vr_support)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (product_id) DO UPDATE
                    SET link=EXCLUDED.link,
                        text_lang=EXCLUDED.text_lang,
                        audio_lang=EXCLUDED.audio_lang,
                        vr_support=EXCLUDED.vr_support
                    """,
                    (product_id, new_link, new_text_lang, new_audio_lang, new_vr_support),
                )

                if payload.platform_codes is not None:
                    # При явном обновлении платформ пересобираем список связей товара.
                    exec1(conn, "DELETE FROM app.product_platforms WHERE product_id=%s", (product_id,))
                    if platform_codes:
                        platform_ids = [get_platform_id(conn, code) for code in platform_codes]
                        with conn.cursor() as cur:
                            cur.executemany(
                                "INSERT INTO app.product_platforms(product_id, platform_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                [(product_id, pid) for pid in platform_ids],
                            )

            if type_code == "subscription":
                new_provider = payload.provider if payload.provider is not None else row[8]
                new_billing_period = payload.billing_period if payload.billing_period is not None else row[9]
                new_notes = payload.subscription_notes if payload.subscription_notes is not None else row[10]
                platform_codes = normalize_platform_codes(payload.platform_codes) if payload.platform_codes is not None else None
                exec1(
                    conn,
                    """
                    INSERT INTO app.subscription_products(product_id, provider, billing_period, notes)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (product_id) DO UPDATE
                    SET provider=EXCLUDED.provider,
                        billing_period=EXCLUDED.billing_period,
                        notes=EXCLUDED.notes
                    """,
                    (product_id, new_provider, new_billing_period, new_notes),
                )
                if platform_codes is not None:
                    # При явном обновлении платформ подписки пересобираем связи так же, как для игр.
                    exec1(conn, "DELETE FROM app.product_platforms WHERE product_id=%s", (product_id,))
                    if platform_codes:
                        platform_ids = [get_platform_id(conn, code) for code in platform_codes]
                        with conn.cursor() as cur:
                            cur.executemany(
                                "INSERT INTO app.product_platforms(product_id, platform_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                [(product_id, pid) for pid in platform_ids],
                            )

            conn.commit()
            item = load_product(conn, product_id)

        if not item:
            raise HTTPException(500, "Failed to load updated product")
        return item

    @app.delete("/products/{product_id}")
    def archive_product(product_id: int, user: UserOut = Depends(get_current_user)):
        # Архивируем товар.
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                """
                SELECT type_code
                FROM app.products p
                WHERE p.product_id=%s
                """,
                (product_id,),
            )
            if not row:
                raise HTTPException(404, "Product not found")
            exec1(conn, "UPDATE app.products SET is_archived=true WHERE product_id=%s", (product_id,))
            conn.commit()
        return {"ok": True}
