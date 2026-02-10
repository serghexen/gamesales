from dataclasses import dataclass
import base64
import hashlib
import hmac
import os
from typing import Callable

import jwt
from fastapi import Depends, Header, HTTPException


@dataclass
class AuthService:
    hash_password: Callable[[str], str]
    verify_password: Callable[[str, str], bool]
    init_auth_schema: Callable[[object], None]
    get_user_by_username: Callable[[object, str], tuple | None]
    get_user_id: Callable[[object, str], int]
    role_exists: Callable[[object, str], bool]
    ensure_admin_user: Callable[[object], None]
    create_access_token: Callable[[int, str, str], str]
    get_current_user: Callable[[str | None], object]
    require_role: Callable[..., Callable[[object], object]]


def build_auth_service(
    *,
    q1,
    exec1,
    now_utc,
    UserOut,
    get_jwt_secret,
    get_jwt_alg,
    get_jwt_ttl_min,
    get_pwd_scheme,
    get_pwd_iterations,
    get_pwd_salt_bytes,
) -> AuthService:
    def b64url_encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")

    def b64url_decode(value: str) -> bytes:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

    def legacy_passlib_b64_decode(value: str) -> bytes:
        normalized = value.replace(".", "+")
        return base64.b64decode(normalized + "=" * (-len(normalized) % 4))

    def hash_password(raw_password: str) -> str:
        salt = os.urandom(get_pwd_salt_bytes())
        digest = hashlib.pbkdf2_hmac("sha256", raw_password.encode("utf-8"), salt, get_pwd_iterations())
        return f"{get_pwd_scheme()}${get_pwd_iterations()}${b64url_encode(salt)}${b64url_encode(digest)}"

    def verify_current_password(raw_password: str, password_hash: str) -> bool:
        try:
            scheme, iterations_text, salt_b64, digest_b64 = password_hash.split("$", 3)
            if scheme != get_pwd_scheme():
                return False
            iterations = int(iterations_text)
            salt = b64url_decode(salt_b64)
            expected = b64url_decode(digest_b64)
        except Exception:
            return False

        calculated = hashlib.pbkdf2_hmac("sha256", raw_password.encode("utf-8"), salt, iterations, dklen=len(expected))
        return hmac.compare_digest(calculated, expected)

    def verify_legacy_passlib_password(raw_password: str, password_hash: str) -> bool:
        if not password_hash.startswith("$pbkdf2-sha256$"):
            return False
        try:
            _, _, rounds_text, salt_raw, digest_raw = password_hash.split("$", 4)
            rounds = int(rounds_text)
            salt = legacy_passlib_b64_decode(salt_raw)
            expected = legacy_passlib_b64_decode(digest_raw)
        except Exception:
            return False
        calculated = hashlib.pbkdf2_hmac("sha256", raw_password.encode("utf-8"), salt, rounds, dklen=len(expected))
        return hmac.compare_digest(calculated, expected)

    def verify_password(raw_password: str, password_hash: str) -> bool:
        return verify_current_password(raw_password, password_hash) or verify_legacy_passlib_password(raw_password, password_hash)

    def get_user_by_username(conn, username: str):
        return q1(
            conn,
            "SELECT user_id, username, password_hash, role_code FROM app.users WHERE username=%s",
            (username,),
        )

    def get_user_id(conn, username: str) -> int:
        row = get_user_by_username(conn, username)
        if not row:
            raise HTTPException(404, "User not found")
        return int(row[0])

    def role_exists(conn, role_code: str) -> bool:
        row = q1(conn, "SELECT 1 FROM app.user_roles WHERE code=%s", (role_code,))
        return bool(row)

    def init_auth_schema(conn):
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS app.user_roles (
                  code text PRIMARY KEY,
                  name text NOT NULL
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS app.users (
                  user_id bigserial PRIMARY KEY,
                  username text NOT NULL UNIQUE,
                  password_hash text NOT NULL,
                  role_code text NOT NULL DEFAULT 'manager' REFERENCES app.user_roles(code),
                  created_at timestamptz NOT NULL DEFAULT now()
                );
                """
            )
            # Поддерживает новые инсталляции и старые БД, где столбца name еще нет.
            cur.execute("ALTER TABLE app.users ADD COLUMN IF NOT EXISTS name text NOT NULL DEFAULT ''")
            cur.execute(
                """
                INSERT INTO app.user_roles(code, name)
                VALUES ('admin','Admin'),('manager','Manager')
                ON CONFLICT (code) DO NOTHING;
                """
            )
            conn.commit()

    def ensure_admin_user(conn):
        admin_username = os.getenv("ADMIN_USERNAME")
        admin_password = os.getenv("ADMIN_PASSWORD")
        admin_role = os.getenv("ADMIN_ROLE", "admin")
        if not admin_username or not admin_password:
            return
        if not role_exists(conn, admin_role):
            exec1(
                conn,
                "INSERT INTO app.user_roles(code, name) VALUES (%s, %s) ON CONFLICT (code) DO NOTHING",
                (admin_role, admin_role.title()),
            )
        row = get_user_by_username(conn, admin_username)
        if row:
            return
        password_hash = hash_password(admin_password)
        exec1(
            conn,
            "INSERT INTO app.users(username, password_hash, role_code) VALUES (%s, %s, %s)",
            (admin_username, password_hash, admin_role),
        )
        conn.commit()

    def create_access_token(user_id: int, username: str, role: str):
        secret = get_jwt_secret()
        alg = get_jwt_alg()
        if not secret:
            raise HTTPException(500, "JWT_SECRET is not set")
        exp = int((now_utc().timestamp()) + get_jwt_ttl_min() * 60)
        payload = {"sub": str(user_id), "username": username, "role": role, "exp": exp}
        return jwt.encode(payload, secret, algorithm=alg)

    def get_current_user(authorization: str = Header(None)) -> UserOut:
        secret = get_jwt_secret()
        alg = get_jwt_alg()
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Missing bearer token")
        token = authorization.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(token, secret, algorithms=[alg])
        except Exception:
            raise HTTPException(401, "Invalid token")
        return UserOut(username=payload.get("username"), role=payload.get("role"))

    def require_role(*roles):
        def _dep(user: UserOut = Depends(get_current_user)) -> UserOut:
            if user.role not in roles:
                raise HTTPException(403, "Forbidden")
            return user
        return _dep

    return AuthService(
        hash_password=hash_password,
        verify_password=verify_password,
        init_auth_schema=init_auth_schema,
        get_user_by_username=get_user_by_username,
        get_user_id=get_user_id,
        role_exists=role_exists,
        ensure_admin_user=ensure_admin_user,
        create_access_token=create_access_token,
        get_current_user=get_current_user,
        require_role=require_role,
    )
