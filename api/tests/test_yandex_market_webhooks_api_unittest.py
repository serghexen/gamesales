import unittest
from unittest.mock import patch

from fastapi import FastAPI

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

try:
    from api.domains.yandex_market_webhooks_api import (
        is_yandex_market_source,
        mount_yandex_market_webhooks_routes,
        notification_fingerprint,
        yandex_market_rejection_detail,
    )
except ModuleNotFoundError:  # Запуск из папки api использует локальный пакет domains.
    from domains.yandex_market_webhooks_api import (
        is_yandex_market_source,
        mount_yandex_market_webhooks_routes,
        notification_fingerprint,
        yandex_market_rejection_detail,
    )


class _FakeConn:
    def __init__(self):
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def commit(self):
        self.commits += 1


class _FakePsycopg:
    def __init__(self):
        self.connections = []

    def connect(self, _dsn):
        connection = _FakeConn()
        self.connections.append(connection)
        return connection


@unittest.skipIf(TestClient is None, "fastapi.testclient requires httpx")
class YandexMarketWebhookTests(unittest.TestCase):
    # Поднимает изолированный маршрут, чтобы проверить контракт Маркета без доступа к PostgreSQL.
    def create_client(self):
        app = FastAPI()
        writes = []
        processed = []
        psycopg = _FakePsycopg()

        def fake_q1(_conn, sql, params=None):
            writes.append((sql, params))
            return (1,)

        def fake_process_event(event_id):
            # Запоминает событие, чтобы проверить фоновый read-only запуск без реальной базы и API.
            processed.append(event_id)

        mount_yandex_market_webhooks_routes(
            app,
            DB_DSN="postgresql://test",
            psycopg=psycopg,
            q1=fake_q1,
            process_event=fake_process_event,
        )
        return TestClient(app), writes, processed, psycopg

    # Проверка подсетей не должна принимать локальный адрес как доверенный источник Маркета.
    def test_source_validation_allows_only_yandex_networks(self):
        self.assertTrue(is_yandex_market_source("5.45.207.10"))
        self.assertTrue(is_yandex_market_source("141.8.142.100"))
        self.assertFalse(is_yandex_market_source("127.0.0.1"))
        self.assertFalse(is_yandex_market_source("not-an-ip"))

    # PING подтверждает URL, сохраняется в журнале и запускает только read-only обработку события.
    def test_ping_returns_yandex_contract_and_writes_event(self):
        client, writes, processed, psycopg = self.create_client()
        payload = {"notificationType": "PING", "time": "2026-07-28T08:00:00Z"}

        response = client.post(
            "/marketplaces/yandex/notifications/notification",
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
        self.assertEqual(processed, [1])
        self.assertEqual([connection.commits for connection in psycopg.connections], [1])

    # Событие заказа журналируется и передается только в фоновое read-only чтение без выдачи ключа.
    def test_order_status_event_is_logged_and_scheduled_for_read_only_processing(self):
        client, writes, processed, _psycopg = self.create_client()
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
        self.assertEqual(processed, [1])

    # Запрос с неподтвержденного адреса отсекается до записи в базу.
    def test_untrusted_source_is_rejected_before_database_write(self):
        client, writes, _processed, _psycopg = self.create_client()

        response = client.post(
            "/marketplaces/yandex/notifications",
            json={"notificationType": "PING"},
            headers={"X-Forwarded-For": "203.0.113.5"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(writes)

    # Диагностический IP возвращается только при явном флаге тестового окружения.
    def test_rejection_detail_hides_source_ip_without_debug_flag(self):
        with patch.dict("os.environ", {"YANDEX_MARKET_WEBHOOK_DEBUG_SOURCE": "true"}):
            self.assertEqual(
                yandex_market_rejection_detail("203.0.113.5"),
                "Yandex Market notification source is not allowed: 203.0.113.5",
            )

        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(
                yandex_market_rejection_detail("203.0.113.5"),
                "Yandex Market notification source is not allowed",
            )

    # Отпечаток одинакового события стабилен, чтобы позднее видеть дубли повторной доставки.
    def test_notification_fingerprint_is_stable(self):
        payload = {"notificationType": "PING", "time": "2026-07-28T08:00:00Z"}

        self.assertEqual(notification_fingerprint(payload), notification_fingerprint(dict(reversed(payload.items()))))
