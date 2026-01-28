from datetime import datetime, timezone
from typing import Optional, List, Tuple

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
    platform_code: str = Field(..., description="steam/psn/xbox/epic")
    region_code: Optional[str] = Field(None, description="RU/TR/US/EU")
    login_name: Optional[str] = None
    domain_code: Optional[str] = Field(None, description="email domain, e.g. example.com")
    slot_capacity: int = 1
    slot_reserved: int = 0
    notes: Optional[str] = None

class AccountUpdate(BaseModel):
    platform_code: Optional[str] = None
    region_code: Optional[str] = None
    login_name: Optional[str] = None
    domain_code: Optional[str] = None
    status_code: Optional[str] = None
    slot_capacity: Optional[int] = None
    slot_reserved: Optional[int] = None
    notes: Optional[str] = None

class AccountOut(BaseModel):
    account_id: int
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
    notes: Optional[str] = None

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

class PlatformIn(BaseModel):
    code: str
    name: str

class RegionIn(BaseModel):
    code: str
    name: str

class RentalCreate(BaseModel):
    account_id: int
    customer_nickname: str
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    slots_used: int = 1
    price: float = 0
    game_id: Optional[int] = None
    platform_code: Optional[str] = None
    source_code: Optional[str] = None
    purchase_at: Optional[datetime] = None

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

class DealCreate(BaseModel):
    deal_type_code: str = Field(..., description="sale/rental")
    account_id: int
    game_id: Optional[int] = None
    customer_nickname: str
    source_code: Optional[str] = None
    platform_code: Optional[str] = None
    price: float = 0
    purchase_at: Optional[datetime] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    slots_used: int = 1
    notes: Optional[str] = None

class DealListItem(BaseModel):
    deal_id: int
    deal_type: str
    status: str
    account_id: int
    account_login: Optional[str]
    game_id: Optional[int]
    game_title: Optional[str]
    platform_code: Optional[str]
    customer_nickname: Optional[str]
    source_code: Optional[str]
    price: float
    purchase_at: Optional[datetime]
    created_at: datetime

class DealListOut(BaseModel):
    total: int
    items: List[DealListItem]

class DomainIn(BaseModel):
    name: str

class SourceIn(BaseModel):
    code: str
    name: str

class NameUpdate(BaseModel):
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

def get_platform_id_optional(conn, code: Optional[str]) -> Optional[int]:
    if not code:
        return None
    row = q1(conn, "SELECT platform_id FROM app.platforms WHERE code=%s", (code,))
    if not row:
        raise HTTPException(400, f"Unknown platform_code: {code}")
    return int(row[0])

def ensure_account_exists(conn, account_id: int):
    row = q1(conn, "SELECT 1 FROM app.accounts WHERE account_id=%s", (account_id,))
    if not row:
        raise HTTPException(400, f"Unknown account_id: {account_id}")

def ensure_game_exists(conn, game_id: Optional[int]):
    if not game_id:
        return
    row = q1(conn, "SELECT 1 FROM app.game_titles WHERE game_id=%s", (game_id,))
    if not row:
        raise HTTPException(400, f"Unknown game_id: {game_id}")

def ensure_source_exists(conn, code: Optional[str]):
    if not code:
        return
    row = q1(conn, "SELECT 1 FROM app.sources WHERE code=%s", (code,))
    if not row:
        raise HTTPException(400, f"Unknown source_code: {code}")

def build_deals_filters(
    account_id: Optional[int],
    game_id: Optional[int],
    platform_code: Optional[str],
    q: Optional[str],
) -> Tuple[str, List]:
    where = []
    params: List = []
    if account_id:
        where.append("di.account_id = %s")
        params.append(account_id)
    if game_id:
        where.append("di.game_id = %s")
        params.append(game_id)
    if platform_code:
        where.append("p.code = %s")
        params.append(platform_code)
    if q:
        where.append("(g.title ILIKE %s OR a.login_name ILIKE %s OR c.nickname ILIKE %s)")
        like = f"%{q}%"
        params.extend([like, like, like])
    where_sql = "WHERE " + " AND ".join(where) if where else ""
    return where_sql, params

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

@app.post("/platforms", response_model=PlatformOut)
def create_platform(payload: PlatformIn, user: UserOut = Depends(require_role("admin"))):
    code = (payload.code or "").strip().lower()
    name = (payload.name or "").strip()
    if not code or not name:
        raise HTTPException(400, "Platform code and name are required")
    with psycopg.connect(DB_DSN) as conn:
        exec1(
            conn,
            "INSERT INTO app.platforms(code, name) VALUES (%s, %s) ON CONFLICT (code) DO NOTHING",
            (code, name),
        )
        conn.commit()
    return PlatformOut(code=code, name=name)

@app.put("/platforms/{code}", response_model=PlatformOut)
def update_platform(code: str, payload: NameUpdate, user: UserOut = Depends(require_role("admin"))):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(400, "Name is required")
    with psycopg.connect(DB_DSN) as conn:
        exec1(conn, "UPDATE app.platforms SET name=%s WHERE code=%s", (name, code))
        conn.commit()
    return PlatformOut(code=code, name=name)

@app.delete("/platforms/{code}")
def delete_platform(code: str, user: UserOut = Depends(require_role("admin"))):
    with psycopg.connect(DB_DSN) as conn:
        try:
            exec1(conn, "DELETE FROM app.platforms WHERE code=%s", (code,))
            conn.commit()
        except Exception:
            raise HTTPException(409, "Platform is in use")
    return {"ok": True}

@app.post("/regions", response_model=RegionOut)
def create_region(payload: RegionIn, user: UserOut = Depends(require_role("admin"))):
    code = (payload.code or "").strip().upper()
    name = (payload.name or "").strip()
    if not code or not name:
        raise HTTPException(400, "Region code and name are required")
    with psycopg.connect(DB_DSN) as conn:
        exec1(
            conn,
            "INSERT INTO app.regions(code, name) VALUES (%s, %s) ON CONFLICT (code) DO NOTHING",
            (code, name),
        )
        conn.commit()
    return RegionOut(code=code, name=name)

@app.put("/regions/{code}", response_model=RegionOut)
def update_region(code: str, payload: NameUpdate, user: UserOut = Depends(require_role("admin"))):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(400, "Name is required")
    with psycopg.connect(DB_DSN) as conn:
        exec1(conn, "UPDATE app.regions SET name=%s WHERE code=%s", (name, code))
        conn.commit()
    return RegionOut(code=code, name=name)

@app.delete("/regions/{code}")
def delete_region(code: str, user: UserOut = Depends(require_role("admin"))):
    with psycopg.connect(DB_DSN) as conn:
        try:
            exec1(conn, "DELETE FROM app.regions WHERE code=%s", (code,))
            conn.commit()
        except Exception:
            raise HTTPException(409, "Region is in use")
    return {"ok": True}

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

@app.post("/domains", response_model=PlatformOut)
def create_domain(payload: DomainIn, user: UserOut = Depends(require_role("admin"))):
    name = (payload.name or "").strip().lower()
    if not name:
        raise HTTPException(400, "Domain name is required")
    with psycopg.connect(DB_DSN) as conn:
        exec1(
            conn,
            "INSERT INTO app.domains(name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
            (name,),
        )
        conn.commit()
    return PlatformOut(code=name, name=name)

@app.put("/domains/{name}", response_model=PlatformOut)
def update_domain(name: str, payload: NameUpdate, user: UserOut = Depends(require_role("admin"))):
    new_name = (payload.name or "").strip().lower()
    if not new_name:
        raise HTTPException(400, "Name is required")
    with psycopg.connect(DB_DSN) as conn:
        exec1(conn, "UPDATE app.domains SET name=%s WHERE name=%s", (new_name, name))
        conn.commit()
    return PlatformOut(code=new_name, name=new_name)

@app.delete("/domains/{name}")
def delete_domain(name: str, user: UserOut = Depends(require_role("admin"))):
    with psycopg.connect(DB_DSN) as conn:
        try:
            exec1(conn, "DELETE FROM app.domains WHERE name=%s", (name,))
            conn.commit()
        except Exception:
            raise HTTPException(409, "Domain is in use")
    return {"ok": True}

@app.post("/sources", response_model=PlatformOut)
def create_source(payload: SourceIn, user: UserOut = Depends(require_role("admin"))):
    code = (payload.code or "").strip().lower()
    name = (payload.name or "").strip()
    if not code or not name:
        raise HTTPException(400, "Source code and name are required")
    with psycopg.connect(DB_DSN) as conn:
        exec1(
            conn,
            "INSERT INTO app.sources(code, name) VALUES (%s, %s) ON CONFLICT (code) DO NOTHING",
            (code, name),
        )
        conn.commit()
    return PlatformOut(code=code, name=name)

@app.put("/sources/{code}", response_model=PlatformOut)
def update_source(code: str, payload: NameUpdate, user: UserOut = Depends(require_role("admin"))):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(400, "Name is required")
    with psycopg.connect(DB_DSN) as conn:
        exec1(conn, "UPDATE app.sources SET name=%s WHERE code=%s", (name, code))
        conn.commit()
    return PlatformOut(code=code, name=name)

@app.delete("/sources/{code}")
def delete_source(code: str, user: UserOut = Depends(require_role("admin"))):
    with psycopg.connect(DB_DSN) as conn:
        try:
            exec1(conn, "DELETE FROM app.sources WHERE code=%s", (code,))
            conn.commit()
        except Exception:
            raise HTTPException(409, "Source is in use")
    return {"ok": True}

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
              p.code as platform_code,
              r.code as region_code,
              a.status_code,
              a.login_name,
              d.name as domain_name,
              a.slot_capacity,
              a.slot_reserved,
              s.occupied_slots,
              s.free_slots,
              a.notes
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
            account_id=row[0], platform_code=row[1], region_code=row[2],
            status=row[3], login_name=row[4], domain_code=row[5],
            login_full=f"{row[4]}@{row[5]}" if row[4] and row[5] else None,
            slot_capacity=row[6], slot_reserved=row[7],
            occupied_slots=row[8] or 0, free_slots=row[9] or 0,
            notes=row[10]
        )
        for row in rows
    ]

@app.post("/accounts", response_model=AccountOut)
def create_account(payload: AccountCreate, user: UserOut = Depends(get_current_user)):
    if payload.slot_capacity < payload.slot_reserved:
        raise HTTPException(400, "slot_capacity must be >= slot_reserved")
    if not payload.login_name or not payload.domain_code:
        raise HTTPException(400, "login_name and domain_code are required")
    with psycopg.connect(DB_DSN) as conn:
        platform_id = get_platform_id(conn, payload.platform_code)
        region_id = get_region_id(conn, payload.region_code)
        domain_id = get_domain_id(conn, payload.domain_code)

        row = q1(conn, """
            INSERT INTO app.accounts(login_name, domain_id, platform_id, region_id, slot_capacity, slot_reserved, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING account_id
        """, (
            payload.login_name, domain_id,
            platform_id, region_id, payload.slot_capacity, payload.slot_reserved, payload.notes
        ))
        account_id = int(row[0])
        conn.commit()

        occ, free = slots_summary(conn, account_id)
        return AccountOut(
            account_id=account_id,
            platform_code=payload.platform_code,
            region_code=payload.region_code,
            status="active",
            login_name=payload.login_name,
            domain_code=payload.domain_code,
            login_full=f"{payload.login_name}@{payload.domain_code}" if payload.login_name and payload.domain_code else None,
            slot_capacity=payload.slot_capacity,
            slot_reserved=payload.slot_reserved,
            occupied_slots=occ,
            free_slots=free,
            notes=payload.notes
        )

@app.put("/accounts/{account_id}", response_model=AccountOut)
def update_account(
    account_id: int,
    payload: AccountUpdate,
    user: UserOut = Depends(require_role("admin")),
):
    if payload.slot_capacity is not None and payload.slot_reserved is not None:
        if payload.slot_capacity < payload.slot_reserved:
            raise HTTPException(400, "slot_capacity must be >= slot_reserved")
    with psycopg.connect(DB_DSN) as conn:
        current = q1(
            conn,
            """
            SELECT login_name, domain_id, platform_id, region_id, status_code, slot_capacity, slot_reserved, notes
            FROM app.accounts
            WHERE account_id=%s
            """,
            (account_id,),
        )
        if not current:
            raise HTTPException(404, "Account not found")

        platform_id = get_platform_id(conn, payload.platform_code) if payload.platform_code else current[2]
        region_id = get_region_id(conn, payload.region_code) if payload.region_code else current[3]
        domain_id = get_domain_id(conn, payload.domain_code) if payload.domain_code else current[1]

        new_login = payload.login_name if payload.login_name is not None else current[0]
        new_status = payload.status_code if payload.status_code is not None else current[4]
        new_capacity = payload.slot_capacity if payload.slot_capacity is not None else current[5]
        new_reserved = payload.slot_reserved if payload.slot_reserved is not None else current[6]
        new_notes = payload.notes if payload.notes is not None else current[7]

        if new_capacity < new_reserved:
            raise HTTPException(400, "slot_capacity must be >= slot_reserved")

        exec1(
            conn,
            """
            UPDATE app.accounts
            SET login_name=%s,
                domain_id=%s,
                platform_id=%s,
                region_id=%s,
                status_code=%s,
                slot_capacity=%s,
                slot_reserved=%s,
                notes=%s
            WHERE account_id=%s
            """,
            (
                new_login,
                domain_id,
                platform_id,
                region_id,
                new_status,
                new_capacity,
                new_reserved,
                new_notes,
                account_id,
            ),
        )
        conn.commit()

        row = q1(
            conn,
            """
            SELECT
              a.account_id,
              p.code as platform_code,
              r.code as region_code,
              a.status_code,
              a.login_name,
              d.name as domain_name,
              a.slot_capacity,
              a.slot_reserved,
              s.occupied_slots,
              s.free_slots,
              a.notes
            FROM app.accounts a
            JOIN app.platforms p ON p.platform_id = a.platform_id
            LEFT JOIN app.regions r ON r.region_id = a.region_id
            LEFT JOIN app.domains d ON d.domain_id = a.domain_id
            LEFT JOIN app.v_account_slots s ON s.account_id = a.account_id
            WHERE a.account_id=%s
            """,
            (account_id,),
        )
        if not row:
            raise HTTPException(404, "Account not found")

    return AccountOut(
        account_id=row[0], platform_code=row[1], region_code=row[2],
        status=row[3], login_name=row[4], domain_code=row[5],
        login_full=f"{row[4]}@{row[5]}" if row[4] and row[5] else None,
        slot_capacity=row[6], slot_reserved=row[7],
        occupied_slots=row[8] or 0, free_slots=row[9] or 0,
        notes=row[10]
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

@app.delete("/accounts/{account_id}/secrets/{secret_key}")
def delete_account_secret(
    account_id: int,
    secret_key: str,
    user: UserOut = Depends(require_role("admin")),
):
    with psycopg.connect(DB_DSN) as conn:
        exec1(
            conn,
            "DELETE FROM app.account_secrets WHERE account_id=%s AND secret_key=%s",
            (account_id, secret_key),
        )
        conn.commit()
    return {"ok": True}

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
        ensure_account_exists(conn, payload.account_id)
        ensure_game_exists(conn, payload.game_id)
        ensure_source_exists(conn, payload.source_code)
        platform_id = get_platform_id_optional(conn, payload.platform_code)
        # ensure customer exists
        row = q1(conn, "SELECT customer_id, source_code FROM app.customers WHERE nickname=%s", (payload.customer_nickname,))
        if row:
            customer_id = int(row[0])
            if payload.source_code and not row[1]:
                exec1(
                    conn,
                    "UPDATE app.customers SET source_code=%s WHERE customer_id=%s",
                    (payload.source_code, customer_id),
                )
        else:
            row = q1(
                conn,
                "INSERT INTO app.customers(nickname, source_code) VALUES (%s, %s) RETURNING customer_id",
                (payload.customer_nickname, payload.source_code),
            )
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
            INSERT INTO app.deal_items(deal_id, account_id, game_id, platform_id, qty, price, start_at, end_at, slots_used, purchase_at, notes)
            VALUES (%s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s)
            RETURNING deal_item_id
        """, (
            deal_id, payload.account_id, payload.game_id, platform_id,
            payload.price, start_at, end_at, payload.slots_used, payload.purchase_at, None
        ))

        conn.commit()

        # return updated slots
        occ2, free2 = slots_summary(conn, payload.account_id)
        return {"deal_id": deal_id, "account_id": payload.account_id, "occupied_slots": occ2, "free_slots": free2}

@app.post("/deals")
def create_deal(payload: DealCreate, user: UserOut = Depends(get_current_user)):
    deal_type = payload.deal_type_code.strip().lower()
    if deal_type not in ("sale", "rental"):
        raise HTTPException(400, "deal_type_code must be sale or rental")
    if deal_type == "rental" and payload.slots_used <= 0:
        raise HTTPException(400, "slots_used must be >= 1 for rental")
    if deal_type == "sale":
        payload.slots_used = 0

    with psycopg.connect(DB_DSN) as conn:
        ensure_account_exists(conn, payload.account_id)
        ensure_game_exists(conn, payload.game_id)
        ensure_source_exists(conn, payload.source_code)
        platform_id = get_platform_id_optional(conn, payload.platform_code)

        row = q1(conn, "SELECT customer_id, source_code FROM app.customers WHERE nickname=%s", (payload.customer_nickname,))
        if row:
            customer_id = int(row[0])
            if payload.source_code and not row[1]:
                exec1(
                    conn,
                    "UPDATE app.customers SET source_code=%s WHERE customer_id=%s",
                    (payload.source_code, customer_id),
                )
        else:
            row = q1(
                conn,
                "INSERT INTO app.customers(nickname, source_code) VALUES (%s, %s) RETURNING customer_id",
                (payload.customer_nickname, payload.source_code),
            )
            customer_id = int(row[0])

        if deal_type == "rental":
            occ, free = slots_summary(conn, payload.account_id)
            if free < payload.slots_used:
                raise HTTPException(409, f"Not enough free slots. free_slots={free}, requested={payload.slots_used}")

        deal_row = q1(conn, """
            INSERT INTO app.deals(deal_type_code, status_code, customer_id, currency, total_amount)
            VALUES (%s, 'confirmed', %s, 'RUB', %s)
            RETURNING deal_id
        """, (deal_type, customer_id, payload.price))
        deal_id = int(deal_row[0])

        q1(conn, """
            INSERT INTO app.deal_items(
              deal_id, account_id, game_id, platform_id,
              qty, price, fee, purchase_at, start_at, end_at, slots_used, notes
            )
            VALUES (%s, %s, %s, %s, 1, %s, 0, %s, %s, %s, %s, %s)
            RETURNING deal_item_id
        """, (
            deal_id, payload.account_id, payload.game_id, platform_id,
            payload.price, payload.purchase_at, payload.start_at, payload.end_at,
            payload.slots_used, payload.notes
        ))
        conn.commit()

        return {"deal_id": deal_id}

@app.get("/deals", response_model=DealListOut)
def list_deals(
    account_id: Optional[int] = None,
    game_id: Optional[int] = None,
    platform_code: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    user: UserOut = Depends(get_current_user),
):
    if page < 1:
        raise HTTPException(400, "page must be >= 1")
    if page_size < 1 or page_size > 200:
        raise HTTPException(400, "page_size must be between 1 and 200")
    offset = (page - 1) * page_size

    with psycopg.connect(DB_DSN) as conn:
        where_sql, params = build_deals_filters(account_id, game_id, platform_code, q)

        total_row = q1(conn, f"""
            SELECT COUNT(*)
            FROM app.deal_items di
            JOIN app.deals d ON d.deal_id = di.deal_id
            LEFT JOIN app.accounts a ON a.account_id = di.account_id
            LEFT JOIN app.domains dm ON dm.domain_id = a.domain_id
            LEFT JOIN app.game_titles g ON g.game_id = di.game_id
            LEFT JOIN app.platforms p ON p.platform_id = di.platform_id
            LEFT JOIN app.customers c ON c.customer_id = d.customer_id
            {where_sql}
        """, params)
        total = int(total_row[0]) if total_row else 0

        rows = qall(conn, f"""
            SELECT
              d.deal_id,
              dt.name as deal_type_name,
              ds.name as status_name,
              di.account_id,
              a.login_name,
              dm.name as domain_name,
              di.game_id,
              g.title,
              p.code as platform_code,
              c.nickname,
              c.source_code,
              di.price,
              di.purchase_at,
              d.created_at
            FROM app.deal_items di
            JOIN app.deals d ON d.deal_id = di.deal_id
            LEFT JOIN app.deal_types dt ON dt.code = d.deal_type_code
            LEFT JOIN app.deal_statuses ds ON ds.code = d.status_code
            LEFT JOIN app.accounts a ON a.account_id = di.account_id
            LEFT JOIN app.domains dm ON dm.domain_id = a.domain_id
            LEFT JOIN app.game_titles g ON g.game_id = di.game_id
            LEFT JOIN app.platforms p ON p.platform_id = di.platform_id
            LEFT JOIN app.customers c ON c.customer_id = d.customer_id
            {where_sql}
            ORDER BY d.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [page_size, offset])

    items = []
    for r in rows:
        login_full = f"{r[4]}@{r[5]}" if r[4] and r[5] else None
        items.append(
            DealListItem(
                deal_id=r[0],
                deal_type=r[1],
                status=r[2],
                account_id=r[3],
                account_login=login_full,
                game_id=r[6],
                game_title=r[7],
                platform_code=r[8],
                customer_nickname=r[9],
                source_code=r[10],
                price=float(r[11] or 0),
                purchase_at=r[12],
                created_at=r[13],
            )
        )

    return DealListOut(total=total, items=items)
