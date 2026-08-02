import os
import unittest
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

try:
    from api.domains.marketplace_connections_api import mount_marketplace_connection_routes
    from api.domains.marketplace_catalog_service import _fetch_ozon_catalog
    from api.domains.marketplace_orders_service import _fetch_ozon_fbo_orders, _fetch_ozon_orders, _fetch_yandex_market_orders, normalize_marketplace_order_status
except ModuleNotFoundError:  # Запуск из папки api использует локальный пакет domains.
    from domains.marketplace_connections_api import mount_marketplace_connection_routes
    from domains.marketplace_catalog_service import _fetch_ozon_catalog
    from domains.marketplace_orders_service import _fetch_ozon_fbo_orders, _fetch_ozon_orders, _fetch_yandex_market_orders, normalize_marketplace_order_status


class _FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def commit(self):
        return None


class _FakePsycopg:
    def connect(self, _dsn):
        return _FakeConn()


@unittest.skipIf(TestClient is None, "fastapi.testclient requires httpx")
class MarketplaceConnectionsApiTests(unittest.TestCase):
    # Поднимает API в памяти, чтобы контракт подключения не требовал реальной БД или токена Ozon.
    def create_client(self, connection_rows=None, qall_callback=None):
        app = FastAPI()

        def fake_q1(_conn, sql, _params=None):
            if "SELECT user_id FROM app.users" in sql:
                return (41,)
            if "FROM marketplace.workspace_members" in sql:
                return (7, "Команда Demo")
            if "SELECT COUNT(*)" in sql:
                return (len(connection_rows or []),)
            if "INSERT INTO marketplace.connections" in sql:
                return (19, "ozon", "ASAT Games", "48186803", None, None, "q9W7", "active", None, "", datetime(2026, 8, 2, tzinfo=timezone.utc))
            if "DELETE FROM marketplace.connections" in sql:
                return (19,)
            return None

        def fake_qall(_conn, sql, params=None):
            if qall_callback:
                qall_callback(sql, params)
            return list(connection_rows or [])

        mount_marketplace_connection_routes(
            app,
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=fake_q1,
            qall=fake_qall,
            get_current_user=lambda: SimpleNamespace(username="alice", role="owner"),
            verify_ozon_connection=lambda **_kwargs: None,
            discover_yandex_market_stores=lambda **_kwargs: [{"business_id": 11, "campaign_id": 22, "display_name": "Яндекс Games"}],
            fetch_marketplace_catalog=lambda **_kwargs: [],
            fetch_marketplace_orders=lambda **_kwargs: [],
            normalize_marketplace_order_status=lambda **_kwargs: "problem",
        )
        return TestClient(app)

    # Новый токен должен уходить в шифрование, а в ответе оставаться только его маска.
    def test_create_connection_masks_token_and_requires_ozon_client_id(self):
        client = self.create_client()
        with patch.dict(os.environ, {"MARKETPLACE_CREDENTIALS_SECRET": "x" * 32}, clear=False):
            with client:
                response = client.post(
                    "/marketplace/connections",
                    json={"provider_code": "ozon", "display_name": "ASAT Games", "client_id": "48186803", "token": "live-token-q9W7"},
                )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["token_masked"], "••••q9W7")
        self.assertNotIn("live-token", str(response.json()))

    # Пустой Client ID для Ozon блокируется до доступа к БД и не создает неполный кабинет.
    def test_create_ozon_connection_requires_client_id(self):
        client = self.create_client()
        with patch.dict(os.environ, {"MARKETPLACE_CREDENTIALS_SECRET": "x" * 32}, clear=False):
            with client:
                response = client.post(
                    "/marketplace/connections",
                    json={"provider_code": "ozon", "display_name": "ASAT Games", "token": "live-token-q9W7"},
                )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Client ID", response.json()["detail"])

    # Список подключений не раскрывает token_ciphertext и остается привязанным к рабочему пространству пользователя.
    def test_list_connections_returns_only_masked_token(self):
        rows = [(19, "yandex_market", "Яндекс Games", "", 11, 22, "ABCD", "active", None, "", datetime(2026, 8, 2, tzinfo=timezone.utc))]
        client = self.create_client(connection_rows=rows)
        with client:
            response = client.get("/marketplace/connections")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["workspace_name"], "Команда Demo")
        self.assertEqual(response.json()["items"][0]["token_masked"], "••••ABCD")

    # API-Key Яндекс Маркета сначала открывает список доступных кампаний, а не принимает ID из формы вслепую.
    def test_discover_yandex_market_stores_from_token(self):
        client = self.create_client()
        with client:
            response = client.post("/marketplace/connections/discover", json={"provider_code": "yandex_market", "token": "market-api-token"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [{"business_id": 11, "campaign_id": 22, "display_name": "Яндекс Games"}])

    # Единый каталог должен сохранить источник товара, чтобы одинаковые SKU разных магазинов не смешивались.
    def test_workspace_catalog_returns_items_with_connection_source(self):
        catalog_rows = [
            ("123", "GAME-100", "SKU-100", "Game 100", "visible", datetime(2026, 8, 2, tzinfo=timezone.utc), 19, "ASAT Games", "ozon"),
        ]
        client = self.create_client(connection_rows=catalog_rows)
        with client:
            response = client.get("/marketplace/catalog?query=GAME")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["connection_name"], "ASAT Games")
        self.assertEqual(response.json()["items"][0]["offer_id"], "GAME-100")
        self.assertEqual(response.json()["items"][0]["sku"], "SKU-100")

    # Период и единый статус должны отфильтровывать локальный снимок на стороне БД, а не в браузере.
    def test_workspace_orders_accepts_status_and_inclusive_date_range(self):
        captured = {}
        order_rows = [
            ("123-0001", "1", "GAME-100", "SKU-100", "Game 100", 1, "done", "", "delivered", "FBO", datetime(2026, 8, 2, 12, tzinfo=timezone.utc), None, datetime(2026, 8, 2, 13, tzinfo=timezone.utc), 19, "ASAT", "ozon"),
        ]

        def capture_query(sql, params):
            captured["sql"] = sql
            captured["params"] = params

        client = self.create_client(connection_rows=order_rows, qall_callback=capture_query)
        with client:
            response = client.get("/marketplace/orders?status=delivered&date_from=2026-08-01&date_to=2026-08-02")

        self.assertEqual(response.status_code, 200)
        self.assertIn("item.normalized_status=%s", captured["sql"])
        self.assertIn("item.created_at < %s", captured["sql"])
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(response.json()["total_pages"], 1)
        self.assertEqual(captured["params"], (7, "delivered", date(2026, 8, 1), date(2026, 8, 3), 20, 0))

    # Подробный ответ Ozon использует id вместо product_id, но название должно попасть к товару из общего списка.
    @patch("api.domains.marketplace_catalog_service._request_json")
    def test_ozon_catalog_uses_detail_id_to_fill_product_title(self, request_json):
        request_json.side_effect = [
            {"result": {"items": [{"product_id": 16987, "offer_id": "16987"}], "last_id": ""}},
            {"items": [{"id": 16987, "offer_id": "16987", "sku": 5204485385, "name": "Apex Legends 6700 Coins"}]},
        ]

        items = _fetch_ozon_catalog(client_id="48186803", token="test-token")

        self.assertEqual(items[0]["name"], "Apex Legends 6700 Coins")
        self.assertEqual(items[0]["sku"], 5204485385)

    # Снимок цифровых заказов Ozon читает страницы и не использует методы загрузки ключей.
    @patch("api.domains.marketplace_orders_service._request_json")
    def test_ozon_orders_reads_digital_postings(self, request_json):
        request_json.return_value = {
            "postings": [{"posting_number": "123-0001", "status": "awaiting_deliver", "products": [{"sku": 5204485385, "offer_id": "PSN-500"}]}],
            "has_next": False,
        }

        rows = _fetch_ozon_orders(client_id="48186803", token="test-token")

        self.assertEqual(rows[0]["posting_number"], "123-0001")
        self.assertTrue(any("/v2/posting/digital/list" in call.args[0] for call in request_json.call_args_list))

    # Заказы услуг FBO приходят отдельным массивом result и должны попасть в общий read-only снимок.
    @patch("api.domains.marketplace_orders_service._request_json")
    def test_ozon_fbo_orders_read_result_array(self, request_json):
        request_json.return_value = {
            "result": [{"posting_number": "51115554-0069-1", "status": "delivered", "products": [{"sku": 17776, "offer_id": "ROBLOX-800"}]}],
        }

        rows = _fetch_ozon_fbo_orders(client_id="48186803", token="test-token")

        self.assertEqual(rows[0]["posting_number"], "51115554-0069-1")
        self.assertEqual(rows[0]["__marketplace_source"], "FBO")
        self.assertIn("/v2/posting/fbo/list", request_json.call_args.args[0])

    # Заказы Маркета читаются по страницам только внутри текущего дня создания заказа.
    @patch("api.domains.marketplace_orders_service._request_json")
    def test_yandex_orders_uses_one_day_creation_period(self, request_json):
        request_json.side_effect = [
            {"result": {"orders": [{"id": page, "campaignId": 22}], "paging": {"nextPageToken": f"page-{page}"} if page < 5 else {}}}
            for page in range(1, 6)
        ]

        rows = _fetch_yandex_market_orders(business_id=11, campaign_id=22, token="test-token")

        self.assertEqual([row["id"] for row in rows], [1, 2, 3, 4, 5])
        self.assertEqual(request_json.call_count, 5)
        dates = request_json.call_args.kwargs["payload"]["dates"]
        self.assertEqual(date.fromisoformat(dates["creationDateTo"]) - date.fromisoformat(dates["creationDateFrom"]), timedelta(days=1))

    # Одинаковый интерфейс использует один код состояния, хотя статусы маркетплейсов различаются.
    def test_marketplace_order_statuses_are_normalized(self):
        self.assertEqual(normalize_marketplace_order_status(provider_code="yandex_market", status="PROCESSING"), "processing")
        self.assertEqual(normalize_marketplace_order_status(provider_code="yandex_market", status="DELIVERY"), "in_delivery")
        self.assertEqual(normalize_marketplace_order_status(provider_code="ozon", status="awaiting_deliver"), "processing")
        self.assertEqual(normalize_marketplace_order_status(provider_code="ozon", status="done"), "delivered")
        self.assertEqual(normalize_marketplace_order_status(provider_code="ozon", status="new-unmapped"), "problem")
