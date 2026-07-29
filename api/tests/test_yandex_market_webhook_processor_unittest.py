import unittest
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

        def fake_q1(_conn, _sql, _params=None):
            return (70940298, 501, "ORDER_CREATED", "received")

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
        self.assertTrue(any(params == ("processed", "", "processed", 7) for _sql, params in writes))

    # PING не содержит заказа, поэтому обработчик помечает его и не обращается к внешнему API.
    def test_ping_event_is_ignored_without_market_api_call(self):
        writes = []

        def fake_q1(_conn, _sql, _params=None):
            return (None, None, "PING", "received")

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
        self.assertTrue(any(params == ("ignored", "", "ignored", 8) for _sql, params in writes))
