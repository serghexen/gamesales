import unittest
from datetime import datetime, timezone
from unittest.mock import patch

try:
    from api.domains import yandex_market_webhook_processor
except ModuleNotFoundError:  # Запуск из папки api использует локальный пакет domains.
    from domains import yandex_market_webhook_processor


class _FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def commit(self):
        pass


class _FakePsycopg:
    def connect(self, _dsn):
        return _FakeConn()


class YandexMarketWebhookProcessorTests(unittest.TestCase):
    # Обработчик заказа читает API и сохраняет снимок локально, не вызывая методы выдачи или изменения статуса.
    def test_order_event_fetches_and_saves_only_its_order(self):
        writes = []

        def fake_q1(_conn, sql, _params=None):
            if "WITH candidate AS" in sql:
                return (7, 70940298, 501, "ORDER_CREATED", None, 1)
            return None

        def fake_exec1(_conn, sql, params=None):
            writes.append((sql, params))

        with (
            patch.object(yandex_market_webhook_processor, "find_yandex_market_store_code_by_campaign_id", return_value="asat"),
            patch.object(
                yandex_market_webhook_processor,
                "fetch_yandex_market_order",
                return_value={"orderId": 501, "campaignId": 70940298, "items": [{"id": 1}]},
            ) as fetch_order,
            patch.object(yandex_market_webhook_processor, "save_yandex_market_order_snapshot", return_value=1) as save_snapshot,
        ):
            process_event = yandex_market_webhook_processor.build_yandex_market_webhook_event_processor(
                DB_DSN="postgresql://test",
                psycopg=_FakePsycopg(),
                q1=fake_q1,
                exec1=fake_exec1,
            )
            process_event(7)

        fetch_order.assert_called_once_with(501, store_code="asat")
        self.assertEqual(save_snapshot.call_args.kwargs["store_code"], "asat")
        self.assertEqual(save_snapshot.call_args.kwargs["orders"][0]["orderId"], 501)
        self.assertTrue(any("processing_state=%s" in sql and params[0:2] == ("processed", 7) for sql, params in writes))

    # PING не содержит заказа, поэтому обработчик помечает его и не обращается к внешнему API.
    def test_ping_event_is_ignored_without_market_api_call(self):
        writes = []

        def fake_q1(_conn, sql, _params=None):
            if "WITH candidate AS" in sql:
                return (8, None, None, "PING", None, 1)
            return None

        def fake_exec1(_conn, sql, params=None):
            writes.append((sql, params))

        with patch.object(yandex_market_webhook_processor, "fetch_yandex_market_order") as fetch_order:
            process_event = yandex_market_webhook_processor.build_yandex_market_webhook_event_processor(
                DB_DSN="postgresql://test",
                psycopg=_FakePsycopg(),
                q1=fake_q1,
                exec1=fake_exec1,
            )
            process_event(8)

        fetch_order.assert_not_called()
        self.assertTrue(any("processing_state=%s" in sql and params[0:2] == ("ignored", 8) for sql, params in writes))

    # Только webhook передает позицию в боевой обработчик; ручная синхронизация этот callback не использует.
    def test_order_event_passes_saved_item_only_to_delivery_callback(self):
        delivered = []

        event_time = datetime(2026, 7, 29, tzinfo=timezone.utc)

        def fake_q1(_conn, sql, _params=None):
            if "WITH candidate AS" in sql:
                return (9, 70940298, 501, "ORDER_CREATED", event_time, 1)
            return None

        with (
            patch.object(yandex_market_webhook_processor, "find_yandex_market_store_code_by_campaign_id", return_value="asat"),
            patch.object(yandex_market_webhook_processor, "fetch_yandex_market_order", return_value={"orderId": 501, "items": [{"id": 99}]}),
            patch.object(yandex_market_webhook_processor, "save_yandex_market_order_snapshot", return_value=1),
        ):
            process_event = yandex_market_webhook_processor.build_yandex_market_webhook_event_processor(
                DB_DSN="postgresql://test",
                psycopg=_FakePsycopg(),
                q1=fake_q1,
                exec1=lambda *_args: None,
                process_delivery=lambda *args: delivered.append(args),
            )
            process_event(9)

        self.assertEqual(delivered, [("asat", 501, 99, event_time)])

    # Claim использует SKIP LOCKED и lease, поэтому второй API-процесс не получает уже арендованное событие.
    def test_two_workers_cannot_claim_the_same_event(self):
        claims = []
        deliveries = []

        def fake_q1(_conn, sql, params=None):
            if "WITH candidate AS" not in sql:
                return None
            claims.append((sql, params))
            return (12, 70940298, 501, "ORDER_CREATED", None, 1) if len(claims) == 1 else None

        with (
            patch.object(yandex_market_webhook_processor, "find_yandex_market_store_code_by_campaign_id", return_value="asat"),
            patch.object(yandex_market_webhook_processor, "fetch_yandex_market_order", return_value={"items": [{"id": 99}]}),
            patch.object(yandex_market_webhook_processor, "save_yandex_market_order_snapshot", return_value=1),
        ):
            process_event = yandex_market_webhook_processor.build_yandex_market_webhook_event_processor(
                DB_DSN="postgresql://test",
                psycopg=_FakePsycopg(),
                q1=fake_q1,
                exec1=lambda *_args: 1,
                process_delivery=lambda *args: deliveries.append(args),
            )
            process_event(12)
            process_event(12)

        self.assertEqual(len(deliveries), 1)
        self.assertIn("FOR UPDATE SKIP LOCKED", claims[0][0])
        self.assertIn("processing_locked_until", claims[0][0])
        self.assertEqual(claims[0][1][0], 12)

    # Периодический воркер подбирает processing с истекшей арендой после рестарта API.
    def test_periodic_worker_recovers_stale_processing_event(self):
        claim_calls = []

        def fake_q1(_conn, sql, params=None):
            if "WITH candidate AS" not in sql:
                return None
            claim_calls.append((sql, params))
            return (15, None, None, "PING", None, 2) if len(claim_calls) == 1 else None

        process_event = yandex_market_webhook_processor.build_yandex_market_webhook_event_processor(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=fake_q1,
            exec1=lambda *_args: 1,
        )

        processed = process_event.process_pending_events()

        self.assertEqual(processed, 1)
        self.assertIn("event.processing_state='processing'", claim_calls[0][0])
        self.assertIn("processing_locked_until <= now()", claim_calls[0][0])
        self.assertIn("interval '10 minutes'", claim_calls[0][0])

    # Ошибка внешнего API освобождает lease и назначает отложенный повтор вместо терминальной потери события.
    def test_failed_event_is_scheduled_for_retry(self):
        writes = []

        def fake_q1(_conn, sql, _params=None):
            if "WITH candidate AS" in sql:
                return (18, 70940298, 501, "ORDER_CREATED", None, 3)
            return None

        with (
            patch.object(yandex_market_webhook_processor, "find_yandex_market_store_code_by_campaign_id", return_value="asat"),
            patch.object(yandex_market_webhook_processor, "fetch_yandex_market_order", side_effect=TimeoutError("temporary")),
        ):
            process_event = yandex_market_webhook_processor.build_yandex_market_webhook_event_processor(
                DB_DSN="postgresql://test",
                psycopg=_FakePsycopg(),
                q1=fake_q1,
                exec1=lambda _conn, sql, params=None: writes.append((sql, params)) or 1,
                retry_base_seconds=15,
            )
            process_event(18)

        failed_updates = [(sql, params) for sql, params in writes if "processing_state='failed'" in sql]
        self.assertEqual(failed_updates[0][1][1], 60)
        self.assertIn("processing_lock_token=NULL", failed_updates[0][0])
        self.assertIn("next_attempt_at", failed_updates[0][0])
