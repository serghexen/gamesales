from __future__ import annotations

from typing import List, Optional

from fastapi import Depends, File, HTTPException, UploadFile


def mount_games_routes(
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
    ensure_game_exists,
    encode_b64,
    get_current_user,
    require_role,
    GameListOut,
    GameOut,
    SlotTypeOut,
    GameCreate,
    GameUpdate,
    UserOut,
):
    @app.get("/games", response_model=GameListOut)
    def list_games(
        q: Optional[str] = None,
        platform_code: Optional[str] = None,
        region_code: Optional[str] = None,
        sort_key: str = "id",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = 50,
        all: bool = False,
        user: UserOut = Depends(get_current_user),
    ):
        page = max(1, page)
        if all:
            page_size = 0
            offset = 0
        else:
            page_size = max(1, min(int(page_size or 50), 200))
            offset = (page - 1) * page_size

        sort_map = {
            "id": "game_id",
            "title": "title",
            "platform": "platform_sort",
            "region": "region_code",
        }
        sort_col = sort_map.get(sort_key, "g.game_id")
        sort_dir = "desc" if str(sort_dir).lower() == "desc" else "asc"

        filters = []
        params = []
        if q:
            filters.append("(g.title ILIKE %s OR g.short_title ILIKE %s)")
            params.extend([f"%{q}%", f"%{q}%"])
        if region_code:
            filters.append("r.code ILIKE %s")
            params.append(f"%{region_code}%")
        if platform_code:
            filters.append(
                """
                EXISTS (
                  SELECT 1
                  FROM app.game_platforms gp2
                  JOIN app.platforms p2 ON p2.platform_id = gp2.platform_id
                  WHERE gp2.game_id = g.game_id AND lower(p2.code) = lower(%s)
                )
            """
            )
            params.append(platform_code)
        filters.append("g.is_archived IS NOT TRUE")

        where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""

        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                f"""
                WITH base AS (
                  SELECT
                    g.game_id,
                    g.title,
                    g.short_title,
                    g.link,
                    g.logo_url,
                    g.text_lang,
                    g.audio_lang,
                    g.vr_support,
                    r.code as region_code,
                    MIN(p.code) as platform_sort
                  FROM app.game_titles g
                  LEFT JOIN app.regions r ON r.region_id = g.region_id
                  LEFT JOIN app.game_platforms gp ON gp.game_id = g.game_id
                  LEFT JOIN app.platforms p ON p.platform_id = gp.platform_id
                  {where_sql}
                  GROUP BY g.game_id, g.title, g.short_title, g.link, g.logo_url, g.text_lang, g.audio_lang, g.vr_support, r.code
                ),
                total AS (
                  SELECT COUNT(*) AS total_count FROM base
                ),
                page AS (
                  SELECT * FROM base
                  ORDER BY {sort_col} {sort_dir}, game_id DESC
                  {"" if all else "LIMIT %s OFFSET %s"}
                )
                SELECT
                  page.game_id,
                  page.title,
                  page.short_title,
                  page.link,
                  page.logo_url,
                  page.text_lang,
                  page.audio_lang,
                  page.vr_support,
                  page.region_code,
                  page.platform_sort,
                  COALESCE(array_agg(p2.code ORDER BY p2.code) FILTER (WHERE p2.code IS NOT NULL), '{{}}'::text[]) AS platform_codes,
                  (SELECT total_count FROM total) as total_count
                FROM page
                LEFT JOIN app.game_platforms gp2 ON gp2.game_id = page.game_id
                LEFT JOIN app.platforms p2 ON p2.platform_id = gp2.platform_id
                GROUP BY page.game_id, page.title, page.short_title, page.link, page.logo_url, page.text_lang, page.audio_lang, page.vr_support, page.region_code, page.platform_sort
                ORDER BY {sort_col} {sort_dir}, page.game_id DESC
                """,
                params + ([] if all else [page_size, offset]),
            )

        items = []
        total = 0
        for (r0, r1, r2, r3, r4, r5, r6, r7, r8, _platform_sort, r9, r10) in rows:
            total = int(r10 or 0)
            items.append(
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
            )
        if not rows:
            with psycopg.connect(DB_DSN) as conn:
                total_row = q1(
                    conn,
                    f"""
                    SELECT COUNT(*) FROM (
                      SELECT g.game_id
                      FROM app.game_titles g
                      LEFT JOIN app.regions r ON r.region_id = g.region_id
                      LEFT JOIN app.game_platforms gp ON gp.game_id = g.game_id
                      LEFT JOIN app.platforms p ON p.platform_id = gp.platform_id
                      {where_sql}
                      GROUP BY g.game_id
                    ) t
                    """,
                    params,
                )
                total = int(total_row[0] or 0) if total_row else 0
        return {"total": total, "items": items}

    @app.get("/slot-types", response_model=List[SlotTypeOut])
    def list_slot_types(user: UserOut = Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                """
                SELECT code, name, platform_code, mode, capacity
                FROM app.slot_types
                ORDER BY
                  CASE WHEN mode = 'activate' THEN 1 ELSE 2 END,
                  platform_code,
                  code
                """,
            )
        return [SlotTypeOut(code=r[0], name=r[1], platform_code=r[2], mode=r[3], capacity=int(r[4] or 0)) for r in rows]

    @app.post("/games", response_model=GameOut)
    def create_game(payload: GameCreate, user: UserOut = Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            platform_codes = normalize_platform_codes(payload.platform_codes)
            conflicts = find_game_title_platform_conflicts(conn, payload.title, platform_codes)
            if conflicts:
                raise HTTPException(409, f"Game already exists for platforms: {', '.join(conflicts)}")
            platform_ids = [get_platform_id(conn, code) for code in platform_codes]
            region_id = get_region_id(conn, payload.region_code)

            row = q1(
                conn,
                """
                INSERT INTO app.game_titles(title, short_title, link, logo_url, text_lang, audio_lang, vr_support, region_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING game_id
                """,
                (
                    payload.title,
                    payload.short_title,
                    payload.link,
                    payload.logo_url,
                    payload.text_lang,
                    payload.audio_lang,
                    payload.vr_support,
                    region_id,
                ),
            )
            gid = int(row[0])
            if platform_ids:
                with conn.cursor() as cur:
                    cur.executemany(
                        "INSERT INTO app.game_platforms(game_id, platform_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        [(gid, pid) for pid in platform_ids],
                    )
            conn.commit()

        return GameOut(
            game_id=gid,
            title=payload.title,
            short_title=payload.short_title,
            link=payload.link,
            logo_url=payload.logo_url,
            text_lang=payload.text_lang,
            audio_lang=payload.audio_lang,
            vr_support=payload.vr_support,
            platform_codes=platform_codes,
            region_code=payload.region_code,
        )

    @app.put("/games/{game_id}", response_model=GameOut)
    def update_game(game_id: int, payload: GameUpdate, user: UserOut = Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                """
                SELECT g.title, g.short_title, g.link, g.logo_url, g.text_lang, g.audio_lang, g.vr_support, r.code
                FROM app.game_titles g
                LEFT JOIN app.regions r ON r.region_id = g.region_id
                WHERE g.game_id=%s
                """,
                (game_id,),
            )
            if not row:
                raise HTTPException(404, "Game not found")

            new_title = payload.title if payload.title is not None else row[0]
            if not new_title:
                raise HTTPException(400, "title is required")
            new_short = payload.short_title if payload.short_title is not None else row[1]
            new_link = payload.link if payload.link is not None else row[2]
            new_logo = payload.logo_url if payload.logo_url is not None else row[3]
            new_text_lang = payload.text_lang if payload.text_lang is not None else row[4]
            new_audio_lang = payload.audio_lang if payload.audio_lang is not None else row[5]
            new_vr_support = payload.vr_support if payload.vr_support is not None else row[6]
            platform_codes = normalize_platform_codes(payload.platform_codes)
            platforms_for_check = platform_codes if payload.platform_codes is not None else get_game_platform_codes(conn, game_id)
            conflicts = find_game_title_platform_conflicts(conn, new_title, platforms_for_check, exclude_game_id=game_id)
            if conflicts:
                raise HTTPException(409, f"Game already exists for platforms: {', '.join(conflicts)}")

            if payload.region_code is None:
                region_code = row[7]
            else:
                region_code = payload.region_code or None

            region_id = get_region_id(conn, region_code)

            exec1(
                conn,
                """
                UPDATE app.game_titles
                SET title=%s,
                    short_title=%s,
                    link=%s,
                    logo_url=%s,
                    text_lang=%s,
                    audio_lang=%s,
                    vr_support=%s,
                    region_id=%s
                WHERE game_id=%s
                """,
                (new_title, new_short, new_link, new_logo, new_text_lang, new_audio_lang, new_vr_support, region_id, game_id),
            )
            if payload.platform_codes is not None:
                exec1(conn, "DELETE FROM app.game_platforms WHERE game_id=%s", (game_id,))
                if platform_codes:
                    platform_ids = [get_platform_id(conn, code) for code in platform_codes]
                    with conn.cursor() as cur:
                        cur.executemany(
                            "INSERT INTO app.game_platforms(game_id, platform_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                            [(game_id, pid) for pid in platform_ids],
                        )
            else:
                rows = qall(
                    conn,
                    """
                    SELECT p.code
                    FROM app.game_platforms gp
                    JOIN app.platforms p ON p.platform_id = gp.platform_id
                    WHERE gp.game_id=%s
                    ORDER BY p.code
                    """,
                    (game_id,),
                )
                platform_codes = [r[0] for r in rows]
            conn.commit()
        return GameOut(
            game_id=game_id,
            title=new_title,
            short_title=new_short,
            link=new_link,
            logo_url=new_logo,
            text_lang=new_text_lang,
            audio_lang=new_audio_lang,
            vr_support=new_vr_support,
            platform_codes=platform_codes,
            region_code=region_code,
        )

    @app.delete("/games/{game_id}")
    def archive_game(game_id: int, user: UserOut = Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT 1 FROM app.game_titles WHERE game_id=%s", (game_id,))
            if not row:
                raise HTTPException(404, "Game not found")
            exec1(conn, "UPDATE app.game_titles SET is_archived=true WHERE game_id=%s", (game_id,))
            conn.commit()
        return {"ok": True}

    @app.get("/games/{game_id}/logo")
    def get_game_logo(game_id: int, user: UserOut = Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                "SELECT logo_blob, logo_mime FROM app.game_titles WHERE game_id=%s",
                (game_id,),
            )
            if not row:
                raise HTTPException(404, "Game not found")
            blob, mime = row
            if not blob or not mime:
                raise HTTPException(404, "Logo not found")
        return {"mime": mime, "data_b64": encode_b64(blob)}

    @app.post("/games/{game_id}/logo")
    def upload_game_logo(game_id: int, file: UploadFile = File(...), user: UserOut = Depends(require_role("admin"))):
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
            ensure_game_exists(conn, game_id)
            exec1(
                conn,
                "UPDATE app.game_titles SET logo_blob=%s, logo_mime=%s WHERE game_id=%s",
                (content, file.content_type, game_id),
            )
            conn.commit()
        return {"ok": True}

    @app.delete("/games/{game_id}/logo")
    def delete_game_logo(game_id: int, user: UserOut = Depends(require_role("admin"))):
        with psycopg.connect(DB_DSN) as conn:
            ensure_game_exists(conn, game_id)
            exec1(conn, "UPDATE app.game_titles SET logo_blob=NULL, logo_mime=NULL WHERE game_id=%s", (game_id,))
            conn.commit()
        return {"ok": True}
