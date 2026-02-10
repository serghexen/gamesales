from datetime import datetime, timezone, date
from typing import Optional, List, Tuple, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import psycopg
from psycopg_pool import ConnectionPool
import os
from dotenv import load_dotenv
from pathlib import Path
import base64
import urllib.request
import urllib.error
import ssl
import uuid

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env.dev", override=True)

def ensure_analytics_schema():
    try:
        with psycopg.connect(DB_DSN) as conn:
            # Поддерживаем схему в актуальном состоянии для локального запуска без ручных миграций.
            exec1(conn, "ALTER TABLE app.regions ADD COLUMN IF NOT EXISTS purchase_cost_rate numeric(12,6) NOT NULL DEFAULT 1.0")
            exec1(conn, "ALTER TABLE app.deals ADD COLUMN IF NOT EXISTS completed_at timestamptz")
            exec1(conn, "ALTER TABLE app.deals ADD COLUMN IF NOT EXISTS order_number text")
            exec1(conn, "ALTER TABLE app.deals ADD COLUMN IF NOT EXISTS responsible_username text")
            exec1(
                conn,
                """
                CREATE TABLE IF NOT EXISTS tg.dialog_snapshot (
                  chat_id       bigint PRIMARY KEY,
                  title         text NOT NULL DEFAULT '',
                  unread_count  integer NOT NULL DEFAULT 0,
                  is_group      boolean NOT NULL DEFAULT false,
                  is_channel    boolean NOT NULL DEFAULT false,
                  updated_at    timestamptz NOT NULL DEFAULT now()
                )
                """,
            )
            exec1(
                conn,
                "CREATE INDEX IF NOT EXISTS idx_tg_dialog_snapshot_updated_at ON tg.dialog_snapshot(updated_at DESC)",
            )
            conn.commit()
    except Exception:
        # Ignore startup migration errors to avoid breaking app boot
        pass


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _pool
    # Создаём и открываем пул соединений при каждом старте (поддерживает повторные запуски в тестах).
    _pool = ConnectionPool(DB_DSN, min_size=2, max_size=10, open=True)
    # Выполняем легкую инициализацию схемы при старте приложения.
    ensure_analytics_schema()
    yield
    # Закрываем пул при остановке приложения.
    _pool.close()
    _pool = None


app = FastAPI(title="GameSales API", version="0.1.0", lifespan=lifespan)

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

# Пул соединений: создаётся и открывается в lifespan, закрывается при остановке.
# Пересоздаётся при каждом запуске (важно для тестов с несколькими TestClient).
# min_size=2 — всегда 2 живых соединения; max_size=10 — не больше 10 одновременно.
_pool: ConnectionPool = None

# Оригинальная функция psycopg.connect, сохранённая при импорте модуля.
# Используется для определения, был ли connect замокан в тестах.
_PSYCOPG_CONNECT_ORIG = psycopg.connect

def _is_retryable_conn_error(exc: Exception) -> bool:
    # Определяет ошибки "протухшего" соединения, когда безопасно один раз взять новый коннект из пула.
    text = str(exc or "").lower()
    return (
        "server closed the connection unexpectedly" in text
        or "consuming input failed" in text
        or "terminating connection due to administrator command" in text
        or "connection not open" in text
    )

class _PoolConnectionContext:
    """Контекст менеджер выдачи коннекта из пула с одной попыткой восстановиться на битом соединении."""
    def __init__(self, pool: ConnectionPool):
        self._pool = pool
        self._ctx = None
        self._conn = None

    def __enter__(self):
        # Даем несколько попыток, чтобы пережить пачку "протухших" коннектов в пуле.
        attempts = 3
        for attempt in range(attempts):
            self._ctx = self._pool.connection()
            self._conn = self._ctx.__enter__()
            try:
                # Быстрый ping перед возвратом соединения, чтобы не отдавать "мертвый" коннект в endpoint.
                with self._conn.cursor() as cur:
                    cur.execute("SELECT 1")
                return self._conn
            except Exception as e:
                # Закрываем текущий коннект явно, чтобы не вернуть в пул "битое" соединение.
                try:
                    if self._conn is not None:
                        self._conn.close()
                except Exception:
                    pass
                self._ctx.__exit__(type(e), e, e.__traceback__)
                self._ctx = None
                self._conn = None
                if attempt + 1 >= attempts or not _is_retryable_conn_error(e):
                    raise
                # Просим пул проверить и заменить невалидные соединения перед следующей попыткой.
                try:
                    self._pool.check()
                except Exception:
                    pass
        raise RuntimeError("Failed to acquire database connection")

    def __exit__(self, exc_type, exc, tb):
        if self._ctx is None:
            return False
        return self._ctx.__exit__(exc_type, exc, tb)

class _PsycopgPoolProxy:
    """Обёртка над пулом, имитирует psycopg.connect() для совместимости с domain-модулями.

    В тестах psycopg.connect может быть замокан через patch.object — в таком случае
    делегируем к нему, чтобы тесты продолжали работать без изменений.
    В продакшене используем пул соединений.
    """
    def connect(self, dsn: str = None):
        if psycopg.connect is not _PSYCOPG_CONNECT_ORIG:
            # psycopg.connect замокан (тесты) — используем мок
            return psycopg.connect(dsn or DB_DSN)
        # Продакшен — берём соединение из пула
        return _PoolConnectionContext(_pool)

pooled_psycopg = _PsycopgPoolProxy()

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
JWT_TTL_MIN = int(os.getenv("JWT_TTL_MIN", "720"))
PWD_SCHEME = "gs_pbkdf2_sha256"
PWD_ITERATIONS = int(os.getenv("PWD_ITERATIONS", "210000"))
PWD_SALT_BYTES = 16

def now_utc():
    return datetime.now(timezone.utc)

MIN_DATE = date(2020, 1, 1)

def validate_date_in_range(value, field_name: str):
    if value is None:
        return
    if isinstance(value, datetime):
        check_date = value.date()
    else:
        check_date = value
    max_date = now_utc().date()
    if check_date < MIN_DATE or check_date > max_date:
        raise HTTPException(400, f"{field_name} must be between {MIN_DATE.isoformat()} and {max_date.isoformat()}")

def validate_date_not_future(value, field_name: str):
    if value is None:
        return
    if isinstance(value, datetime):
        check_date = value.date()
    else:
        check_date = value
    max_date = now_utc().date()
    if check_date > max_date:
        raise HTTPException(400, f"{field_name} must be <= {max_date.isoformat()}")

def validate_date_range(start_value, end_value, field_name: str):
    if not start_value or not end_value:
        return
    if isinstance(start_value, datetime):
        start_date = start_value.date()
    else:
        start_date = start_value
    if isinstance(end_value, datetime):
        end_date = end_value.date()
    else:
        end_date = end_value
    if end_date < start_date:
        raise HTTPException(400, f"{field_name} must be >= start_at")

def normalize_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return value

def normalize_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return value

# ----------------------------
# Models
# ----------------------------
from domains.accounts_models import (
    AccountCreate,
    AccountUpdate,
    AccountPlatformSlots,
    AccountSlotStatusOut,
    AccountOut,
    AccountListOut,
    AccountSecretIn,
    AccountSecretOut,
    AccountSecretsBatchIn,
    AccountSecretsBatchItem,
    SlotAvailabilityOut,
    AccountGamesIn,
    GameAccountOut,
    SlotTypeOut,
    AccountSlotAssignmentOut,
)
from domains.accounts_api import mount_accounts_routes
from domains.deals_models import (
    RentalCreate,
    DealCreate,
    DealUpdate,
    DealListItem,
    DealListOut,
)
from domains.deals_api import mount_deals_routes
from domains.deals_ws import build_deals_events, mount_deals_ws_routes
from domains.telegram_api import mount_telegram_routes
from domains.imports_models import ImportReportIn
from domains.analytics_api import mount_analytics_routes
from domains.games_api import mount_games_routes
from domains.games_import_api import mount_games_import_routes
from domains.accounts_import_api import mount_accounts_import_routes
from domains.catalogs_api import mount_catalogs_routes
from domains.auth_api import mount_auth_routes
from domains.slots_import_api import mount_slots_import_routes
from domains.import_jobs import build_import_jobs
from domains.import_report_utils import build_import_report_xlsx
from domains.import_parsers import build_import_parsers
from domains.import_status import build_import_status_store
from domains.telegram_sync import build_telegram_sync_service
from domains.auth_service import build_auth_service
from domains.db_helpers import build_db_helpers
from domains.games_lookup_service import build_games_lookup_service

class GameCreate(BaseModel):
    title: str
    short_title: Optional[str] = None
    link: Optional[str] = None
    logo_url: Optional[str] = None
    text_lang: Optional[str] = None
    audio_lang: Optional[str] = None
    vr_support: Optional[str] = None
    platform_codes: Optional[List[str]] = None
    region_code: Optional[str] = None

class GameUpdate(BaseModel):
    title: Optional[str] = None
    short_title: Optional[str] = None
    link: Optional[str] = None
    logo_url: Optional[str] = None
    text_lang: Optional[str] = None
    audio_lang: Optional[str] = None
    vr_support: Optional[str] = None
    platform_codes: Optional[List[str]] = None
    region_code: Optional[str] = None

class GameOut(BaseModel):
    game_id: int
    title: str
    short_title: Optional[str] = None
    link: Optional[str] = None
    logo_url: Optional[str] = None
    text_lang: Optional[str] = None
    audio_lang: Optional[str] = None
    vr_support: Optional[str] = None
    platform_codes: List[str]
    region_code: Optional[str]

class GameListOut(BaseModel):
    total: int
    items: List[GameOut]

class PlatformOut(BaseModel):
    code: str
    name: str
    slot_capacity: int

class SourceOut(BaseModel):
    source_id: int
    code: str
    name: str

class RegionOut(BaseModel):
    code: str
    name: str
    purchase_cost_rate: float
    purchase_cost_rate: float

class PlatformIn(BaseModel):
    code: str
    name: str
    slot_capacity: int = 0

class PlatformUpdate(BaseModel):
    name: Optional[str] = None
    slot_capacity: Optional[int] = None

class RegionIn(BaseModel):
    code: str
    name: str
    purchase_cost_rate: float = 1.0

class RegionUpdate(BaseModel):
    name: Optional[str] = None
    purchase_cost_rate: Optional[float] = None

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
    name: str = ""
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

class DomainIn(BaseModel):
    name: str

class SourceIn(BaseModel):
    code: str
    name: str

class SourceUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None

class NameUpdate(BaseModel):
    name: str

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

db_helpers = build_db_helpers(
    q1=lambda conn, sql, params=None: q1(conn, sql, params),
    qall=lambda conn, sql, params=None: qall(conn, sql, params),
    exec1=lambda conn, sql, params=None: exec1(conn, sql, params),
    HTTPException=HTTPException,
    AccountPlatformSlots=AccountPlatformSlots,
    AccountSlotStatusOut=AccountSlotStatusOut,
)

get_platform_id = db_helpers.get_platform_id
get_platform_info = db_helpers.get_platform_info
get_region_id = db_helpers.get_region_id
get_domain_id = db_helpers.get_domain_id
get_platform_id_optional = db_helpers.get_platform_id_optional
ensure_account_exists = db_helpers.ensure_account_exists
ensure_game_exists = db_helpers.ensure_game_exists
ensure_game_active = db_helpers.ensure_game_active
ensure_customer = db_helpers.ensure_customer
ensure_source_exists = db_helpers.ensure_source_exists
build_deals_filters = db_helpers.build_deals_filters
slots_summary = db_helpers.slots_summary
get_account_platform_slots = db_helpers.get_account_platform_slots
get_account_slot_status = db_helpers.get_account_slot_status
normalize_platform_codes = db_helpers.normalize_platform_codes
get_game_platform_codes = db_helpers.get_game_platform_codes
get_account_platform_codes = db_helpers.get_account_platform_codes
account_has_ps4 = db_helpers.account_has_ps4
ensure_account_allows_slot_type = db_helpers.ensure_account_allows_slot_type

def encode_b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")

get_slot_type = db_helpers.get_slot_type
get_account_slot_free = db_helpers.get_account_slot_free
release_slot_assignment = db_helpers.release_slot_assignment

MAX_LOGO_BYTES = 5 * 1024 * 1024
ALLOWED_LOGO_MIME = {"image/jpeg", "image/png", "image/webp"}

def detect_logo_mime_from_bytes(data: bytes) -> str:
    if not data:
        return ""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return ""

def fetch_logo_from_url(url: str) -> Tuple[bytes, str]:
    if not url:
        raise ValueError("logo url is empty")
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "gamesales-import"})
    try:
        with urllib.request.urlopen(req, timeout=10, context=context) as resp:
            content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            data = resp.read(MAX_LOGO_BYTES + 1)
    except urllib.error.URLError as exc:
        raise ValueError(f"logo download failed: {exc}") from exc
    if len(data) > MAX_LOGO_BYTES:
        raise ValueError("logo too large")
    mime = content_type if content_type in ALLOWED_LOGO_MIME else ""
    if not mime:
        mime = detect_logo_mime_from_bytes(data)
    if mime not in ALLOWED_LOGO_MIME:
        raise ValueError("logo type not allowed")
    return data, mime

LOGO_DOWNLOAD_DELAY_SEC = 0.25
IMPORT_STATUS_TTL_SEC = 24 * 60 * 60
_QUEUE_API_URL = os.getenv("QUEUE_API_URL", "")
_QUEUE_API_KEY = os.getenv("QUEUE_API_KEY", "")
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_TELEGRAM_API_URL = os.getenv("TELEGRAM_API_URL", "")
_TELEGRAM_API_KEY = os.getenv("TELEGRAM_API_KEY", "")
TELEGRAM_DIALOGS_SYNC_LIMIT = int(os.getenv("TELEGRAM_DIALOGS_SYNC_LIMIT", "0") or "0")
TELEGRAM_DIALOGS_SYNC_BATCH = int(os.getenv("TELEGRAM_DIALOGS_SYNC_BATCH", "100") or "100")
TELEGRAM_DIALOGS_SYNC_COOLDOWN_SEC = int(os.getenv("TELEGRAM_DIALOGS_SYNC_COOLDOWN_SEC", "45") or "45")
TELEGRAM_DIALOGS_SYNC_BATCH_DELAY_MS = int(os.getenv("TELEGRAM_DIALOGS_SYNC_BATCH_DELAY_MS", "250") or "250")

import_status_store = build_import_status_store(
    import_status_ttl_sec=IMPORT_STATUS_TTL_SEC,
    queue_api_url=_QUEUE_API_URL,
    queue_api_key=_QUEUE_API_KEY,
    redis_url=_REDIS_URL,
)

is_import_cancelled = import_status_store.is_import_cancelled
set_import_progress = import_status_store.set_import_progress
get_import_progress = import_status_store.get_import_progress
clear_import_progress = import_status_store.clear_import_progress

telegram_sync_service = build_telegram_sync_service(
    DB_DSN=DB_DSN,
    psycopg=pooled_psycopg,
    q1=q1,
    exec1=exec1,
    telegram_api_url=_TELEGRAM_API_URL,
    telegram_api_key=_TELEGRAM_API_KEY,
    sync_limit=TELEGRAM_DIALOGS_SYNC_LIMIT,
    sync_batch=TELEGRAM_DIALOGS_SYNC_BATCH,
    sync_cooldown_sec=TELEGRAM_DIALOGS_SYNC_COOLDOWN_SEC,
    sync_batch_delay_ms=TELEGRAM_DIALOGS_SYNC_BATCH_DELAY_MS,
)

_telegram_api_request = telegram_sync_service.telegram_api_request
_telegram_api_request_raw = telegram_sync_service.telegram_api_request_raw
_upsert_telegram_dialog_snapshot = telegram_sync_service.upsert_telegram_dialog_snapshot
_delete_dead_dialog = telegram_sync_service.delete_dead_dialog
_trigger_telegram_dialogs_sync = telegram_sync_service.trigger_telegram_dialogs_sync
_get_telegram_sync_stats = telegram_sync_service.get_sync_stats

parse_ws_user, publish_deal_event = build_deals_events(
    redis_url=_REDIS_URL,
    jwt_secret=JWT_SECRET,
    jwt_alg=JWT_ALG,
    UserOut=UserOut,
)

games_lookup_service = build_games_lookup_service(
    q1=lambda conn, sql, params=None: q1(conn, sql, params),
    qall=lambda conn, sql, params=None: qall(conn, sql, params),
    normalize_platform_codes=normalize_platform_codes,
)

find_game_title_platform_conflicts = games_lookup_service.find_game_title_platform_conflicts
find_game_id_by_title_platforms = games_lookup_service.find_game_id_by_title_platforms

import_parsers = build_import_parsers(
    q1=lambda conn, sql, params=None: q1(conn, sql, params),
    qall=lambda conn, sql, params=None: qall(conn, sql, params),
    normalize_platform_codes=normalize_platform_codes,
)

GAME_IMPORT_HEADERS = import_parsers.GAME_IMPORT_HEADERS
parse_import_platforms = import_parsers.parse_import_platforms
validate_game_import_rows = import_parsers.validate_game_import_rows
read_games_from_excel = import_parsers.read_games_from_excel
read_accounts_from_excel = import_parsers.read_accounts_from_excel
read_slots_from_excel = import_parsers.read_slots_from_excel
clean_slots_excel = import_parsers.clean_slots_excel
split_account = import_parsers.split_account
validate_account_import_rows = import_parsers.validate_account_import_rows
SLOT_FILE_TO_TYPE = import_parsers.SLOT_FILE_TO_TYPE
normalize_slot_file_value = import_parsers.normalize_slot_file_value
normalize_cell_text = import_parsers.normalize_cell_text
normalize_slot_date = import_parsers.normalize_slot_date
normalize_slot_date_to_dt = import_parsers.normalize_slot_date_to_dt
resolve_source_id = import_parsers.resolve_source_id
validate_slot_import_rows = import_parsers.validate_slot_import_rows

auth_service = build_auth_service(
    q1=lambda conn, sql, params=None: q1(conn, sql, params),
    exec1=lambda conn, sql, params=None: exec1(conn, sql, params),
    now_utc=now_utc,
    UserOut=UserOut,
    get_jwt_secret=lambda: JWT_SECRET,
    get_jwt_alg=lambda: JWT_ALG,
    get_jwt_ttl_min=lambda: JWT_TTL_MIN,
    get_pwd_scheme=lambda: PWD_SCHEME,
    get_pwd_iterations=lambda: PWD_ITERATIONS,
    get_pwd_salt_bytes=lambda: PWD_SALT_BYTES,
)

hash_password = auth_service.hash_password
verify_password = auth_service.verify_password
init_auth_schema = auth_service.init_auth_schema
get_user_by_username = auth_service.get_user_by_username
get_user_id = auth_service.get_user_id
role_exists = auth_service.role_exists
ensure_admin_user = auth_service.ensure_admin_user
create_access_token = auth_service.create_access_token
get_current_user = auth_service.get_current_user
require_role = auth_service.require_role

def b64_encode(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("utf-8")

# ----------------------------
# Endpoints
# ----------------------------
@app.get("/health")
def health():
    with _pool.connection() as conn:
        init_auth_schema(conn)
        ensure_admin_user(conn)
        q1(conn, "SELECT 1")
    return {"ok": True}

mount_auth_routes(
    app,
    DB_DSN=DB_DSN,
    psycopg=pooled_psycopg,
    q1=lambda conn, sql, params=None: q1(conn, sql, params),
    qall=lambda conn, sql, params=None: qall(conn, sql, params),
    exec1=lambda conn, sql, params=None: exec1(conn, sql, params),
    init_auth_schema=lambda conn: init_auth_schema(conn),
    ensure_admin_user=lambda conn: ensure_admin_user(conn),
    get_user_by_username=lambda conn, username: get_user_by_username(conn, username),
    verify_password=lambda raw_password, password_hash: verify_password(raw_password, password_hash),
    hash_password=lambda raw_password: hash_password(raw_password),
    create_access_token=lambda user_id, username, role: create_access_token(user_id, username, role),
    role_exists=lambda conn, role_code: role_exists(conn, role_code),
    get_current_user=get_current_user,
    require_role=require_role,
    LoginIn=LoginIn,
    LoginOut=LoginOut,
    UserOut=UserOut,
    ChangePasswordIn=ChangePasswordIn,
    RoleOut=RoleOut,
    UserListOut=UserListOut,
    UserCreate=UserCreate,
    ResetPasswordIn=ResetPasswordIn,
)


mount_telegram_routes(
    app,
    DB_DSN=DB_DSN,
    psycopg=pooled_psycopg,
    q1=q1,
    qall=qall,
    exec1=exec1,
    get_user_id=get_user_id,
    get_current_user=get_current_user,
    require_role=require_role,
    telegram_api_request=_telegram_api_request,
    telegram_api_request_raw=_telegram_api_request_raw,
    upsert_telegram_dialog_snapshot=_upsert_telegram_dialog_snapshot,
    delete_dead_dialog=_delete_dead_dialog,
    trigger_telegram_dialogs_sync=_trigger_telegram_dialogs_sync,
    get_sync_stats=_get_telegram_sync_stats,
)

mount_catalogs_routes(
    app,
    DB_DSN=DB_DSN,
    psycopg=pooled_psycopg,
    q1=lambda conn, sql, params=None: q1(conn, sql, params),
    qall=lambda conn, sql, params=None: qall(conn, sql, params),
    exec1=lambda conn, sql, params=None: exec1(conn, sql, params),
    get_current_user=get_current_user,
    require_role=require_role,
    UserOut=UserOut,
    PlatformOut=PlatformOut,
    PlatformIn=PlatformIn,
    PlatformUpdate=PlatformUpdate,
    RegionOut=RegionOut,
    RegionIn=RegionIn,
    RegionUpdate=RegionUpdate,
    DomainIn=DomainIn,
    NameUpdate=NameUpdate,
    SourceOut=SourceOut,
    SourceIn=SourceIn,
    SourceUpdate=SourceUpdate,
)

mount_accounts_routes(
    app,
    DB_DSN=DB_DSN,
    psycopg=pooled_psycopg,
    q1=q1,
    qall=qall,
    exec1=exec1,
    get_region_id=get_region_id,
    get_domain_id=get_domain_id,
    get_platform_info=get_platform_info,
    ensure_account_exists=ensure_account_exists,
    ensure_game_exists=ensure_game_exists,
    validate_date_not_future=validate_date_not_future,
    get_account_platform_slots=get_account_platform_slots,
    get_account_slot_status=get_account_slot_status,
    b64_encode=b64_encode,
    require_role=require_role,
    get_current_user=get_current_user,
    GameOut=GameOut,
)

mount_games_routes(
    app,
    DB_DSN=DB_DSN,
    psycopg=pooled_psycopg,
    q1=q1,
    qall=qall,
    exec1=exec1,
    normalize_platform_codes=normalize_platform_codes,
    find_game_title_platform_conflicts=find_game_title_platform_conflicts,
    get_platform_id=get_platform_id,
    get_region_id=get_region_id,
    get_game_platform_codes=get_game_platform_codes,
    ensure_game_exists=ensure_game_exists,
    encode_b64=encode_b64,
    get_current_user=get_current_user,
    require_role=require_role,
    GameListOut=GameListOut,
    GameOut=GameOut,
    SlotTypeOut=SlotTypeOut,
    GameCreate=GameCreate,
    GameUpdate=GameUpdate,
    UserOut=UserOut,
)

import_jobs = build_import_jobs(
    DB_DSN=DB_DSN,
    psycopg=pooled_psycopg,
    q1=q1,
    exec1=exec1,
    read_games_from_excel=read_games_from_excel,
    validate_game_import_rows=validate_game_import_rows,
    parse_import_platforms=parse_import_platforms,
    find_game_id_by_title_platforms=find_game_id_by_title_platforms,
    get_platform_id=get_platform_id,
    read_accounts_from_excel=read_accounts_from_excel,
    validate_account_import_rows=validate_account_import_rows,
    split_account=split_account,
    b64_encode=b64_encode,
    get_platform_info=get_platform_info,
    read_slots_from_excel=read_slots_from_excel,
    validate_slot_import_rows=validate_slot_import_rows,
    normalize_cell_text=normalize_cell_text,
    normalize_slot_file_value=normalize_slot_file_value,
    SLOT_FILE_TO_TYPE=SLOT_FILE_TO_TYPE,
    normalize_slot_date_to_dt=normalize_slot_date_to_dt,
    resolve_source_id=resolve_source_id,
    ensure_account_allows_slot_type=ensure_account_allows_slot_type,
    ensure_customer=ensure_customer,
    is_import_cancelled=is_import_cancelled,
    set_import_progress=set_import_progress,
    MIN_DATE=MIN_DATE,
)

run_games_import_job = import_jobs.run_games_import_job
run_accounts_import_job = import_jobs.run_accounts_import_job
run_slots_validate_job = import_jobs.run_slots_validate_job
run_slots_import_job = import_jobs.run_slots_import_job

mount_games_import_routes(
    app,
    DB_DSN=DB_DSN,
    psycopg=pooled_psycopg,
    read_games_from_excel=read_games_from_excel,
    validate_game_import_rows=validate_game_import_rows,
    set_import_progress=set_import_progress,
    get_import_progress=get_import_progress,
    run_games_import_job=run_games_import_job,
    build_import_report_xlsx=build_import_report_xlsx,
    require_role=require_role,
    UserOut=UserOut,
    ImportReportIn=ImportReportIn,
    GAME_IMPORT_HEADERS=GAME_IMPORT_HEADERS,
)

mount_accounts_import_routes(
    app,
    DB_DSN=DB_DSN,
    psycopg=pooled_psycopg,
    read_accounts_from_excel=read_accounts_from_excel,
    validate_account_import_rows=validate_account_import_rows,
    set_import_progress=set_import_progress,
    get_import_progress=get_import_progress,
    run_accounts_import_job=run_accounts_import_job,
    build_import_report_xlsx=build_import_report_xlsx,
    require_role=require_role,
    UserOut=UserOut,
    ImportReportIn=ImportReportIn,
)

mount_slots_import_routes(
    app,
    clean_slots_excel=clean_slots_excel,
    set_import_progress=set_import_progress,
    get_import_progress=get_import_progress,
    run_slots_validate_job=run_slots_validate_job,
    run_slots_import_job=run_slots_import_job,
    build_import_report_xlsx=build_import_report_xlsx,
    require_role=require_role,
    UserOut=UserOut,
    ImportReportIn=ImportReportIn,
)

mount_deals_routes(
    app,
    DB_DSN=DB_DSN,
    psycopg=pooled_psycopg,
    q1=q1,
    qall=qall,
    exec1=exec1,
    now_utc=now_utc,
    validate_date_in_range=validate_date_in_range,
    validate_date_range=validate_date_range,
    ensure_account_exists=ensure_account_exists,
    ensure_game_active=ensure_game_active,
    ensure_source_exists=ensure_source_exists,
    ensure_account_allows_slot_type=ensure_account_allows_slot_type,
    get_platform_id=get_platform_id,
    get_region_id=get_region_id,
    get_account_slot_free=get_account_slot_free,
    ensure_customer=ensure_customer,
    get_slot_type=get_slot_type,
    ensure_game_exists=ensure_game_exists,
    account_has_ps4=account_has_ps4,
    release_slot_assignment=release_slot_assignment,
    build_deals_filters=build_deals_filters,
    slots_summary=slots_summary,
    get_current_user=get_current_user,
    publish_deal_event=publish_deal_event,
)

mount_deals_ws_routes(
    app,
    redis_url=_REDIS_URL,
    parse_ws_user=parse_ws_user,
)

mount_analytics_routes(
    app,
    DB_DSN=DB_DSN,
    get_current_user=get_current_user,
    q1=q1,
    qall=qall,
    psycopg=pooled_psycopg,
)
