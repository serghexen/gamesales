from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import psycopg
import os
from dotenv import load_dotenv
from pathlib import Path
import jwt
from passlib.context import CryptContext
import base64

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env.dev", override=True)

app = FastAPI(title="GameSales API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compose service name: "postgres"
DB_DSN = os.getenv(
    "DATABASE_URL",
    "postgresql://gamesales_app:najTylth1@postgres:5432/gamesales",
)

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
JWT_TTL_MIN = int(os.getenv("JWT_TTL_MIN", "720"))

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def now_utc():
    return datetime.now(timezone.utc)

# ----------------------------
# Models
# ----------------------------
class AccountCreate(BaseModel):
    nickname: str
    platform_code: str = Field(..., description="steam/psn/xbox/epic")
    region_code: Optional[str] = Field(None, description="RU/TR/US/EU")
    login_name: Optional[str] = None
    domain_code: Optional[str] = Field(None, description="email domain, e.g. example.com")
    slot_capacity: int = 1
    slot_reserved: int = 0
    notes: Optional[str] = None

class AccountOut(BaseModel):
    account_id: int
    nickname: str
    platform_code: str
    region_code: Optional[str]
    status: str
    login_name: Optional[str]
    domain_code: Optional[str]
    login_full: Optional[str]
    slot_capacity: int
    slot_reserved: int
    occupied_slots: int
    free_slots: int

class GameCreate(BaseModel):
    title: str
    platform_code: Optional[str] = None
    region_code: Optional[str] = None

class GameOut(BaseModel):
    game_id: int
    title: str
    platform_code: Optional[str]
    region_code: Optional[str]

class PlatformOut(BaseModel):
    code: str
    name: str

class RegionOut(BaseModel):
    code: str
    name: str

class RentalCreate(BaseModel):
    account_id: int
    customer_nickname: str
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    slots_used: int = 1
    price: float = 0

class LoginIn(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    username: str
    role: str

class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class UserCreate(BaseModel):
    username: str
    password: str
    role_code: str = "manager"

class UserListOut(BaseModel):
    username: str
    role: str
    created_at: datetime

class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str

class ResetPasswordIn(BaseModel):
    new_password: str

class RoleOut(BaseModel):
    code: str
    name: str

class AccountSecretIn(BaseModel):
    secret_key: str
    secret_value: str

class AccountSecretOut(BaseModel):
    secret_key: str
    secret_value_b64: str
    created_at: datetime

# ----------------------------
# DB helpers
# ----------------------------
def q1(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        row = cur.fetchone()
        return row

def qall(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()

def exec1(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.rowcount

def get_platform_id(conn, code: str) -> int:
    row = q1(conn, "SELECT platform_id FROM app.platforms WHERE code=%s", (code,))
    if not row:
        raise HTTPException(400, f"Unknown platform_code: {code}")
    return int(row[0])

def get_region_id(conn, code: Optional[str]) -> Optional[int]:
    if not code:
        return None
    row = q1(conn, "SELECT region_id FROM app.regions WHERE code=%s", (code,))
    if not row:
        raise HTTPException(400, f"Unknown region_code: {code}")
    return int(row[0])

def get_domain_id(conn, code: Optional[str]) -> Optional[int]:
    if not code:
        return None
    row = q1(conn, "SELECT domain_id FROM app.domains WHERE name=%s", (code,))
    if not row:
        raise HTTPException(400, f"Unknown domain: {code}")
    return int(row[0])

def slots_summary(conn, account_id: int):
    row = q1(conn, "SELECT occupied_slots, free_slots FROM app.v_account_slots WHERE account_id=%s", (account_id,))
    if not row:
        return (0, 0)
    return int(row[0]), int(row[1])

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
        cur.execute(
            """
            INSERT INTO app.user_roles(code, name)
            VALUES ('admin','Admin'),('manager','Manager')
            ON CONFLICT (code) DO NOTHING;
            """
        )
        conn.commit()

def get_user_by_username(conn, username: str):
    return q1(
        conn,
        "SELECT user_id, username, password_hash, role_code FROM app.users WHERE username=%s",
        (username,),
    )

def role_exists(conn, role_code: str) -> bool:
    row = q1(conn, "SELECT 1 FROM app.user_roles WHERE code=%s", (role_code,))
    return bool(row)

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
    password_hash = pwd_context.hash(admin_password)
    exec1(
        conn,
        "INSERT INTO app.users(username, password_hash, role_code) VALUES (%s, %s, %s)",
        (admin_username, password_hash, admin_role),
    )
    conn.commit()

def create_access_token(user_id: int, username: str, role: str):
    if not JWT_SECRET:
        raise HTTPException(500, "JWT_SECRET is not set")
    exp = int((now_utc().timestamp()) + JWT_TTL_MIN * 60)
    payload = {"sub": str(user_id), "username": username, "role": role, "exp": exp}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def get_current_user(authorization: str = Header(None)) -> UserOut:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        raise HTTPException(401, "Invalid token")
    return UserOut(username=payload.get("username"), role=payload.get("role"))

def b64_encode(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("utf-8")

def require_role(*roles):
    def _dep(user: UserOut = Depends(get_current_user)) -> UserOut:
        if user.role not in roles:
            raise HTTPException(403, "Forbidden")
        return user
    return _dep

# ----------------------------
# Endpoints
# ----------------------------
@app.get("/health")
def health():
    with psycopg.connect(DB_DSN) as conn:
        init_auth_schema(conn)
        ensure_admin_user(conn)
        v = q1(conn, "SELECT 1")
    return {"ok": True}

@app.post("/auth/login", response_model=LoginOut)
def login(payload: LoginIn):
    with psycopg.connect(DB_DSN) as conn:
        init_auth_schema(conn)
        ensure_admin_user(conn)
        row = get_user_by_username(conn, payload.username)
        if not row:
            raise HTTPException(401, "Invalid credentials")
        user_id, username, password_hash, role = row
        if not pwd_context.verify(payload.password, password_hash):
            raise HTTPException(401, "Invalid credentials")
        token = create_access_token(int(user_id), str(username), str(role))
        return LoginOut(access_token=token, user=UserOut(username=str(username), role=str(role)))

@app.get("/auth/me", response_model=UserOut)
def me(user: UserOut = Depends(get_current_user)):
    return user

@app.get("/platforms", response_model=List[PlatformOut])
def list_platforms(user: UserOut = Depends(get_current_user)):
    with psycopg.connect(DB_DSN) as conn:
        rows = qall(conn, "SELECT code, name FROM app.platforms ORDER BY code")
    return [PlatformOut(code=r0, name=r1) for (r0, r1) in rows]

@app.get("/regions", response_model=List[RegionOut])
def list_regions(user: UserOut = Depends(get_current_user)):
    with psycopg.connect(DB_DSN) as conn:
        rows = qall(conn, "SELECT code, name FROM app.regions ORDER BY code")
    return [RegionOut(code=r0, name=r1) for (r0, r1) in rows]

@app.get("/domains", response_model=List[PlatformOut])
def list_domains(user: UserOut = Depends(get_current_user)):
    with psycopg.connect(DB_DSN) as conn:
        rows = qall(conn, "SELECT name, name FROM app.domains ORDER BY name")
    return [PlatformOut(code=r0, name=r1) for (r0, r1) in rows]

@app.get("/sources", response_model=List[PlatformOut])
def list_sources(user: UserOut = Depends(get_current_user)):
    with psycopg.connect(DB_DSN) as conn:
        rows = qall(conn, "SELECT code, name FROM app.sources ORDER BY code")
    return [PlatformOut(code=r0, name=r1) for (r0, r1) in rows]

@app.post("/auth/change-password")
def change_password(payload: ChangePasswordIn, user: UserOut = Depends(get_current_user)):
    with psycopg.connect(DB_DSN) as conn:
        row = get_user_by_username(conn, user.username)
        if not row:
            raise HTTPException(404, "User not found")
        user_id, username, password_hash, role = row
        if not pwd_context.verify(payload.current_password, password_hash):
            raise HTTPException(401, "Invalid credentials")
        new_hash = pwd_context.hash(payload.new_password)
        exec1(
            conn,
            "UPDATE app.users SET password_hash=%s WHERE user_id=%s",
            (new_hash, user_id),
        )
        conn.commit()
    return {"ok": True}

@app.get("/user-roles", response_model=List[RoleOut])
def list_roles(user: UserOut = Depends(get_current_user)):
    with psycopg.connect(DB_DSN) as conn:
        rows = qall(conn, "SELECT code, name FROM app.user_roles ORDER BY code")
    return [RoleOut(code=r0, name=r1) for (r0, r1) in rows]

@app.get("/users", response_model=List[UserListOut])
def list_users(user: UserOut = Depends(require_role("admin"))):
    with psycopg.connect(DB_DSN) as conn:
        rows = qall(conn, "SELECT username, role_code, created_at FROM app.users ORDER BY user_id")
    return [UserListOut(username=r0, role=r1, created_at=r2) for (r0, r1, r2) in rows]

@app.post("/users", response_model=UserOut)
def create_user(payload: UserCreate, user: UserOut = Depends(require_role("admin"))):
    with psycopg.connect(DB_DSN) as conn:
        if not role_exists(conn, payload.role_code):
            raise HTTPException(400, "Unknown role")
        row = get_user_by_username(conn, payload.username)
        if row:
            raise HTTPException(409, "User already exists")
        password_hash = pwd_context.hash(payload.password)
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
        new_hash = pwd_context.hash(payload.new_password)
        exec1(
            conn,
            "UPDATE app.users SET password_hash=%s WHERE user_id=%s",
            (new_hash, user_id),
        )
        conn.commit()
    return {"ok": True}

@app.get("/accounts", response_model=List[AccountOut])
def list_accounts(user: UserOut = Depends(get_current_user)):
    with psycopg.connect(DB_DSN) as conn:
        rows = qall(conn, """
            SELECT
              a.account_id,
              a.nickname,
              p.code as platform_code,
              r.code as region_code,
              a.status_code,
              a.login_name,
              d.name as domain_name,
              a.slot_capacity,
              a.slot_reserved,
              s.occupied_slots,
              s.free_slots
            FROM app.accounts a
            JOIN app.platforms p ON p.platform_id = a.platform_id
            LEFT JOIN app.regions r ON r.region_id = a.region_id
            LEFT JOIN app.domains d ON d.domain_id = a.domain_id
            LEFT JOIN app.v_account_slots s ON s.account_id = a.account_id
            ORDER BY a.account_id DESC
            LIMIT 200
        """)
    return [
        AccountOut(
            account_id=row[0], nickname=row[1], platform_code=row[2], region_code=row[3],
            status=row[4], login_name=row[5], domain_code=row[6],
            login_full=f"{row[5]}@{row[6]}" if row[5] and row[6] else None,
            slot_capacity=row[7], slot_reserved=row[8],
            occupied_slots=row[9] or 0, free_slots=row[10] or 0
        )
        for row in rows
    ]

@app.post("/accounts", response_model=AccountOut)
def create_account(payload: AccountCreate, user: UserOut = Depends(get_current_user)):
    if payload.slot_capacity < payload.slot_reserved:
        raise HTTPException(400, "slot_capacity must be >= slot_reserved")
    with psycopg.connect(DB_DSN) as conn:
        platform_id = get_platform_id(conn, payload.platform_code)
        region_id = get_region_id(conn, payload.region_code)
        domain_id = get_domain_id(conn, payload.domain_code)

        row = q1(conn, """
            INSERT INTO app.accounts(nickname, login_name, domain_id, platform_id, region_id, slot_capacity, slot_reserved, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING account_id
        """, (
            payload.nickname, payload.login_name, domain_id,
            platform_id, region_id, payload.slot_capacity, payload.slot_reserved, payload.notes
        ))
        account_id = int(row[0])
        conn.commit()

        occ, free = slots_summary(conn, account_id)
        return AccountOut(
            account_id=account_id,
            nickname=payload.nickname,
            platform_code=payload.platform_code,
            region_code=payload.region_code,
            status="active",
            login_name=payload.login_name,
            domain_code=payload.domain_code,
            login_full=f"{payload.login_name}@{payload.domain_code}" if payload.login_name and payload.domain_code else None,
            slot_capacity=payload.slot_capacity,
            slot_reserved=payload.slot_reserved,
            occupied_slots=occ,
            free_slots=free
        )

@app.get("/accounts/{account_id}/secrets", response_model=List[AccountSecretOut])
def list_account_secrets(account_id: int, user: UserOut = Depends(require_role("admin"))):
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

@app.post("/accounts/{account_id}/secrets", response_model=AccountSecretOut)
def upsert_account_secret(
    account_id: int,
    payload: AccountSecretIn,
    user: UserOut = Depends(require_role("admin")),
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

@app.get("/games", response_model=List[GameOut])
def list_games(q: Optional[str] = None, user: UserOut = Depends(get_current_user)):
    with psycopg.connect(DB_DSN) as conn:
        if q:
            rows = qall(conn, """
                SELECT g.game_id, g.title, p.code, r.code
                FROM app.game_titles g
                LEFT JOIN app.platforms p ON p.platform_id = g.platform_id
                LEFT JOIN app.regions r ON r.region_id = g.region_id
                WHERE g.title ILIKE %s
                ORDER BY g.game_id DESC
                LIMIT 200
            """, (f"%{q}%",))
        else:
            rows = qall(conn, """
                SELECT g.game_id, g.title, p.code, r.code
                FROM app.game_titles g
                LEFT JOIN app.platforms p ON p.platform_id = g.platform_id
                LEFT JOIN app.regions r ON r.region_id = g.region_id
                ORDER BY g.game_id DESC
                LIMIT 200
            """)
    return [GameOut(game_id=r0, title=r1, platform_code=r2, region_code=r3) for (r0, r1, r2, r3) in rows]

@app.post("/games", response_model=GameOut)
def create_game(payload: GameCreate, user: UserOut = Depends(get_current_user)):
    with psycopg.connect(DB_DSN) as conn:
        platform_id = get_platform_id(conn, payload.platform_code) if payload.platform_code else None
        region_id = get_region_id(conn, payload.region_code)

        row = q1(conn, """
            INSERT INTO app.game_titles(title, platform_id, region_id)
            VALUES (%s, %s, %s)
            RETURNING game_id
        """, (payload.title, platform_id, region_id))
        gid = int(row[0])
        conn.commit()

    return GameOut(game_id=gid, title=payload.title, platform_code=payload.platform_code, region_code=payload.region_code)

@app.post("/rentals")
def create_rental(payload: RentalCreate, user: UserOut = Depends(get_current_user)):
    if payload.slots_used <= 0:
        raise HTTPException(400, "slots_used must be >= 1")

    start_at = payload.start_at or now_utc()
    end_at = payload.end_at

    with psycopg.connect(DB_DSN) as conn:
        # ensure customer exists
        row = q1(conn, "SELECT customer_id FROM app.customers WHERE nickname=%s", (payload.customer_nickname,))
        if row:
            customer_id = int(row[0])
        else:
            row = q1(conn, "INSERT INTO app.customers(nickname) VALUES (%s) RETURNING customer_id", (payload.customer_nickname,))
            customer_id = int(row[0])

        # check slots
        occ, free = slots_summary(conn, payload.account_id)
        if free < payload.slots_used:
            raise HTTPException(409, f"Not enough free slots. free_slots={free}, requested={payload.slots_used}")

        # create deal + item
        deal_row = q1(conn, """
            INSERT INTO app.deals(deal_type_code, status_code, customer_id, currency, total_amount)
            VALUES ('rental', 'confirmed', %s, 'RUB', %s)
            RETURNING deal_id
        """, (customer_id, payload.price))
        deal_id = int(deal_row[0])

        q1(conn, """
            INSERT INTO app.deal_items(deal_id, account_id, qty, price, start_at, end_at, slots_used)
            VALUES (%s, %s, 1, %s, %s, %s, %s)
            RETURNING deal_item_id
        """, (deal_id, payload.account_id, payload.price, start_at, end_at, payload.slots_used))

        conn.commit()

        # return updated slots
        occ2, free2 = slots_summary(conn, payload.account_id)
        return {"deal_id": deal_id, "account_id": payload.account_id, "occupied_slots": occ2, "free_slots": free2}
