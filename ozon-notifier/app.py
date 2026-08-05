"""Отправляет в Telegram тревоги по цифровым выдачам Ozon и Яндекс Маркета."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
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
YANDEX_NOTIFIER_CODE = "telegram_yandex_market_orders"
STOP_REQUESTED = False


@dataclass(frozen=True)
class Settings:
    database_url: str
    bot_token: str
    poll_interval_sec: int
    operator_wait_sec: int


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
        operator_wait_sec=env_int("OZON_NOTIFIER_OPERATOR_WAIT_SEC", default=120, minimum=30),
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


def alert_key(order: dict[str, Any]) -> str:
    # Создаёт устойчивый ключ причины, чтобы бот повторял тревогу только при новом состоянии или новой ошибке.
    status = str(order.get("status") or "").strip().lower()
    error = str(order.get("last_error") or "").strip()
    if status == "cancelled":
        return "alert:cancelled"
    if error:
        return f"alert:error:{sha256(error.encode('utf-8')).hexdigest()}"
    if status == "manual_required":
        return "alert:manual_wait" if bool(order.get("operator_wait_expired")) else "alert:manual_required"
    return ""


def notification_key(order: dict[str, Any]) -> str:
    # Определяет, нужна ли новая тревога или одно сообщение о её закрытии после смены проблемного состояния.
    active_alert = alert_key(order)
    previous_key = str(order.get("last_status") or "")
    if active_alert:
        return active_alert
    if previous_key.startswith("alert:"):
        return "resolved"
    return ""


def yandex_status_title(status: str) -> str:
    # Переводит внутреннюю стадию выдачи Яндекс Маркета в понятную подпись для оператора.
    labels = {
        "manual_required": "Принят, ожидает обработки",
        "supplier_processing": "Обрабатывается поставщиком",
        "market_sending": "Передаётся в Яндекс Маркет",
        "market_submitted": "Отправлен в Яндекс Маркет",
        "market_unknown": "Требует проверки отправки",
        "market_delivered": "Выдан",
        "cancelled": "Отменён",
    }
    return labels.get(str(status or "").strip().lower(), "Обрабатывается")


def yandex_alert_key(delivery: dict[str, Any]) -> str:
    # Создаёт ключ тревоги Яндекс Маркета, чтобы повторять уведомление только для новой причины.
    status = str(delivery.get("status") or "").strip().lower()
    error = str(delivery.get("last_error") or "").strip()
    if status == "cancelled":
        return "alert:cancelled"
    if error:
        return f"alert:error:{sha256(error.encode('utf-8')).hexdigest()}"
    if status == "market_unknown":
        return "alert:market_unknown"
    if status == "manual_required":
        return "alert:manual_wait" if bool(delivery.get("operator_wait_expired")) else "alert:manual_required"
    return ""


def yandex_notification_key(delivery: dict[str, Any]) -> str:
    # Отправляет закрытие только после реально отправленной тревоги по той же цифровой выдаче Яндекс Маркета.
    active_alert = yandex_alert_key(delivery)
    previous_key = str(delivery.get("last_status") or "")
    if active_alert:
        return active_alert
    if previous_key.startswith("alert:"):
        return "resolved"
    return ""


def alert_text(order: dict[str, Any]) -> str:
    # Формирует короткое действие для оператора вместо сообщений о штатном ходе и успешной выдаче.
    order_number = str(order.get("order_number") or order.get("posting_number") or "—")
    product_name = str(order.get("product_name") or "Товар не указан").strip()[:1000]
    status = str(order.get("status") or "").strip().lower()
    error = str(order.get("last_error") or "").strip()
    if status == "cancelled":
        title = "⚠️ Заказ Ozon отменён"
        reason = "Ozon отменил заказ. Проверьте, не началась ли выдача у поставщика."
    elif error:
        title = "⚠️ Требуется оператор"
        reason = "Необходим ручной ввод или ручная отправка."
    else:
        title = "⚠️ Требуется оператор"
        reason = "Необходим ручной ввод или ручная отправка."
    return "\n".join(
        (
            title,
            "Площадка: Ozon",
            f"Заказ: {order_number}",
            f"Товар: {product_name}",
            f"Количество: {int(order.get('required_qty') or 1)}",
            f"Статус: {status_title(status)}",
            f"Причина: {reason[:1500]}",
        )
    )


def resolution_text(order: dict[str, Any]) -> str:
    # Сообщает об устранении проблемы отдельной записью, сохраняя исходную тревогу в истории чата.
    order_number = str(order.get("order_number") or order.get("posting_number") or "—")
    product_name = str(order.get("product_name") or "Товар не указан").strip()[:1000]
    return "\n".join(
        (
            "✅ Проблема решена",
            "Площадка: Ozon",
            f"Заказ: {order_number}",
            f"Товар: {product_name}",
            f"Количество: {int(order.get('required_qty') or 1)}",
            f"Текущий статус: {status_title(str(order.get('status') or ''))}",
        )
    )


def yandex_alert_text(delivery: dict[str, Any]) -> str:
    # Формирует тревогу Яндекс Маркета теми же простыми действиями без показа технической ошибки поставщика.
    status = str(delivery.get("status") or "").strip().lower()
    if status == "cancelled":
        title = "⚠️ Заказ Яндекс Маркета отменён"
        reason = "Яндекс Маркет отменил заказ. Проверьте, не началась ли выдача у поставщика."
    else:
        title = "⚠️ Требуется оператор"
        reason = "Необходим ручной ввод или ручная отправка."
    return "\n".join(
        (
            title,
            "Площадка: Яндекс Маркет",
            f"Заказ: {delivery.get('order_id') or '—'}",
            f"Товар: {str(delivery.get('item_name') or delivery.get('offer_id') or 'Товар не указан').strip()[:1000]}",
            f"Количество: {int(delivery.get('required_qty') or 1)}",
            f"Статус: {yandex_status_title(status)}",
            f"Причина: {reason}",
        )
    )


def yandex_resolution_text(delivery: dict[str, Any]) -> str:
    # Сообщает отдельной записью, что ранее тревожившая цифровая выдача Яндекс Маркета вышла из проблемы.
    return "\n".join(
        (
            "✅ Проблема решена",
            "Площадка: Яндекс Маркет",
            f"Заказ: {delivery.get('order_id') or '—'}",
            f"Товар: {str(delivery.get('item_name') or delivery.get('offer_id') or 'Товар не указан').strip()[:1000]}",
            f"Количество: {int(delivery.get('required_qty') or 1)}",
            f"Текущий статус: {yandex_status_title(str(delivery.get('status') or ''))}",
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


def send_message(settings: Settings, chat_id: int, order: dict[str, Any], event_key: str) -> int:
    # Отправляет новую запись в чат и не редактирует прежнее сообщение оператора при закрытии проблемы.
    text = resolution_text(order) if event_key == "resolved" else alert_text(order)
    return send_text(settings, chat_id, text)


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


def initialize_yandex_tracking(conn: psycopg.Connection[Any]) -> None:
    # На первом запуске отмечает уже существующие выдачи Яндекс Маркета, чтобы бот не прислал старую историю.
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO app.yandex_market_order_notifier_state(notifier_code)
            VALUES (%s)
            ON CONFLICT (notifier_code) DO NOTHING
            """,
            (YANDEX_NOTIFIER_CODE,),
        )
        cursor.execute(
            """
            UPDATE app.yandex_market_order_notifier_state
            SET baseline_delivery_id=(SELECT COALESCE(MAX(id), 0) FROM app.marketplace_yandex_digital_deliveries)
            WHERE notifier_code=%s AND baseline_delivery_id=0
            """,
            (YANDEX_NOTIFIER_CODE,),
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
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM app.marketplace_yandex_digital_deliveries")
        yandex_delivery_watermark = int(cursor.fetchone()[0] or 0)
        cursor.execute(
            """
            INSERT INTO app.ozon_order_notifier_recipients(
              chat_id, chat_type, title, orders_from_id, yandex_from_delivery_id, is_active, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, true, now())
            ON CONFLICT (chat_id) DO UPDATE
            SET chat_type=excluded.chat_type,
                title=excluded.title,
                orders_from_id=CASE
                  WHEN app.ozon_order_notifier_recipients.is_active THEN app.ozon_order_notifier_recipients.orders_from_id
                  ELSE excluded.orders_from_id
                END,
                yandex_from_delivery_id=CASE
                  WHEN app.ozon_order_notifier_recipients.is_active THEN app.ozon_order_notifier_recipients.yandex_from_delivery_id
                  ELSE excluded.yandex_from_delivery_id
                END,
                is_active=true,
                updated_at=now()
            """,
            (
                chat_id, str(chat.get("type") or ""), str(chat.get("title") or chat.get("username") or ""),
                order_watermark, yandex_delivery_watermark,
            ),
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
            send_text(settings, chat_id, "Уведомления о проблемах Ozon и Яндекс Маркета включены. Для остановки отправьте /stop.")
        elif action == "unsubscribe" and chat_id:
            with psycopg.connect(settings.database_url) as conn:
                unsubscribe_recipient(conn, chat_id)
            send_text(settings, chat_id, "Уведомления о проблемах Ozon и Яндекс Маркета отключены. Чтобы включить снова, отправьте /start.")
        if update_id:
            with psycopg.connect(settings.database_url) as conn:
                save_update_offset(conn, update_id + 1)


def read_pending_orders(conn: psycopg.Connection[Any], settings: Settings) -> list[dict[str, Any]]:
    # Выбирает тревоги и закрытия прежних тревог, не уведомляя о штатных промежуточных статусах.
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT orders.id, orders.posting_number, orders.order_number, orders.product_name, orders.required_qty,
                   orders.status, orders.last_error, settings.auto_issue_enabled, recipient.chat_id,
                   delivery.telegram_message_id, delivery.last_status,
                   orders.updated_at <= now() - (%s * interval '1 second') AS operator_wait_expired
            FROM app.ozon_order_notifier_recipients AS recipient
            JOIN app.ozon_order_notifier_state AS state ON state.notifier_code=%s
            JOIN app.marketplace_ozon_digital_orders AS orders
              ON orders.id > GREATEST(state.baseline_order_id, recipient.orders_from_id)
            JOIN app.marketplace_ozon_digital_settings AS settings
              ON settings.store_code=orders.store_code
             AND settings.external_product_id=orders.external_product_id
            LEFT JOIN app.ozon_order_notifier_deliveries AS delivery
              ON delivery.order_id=orders.id AND delivery.chat_id=recipient.chat_id
            WHERE recipient.is_active=true
              AND (
                orders.status='cancelled'
                OR orders.last_error <> ''
                OR (
                  orders.status='manual_required'
                  AND (
                    settings.auto_issue_enabled=false
                    OR orders.updated_at <= now() - (%s * interval '1 second')
                  )
                )
                OR delivery.last_status LIKE 'alert:%%'
              )
            ORDER BY orders.created_at ASC NULLS LAST, orders.id ASC
            LIMIT 200
            """,
            (settings.operator_wait_sec, NOTIFIER_CODE, settings.operator_wait_sec),
        )
        return [
            order
            for order in cursor.fetchall()
            if notification_key(order) and notification_key(order) != str(order.get("last_status") or "")
        ]


def read_pending_yandex_deliveries(conn: psycopg.Connection[Any], settings: Settings) -> list[dict[str, Any]]:
    # Выбирает только проблемные цифровые выдачи Яндекс Маркета и закрытия уже отправленных тревог.
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT delivery.id, delivery.order_id, delivery.item_id, delivery.offer_id, delivery.required_qty,
                   delivery.status, delivery.last_error, order_item.item_name, recipient.chat_id,
                   notice.telegram_message_id, notice.last_status,
                   delivery.updated_at <= now() - (%s * interval '1 second') AS operator_wait_expired
            FROM app.ozon_order_notifier_recipients AS recipient
            JOIN app.yandex_market_order_notifier_state AS state ON state.notifier_code=%s
            JOIN app.marketplace_yandex_digital_deliveries AS delivery
              ON delivery.id > GREATEST(state.baseline_delivery_id, recipient.yandex_from_delivery_id)
            JOIN app.marketplace_yandex_order_items AS order_item
              ON order_item.store_code=delivery.store_code
             AND order_item.order_id=delivery.order_id
             AND order_item.item_id=delivery.item_id
            LEFT JOIN app.marketplace_yandex_stock_settings AS settings
              ON settings.store_code=delivery.store_code AND settings.offer_id=delivery.offer_id
            LEFT JOIN app.yandex_market_order_notifier_deliveries AS notice
              ON notice.delivery_id=delivery.id AND notice.chat_id=recipient.chat_id
            WHERE recipient.is_active=true
              AND order_item.is_sandbox=false
              AND (
                delivery.status IN ('cancelled', 'market_unknown')
                OR delivery.last_error <> ''
                OR (
                  delivery.status='manual_required'
                  AND (
                    COALESCE(settings.auto_issue_enabled, false)=false
                    OR delivery.updated_at <= now() - (%s * interval '1 second')
                  )
                )
                OR notice.last_status LIKE 'alert:%%'
              )
            ORDER BY delivery.created_at ASC, delivery.id ASC
            LIMIT 200
            """,
            (settings.operator_wait_sec, YANDEX_NOTIFIER_CODE, settings.operator_wait_sec),
        )
        return [
            delivery
            for delivery in cursor.fetchall()
            if yandex_notification_key(delivery) and yandex_notification_key(delivery) != str(delivery.get("last_status") or "")
        ]


def send_yandex_message(settings: Settings, chat_id: int, delivery: dict[str, Any], event_key: str) -> int:
    # Отправляет тревогу или закрытие Яндекс Маркета отдельным сообщением, не меняя историю прежней проблемы.
    text = yandex_resolution_text(delivery) if event_key == "resolved" else yandex_alert_text(delivery)
    return send_text(settings, chat_id, text)


def remember_success(conn: psycopg.Connection[Any], order: dict[str, Any], message_id: int, sent_event_key: str) -> None:
    # Фиксирует ключ тревоги или её закрытия, чтобы каждое полезное событие пришло получателю только один раз.
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
            (int(order["id"]), int(order["chat_id"]), message_id, sent_event_key),
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


def remember_yandex_success(conn: psycopg.Connection[Any], delivery: dict[str, Any], message_id: int, sent_event_key: str) -> None:
    # Фиксирует доставленную тревогу Яндекс Маркета, чтобы следующая проверка не прислала её повторно.
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO app.yandex_market_order_notifier_deliveries(
              delivery_id, chat_id, telegram_message_id, last_status, notified_at, last_error, updated_at
            )
            VALUES (%s, %s, %s, %s, now(), '', now())
            ON CONFLICT (delivery_id, chat_id) DO UPDATE
            SET telegram_message_id=excluded.telegram_message_id,
                last_status=excluded.last_status,
                notified_at=COALESCE(app.yandex_market_order_notifier_deliveries.notified_at, excluded.notified_at),
                last_error='',
                updated_at=now()
            """,
            (int(delivery["id"]), int(delivery["chat_id"]), message_id, sent_event_key),
        )
    conn.commit()


def remember_yandex_error(conn: psycopg.Connection[Any], delivery: dict[str, Any], error: Exception) -> None:
    # Сохраняет сбой Telegram для повторной отправки тревоги Яндекс Маркета на следующем цикле.
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO app.yandex_market_order_notifier_deliveries(
              delivery_id, chat_id, last_status, last_error, updated_at
            )
            VALUES (%s, %s, '', %s, now())
            ON CONFLICT (delivery_id, chat_id) DO UPDATE
            SET last_error=excluded.last_error, updated_at=now()
            """,
            (int(delivery["id"]), int(delivery["chat_id"]), str(error)[:2000]),
        )
    conn.commit()


def run_cycle(settings: Settings) -> None:
    # Выполняет одну короткую проверку БД, не удерживая соединение во время вызова Telegram API.
    with psycopg.connect(settings.database_url) as conn:
        initialize_tracking(conn)
        initialize_yandex_tracking(conn)
    sync_recipients(settings)
    with psycopg.connect(settings.database_url) as conn:
        orders = read_pending_orders(conn, settings)
        yandex_deliveries = read_pending_yandex_deliveries(conn, settings)

    for order in orders:
        chat_id = int(order["chat_id"])
        sent_event_key = notification_key(order)
        try:
            message_id = send_message(settings, chat_id, order, sent_event_key)
            with psycopg.connect(settings.database_url) as conn:
                remember_success(conn, order, message_id, sent_event_key)
            LOGGER.info("Order %s notification was sent: %s", order["id"], sent_event_key)
        except Exception as exc:
            LOGGER.exception("Cannot notify order %s", order["id"])
            with psycopg.connect(settings.database_url) as conn:
                remember_error(conn, order, exc)

    for delivery in yandex_deliveries:
        chat_id = int(delivery["chat_id"])
        sent_event_key = yandex_notification_key(delivery)
        try:
            message_id = send_yandex_message(settings, chat_id, delivery, sent_event_key)
            with psycopg.connect(settings.database_url) as conn:
                remember_yandex_success(conn, delivery, message_id, sent_event_key)
            LOGGER.info("Yandex Market delivery %s notification was sent: %s", delivery["id"], sent_event_key)
        except Exception as exc:
            LOGGER.exception("Cannot notify Yandex Market delivery %s", delivery["id"])
            with psycopg.connect(settings.database_url) as conn:
                remember_yandex_error(conn, delivery, exc)


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
