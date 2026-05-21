from fastapi import Depends, HTTPException


def mount_catalogs_routes(
    app,
    *,
    DB_DSN,
    psycopg,
    q1,
    qall,
    exec1,
    get_current_user,
    require_role,
    UserOut,
    PlatformOut,
    PlatformIn,
    PlatformUpdate,
    RegionOut,
    RegionIn,
    RegionUpdate,
    DomainIn,
    NameUpdate,
    SourceOut,
    SourceIn,
    SourceUpdate,
    MessengerOut,
    MessengerIn,
    MessengerUpdate,
):
    @app.get("/platforms", response_model=list[PlatformOut])
    def list_platforms(user: UserOut = Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(conn, "SELECT code, name, slot_capacity FROM app.platforms WHERE is_archived IS NOT TRUE ORDER BY code")
        return [PlatformOut(code=r0, name=r1, slot_capacity=int(r2 or 0)) for (r0, r1, r2) in rows]

    @app.get("/regions", response_model=list[RegionOut])
    def list_regions(user: UserOut = Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(conn, "SELECT code, name, purchase_cost_rate FROM app.regions WHERE is_archived IS NOT TRUE ORDER BY code")
        return [RegionOut(code=r0, name=r1, purchase_cost_rate=float(r2 or 1.0)) for (r0, r1, r2) in rows]

    @app.post("/platforms", response_model=PlatformOut)
    def create_platform(payload: PlatformIn, user: UserOut = Depends(require_role("admin", "owner"))):
        code = (payload.code or "").strip().lower()
        name = (payload.name or "").strip()
        if not code or not name:
            raise HTTPException(400, "Platform code and name are required")
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                INSERT INTO app.platforms(code, name, slot_capacity, is_archived)
                VALUES (%s, %s, %s, false)
                ON CONFLICT (code)
                DO UPDATE SET name=excluded.name, slot_capacity=excluded.slot_capacity, is_archived=false
                """,
                (code, name, payload.slot_capacity),
            )
            conn.commit()
        return PlatformOut(code=code, name=name, slot_capacity=payload.slot_capacity)

    @app.put("/platforms/{code}", response_model=PlatformOut)
    def update_platform(code: str, payload: PlatformUpdate, user: UserOut = Depends(require_role("admin", "owner"))):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT name, slot_capacity FROM app.platforms WHERE code=%s AND is_archived IS NOT TRUE", (code,))
            if not row:
                raise HTTPException(404, "Platform not found")
            new_name = (payload.name or row[0]).strip()
            new_slots = payload.slot_capacity if payload.slot_capacity is not None else row[1]
            exec1(conn, "UPDATE app.platforms SET name=%s, slot_capacity=%s WHERE code=%s", (new_name, new_slots, code))
            conn.commit()
        return PlatformOut(code=code, name=new_name, slot_capacity=new_slots)

    @app.delete("/platforms/{code}")
    def delete_platform(code: str, user: UserOut = Depends(require_role("admin", "owner"))):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT 1 FROM app.platforms WHERE code=%s", (code,))
            if not row:
                raise HTTPException(404, "Platform not found")
            exec1(conn, "UPDATE app.platforms SET is_archived=true WHERE code=%s", (code,))
            conn.commit()
        return {"ok": True}

    @app.post("/regions", response_model=RegionOut)
    def create_region(payload: RegionIn, user: UserOut = Depends(require_role("admin", "owner"))):
        code = (payload.code or "").strip().upper()
        name = (payload.name or "").strip()
        rate = float(payload.purchase_cost_rate or 1.0)
        if not code or not name:
            raise HTTPException(400, "Region code and name are required")
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                INSERT INTO app.regions(code, name, purchase_cost_rate, is_archived)
                VALUES (%s, %s, %s, false)
                ON CONFLICT (code)
                DO UPDATE SET name=excluded.name, purchase_cost_rate=excluded.purchase_cost_rate, is_archived=false
                """,
                (code, name, rate),
            )
            conn.commit()
        return RegionOut(code=code, name=name, purchase_cost_rate=rate)

    @app.put("/regions/{code}", response_model=RegionOut)
    def update_region(code: str, payload: RegionUpdate, user: UserOut = Depends(require_role("admin", "owner"))):
        name = (payload.name or "").strip() if payload.name is not None else None
        rate = payload.purchase_cost_rate
        if name is not None and not name:
            raise HTTPException(400, "Name is required")
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT name, purchase_cost_rate FROM app.regions WHERE code=%s AND is_archived IS NOT TRUE", (code,))
            if not row:
                raise HTTPException(404, "Region not found")
            new_name = name if name is not None else row[0]
            new_rate = float(rate) if rate is not None else float(row[1] or 1.0)
            exec1(conn, "UPDATE app.regions SET name=%s, purchase_cost_rate=%s WHERE code=%s", (new_name, new_rate, code))
            conn.commit()
        return RegionOut(code=code, name=new_name, purchase_cost_rate=new_rate)

    @app.delete("/regions/{code}")
    def delete_region(code: str, user: UserOut = Depends(require_role("admin", "owner"))):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT 1 FROM app.regions WHERE code=%s", (code,))
            if not row:
                raise HTTPException(404, "Region not found")
            exec1(conn, "UPDATE app.regions SET is_archived=true WHERE code=%s", (code,))
            conn.commit()
        return {"ok": True}

    @app.get("/domains", response_model=list[PlatformOut])
    def list_domains(user: UserOut = Depends(get_current_user)):
        def load_rows():
            with psycopg.connect(DB_DSN) as conn:
                return qall(conn, "SELECT name, name FROM app.domains WHERE is_archived IS NOT TRUE ORDER BY name")

        try:
            rows = load_rows()
        except Exception as e:
            # После перезапуска PostgreSQL из пула может прийти "мертвый" коннект; один ретрай обычно решает.
            text = str(e).lower()
            if "server closed the connection unexpectedly" in text or "consuming input failed" in text:
                rows = load_rows()
            else:
                raise
        return [PlatformOut(code=r0, name=r1, slot_capacity=0) for (r0, r1) in rows]

    @app.get("/sources", response_model=list[SourceOut])
    def list_sources(user: UserOut = Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(conn, "SELECT source_id, code, name FROM app.sources WHERE is_archived IS NOT TRUE ORDER BY source_id")
        return [SourceOut(source_id=int(r0), code=r1, name=r2) for (r0, r1, r2) in rows]

    @app.get("/messengers", response_model=list[MessengerOut])
    def list_messengers(user: UserOut = Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                "SELECT messenger_id, code, name FROM app.messengers WHERE is_archived IS NOT TRUE ORDER BY messenger_id",
            )
        return [MessengerOut(messenger_id=int(r0), code=r1, name=r2) for (r0, r1, r2) in rows]

    @app.post("/domains", response_model=PlatformOut)
    def create_domain(payload: DomainIn, user: UserOut = Depends(require_role("admin", "owner"))):
        name = (payload.name or "").strip().lower()
        if not name:
            raise HTTPException(400, "Domain name is required")
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                INSERT INTO app.domains(name, is_archived)
                VALUES (%s, false)
                ON CONFLICT (name)
                DO UPDATE SET is_archived=false
                """,
                (name,),
            )
            conn.commit()
        return PlatformOut(code=name, name=name, slot_capacity=0)

    @app.put("/domains/{name}", response_model=PlatformOut)
    def update_domain(name: str, payload: NameUpdate, user: UserOut = Depends(require_role("admin", "owner"))):
        new_name = (payload.name or "").strip().lower()
        if not new_name:
            raise HTTPException(400, "Name is required")
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT 1 FROM app.domains WHERE name=%s AND is_archived IS NOT TRUE", (name,))
            if not row:
                raise HTTPException(404, "Domain not found")
            exec1(conn, "UPDATE app.domains SET name=%s WHERE name=%s", (new_name, name))
            conn.commit()
        return PlatformOut(code=new_name, name=new_name, slot_capacity=0)

    @app.delete("/domains/{name}")
    def delete_domain(name: str, user: UserOut = Depends(require_role("admin", "owner"))):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT 1 FROM app.domains WHERE name=%s", (name,))
            if not row:
                raise HTTPException(404, "Domain not found")
            exec1(conn, "UPDATE app.domains SET is_archived=true WHERE name=%s", (name,))
            conn.commit()
        return {"ok": True}

    @app.post("/sources", response_model=SourceOut)
    def create_source(payload: SourceIn, user: UserOut = Depends(require_role("admin", "owner"))):
        code = (payload.code or "").strip().lower()
        name = (payload.name or "").strip()
        if not code or not name:
            raise HTTPException(400, "Source code and name are required")
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                """
                INSERT INTO app.sources(code, name, is_archived)
                VALUES (%s, %s, false)
                RETURNING source_id, code, name
                """,
                (code, name),
            )
            conn.commit()
        if not row:
            raise HTTPException(500, "Failed to create source")
        return SourceOut(source_id=int(row[0]), code=row[1], name=row[2])

    @app.put("/sources/{source_id}", response_model=SourceOut)
    def update_source(source_id: int, payload: SourceUpdate, user: UserOut = Depends(require_role("admin", "owner"))):
        code = (payload.code or "").strip().lower() if payload.code is not None else None
        name = (payload.name or "").strip() if payload.name is not None else None
        if code is not None and not code:
            raise HTTPException(400, "Source code is required")
        if name is not None and not name:
            raise HTTPException(400, "Name is required")
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT code, name FROM app.sources WHERE source_id=%s AND is_archived IS NOT TRUE", (source_id,))
            if not row:
                raise HTTPException(404, "Source not found")
            new_code = code if code is not None else row[0]
            new_name = name if name is not None else row[1]
            exec1(conn, "UPDATE app.sources SET code=%s, name=%s WHERE source_id=%s", (new_code, new_name, source_id))
            conn.commit()
        return SourceOut(source_id=source_id, code=new_code, name=new_name)

    @app.delete("/sources/{source_id}")
    def delete_source(source_id: int, user: UserOut = Depends(require_role("admin", "owner"))):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT 1 FROM app.sources WHERE source_id=%s", (source_id,))
            if not row:
                raise HTTPException(404, "Source not found")
            exec1(conn, "UPDATE app.sources SET is_archived=true WHERE source_id=%s", (source_id,))
            conn.commit()
        return {"ok": True}

    @app.post("/messengers", response_model=MessengerOut)
    def create_messenger(payload: MessengerIn, user: UserOut = Depends(require_role("admin", "owner"))):
        code = (payload.code or "").strip().lower()
        name = (payload.name or "").strip()
        if not code or not name:
            raise HTTPException(400, "Messenger code and name are required")
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                """
                INSERT INTO app.messengers(code, name, is_archived)
                VALUES (%s, %s, false)
                RETURNING messenger_id, code, name
                """,
                (code, name),
            )
            conn.commit()
        if not row:
            raise HTTPException(500, "Failed to create messenger")
        return MessengerOut(messenger_id=int(row[0]), code=row[1], name=row[2])

    @app.put("/messengers/{messenger_id}", response_model=MessengerOut)
    def update_messenger(messenger_id: int, payload: MessengerUpdate, user: UserOut = Depends(require_role("admin", "owner"))):
        code = (payload.code or "").strip().lower() if payload.code is not None else None
        name = (payload.name or "").strip() if payload.name is not None else None
        if code is not None and not code:
            raise HTTPException(400, "Messenger code is required")
        if name is not None and not name:
            raise HTTPException(400, "Name is required")
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                "SELECT code, name FROM app.messengers WHERE messenger_id=%s AND is_archived IS NOT TRUE",
                (messenger_id,),
            )
            if not row:
                raise HTTPException(404, "Messenger not found")
            new_code = code if code is not None else row[0]
            new_name = name if name is not None else row[1]
            exec1(conn, "UPDATE app.messengers SET code=%s, name=%s WHERE messenger_id=%s", (new_code, new_name, messenger_id))
            conn.commit()
        return MessengerOut(messenger_id=messenger_id, code=new_code, name=new_name)

    @app.delete("/messengers/{messenger_id}")
    def delete_messenger(messenger_id: int, user: UserOut = Depends(require_role("admin", "owner"))):
        with psycopg.connect(DB_DSN) as conn:
            row = q1(conn, "SELECT 1 FROM app.messengers WHERE messenger_id=%s", (messenger_id,))
            if not row:
                raise HTTPException(404, "Messenger not found")
            exec1(conn, "UPDATE app.messengers SET is_archived=true WHERE messenger_id=%s", (messenger_id,))
            conn.commit()
        return {"ok": True}
