from typing import List, Optional

from fastapi import Body, Depends, File, HTTPException, UploadFile


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
    require_role,
    encode_b64,
    ProductCreate,
    ProductUpdate,
    ProductOut,
    ProductListOut,
    SlotTypeOut,
    UserOut,
):
    @app.get("/slot-types", response_model=List[SlotTypeOut])
    def list_slot_types(user: UserOut = Depends(get_current_user)):
        # Возвращает справочник типов слотов для модалки сделок.
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                """
                SELECT st.code, st.name, p.code AS platform_code, st.mode, st.capacity
                FROM app.slot_types st
                JOIN app.platforms p ON p.platform_id = st.platform_id
                ORDER BY p.code, st.capacity, st.code
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
              gp.logo_url,
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
        # Платформы читаем через нейтральную связку product_platforms.
        platform_codes = []
        if str(row[1] or "").strip().lower() == "game":
            platform_codes = get_game_platform_codes(conn, int(row[0]))
        return ProductOut(
            product_id=int(row[0]),
            type_code=row[1],
            title=row[2],
            short_title=row[3],
            region_code=row[4],
            link=row[5],
            logo_url=row[6],
            text_lang=row[7],
            audio_lang=row[8],
            vr_support=row[9],
            platform_codes=platform_codes,
            provider=row[10],
            billing_period=row[11],
            subscription_notes=row[12],
        )

    # Проверяет, что товар существует и относится к типу game.
    def ensure_game_product(conn, product_id: int) -> None:
        row = q1(
            conn,
            "SELECT type_code FROM app.products WHERE product_id=%s",
            (product_id,),
        )
        if not row:
            raise HTTPException(404, "Product not found")
        type_code = str(row[0] or "").strip().lower()
        if type_code != "game":
            raise HTTPException(400, "logo is supported only for game products")

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
                    gp.logo_url,
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
                    gp.logo_url,
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
                  b.logo_url,
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
                  b.logo_url,
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
            total = int(row[14] or 0)
            items.append(
                ProductOut(
                    product_id=int(row[0]),
                    type_code=row[1],
                    title=row[2],
                    short_title=row[3],
                    region_code=row[4],
                    link=row[5],
                    logo_url=row[6],
                    text_lang=row[7],
                    audio_lang=row[8],
                    vr_support=row[9],
                    provider=row[10],
                    billing_period=row[11],
                    subscription_notes=row[12],
                    platform_codes=list(row[13] or []),
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
                    INSERT INTO app.game_products(product_id, link, logo_url, text_lang, audio_lang, vr_support)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (product_id) DO UPDATE
                    SET link=EXCLUDED.link,
                        logo_url=EXCLUDED.logo_url,
                        text_lang=EXCLUDED.text_lang,
                        audio_lang=EXCLUDED.audio_lang,
                        vr_support=EXCLUDED.vr_support
                    """,
                    (
                        product_id,
                        payload.link,
                        payload.logo_url,
                        payload.text_lang,
                        payload.audio_lang,
                        payload.vr_support,
                    ),
                )
            elif type_code == "subscription":
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
                       gp.link, gp.logo_url, gp.text_lang, gp.audio_lang, gp.vr_support,
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
                new_logo_url = payload.logo_url if payload.logo_url is not None else row[5]
                new_text_lang = payload.text_lang if payload.text_lang is not None else row[6]
                new_audio_lang = payload.audio_lang if payload.audio_lang is not None else row[7]
                new_vr_support = payload.vr_support if payload.vr_support is not None else row[8]

                exec1(
                    conn,
                    """
                    INSERT INTO app.game_products(product_id, link, logo_url, text_lang, audio_lang, vr_support)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (product_id) DO UPDATE
                    SET link=EXCLUDED.link,
                        logo_url=EXCLUDED.logo_url,
                        text_lang=EXCLUDED.text_lang,
                        audio_lang=EXCLUDED.audio_lang,
                        vr_support=EXCLUDED.vr_support
                    """,
                    (product_id, new_link, new_logo_url, new_text_lang, new_audio_lang, new_vr_support),
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
                new_provider = payload.provider if payload.provider is not None else row[9]
                new_billing_period = payload.billing_period if payload.billing_period is not None else row[10]
                new_notes = payload.subscription_notes if payload.subscription_notes is not None else row[11]
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

    @app.get("/products/{product_id}/logo")
    def get_product_logo(product_id: int, user: UserOut = Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            ensure_game_product(conn, product_id)
            row = q1(
                conn,
                "SELECT logo_blob, logo_mime FROM app.game_products WHERE product_id=%s",
                (product_id,),
            )
            blob, mime = row if row else (None, None)
            if not blob or not mime:
                raise HTTPException(404, "Logo not found")
        return {"mime": mime, "data_b64": encode_b64(blob)}

    @app.post("/products/{product_id}/logo")
    def upload_product_logo(
        product_id: int,
        file: UploadFile = File(...),
        user: UserOut = Depends(require_role("admin")),
    ):
        if not file or not file.content_type:
            raise HTTPException(400, "file is required")
        if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
            raise HTTPException(400, "Only jpg, png, webp are allowed")
        content = file.file.read()
        if content is None:
            raise HTTPException(400, "file is required")
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(400, "File too large. Max 5MB")
        with psycopg.connect(DB_DSN) as conn:
            ensure_game_product(conn, product_id)
            exec1(
                conn,
                """
                INSERT INTO app.game_products(product_id, logo_blob, logo_mime)
                VALUES (%s, %s, %s)
                ON CONFLICT (product_id) DO UPDATE
                SET logo_blob=EXCLUDED.logo_blob, logo_mime=EXCLUDED.logo_mime
                """,
                (product_id, content, file.content_type),
            )
            conn.commit()
        return {"ok": True}

    @app.delete("/products/{product_id}/logo")
    def delete_product_logo(product_id: int, user: UserOut = Depends(require_role("admin"))):
        with psycopg.connect(DB_DSN) as conn:
            ensure_game_product(conn, product_id)
            exec1(
                conn,
                "UPDATE app.game_products SET logo_blob=NULL, logo_mime=NULL WHERE product_id=%s",
                (product_id,),
            )
            conn.commit()
        return {"ok": True}
