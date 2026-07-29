from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from .yandex_market_catalog_service import (
    fetch_yandex_market_order,
    find_yandex_market_store_code_by_campaign_id,
    yandex_market_sandbox_orders_enabled,
)
from .yandex_market_order_storage import save_yandex_market_order_snapshot


def _error_text(error: Exception) -> str:
    # Оставляет в журнале короткую понятную причину, не записывая целые ответы внешнего API.
    detail = getattr(error, "detail", None)
    return str(detail or error or error.__class__.__name__)[:1000]


def build_yandex_market_webhook_event_processor(*, DB_DSN: str, psycopg, q1, exec1) -> Callable[[int], None]:
    # Создает фоновую обработку журнала: уведомление уже подтверждено Маркету, а чтение заказа идет отдельно.
    def set_event_state(event_id: int, state: str, *, error_text: str = "") -> None:
        # Отмечает итог обработки, чтобы повторные уведомления и ошибки были видны в локальном журнале.
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                UPDATE app.marketplace_yandex_market_webhook_events
                SET processing_state=%s,
                    last_error=%s,
                    processed_at=CASE WHEN %s IN ('processed', 'ignored', 'failed') THEN now() ELSE NULL END
                WHERE id=%s
                """,
                (state, error_text, state, event_id),
            )
            conn.commit()

    def process_event(event_id: int) -> None:
        # Берет одно принятое событие, читает только связанный заказ и сохраняет его без внешних изменений.
        event: tuple | None = None
        try:
            with psycopg.connect(DB_DSN) as conn:
                event = q1(
                    conn,
                    """
                    SELECT campaign_id, order_id, notification_type, processing_state
                    FROM app.marketplace_yandex_market_webhook_events
                    WHERE id=%s
                    FOR UPDATE SKIP LOCKED
                    """,
                    (event_id,),
                )
                if not event or str(event[3] or "") in {"processed", "ignored"}:
                    return
                # Помечаем попытку до сетевого чтения, чтобы при ошибке событие осталось в журнале для повтора.
                exec1(
                    conn,
                    """
                    UPDATE app.marketplace_yandex_market_webhook_events
                    SET processing_state='processing', processing_attempts=processing_attempts + 1, last_error=''
                    WHERE id=%s
                    """,
                    (event_id,),
                )
                conn.commit()

            campaign_id = int(event[0]) if event[0] is not None else 0
            order_id = int(event[1]) if event[1] is not None else 0
            if not campaign_id or not order_id:
                # PING и сервисные события не содержат заказа, поэтому для них чтение Маркета не требуется.
                set_event_state(event_id, "ignored")
                return

            store_code = find_yandex_market_store_code_by_campaign_id(campaign_id)
            if not store_code:
                raise ValueError(f"Yandex Market campaign {campaign_id} is not configured")

            # Метод POST только читает один заказ: здесь нет передачи ключей или изменения его статуса.
            order = fetch_yandex_market_order(order_id, store_code=store_code)
            saved = save_yandex_market_order_snapshot(
                DB_DSN=DB_DSN,
                psycopg=psycopg,
                exec1=exec1,
                store_code=store_code,
                orders=[order],
                is_sandbox=yandex_market_sandbox_orders_enabled(store_code),
                synced_at=datetime.now(timezone.utc),
            )
            if not saved:
                raise ValueError(f"Yandex Market order {order_id} does not contain saved items")
            set_event_state(event_id, "processed")
        except Exception as error:
            # Ошибку чтения сохраняем отдельно: HTTP-ответ уведомлению уже был отдан без задержки.
            set_event_state(event_id, "failed", error_text=_error_text(error))

    return process_event
