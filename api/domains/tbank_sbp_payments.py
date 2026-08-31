"""Независимые СБП-платежи CRM через динамические QR Т-Банка."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field


FINAL_FAILURE_STATUSES = {"REJECTED", "REVERSED", "CANCELED", "DEADLINE_EXPIRED"}
FINAL_PAYMENT_STATES = {"confirmed", "rejected", "expired", "cancelled", "failed"}
RECEIPT_TAXATIONS = {"osn", "usn_income", "usn_income_outcome", "esn", "patent"}
RECEIPT_TAXES = {
    "none", "vat0", "vat5", "vat7", "vat10", "vat22", "vat105", "vat107", "vat110", "vat122",
}


class TBankError(RuntimeError):
    """Хранит ошибку банка и признак неопределённого сетевого результата."""

    def __init__(self, message: str, *, uncertain: bool = False) -> None:
        super().__init__(message)
        self.uncertain = uncertain


@dataclass(frozen=True)
class TBankSettings:
    base_url: str
    terminal_key: str
    password: str
    notification_url: str
    success_url: str
    fail_url: str
    timeout_seconds: int


class SbpPaymentCreateIn(BaseModel):
    description: str = Field(min_length=1, max_length=128)
    buyer: str = Field(min_length=1, max_length=200)
    amount: int = Field(description="Сумма платежа в копейках")


class SbpPaymentOut(BaseModel):
    id: UUID
    order_id: str
    description: str
    buyer: str
    created_by: str
    amount: int
    currency: str
    state: str
    provider_status: str
    qr_data_url: str
    last_error: str
    expires_at: datetime | None
    confirmed_at: datetime | None
    created_at: datetime
    is_seen: bool


class SbpPaymentListOut(BaseModel):
    total: int
    unseen_confirmed_count: int
    items: list[SbpPaymentOut]


class SbpPaymentConfigOut(BaseModel):
    enabled: bool
    min_amount: int
    max_amount: int
    qr_lifetime_minutes: int


def _bool_env(name: str, default: str = "false") -> bool:
    # Читает булевую настройку одинаково для локального и серверного окружения.
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def payments_enabled() -> bool:
    # Опасное внешнее действие включается только явным флагом окружения.
    return _bool_env("CRM_TBANK_SBP_ENABLED")


def min_payment_amount() -> int:
    # Минимум Т-Банка для СБП — 10 рублей; значение хранится в копейках.
    return max(1_000, int(os.getenv("CRM_TBANK_SBP_MIN_AMOUNT", "1000") or "1000"))


def max_payment_amount() -> int:
    # Верхняя граница защищает оператора от случайно введённой слишком большой суммы.
    configured = int(os.getenv("CRM_TBANK_SBP_MAX_AMOUNT", "10000000") or "10000000")
    return max(min_payment_amount(), configured)


def qr_lifetime_minutes() -> int:
    # Динамический QR живёт ограниченное время, которое передаём банку в Init.
    return max(1, min(int(os.getenv("CRM_TBANK_SBP_QR_LIFETIME_MINUTES", "15") or "15"), 1440))


def tbank_settings() -> TBankSettings:
    # Собирает реквизиты интеграции без безопасных значений по умолчанию для секретов.
    settings = TBankSettings(
        base_url=str(os.getenv("TBANK_BASE_URL", "https://securepay.tinkoff.ru/v2")).strip().rstrip("/"),
        terminal_key=str(os.getenv("TBANK_TERMINAL_KEY", "")).strip(),
        password=str(os.getenv("TBANK_PASSWORD", "")).strip(),
        notification_url=str(os.getenv("TBANK_NOTIFICATION_URL", "")).strip(),
        success_url=str(os.getenv("TBANK_SUCCESS_URL", "")).strip(),
        fail_url=str(os.getenv("TBANK_FAIL_URL", "")).strip(),
        timeout_seconds=max(3, min(int(os.getenv("TBANK_REQUEST_TIMEOUT_SECONDS", "15") or "15"), 60)),
    )
    if not settings.terminal_key or not settings.password:
        raise TBankError("Не заданы TBANK_TERMINAL_KEY и TBANK_PASSWORD")
    if not settings.notification_url or not settings.success_url or not settings.fail_url:
        raise TBankError("Не заданы URL уведомления, успеха и ошибки Т-Банка")
    return settings


def payment_receipt(*, amount: int, description: str) -> dict[str, Any]:
    """Формирует чек ФФД 1.2: услуга, полный расчёт, ставка из окружения."""
    email = str(os.getenv("TBANK_RECEIPT_EMAIL", "")).strip().lower()
    taxation = str(os.getenv("TBANK_RECEIPT_TAXATION", "")).strip().lower()
    tax = str(os.getenv("TBANK_RECEIPT_TAX", "")).strip().lower()
    if not email or len(email) > 64 or "@" not in email:
        raise TBankError("Не задан корректный TBANK_RECEIPT_EMAIL")
    if taxation not in RECEIPT_TAXATIONS:
        raise TBankError("Не задан корректный TBANK_RECEIPT_TAXATION")
    if tax not in RECEIPT_TAXES:
        raise TBankError("Не задан корректный TBANK_RECEIPT_TAX")
    return {
        "FfdVersion": "1.2",
        "Email": email,
        "Taxation": taxation,
        "Items": [
            {
                "Name": description,
                "Price": amount,
                "Quantity": 1,
                "Amount": amount,
                "Tax": tax,
                "PaymentMethod": "full_payment",
                "PaymentObject": "service",
                "MeasurementUnit": "шт",
            }
        ],
    }


def _token_value(value: Any) -> str:
    # Булевы поля участвуют в подписи в нижнем регистре по протоколу банка.
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def make_token(payload: dict[str, Any], password: str) -> str:
    """Считает SHA-256 только по корневым скалярным полям запроса."""
    values: dict[str, Any] = {"Password": password}
    for key, value in payload.items():
        if key in {"Token", "Password"} or value is None or isinstance(value, (dict, list, tuple)):
            continue
        values[key] = value
    source = "".join(_token_value(values[key]) for key in sorted(values))
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def notification_token_is_valid(payload: dict[str, Any], password: str) -> bool:
    # Сравнивает подписи без утечки информации о первом несовпавшем символе.
    supplied = str(payload.get("Token") or "")
    return bool(supplied) and hmac.compare_digest(supplied.lower(), make_token(payload, password).lower())


def _ssl_context() -> ssl.SSLContext:
    # Расширяет доверие только для клиента Т-Банка, не меняя глобальный trust store контейнера.
    ca_bundle = str(os.getenv("TBANK_CA_BUNDLE", "")).strip()
    try:
        import certifi

        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context = ssl.create_default_context()
    if ca_bundle:
        context.load_verify_locations(cafile=ca_bundle)
        return context
    cert_dir = Path(__file__).resolve().parents[1] / "certs"
    for filename in ("russian_trusted_root_ca.crt", "russian_trusted_sub_ca.crt"):
        cert_path = cert_dir / filename
        if cert_path.exists():
            context.load_verify_locations(cafile=str(cert_path))
    return context


class TBankClient:
    """Минимальный подписанный клиент методов Init, GetQr и GetState."""

    def __init__(self, settings: TBankSettings) -> None:
        self.settings = settings

    def call(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        # Подписывает JSON и различает окончательный отказ и неопределённую сетевую ошибку.
        body = {**payload, "TerminalKey": self.settings.terminal_key}
        body["Token"] = make_token(body, self.settings.password)
        request = urllib.request.Request(
            f"{self.settings.base_url}/{method}",
            data=json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.settings.timeout_seconds, context=_ssl_context()
            ) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                error_payload = json.loads(exc.read().decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                error_payload = {}
            message = str(error_payload.get("Message") or error_payload.get("Details") or f"HTTP {exc.code}")
            raise TBankError(message, uncertain=int(exc.code) in {408, 429} or int(exc.code) >= 500) from exc
        except (TimeoutError, urllib.error.URLError, OSError) as exc:
            raise TBankError("Т-Банк временно не ответил", uncertain=True) from exc
        except (ValueError, UnicodeDecodeError) as exc:
            raise TBankError("Т-Банк вернул некорректный ответ", uncertain=True) from exc
        if not isinstance(result, dict):
            raise TBankError("Т-Банк вернул некорректный ответ", uncertain=True)
        if not bool(result.get("Success")):
            code = str(result.get("ErrorCode") or "")
            message = str(result.get("Message") or result.get("Details") or "Платёж отклонён")
            raise TBankError(f"{message} ({code})" if code else message)
        return result

    def init(
        self,
        *,
        order_id: str,
        amount: int,
        description: str,
        expires_at: datetime,
        receipt: dict[str, Any],
    ) -> dict[str, Any]:
        # Создаёт новый платёж; buyer намеренно отсутствует во внешнем payload.
        return self.call(
            "Init",
            {
                "Amount": amount,
                "OrderId": order_id,
                "Description": description,
                "PayType": "O",
                "NotificationURL": self.settings.notification_url,
                "SuccessURL": self.settings.success_url,
                "FailURL": self.settings.fail_url,
                "RedirectDueDate": expires_at.isoformat(timespec="seconds"),
                "Receipt": receipt,
            },
        )

    def get_qr(self, payment_id: str) -> dict[str, Any]:
        # Запрашивает изображение динамического QR именно для СБП.
        return self.call("GetQr", {"PaymentId": payment_id, "DataType": "IMAGE", "PaymentMethod": "SBP"})

    def get_state(self, payment_id: str) -> dict[str, Any]:
        # Перепроверяет платёж, если webhook задержался или не был доставлен.
        return self.call("GetState", {"PaymentId": payment_id})


def qr_data_url(value: Any) -> str:
    """Принимает SVG/base64 и возвращает безопасный data URL только для img."""
    raw = str(value or "").strip()
    if raw.startswith("data:image/svg+xml;base64,"):
        encoded = raw.split(",", 1)[1]
        try:
            svg = base64.b64decode(encoded, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise TBankError("Т-Банк вернул повреждённый QR-код") from exc
    elif raw.startswith("<svg") or raw.startswith("<?xml"):
        svg = raw
    else:
        try:
            svg = base64.b64decode(raw, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise TBankError("Т-Банк вернул QR-код неизвестного формата") from exc
    lowered = svg.lower()
    unsafe_markers = ("<script", "javascript:", "onload=", "onerror=", "<foreignobject")
    if "<svg" not in lowered or any(marker in lowered for marker in unsafe_markers):
        raise TBankError("Т-Банк вернул небезопасное изображение QR-кода")
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def provider_state(status: str) -> str:
    # Приводит статусы банка к небольшому набору состояний интерфейса CRM.
    normalized = str(status or "").strip().upper()
    if normalized == "CONFIRMED":
        return "confirmed"
    if normalized == "DEADLINE_EXPIRED":
        return "expired"
    if normalized == "CANCELED":
        return "cancelled"
    if normalized in FINAL_FAILURE_STATUSES:
        return "rejected"
    return "pending"


def should_apply_provider_state(current_state: str, incoming_state: str) -> bool:
    """Не позволяет запоздалому промежуточному статусу откатить завершённый платёж."""
    current = str(current_state or "").strip().lower()
    incoming = str(incoming_state or "").strip().lower()
    if current == "confirmed":
        return incoming == "confirmed"
    if incoming == "confirmed":
        return True
    if current in FINAL_PAYMENT_STATES:
        return incoming == current
    return True


PAYMENT_SELECT = """
SELECT p.public_id, p.order_id, p.description, p.buyer,
       COALESCE(NULLIF(BTRIM(creator.name), ''), p.created_by_username) AS created_by,
       p.amount, p.currency, p.state, p.provider_status, p.qr_data_url, p.last_error,
       p.expires_at, p.confirmed_at, p.created_at,
       EXISTS(
         SELECT 1 FROM app.tbank_sbp_payment_reads r
         WHERE r.payment_id=p.payment_id AND r.user_id=%s
       ) AS is_seen
FROM app.tbank_sbp_payments p
LEFT JOIN app.users creator ON creator.user_id=p.created_by_user_id
"""


def _payment_out(row) -> SbpPaymentOut:
    # Преобразует стабильный SQL-кортеж в публичную модель без внутренних ключей.
    return SbpPaymentOut(
        id=row[0], order_id=str(row[1]), description=str(row[2]), buyer=str(row[3]),
        created_by=str(row[4]), amount=int(row[5]), currency=str(row[6]), state=str(row[7]),
        provider_status=str(row[8] or ""), qr_data_url=str(row[9] or ""), last_error=str(row[10] or ""),
        expires_at=row[11], confirmed_at=row[12], created_at=row[13], is_seen=bool(row[14]),
    )


@dataclass(frozen=True)
class ClaimedPayment:
    id: int
    provider_payment_id: str
    amount: int
    lock_token: UUID
    attempt_count: int


class TBankReconciliationProcessor:
    """Сверяет незавершённые платежи общей безопасной очередью PostgreSQL."""

    def __init__(self, *, database_url: str, psycopg, client_factory=TBankClient) -> None:
        self._database_url = database_url
        self._psycopg = psycopg
        self._client_factory = client_factory

    def process_pending(self, limit: int = 5) -> int:
        # Забирает ограниченную пачку, чтобы одна интеграция не заняла весь пул API.
        if not payments_enabled():
            return 0
        settings = tbank_settings()
        processed = 0
        for _ in range(max(1, min(int(limit), 50))):
            claimed = self._claim()
            if claimed is None:
                break
            processed += 1
            try:
                result = self._client_factory(settings).get_state(claimed.provider_payment_id)
                response_payment_id = str(result.get("PaymentId") or claimed.provider_payment_id)
                response_amount = int(result.get("Amount"))
                if response_payment_id != claimed.provider_payment_id or response_amount != claimed.amount:
                    raise TBankError("GetState вернул платёж с несовпадающими реквизитами")
                self._finish(claimed, str(result.get("Status") or ""))
            except Exception as exc:
                self._retry(claimed, str(exc))
        return processed

    def _claim(self) -> ClaimedPayment | None:
        # SKIP LOCKED не даёт двум API-репликам сверять одну операцию одновременно.
        token = uuid4()
        with self._psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT payment_id, provider_payment_id, amount, reconcile_attempt_count
                    FROM app.tbank_sbp_payments
                    WHERE state='pending' AND provider_payment_id IS NOT NULL
                      AND next_reconcile_at<=now()
                      AND (reconcile_locked_until IS NULL OR reconcile_locked_until<now())
                    ORDER BY next_reconcile_at, payment_id
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()
                if not row:
                    return None
                cursor.execute(
                    """
                    UPDATE app.tbank_sbp_payments
                    SET reconcile_lock_token=%s, reconcile_locked_until=now()+interval '90 seconds',
                        reconcile_attempt_count=reconcile_attempt_count+1, updated_at=now()
                    WHERE payment_id=%s
                    """,
                    (token, row[0]),
                )
        return ClaimedPayment(
            id=int(row[0]), provider_payment_id=str(row[1]), amount=int(row[2]),
            lock_token=token, attempt_count=int(row[3]) + 1,
        )

    def _finish(self, claimed: ClaimedPayment, status: str) -> None:
        # Фиксирует только допустимый переход и освобождает аренду операции.
        state = provider_state(status)
        with self._psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT state FROM app.tbank_sbp_payments WHERE payment_id=%s AND reconcile_lock_token=%s FOR UPDATE",
                    (claimed.id, claimed.lock_token),
                )
                current_row = cursor.fetchone()
                if not current_row:
                    return
                if not should_apply_provider_state(str(current_row[0]), state):
                    cursor.execute(
                        """
                        UPDATE app.tbank_sbp_payments
                        SET next_reconcile_at=NULL, reconcile_lock_token=NULL,
                            reconcile_locked_until=NULL, last_error='', updated_at=now()
                        WHERE payment_id=%s
                        """,
                        (claimed.id,),
                    )
                    return
                cursor.execute(
                    """
                    UPDATE app.tbank_sbp_payments
                    SET provider_status=%s, state=%s,
                        confirmed_at=CASE WHEN %s='confirmed' THEN COALESCE(confirmed_at, now()) ELSE confirmed_at END,
                        next_reconcile_at=CASE WHEN %s='pending' THEN now()+interval '1 minute' ELSE NULL END,
                        reconcile_lock_token=NULL, reconcile_locked_until=NULL, last_error='', updated_at=now()
                    WHERE payment_id=%s
                    """,
                    (status.upper(), state, state, state, claimed.id),
                )

    def _retry(self, claimed: ClaimedPayment, message: str) -> None:
        # Ограниченный backoff не создаёт частый поток запросов при недоступности банка.
        delay = min(15 * (2 ** max(0, min(claimed.attempt_count, 8) - 1)), 900)
        with self._psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE app.tbank_sbp_payments
                    SET next_reconcile_at=now()+(%s*interval '1 second'), reconcile_lock_token=NULL,
                        reconcile_locked_until=NULL, last_error=%s, updated_at=now()
                    WHERE payment_id=%s AND reconcile_lock_token=%s AND state='pending'
                    """,
                    (delay, message[:500], claimed.id, claimed.lock_token),
                )


def build_tbank_reconciliation_processor(*, database_url: str, psycopg) -> TBankReconciliationProcessor:
    # Создаёт один stateless-процессор, пригодный для нескольких API-реплик.
    return TBankReconciliationProcessor(database_url=database_url, psycopg=psycopg)


def mount_tbank_sbp_payment_routes(
    app: FastAPI,
    *,
    database_url: str,
    psycopg,
    get_current_user: Callable,
    get_user_id: Callable,
) -> None:
    """Подключает общий для CRM API платежей и публичный подписанный webhook."""

    def current_user_id(connection, user) -> int:
        # Получает id только по проверенному JWT username, а не из пользовательского запроса.
        return int(get_user_id(connection, str(user.username)))

    def find_payment(connection, *, public_id: UUID, user_id: int):
        # Возвращает платёж всем сотрудникам и добавляет персональную отметку просмотра.
        with connection.cursor() as cursor:
            cursor.execute(f"{PAYMENT_SELECT} WHERE p.public_id=%s", (user_id, public_id))
            return cursor.fetchone()

    def refresh_missing_qr(public_id: UUID, row):
        # Повторяет только безопасный GetQr, если Init прошёл, а изображение не было получено.
        if not row or str(row[7]) != "pending" or str(row[9] or ""):
            return row
        with psycopg.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT provider_payment_id FROM app.tbank_sbp_payments WHERE public_id=%s",
                    (public_id,),
                )
                payment_row = cursor.fetchone()
        payment_id = str(payment_row[0] or "") if payment_row else ""
        if not payment_id:
            return row
        try:
            qr_url = qr_data_url(TBankClient(tbank_settings()).get_qr(payment_id).get("Data"))
            with psycopg.connect(database_url) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE app.tbank_sbp_payments SET qr_data_url=%s, last_error='', updated_at=now() WHERE public_id=%s",
                        (qr_url, public_id),
                    )
        except TBankError:
            return row
        return None

    @app.get("/payments/tbank/sbp/config", response_model=SbpPaymentConfigOut)
    def get_payment_config(user=Depends(get_current_user)) -> SbpPaymentConfigOut:
        # Аутентификация нужна даже для лимитов, чтобы не раскрывать включённые интеграции наружу.
        del user
        configured = False
        try:
            tbank_settings()
            payment_receipt(amount=min_payment_amount(), description="Проверка настроек")
            configured = True
        except TBankError:
            pass
        return SbpPaymentConfigOut(
            enabled=payments_enabled() and configured,
            min_amount=min_payment_amount(),
            max_amount=max_payment_amount(),
            qr_lifetime_minutes=qr_lifetime_minutes(),
        )

    @app.post("/payments/tbank/sbp", response_model=SbpPaymentOut, status_code=201)
    def create_payment(payload: SbpPaymentCreateIn, user=Depends(get_current_user)) -> SbpPaymentOut:
        # Записывает уникальную операцию до первого внешнего запроса, исключая гонки между сотрудниками.
        if not payments_enabled():
            raise HTTPException(status_code=503, detail="Платежи СБП пока выключены")
        description = str(payload.description or "").strip()
        buyer = str(payload.buyer or "").strip()
        if not description or len(description) > 128:
            raise HTTPException(status_code=400, detail="Описание должно содержать от 1 до 128 символов")
        if not buyer or len(buyer) > 200:
            raise HTTPException(status_code=400, detail="Покупатель должен содержать от 1 до 200 символов")
        if payload.amount < min_payment_amount() or payload.amount > max_payment_amount():
            raise HTTPException(
                status_code=400,
                detail=f"Введите сумму от {min_payment_amount() // 100} до {max_payment_amount() // 100} ₽",
            )
        try:
            settings = tbank_settings()
            receipt = payment_receipt(amount=payload.amount, description=description)
        except TBankError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        order_id = f"crm_{uuid4().hex}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=qr_lifetime_minutes())
        with psycopg.connect(database_url) as connection:
            creator_id = current_user_id(connection, user)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app.tbank_sbp_payments(
                      created_by_user_id, created_by_username, buyer, description,
                      terminal_key, order_id, amount, state, expires_at, next_reconcile_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'init_pending', %s, %s)
                    RETURNING payment_id, public_id
                    """,
                    (
                        creator_id, str(user.username), buyer, description, settings.terminal_key,
                        order_id, payload.amount, expires_at, datetime.now(timezone.utc) + timedelta(minutes=1),
                    ),
                )
                payment_db_id, public_id = cursor.fetchone()
        client = TBankClient(settings)
        try:
            init_result = client.init(
                order_id=order_id,
                amount=payload.amount,
                description=description,
                expires_at=expires_at,
                receipt=receipt,
            )
            provider_payment_id = str(init_result.get("PaymentId") or "").strip()
            if not provider_payment_id:
                raise TBankError("Т-Банк не вернул идентификатор платежа", uncertain=True)
        except TBankError as exc:
            with psycopg.connect(database_url) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE app.tbank_sbp_payments SET state=%s, last_error=%s, updated_at=now() WHERE payment_id=%s",
                        ("init_unknown" if exc.uncertain else "failed", str(exc)[:500], payment_db_id),
                    )
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        provider_status = str(init_result.get("Status") or "NEW")
        with psycopg.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE app.tbank_sbp_payments
                    SET provider_payment_id=%s, provider_status=%s, state='pending', updated_at=now()
                    WHERE payment_id=%s AND state='init_pending'
                    """,
                    (provider_payment_id, provider_status, payment_db_id),
                )
        try:
            qr_url = qr_data_url(client.get_qr(provider_payment_id).get("Data"))
            qr_error = ""
        except TBankError as exc:
            qr_url = ""
            qr_error = f"Платёж создан, но QR-код пока недоступен: {exc}"
        with psycopg.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE app.tbank_sbp_payments SET qr_data_url=%s, last_error=%s, updated_at=now() WHERE payment_id=%s",
                    (qr_url, qr_error[:500], payment_db_id),
                )
                cursor.execute(f"{PAYMENT_SELECT} WHERE p.public_id=%s", (creator_id, public_id))
                row = cursor.fetchone()
        return _payment_out(row)

    @app.get("/payments/tbank/sbp", response_model=SbpPaymentListOut)
    def list_payments(
        mine: bool = Query(False),
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
        user=Depends(get_current_user),
    ) -> SbpPaymentListOut:
        # Возвращает общую историю; mine оставляет удобный фильтр по текущему сотруднику.
        with psycopg.connect(database_url) as connection:
            user_id = current_user_id(connection, user)
            filters = "WHERE p.created_by_user_id=%s" if mine else ""
            filter_params = (user_id,) if mine else ()
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM app.tbank_sbp_payments p {filters}", filter_params)
                total = int(cursor.fetchone()[0])
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM app.tbank_sbp_payments p
                    WHERE p.state='confirmed'
                      AND NOT EXISTS(
                        SELECT 1 FROM app.tbank_sbp_payment_reads r
                        WHERE r.payment_id=p.payment_id AND r.user_id=%s
                      )
                    """,
                    (user_id,),
                )
                unseen_count = int(cursor.fetchone()[0])
                cursor.execute(
                    f"{PAYMENT_SELECT} {filters} ORDER BY p.created_at DESC, p.payment_id DESC LIMIT %s OFFSET %s",
                    (user_id, *filter_params, limit, offset),
                )
                rows = cursor.fetchall()
        return SbpPaymentListOut(
            total=total,
            unseen_confirmed_count=unseen_count,
            items=[_payment_out(row) for row in rows],
        )

    @app.post("/payments/tbank/sbp/mark-seen")
    def mark_confirmed_seen(user=Depends(get_current_user)) -> dict[str, bool]:
        # Одним запросом снимает badge со всех подтверждённых платежей для текущего сотрудника.
        with psycopg.connect(database_url) as connection:
            user_id = current_user_id(connection, user)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app.tbank_sbp_payment_reads(payment_id, user_id)
                    SELECT payment_id, %s
                    FROM app.tbank_sbp_payments
                    WHERE state='confirmed'
                    ON CONFLICT (payment_id, user_id) DO UPDATE SET seen_at=now()
                    """,
                    (user_id,),
                )
        return {"ok": True}

    @app.get("/payments/tbank/sbp/{payment_public_id}", response_model=SbpPaymentOut)
    def get_payment(payment_public_id: UUID, user=Depends(get_current_user)) -> SbpPaymentOut:
        # Перечитывает конкретную операцию независимо от того, кто её создал.
        with psycopg.connect(database_url) as connection:
            user_id = current_user_id(connection, user)
            row = find_payment(connection, public_id=payment_public_id, user_id=user_id)
        if not row:
            raise HTTPException(status_code=404, detail="Платёж не найден")
        refreshed = refresh_missing_qr(payment_public_id, row)
        if refreshed is None:
            with psycopg.connect(database_url) as connection:
                row = find_payment(connection, public_id=payment_public_id, user_id=user_id)
        return _payment_out(row)

    @app.post("/payments/tbank/notifications", response_class=PlainTextResponse)
    async def tbank_notification(request: Request) -> PlainTextResponse:
        # Проверяет подпись и идемпотентно применяет статус к найденной операции CRM.
        body = await request.body()
        max_body_bytes = max(
            1_024,
            min(int(os.getenv("TBANK_NOTIFICATION_MAX_BODY_BYTES", "65536") or "65536"), 1_048_576),
        )
        if len(body) > max_body_bytes:
            raise HTTPException(status_code=413, detail="Payload is too large")
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeDecodeError) as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Invalid payload")
        try:
            settings = tbank_settings()
        except TBankError as exc:
            raise HTTPException(status_code=503, detail="Payment notifications are not configured") from exc
        if str(payload.get("TerminalKey") or "") != settings.terminal_key:
            raise HTTPException(status_code=403, detail="Unknown terminal")
        if not notification_token_is_valid(payload, settings.password):
            raise HTTPException(status_code=403, detail="Invalid token")
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        order_id = str(payload.get("OrderId") or "")
        provider_payment_id = str(payload.get("PaymentId") or "")
        status = str(payload.get("Status") or "").upper()
        try:
            amount = int(payload.get("Amount"))
        except (TypeError, ValueError):
            amount = None
        with psycopg.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app.tbank_sbp_payment_events(
                      event_fingerprint, terminal_key, order_id, provider_payment_id,
                      provider_status, amount, signature_valid
                    ) VALUES (%s, %s, %s, %s, %s, %s, true)
                    ON CONFLICT (event_fingerprint) DO NOTHING
                    RETURNING event_id
                    """,
                    (fingerprint, settings.terminal_key, order_id, provider_payment_id, status, amount),
                )
                event_row = cursor.fetchone()
                if not event_row:
                    return PlainTextResponse("OK")
                event_id = int(event_row[0])
                cursor.execute(
                    """
                    SELECT payment_id, amount, provider_payment_id, state
                    FROM app.tbank_sbp_payments
                    WHERE order_id=%s AND terminal_key=%s
                    FOR UPDATE
                    """,
                    (order_id, settings.terminal_key),
                )
                payment = cursor.fetchone()
                if not payment:
                    cursor.execute(
                        """
                        UPDATE app.tbank_sbp_payment_events
                        SET processing_state='ignored', processed_at=now(), last_error='unknown order'
                        WHERE event_id=%s
                        """,
                        (event_id,),
                    )
                    return PlainTextResponse("OK")
                payment_db_id, expected_amount, known_payment_id, current_state = payment
                if (
                    not provider_payment_id
                    or str(known_payment_id or "") not in {"", provider_payment_id}
                    or amount != int(expected_amount)
                ):
                    cursor.execute(
                        """
                        UPDATE app.tbank_sbp_payment_events
                        SET processing_state='failed', processed_at=now(), last_error='payment identity mismatch'
                        WHERE event_id=%s
                        """,
                        (event_id,),
                    )
                    # Сохраняем факт несовпадения до HTTP 409, чтобы расследование не зависело от повторной доставки.
                    connection.commit()
                    raise HTTPException(status_code=409, detail="Payment identity mismatch")
                state = provider_state(status)
                if should_apply_provider_state(str(current_state), state):
                    cursor.execute(
                        """
                        UPDATE app.tbank_sbp_payments
                        SET provider_payment_id=COALESCE(provider_payment_id, %s), provider_status=%s,
                            state=%s,
                            confirmed_at=CASE WHEN %s='confirmed' THEN COALESCE(confirmed_at, now()) ELSE confirmed_at END,
                            next_reconcile_at=CASE WHEN %s='pending' THEN now()+interval '1 minute' ELSE NULL END,
                            last_error='', updated_at=now()
                        WHERE payment_id=%s
                        """,
                        (provider_payment_id, status, state, state, state, payment_db_id),
                    )
                cursor.execute(
                    """
                    UPDATE app.tbank_sbp_payment_events
                    SET processing_state='processed', processed_at=now()
                    WHERE event_id=%s
                    """,
                    (event_id,),
                )
        return PlainTextResponse("OK")
