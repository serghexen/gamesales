from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import psycopg
import os

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

def now_utc():
    return datetime.now(timezone.utc)

# ----------------------------
# Models
# ----------------------------
class AccountCreate(BaseModel):
    nickname: str
    platform_code: str = Field(..., description="steam/psn/xbox/epic")
    region_code: Optional[str] = Field(None, description="RU/TR/US/EU")
    slot_capacity: int = 1
    slot_reserved: int = 0
    notes: Optional[str] = None

class AccountOut(BaseModel):
    account_id: int
    nickname: str
    platform_code: str
    region_code: Optional[str]
    status: str
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

class RentalCreate(BaseModel):
    account_id: int
    customer_nickname: str
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    slots_used: int = 1
    price: float = 0

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

def slots_summary(conn, account_id: int):
    row = q1(conn, "SELECT occupied_slots, free_slots FROM app.v_account_slots WHERE account_id=%s", (account_id,))
    if not row:
        return (0, 0)
    return int(row[0]), int(row[1])

# ----------------------------
# Endpoints
# ----------------------------
@app.get("/health")
def health():
    with psycopg.connect(DB_DSN) as conn:
        v = q1(conn, "SELECT 1")
    return {"ok": True}

@app.get("/accounts", response_model=List[AccountOut])
def list_accounts():
    with psycopg.connect(DB_DSN) as conn:
        rows = qall(conn, """
            SELECT
              a.account_id,
              a.nickname,
              p.code as platform_code,
              r.code as region_code,
              a.status::text,
              a.slot_capacity,
              a.slot_reserved,
              s.occupied_slots,
              s.free_slots
            FROM app.accounts a
            JOIN app.platforms p ON p.platform_id = a.platform_id
            LEFT JOIN app.regions r ON r.region_id = a.region_id
            LEFT JOIN app.v_account_slots s ON s.account_id = a.account_id
            ORDER BY a.account_id DESC
            LIMIT 200
        """)
    return [
        AccountOut(
            account_id=row[0], nickname=row[1], platform_code=row[2], region_code=row[3],
            status=row[4], slot_capacity=row[5], slot_reserved=row[6],
            occupied_slots=row[7] or 0, free_slots=row[8] or 0
        )
        for row in rows
    ]

@app.post("/accounts", response_model=AccountOut)
def create_account(payload: AccountCreate):
    if payload.slot_capacity < payload.slot_reserved:
        raise HTTPException(400, "slot_capacity must be >= slot_reserved")
    with psycopg.connect(DB_DSN) as conn:
        platform_id = get_platform_id(conn, payload.platform_code)
        region_id = get_region_id(conn, payload.region_code)

        row = q1(conn, """
            INSERT INTO app.accounts(nickname, platform_id, region_id, slot_capacity, slot_reserved, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING account_id
        """, (payload.nickname, platform_id, region_id, payload.slot_capacity, payload.slot_reserved, payload.notes))
        account_id = int(row[0])
        conn.commit()

        occ, free = slots_summary(conn, account_id)
        return AccountOut(
            account_id=account_id,
            nickname=payload.nickname,
            platform_code=payload.platform_code,
            region_code=payload.region_code,
            status="active",
            slot_capacity=payload.slot_capacity,
            slot_reserved=payload.slot_reserved,
            occupied_slots=occ,
            free_slots=free
        )

@app.get("/games", response_model=List[GameOut])
def list_games(q: Optional[str] = None):
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
def create_game(payload: GameCreate):
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
def create_rental(payload: RentalCreate):
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
            INSERT INTO app.deals(deal_type, status, customer_id, currency, total_amount)
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
