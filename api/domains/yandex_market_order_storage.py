from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def first_text(*values: Any) -> str:
    # Берет первое непустое текстовое поле из разных вариантов ответа Маркета.
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def optional_int(value: Any) -> int | None:
    # Приводит внешний идентификатор к числу и сохраняет пустое значение как отсутствующее.
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


def optional_datetime(value: Any) -> datetime | None:
    # Разбирает дату Маркета без ошибки для необязательных или старых полей.
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def nonnegative_int(value: Any) -> int:
    # Не дает некорректному количеству позиции попасть в локальную историю как отрицательное число.
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def save_yandex_market_order_snapshot(
    *,
    DB_DSN: str,
    psycopg,
    exec1,
    store_code: str,
    orders: list[dict[str, Any]],
    synced_at: datetime | None = None,
) -> int:
    # Сохраняет локальный снимок позиций заказов и не вызывает выдачу, остатки или изменение статуса в Маркете.
    saved_at = synced_at or datetime.now(timezone.utc)
    imported_orders = 0

    with psycopg.connect(DB_DSN) as conn:
        for order in orders:
            if not isinstance(order, dict):
                continue
            order_id = optional_int(order.get("orderId") or order.get("id"))
            campaign_id = optional_int(order.get("campaignId"))
            if not order_id or not campaign_id:
                continue
            items = order.get("items") if isinstance(order.get("items"), list) else []
            for item in items:
                if not isinstance(item, dict):
                    continue
                item_id = optional_int(item.get("id"))
                offer_id = first_text(item.get("offerId"))
                if not item_id or not offer_id:
                    continue
                prices = item.get("prices") if isinstance(item.get("prices"), dict) else {}
                payment = prices.get("payment") if isinstance(prices.get("payment"), dict) else {}
                # Одна и та же позиция обновляется по ключу заказа, поэтому повторное уведомление безопасно.
                exec1(
                    conn,
                    """
                    INSERT INTO app.marketplace_yandex_order_items(
                      store_code, order_id, item_id, campaign_id, offer_id, item_name, quantity,
                      status, substatus, price, currency_code, created_at, updated_at, synced_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (store_code, order_id, item_id) DO UPDATE
                    SET campaign_id=excluded.campaign_id,
                        offer_id=excluded.offer_id,
                        item_name=excluded.item_name,
                        quantity=excluded.quantity,
                        status=excluded.status,
                        substatus=excluded.substatus,
                        price=excluded.price,
                        currency_code=excluded.currency_code,
                        created_at=excluded.created_at,
                        updated_at=excluded.updated_at,
                        synced_at=excluded.synced_at
                    """,
                    (
                        store_code,
                        order_id,
                        item_id,
                        campaign_id,
                        offer_id,
                        first_text(item.get("offerName")),
                        nonnegative_int(item.get("count")),
                        first_text(order.get("status")),
                        first_text(order.get("substatus")),
                        first_text(payment.get("value"), item.get("price")),
                        first_text(payment.get("currencyId"), order.get("currency")),
                        optional_datetime(order.get("creationDate")),
                        optional_datetime(first_text(order.get("updateDate"), order.get("updatedAt"))),
                        saved_at,
                    ),
                )
                imported_orders += 1
        conn.commit()
    return imported_orders
