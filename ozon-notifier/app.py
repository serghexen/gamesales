"""Отправляет в Telegram и обновляет статусы цифровых заказов Ozon."""

from __future__ import annotations

from dataclasses import dataclass
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
    poll_interval_sec: int


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


def load_settings() -> Settings:
    # Собирает все настройки в одном месте, чтобы контейнер одинаково работал в dev, staging и production.
    return Settings(
        database_url=env_required("DATABASE_URL"),
        bot_token=env_required("OZON_NOTIFIER_BOT_TOKEN"),
        poll_interval_sec=env_int("OZON_NOTIFIER_POLL_INTERVAL_SEC", default=15, minimum=5),
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


def message_text(order: dict[str, Any]) -> str:
    # Сохраняет факт поступления в заголовке и отдельно показывает актуальную стадию обработки заказа.
    order_number = str(order.get("order_number") or order.get("posting_number") or "—")
    product_name = str(order.get("product_name") or "Товар не указан").strip()[:1000]
    return "\n".join(
        (
            "🛍 Поступил новый заказ Ozon",
            f"Заказ: {order_number}",
            f"Товар: {product_name}",
            f"Количество: {int(order.get('required_qty') or 1)}",
            f"Текущий статус: {status_title(str(order.get('status') or ''))}",
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


def send_text(settings: Settings, chat_id: int, text: str) -> int:
    # Отправляет служебный ответ или первое уведомление и возвращает его ID для последующего редактирования.
    data = telegram_request(settings, "sendMessage", {"chat_id": chat_id, "text": text})
    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    message_id = int(result.get("message_id") or 0)
    if message_id <= 0:
        raise RuntimeError("Telegram API did not return message_id")
    return message_id


def send_message(settings: Settings, chat_id: int, order: dict[str, Any]) -> int:
    # Создаёт первое сообщение о заказе и возвращает его ID для дальнейшего редактирования.
    return send_text(settings, chat_id, message_text(order))


def edit_message(settings: Settings, chat_id: int, message_id: int, order: dict[str, Any]) -> None:
    # Обновляет исходное сообщение, чтобы один заказ не засорял чат несколькими уведомлениями.
    try:
        telegram_request(
            settings,
            "editMessageText",
            {"chat_id": chat_id, "message_id": message_id, "text": message_text(order)},
        )
    except RuntimeError as exc:
        if "message is not modified" not in str(exc).lower():
            raise


def initialize_tracking(conn: psycopg.Connection[Any]) -> None:
    # На первом запуске запоминает границу старой истории, чтобы новые подписчики не получили накопившиеся заказы.
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
        cursor.execute(
            """
            UPDATE app.ozon_order_notifier_state
            SET baseline_order_id=(SELECT COALESCE(MAX(id), 0) FROM app.marketplace_ozon_digital_orders)
            WHERE notifier_code=%s AND baseline_order_id=0
            """,
            (NOTIFIER_CODE,),
        )
    conn.commit()


def command_kind(text: Any) -> str:
    # Распознаёт команды подписки с суффиксом имени бота, который Telegram добавляет в групповых чатах.
    command = str(text or "").strip().split(maxsplit=1)[0].lower().split("@", 1)[0]
    if command in {"/start", "/subscribe"}:
        return "subscribe"
    if command in {"/stop", "/unsubscribe"}:
        return "unsubscribe"
    return ""


def save_update_offset(conn: psycopg.Connection[Any], update_offset: int) -> None:
    # Запоминает обработанное обновление Telegram, чтобы после рестарта команда не выполнилась повторно.
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE app.ozon_order_notifier_state
            SET telegram_update_offset=GREATEST(telegram_update_offset, %s)
            WHERE notifier_code=%s
            """,
            (update_offset, NOTIFIER_CODE),
        )
    conn.commit()


def subscribe_recipient(conn: psycopg.Connection[Any], chat: dict[str, Any]) -> None:
    # Включает уведомления для личного или группового чата только о заказах, пришедших после подписки.
    chat_id = int(chat["id"])
    with conn.cursor() as cursor:
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM app.marketplace_ozon_digital_orders")
        order_watermark = int(cursor.fetchone()[0] or 0)
        cursor.execute(
            """
            INSERT INTO app.ozon_order_notifier_recipients(chat_id, chat_type, title, orders_from_id, is_active, updated_at)
            VALUES (%s, %s, %s, %s, true, now())
            ON CONFLICT (chat_id) DO UPDATE
            SET chat_type=excluded.chat_type,
                title=excluded.title,
                orders_from_id=CASE
                  WHEN app.ozon_order_notifier_recipients.is_active THEN app.ozon_order_notifier_recipients.orders_from_id
                  ELSE excluded.orders_from_id
                END,
                is_active=true,
                updated_at=now()
            """,
            (chat_id, str(chat.get("type") or ""), str(chat.get("title") or chat.get("username") or ""), order_watermark),
        )
    conn.commit()


def unsubscribe_recipient(conn: psycopg.Connection[Any], chat_id: int) -> None:
    # Выключает уведомления, сохраняя запись чата для безопасного повторного включения через /start.
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE app.ozon_order_notifier_recipients SET is_active=false, updated_at=now() WHERE chat_id=%s",
            (chat_id,),
        )
    conn.commit()


def sync_recipients(settings: Settings) -> None:
    # Читает команды Bot API и самостоятельно ведёт список получателей, поэтому ID чата не нужно задавать в env.
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT telegram_update_offset FROM app.ozon_order_notifier_state WHERE notifier_code=%s",
                (NOTIFIER_CODE,),
            )
            state = cursor.fetchone() or {}
        offset = int(state.get("telegram_update_offset") or 0)

    data = telegram_request(settings, "getUpdates", {"offset": offset, "timeout": 0, "allowed_updates": ["message"]})
    updates = data.get("result") if isinstance(data.get("result"), list) else []
    for update in updates:
        if not isinstance(update, dict):
            continue
        update_id = int(update.get("update_id") or 0)
        message = update.get("message") if isinstance(update.get("message"), dict) else {}
        chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
        action = command_kind(message.get("text"))
        chat_id = int(chat.get("id") or 0)
        if action == "subscribe" and chat_id:
            with psycopg.connect(settings.database_url) as conn:
                subscribe_recipient(conn, chat)
            send_text(settings, chat_id, "Уведомления о новых заказах Ozon включены. Для остановки отправьте /stop.")
        elif action == "unsubscribe" and chat_id:
            with psycopg.connect(settings.database_url) as conn:
                unsubscribe_recipient(conn, chat_id)
            send_text(settings, chat_id, "Уведомления о новых заказах Ozon отключены. Чтобы включить снова, отправьте /start.")
        if update_id:
            with psycopg.connect(settings.database_url) as conn:
                save_update_offset(conn, update_id + 1)


def read_pending_orders(conn: psycopg.Connection[Any]) -> list[dict[str, Any]]:
    # Выбирает только новые заказы и сменившиеся статусы для каждого активного получателя без повторной рассылки.
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT orders.id, orders.posting_number, orders.order_number, orders.product_name, orders.required_qty,
                   orders.status, orders.waiting_deadline_at, recipient.chat_id, delivery.telegram_message_id,
                   delivery.last_status
            FROM app.ozon_order_notifier_recipients AS recipient
            JOIN app.ozon_order_notifier_state AS state ON state.notifier_code=%s
            JOIN app.marketplace_ozon_digital_orders AS orders
              ON orders.id > GREATEST(state.baseline_order_id, recipient.orders_from_id)
            LEFT JOIN app.ozon_order_notifier_deliveries AS delivery
              ON delivery.order_id=orders.id AND delivery.chat_id=recipient.chat_id
            WHERE recipient.is_active=true
              AND (
                delivery.order_id IS NULL
                OR delivery.telegram_message_id IS NULL
                OR delivery.last_status IS DISTINCT FROM orders.status
              )
            ORDER BY orders.created_at ASC NULLS LAST, orders.id ASC
            LIMIT 100
            """,
            (NOTIFIER_CODE,),
        )
        return list(cursor.fetchall())


def remember_success(conn: psycopg.Connection[Any], order: dict[str, Any], message_id: int) -> None:
    # Фиксирует ID Telegram-сообщения и текущий статус отдельно для каждого получателя после успешной доставки.
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO app.ozon_order_notifier_deliveries(
              order_id, chat_id, telegram_message_id, last_status, notified_at, last_error, updated_at
            )
            VALUES (%s, %s, %s, %s, now(), '', now())
            ON CONFLICT (order_id, chat_id) DO UPDATE
            SET telegram_message_id=excluded.telegram_message_id,
                last_status=excluded.last_status,
                notified_at=COALESCE(app.ozon_order_notifier_deliveries.notified_at, excluded.notified_at),
                last_error='',
                updated_at=now()
            """,
            (int(order["id"]), int(order["chat_id"]), message_id, str(order.get("status") or "")),
        )
    conn.commit()


def remember_error(conn: psycopg.Connection[Any], order: dict[str, Any], error: Exception) -> None:
    # Сохраняет причину сбоя, чтобы следующая проверка повторила доставку и ошибка осталась в БД для диагностики.
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO app.ozon_order_notifier_deliveries(order_id, chat_id, last_status, last_error, updated_at)
            VALUES (%s, %s, '', %s, now())
            ON CONFLICT (order_id, chat_id) DO UPDATE
            SET last_error=excluded.last_error, updated_at=now()
            """,
            (int(order["id"]), int(order["chat_id"]), str(error)[:2000]),
        )
    conn.commit()


def run_cycle(settings: Settings) -> None:
    # Выполняет одну короткую проверку БД, не удерживая соединение во время вызова Telegram API.
    with psycopg.connect(settings.database_url) as conn:
        initialize_tracking(conn)
    sync_recipients(settings)
    with psycopg.connect(settings.database_url) as conn:
        orders = read_pending_orders(conn)

    for order in orders:
        message_id = int(order.get("telegram_message_id") or 0)
        chat_id = int(order["chat_id"])
        try:
            if message_id:
                edit_message(settings, chat_id, message_id, order)
            else:
                message_id = send_message(settings, chat_id, order)
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
