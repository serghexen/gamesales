from fastapi import Depends, HTTPException


def mount_auth_routes(
    app,
    *,
    DB_DSN,
    psycopg,
    q1,
    qall,
    exec1,
    init_auth_schema,
    ensure_admin_user,
    get_user_by_username,
    verify_password,
    hash_password,
    create_access_token,
    role_exists,
    get_current_user,
    require_role,
    LoginIn,
    LoginOut,
    UserOut,
    ChangePasswordIn,
    RoleOut,
    UserListOut,
    UserCreate,
    ResetPasswordIn,
):
    @app.post("/auth/login", response_model=LoginOut)
    def login(payload: LoginIn):
        with psycopg.connect(DB_DSN) as conn:
            # На логине не запускаем DDL, чтобы не зависеть от состояния миграций и не ронять коннект к БД.
            ensure_admin_user(conn)
            row = get_user_by_username(conn, payload.username)
            if not row:
                raise HTTPException(401, "Invalid credentials")
            user_id, username, password_hash, role = row
            if not verify_password(payload.password, password_hash):
                raise HTTPException(401, "Invalid credentials")
            token = create_access_token(int(user_id), str(username), str(role))
            return LoginOut(access_token=token, user=UserOut(username=str(username), role=str(role)))

    @app.get("/auth/me", response_model=UserOut)
    def me(user: UserOut = Depends(get_current_user)):
        return user

    @app.post("/auth/change-password")
    def change_password(payload: ChangePasswordIn, user: UserOut = Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            row = get_user_by_username(conn, user.username)
            if not row:
                raise HTTPException(404, "User not found")
            user_id, username, password_hash, role = row
            if not verify_password(payload.current_password, password_hash):
                raise HTTPException(401, "Invalid credentials")
            new_hash = hash_password(payload.new_password)
            exec1(
                conn,
                "UPDATE app.users SET password_hash=%s WHERE user_id=%s",
                (new_hash, user_id),
            )
            conn.commit()
        return {"ok": True}

    @app.get("/user-roles", response_model=list[RoleOut])
    def list_roles(user: UserOut = Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(conn, "SELECT code, name FROM app.user_roles ORDER BY code")
        return [RoleOut(code=r0, name=r1) for (r0, r1) in rows]

    @app.get("/users", response_model=list[UserListOut])
    def list_users(user: UserOut = Depends(get_current_user)):
        with psycopg.connect(DB_DSN) as conn:
            # Для обычных пользователей скрываем системные роли admin/owner из списка ответственных.
            can_view_all = (user.role in ("admin", "owner")) or (user.username in ("admin", "owner"))
            if can_view_all:
                rows = qall(conn, "SELECT username, name, role_code, created_at FROM app.users ORDER BY user_id")
            else:
                rows = qall(
                    conn,
                    """
                    SELECT username, name, role_code, created_at
                    FROM app.users
                    WHERE lower(role_code) NOT IN ('admin', 'owner')
                    ORDER BY user_id
                    """,
                )
        return [UserListOut(username=r0, name=(r1 or ""), role=r2, created_at=r3) for (r0, r1, r2, r3) in rows]

    @app.post("/users", response_model=UserOut)
    def create_user(payload: UserCreate, user: UserOut = Depends(require_role("admin"))):
        with psycopg.connect(DB_DSN) as conn:
            if not role_exists(conn, payload.role_code):
                raise HTTPException(400, "Unknown role")
            row = get_user_by_username(conn, payload.username)
            if row:
                raise HTTPException(409, "User already exists")
            password_hash = hash_password(payload.password)
            exec1(
                conn,
                "INSERT INTO app.users(username, password_hash, role_code) VALUES (%s, %s, %s)",
                (payload.username, password_hash, payload.role_code),
            )
            conn.commit()
        return UserOut(username=payload.username, role=payload.role_code)

    @app.post("/users/{username}/password")
    def reset_password(username: str, payload: ResetPasswordIn, user: UserOut = Depends(require_role("admin"))):
        with psycopg.connect(DB_DSN) as conn:
            row = get_user_by_username(conn, username)
            if not row:
                raise HTTPException(404, "User not found")
            user_id = int(row[0])
            new_hash = hash_password(payload.new_password)
            exec1(
                conn,
                "UPDATE app.users SET password_hash=%s WHERE user_id=%s",
                (new_hash, user_id),
            )
            conn.commit()
        return {"ok": True}
