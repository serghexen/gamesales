"""Отправляет в Telegram и обновляет статусы цифровых заказов Ozon."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import logging
import os
import signal
import time
from typing import Any
import urllib.error
import urllib.request

import psycopg
from psycopg.rows import dict_row


LOGGER = logging.getLogger("ozon_notifier")
NOTIFIER_CODE = "telegram_ozon_orders"
STOP_REQUESTED = False


@dataclass(frozen=True)
class Settings:
    database_url: str
    bot_token: str
    chat_id: str
    poll_interval_sec: int
    notify_existing: bool


def env_required(name: str) -> str:
    # Не запускает сервис с пустым секретом, чтобы ошибка была видна сразу в логах контейнера.
    value = str(os.getenv(name, "") or "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def env_int(name: str, default: int, minimum: int) -> int:
    # Читает интервал проверки и защищает PostgreSQL от слишком частого опроса по ошибке в настройке.
    raw = str(os.getenv(name, "") or "").strip()
    if not raw:
        return default
    try:
        return max(minimum, int(raw))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


def env_bool(name: str, default: bool = False) -> bool:
    # Разрешает явно включить уведомления по старой истории только при первом запуске сервиса.
    raw = str(os.getenv(name, "") or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    # Собирает все настройки в одном месте, чтобы контейнер одинаково работал в dev, staging и production.
    return Settings(
        database_url=env_required("DATABASE_URL"),
        bot_token=env_required("OZON_NOTIFIER_BOT_TOKEN"),
        chat_id=env_required("OZON_NOTIFIER_CHAT_ID"),
        poll_interval_sec=env_int("OZON_NOTIFIER_POLL_INTERVAL_SEC", default=15, minimum=5),
        notify_existing=env_bool("OZON_NOTIFIER_NOTIFY_EXISTING"),
    )


def status_title(status: str) -> str:
    # Переводит внутренний статус в короткую подпись, понятную в рабочем Telegram-чате.
    labels = {
        "manual_required": "Принят, ожидает обработки",
        "supplier_processing": "Обрабатывается поставщиком",
        "delivering": "Передаётся в Ozon",
        "delivered": "Выполнен",
        "cancelled": "Отменён",
    }
    return labels.get(str(status or "").strip().lower(), "Обрабатывается")


def format_datetime(value: Any) -> str:
    # Показывает дедлайн без технического формата PostgreSQL и не падает на неполной дате от Ozon.
    if isinstance(value, datetime):
        return value.astimezone().strftime("%d.%m.%Y %H:%M")
    return "—"


def message_text(order: dict[str, Any]) -> str:
    # Формирует одно компактное сообщение, которое затем редактируется при изменении статуса заказа.
    order_number = str(order.get("order_number") or order.get("posting_number") or "—")
    product_name = str(order.get("product_name") or "Товар не указан").strip()[:1000]
    return "\n".join(
        (
            "🛍 Новый заказ Ozon",
            f"Заказ: {order_number}",
            f"Товар: {product_name}",
            f"Количество: {int(order.get('required_qty') or 1)}",
            f"Статус: {status_title(str(order.get('status') or ''))}",
            f"Дедлайн выдачи: {format_datetime(order.get('waiting_deadline_at'))}",
        )
    )


def telegram_request(settings: Settings, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    # Вызывает Bot API напрямую, поэтому сервис не зависит от Telegram-аккаунта, подключённого в основном приложении.
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{settings.bot_token}/{method}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram API returned HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Telegram API is unavailable: {exc.reason}") from exc
    if not isinstance(data, dict) or not data.get("ok"):
        raise RuntimeError(f"Telegram API rejected request: {str(data)[:500]}")
    return data


def send_message(settings: Settings, order: dict[str, Any]) -> int:
    # Создаёт первое сообщение о заказе и возвращает его ID для дальнейшего редактирования.
    data = telegram_request(settings, "sendMessage", {"chat_id": settings.chat_id, "text": message_text(order)})
    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    message_id = int(result.get("message_id") or 0)
    if message_id <= 0:
        raise RuntimeError("Telegram API did not return message_id")
    return message_id


def edit_message(settings: Settings, message_id: int, order: dict[str, Any]) -> None:
    # Обновляет исходное сообщение, чтобы один заказ не засорял чат несколькими уведомлениями.
    try:
        telegram_request(
            settings,
            "editMessageText",
            {"chat_id": settings.chat_id, "message_id": message_id, "text": message_text(order)},
        )
    except RuntimeError as exc:
        if "message is not modified" not in str(exc).lower():
            raise


def initialize_tracking(conn: psycopg.Connection[Any], settings: Settings) -> bool:
    # На первом запуске запоминает текущую историю без рассылки, чтобы чат не получил старые заказы.
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO app.ozon_order_notifier_state(notifier_code)
            VALUES (%s)
            ON CONFLICT (notifier_code) DO NOTHING
            RETURNING notifier_code
            """,
            (NOTIFIER_CODE,),
        )
        initialized_now = cursor.fetchone() is not None
        if initialized_now and not settings.notify_existing:
            cursor.execute(
                """
                INSERT INTO app.marketplace_ozon_order_notifications(order_id, last_status, is_baseline)
                SELECT orders.id, orders.status, true
                FROM app.marketplace_ozon_digital_orders AS orders
                ON CONFLICT (order_id) DO NOTHING
                """
            )
    conn.commit()
    return initialized_now


def read_pending_orders(conn: psycopg.Connection[Any]) -> list[dict[str, Any]]:
    # Выбирает только новые заказы и сменившиеся статусы, оставляя историю без повторной рассылки.
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT orders.id, orders.posting_number, orders.order_number, orders.product_name, orders.required_qty,
                   orders.status, orders.waiting_deadline_at, notification.telegram_message_id,
                   notification.last_status, notification.is_baseline
            FROM app.marketplace_ozon_digital_orders AS orders
            LEFT JOIN app.marketplace_ozon_order_notifications AS notification ON notification.order_id=orders.id
            WHERE COALESCE(notification.is_baseline, false)=false
              AND (
                notification.order_id IS NULL
                OR notification.telegram_message_id IS NULL
                OR notification.last_status IS DISTINCT FROM orders.status
              )
            ORDER BY orders.created_at ASC NULLS LAST, orders.id ASC
            LIMIT 100
            """
        )
        return list(cursor.fetchall())


def remember_success(conn: psycopg.Connection[Any], order: dict[str, Any], message_id: int) -> None:
    # Фиксирует ID Telegram-сообщения и текущий статус только после успешной отправки или редактирования.
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO app.marketplace_ozon_order_notifications(
              order_id, telegram_message_id, last_status, notified_at, last_error, updated_at
            )
            VALUES (%s, %s, %s, now(), '', now())
            ON CONFLICT (order_id) DO UPDATE
            SET telegram_message_id=excluded.telegram_message_id,
                last_status=excluded.last_status,
                notified_at=COALESCE(app.marketplace_ozon_order_notifications.notified_at, excluded.notified_at),
                last_error='',
                updated_at=now()
            """,
            (int(order["id"]), message_id, str(order.get("status") or "")),
        )
    conn.commit()


def remember_error(conn: psycopg.Connection[Any], order: dict[str, Any], error: Exception) -> None:
    # Сохраняет причину сбоя, чтобы следующая проверка повторила доставку и ошибка осталась в БД для диагностики.
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO app.marketplace_ozon_order_notifications(order_id, last_status, last_error, updated_at)
            VALUES (%s, '', %s, now())
            ON CONFLICT (order_id) DO UPDATE
            SET last_error=excluded.last_error, updated_at=now()
            """,
            (int(order["id"]), str(error)[:2000]),
        )
    conn.commit()


def run_cycle(settings: Settings) -> None:
    # Выполняет одну короткую проверку БД, не удерживая соединение во время вызова Telegram API.
    with psycopg.connect(settings.database_url) as conn:
        initialized_now = initialize_tracking(conn, settings)
        if initialized_now and not settings.notify_existing:
            LOGGER.info("Existing Ozon orders were saved as baseline without notifications")
            return
        orders = read_pending_orders(conn)

    for order in orders:
        message_id = int(order.get("telegram_message_id") or 0)
        try:
            if message_id:
                edit_message(settings, message_id, order)
            else:
                message_id = send_message(settings, order)
            with psycopg.connect(settings.database_url) as conn:
                remember_success(conn, order, message_id)
            LOGGER.info("Order %s was notified with status %s", order["id"], order["status"])
        except Exception as exc:
            LOGGER.exception("Cannot notify order %s", order["id"])
            with psycopg.connect(settings.database_url) as conn:
                remember_error(conn, order, exc)


def request_stop(_signal: int, _frame: Any) -> None:
    # Завершает цикл по сигналу Docker, чтобы контейнер останавливался без обрыва посередине ожидания.
    global STOP_REQUESTED
    STOP_REQUESTED = True


def main() -> None:
    # Запускает вечный цикл с повтором после временных проблем PostgreSQL или Telegram.
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    LOGGER.info("Ozon notifier started with %s-second polling", settings.poll_interval_sec)
    while not STOP_REQUESTED:
        try:
            run_cycle(settings)
        except Exception:
            LOGGER.exception("Ozon notifier cycle failed")
        for _ in range(settings.poll_interval_sec):
            if STOP_REQUESTED:
                break
            time.sleep(1)


if __name__ == "__main__":
    main()
