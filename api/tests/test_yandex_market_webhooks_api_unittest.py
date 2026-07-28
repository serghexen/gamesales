import unittest

from fastapi import FastAPI

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

from api.domains.yandex_market_webhooks_api import (
    is_yandex_market_source,
    mount_yandex_market_webhooks_routes,
    notification_fingerprint,
)


class _FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class _FakePsycopg:
    def connect(self, _dsn):
        return _FakeConn()


@unittest.skipIf(TestClient is None, "fastapi.testclient requires httpx")
class YandexMarketWebhookTests(unittest.TestCase):
    # Поднимает изолированный маршрут, чтобы проверить контракт Маркета без доступа к PostgreSQL.
    def create_client(self):
        app = FastAPI()
        writes = []

        def fake_exec1(_conn, sql, params=None):
            writes.append((sql, params))

        mount_yandex_market_webhooks_routes(
            app,
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            exec1=fake_exec1,
        )
        return TestClient(app), writes

    # Проверка подсетей не должна принимать локальный адрес как доверенный источник Маркета.
    def test_source_validation_allows_only_yandex_networks(self):
        self.assertTrue(is_yandex_market_source("5.45.207.10"))
        self.assertTrue(is_yandex_market_source("141.8.142.100"))
        self.assertFalse(is_yandex_market_source("127.0.0.1"))
        self.assertFalse(is_yandex_market_source("not-an-ip"))

    # PING подтверждает URL и сохраняется в тот же журнал без запуска какой-либо выдачи.
    def test_ping_returns_yandex_contract_and_writes_event(self):
        client, writes = self.create_client()
        payload = {"notificationType": "PING", "time": "2026-07-28T08:00:00Z"}

        response = client.post(
            "/marketplaces/yandex/notifications",
            json=payload,
            headers={"X-Forwarded-For": "5.45.207.10"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "GameSales")
        self.assertEqual(response.json()["version"], "1.0.0")
        self.assertEqual(response.json()["time"], payload["time"])
        self.assertEqual(len(writes), 1)
        self.assertIn("marketplace_yandex_market_webhook_events", writes[0][0])
        self.assertEqual(writes[0][1][1], "PING")

    # Событие заказа журналируется, но не содержит вызова выдачи ключа или записи в заказ Маркета.
    def test_order_status_event_is_only_logged(self):
        client, writes = self.create_client()
        payload = {
            "notificationType": "ORDER_STATUS_UPDATED",
            "campaignId": 70940298,
            "orderId": 59533171650,
            "status": "DELIVERED",
            "substatus": "DELIVERY_SERVICE_DELIVERED",
            "updatedAt": "2026-07-28T08:10:00.000Z",
        }

        response = client.post(
            "/marketplaces/yandex/notifications",
            json=payload,
            headers={"X-Forwarded-For": "141.8.142.1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][1][2:6], (70940298, 59533171650, "DELIVERED", "DELIVERY_SERVICE_DELIVERED"))
        self.assertNotIn("marketplace_yandex_market_orders", writes[0][0])

    # Запрос с неподтвержденного адреса отсекается до записи в базу.
    def test_untrusted_source_is_rejected_before_database_write(self):
        client, writes = self.create_client()

        response = client.post(
            "/marketplaces/yandex/notifications",
            json={"notificationType": "PING"},
            headers={"X-Forwarded-For": "203.0.113.5"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(writes)

    # Отпечаток одинакового события стабилен, чтобы позднее видеть дубли повторной доставки.
    def test_notification_fingerprint_is_stable(self):
        payload = {"notificationType": "PING", "time": "2026-07-28T08:00:00Z"}

        self.assertEqual(notification_fingerprint(payload), notification_fingerprint(dict(reversed(payload.items()))))
