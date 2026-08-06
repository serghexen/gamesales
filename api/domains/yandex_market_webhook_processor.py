from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable
import uuid

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


def build_yandex_market_webhook_event_processor(
    *,
    DB_DSN: str,
    psycopg,
    q1,
    exec1,
    process_delivery=None,
    lease_seconds: int = 600,
    retry_base_seconds: int = 15,
    retry_max_seconds: int = 3600,
) -> Callable[[int], None]:
    # Создает долговечную DB-очередь: быстрый вызов и периодический воркер используют один атомарный claim.
    normalized_lease_seconds = max(60, int(lease_seconds or 600))
    normalized_retry_base = max(1, int(retry_base_seconds or 15))
    normalized_retry_max = max(normalized_retry_base, int(retry_max_seconds or 3600))

    def claim_event(event_id: int | None = None):
        # Атомарно арендует одно доступное событие, чтобы два API-процесса не обработали его одновременно.
        lock_token = str(uuid.uuid4())
        id_filter = "AND event.id=%s" if event_id is not None else ""
        with psycopg.connect(DB_DSN) as conn:
            params = (event_id, lock_token, normalized_lease_seconds) if event_id is not None else (lock_token, normalized_lease_seconds)
            claimed = q1(
                conn,
                f"""
                WITH candidate AS (
                  SELECT event.id
                  FROM app.marketplace_yandex_market_webhook_events AS event
                  WHERE (
                      (
                        event.processing_state IN ('received', 'failed')
                        AND event.next_attempt_at <= now()
                        AND (event.processing_locked_until IS NULL OR event.processing_locked_until <= now())
                      )
                      OR (
                        event.processing_state='processing'
                        AND (
                          (event.processing_lock_token IS NOT NULL AND event.processing_locked_until <= now())
                          OR (
                            event.processing_lock_token IS NULL
                            AND COALESCE(event.last_attempt_at, event.updated_at) <= now() - interval '10 minutes'
                          )
                        )
                      )
                    )
                    {id_filter}
                  ORDER BY event.next_attempt_at, event.id
                  FOR UPDATE SKIP LOCKED
                  LIMIT 1
                )
                UPDATE app.marketplace_yandex_market_webhook_events AS event
                SET processing_state='processing',
                    processing_attempts=event.processing_attempts + 1,
                    processing_lock_token=%s::uuid,
                    processing_locked_until=now() + (%s * interval '1 second'),
                    last_attempt_at=now(),
                    last_error='',
                    updated_at=now()
                FROM candidate
                WHERE event.id=candidate.id
                RETURNING event.id, event.campaign_id, event.order_id, event.notification_type,
                          event.event_time, event.processing_attempts
                """,
                params,
            )
            conn.commit()
        return (claimed, lock_token) if claimed else (None, lock_token)

    def finish_event(event_id: int, lock_token: str, state: str) -> None:
        # Завершает только собственную аренду; запоздалый воркер не перезапишет результат нового владельца.
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                UPDATE app.marketplace_yandex_market_webhook_events
                SET processing_state=%s, last_error='', processed_at=now(),
                    processing_lock_token=NULL, processing_locked_until=NULL, updated_at=now()
                WHERE id=%s AND processing_lock_token=%s::uuid
                """,
                (state, event_id, lock_token),
            )
            conn.commit()

    def fail_event(event_id: int, lock_token: str, attempts: int, error: Exception) -> None:
        # Ошибка получает ограниченную экспоненциальную паузу и остается доступной для следующего воркера.
        exponent = max(0, min(16, int(attempts or 1) - 1))
        retry_seconds = min(normalized_retry_max, normalized_retry_base * (2**exponent))
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                UPDATE app.marketplace_yandex_market_webhook_events
                SET processing_state='failed', last_error=%s, processed_at=NULL,
                    next_attempt_at=now() + (%s * interval '1 second'),
                    processing_lock_token=NULL, processing_locked_until=NULL, updated_at=now()
                WHERE id=%s AND processing_lock_token=%s::uuid
                """,
                (_error_text(error), retry_seconds, event_id, lock_token),
            )
            conn.commit()

    def process_claimed_event(event: tuple, lock_token: str) -> None:
        # Обрабатывает уже арендованное событие и фиксирует результат с проверкой владельца lease.
        event_id = int(event[0])
        attempts = int(event[5] or 1)
        try:
            campaign_id = int(event[1]) if event[1] is not None else 0
            order_id = int(event[2]) if event[2] is not None else 0
            if not campaign_id or not order_id:
                # PING и сервисные события не содержат заказа, поэтому для них чтение Маркета не требуется.
                finish_event(event_id, lock_token, "ignored")
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
            if process_delivery:
                # Боевой обработчик вызывается только из подтвержденного уведомления, а не из ручной синхронизации.
                for item in order.get("items") if isinstance(order.get("items"), list) else []:
                    if isinstance(item, dict) and item.get("id"):
                        process_delivery(store_code, order_id, int(item["id"]), event[4])
            finish_event(event_id, lock_token, "processed")
        except Exception as error:
            # HTTP 200 уже отдан, поэтому ошибка остается в очереди и повторяется с безопасной паузой.
            fail_event(event_id, lock_token, attempts, error)

    def process_event(event_id: int) -> None:
        # Быстрый путь после HTTP 200 арендует конкретное событие по тем же правилам, что и воркер.
        event, lock_token = claim_event(int(event_id))
        if event:
            process_claimed_event(event, lock_token)

    def process_pending_events(batch_size: int = 25) -> int:
        # После старта и по таймеру подбирает received, failed и события с истекшей processing-арендой.
        processed_count = 0
        for _index in range(max(1, min(100, int(batch_size or 25)))):
            event, lock_token = claim_event()
            if not event:
                break
            process_claimed_event(event, lock_token)
            processed_count += 1
        return processed_count

    process_event.process_pending_events = process_pending_events  # type: ignore[attr-defined]
    process_event.claim_event = claim_event  # type: ignore[attr-defined]
    return process_event
