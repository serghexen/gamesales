import unittest
import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

try:
    from api.domains import yandex_market_catalog_api
except ModuleNotFoundError:  # Запуск из папки api использует локальный пакет domains.
    from domains import yandex_market_catalog_api

mount_yandex_market_catalog_routes = yandex_market_catalog_api.mount_yandex_market_catalog_routes


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
class YandexMarketCatalogApiTests(unittest.TestCase):
    # Поднимает изолированные маршруты, чтобы проверить контракт без реального кабинета Маркета.
    def create_client(self, rows=None, detail_row=None, q1_handler=None, required_roles=None):
        app = FastAPI()
        write_log = []

        def fake_qall(_conn, _sql, _params=None):
            return list(rows or [])

        def fake_q1(_conn, sql, params=None):
            if q1_handler:
                return q1_handler(sql, params)
            return detail_row

        def fake_exec1(_conn, sql, params=None):
            write_log.append((sql, params))

        def fake_require_role(*roles):
            # Запоминает роли маршрутов, чтобы товарные операции не стали доступны оператору.
            if required_roles is not None:
                required_roles.append(roles)
            return lambda: SimpleNamespace(username="owner", role="owner")

        mount_yandex_market_catalog_routes(
            app,
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=fake_q1,
            qall=fake_qall,
            exec1=fake_exec1,
            require_role=fake_require_role,
        )
        return TestClient(app), write_log

    # Каталог сохраняет активные и архивные карточки в локальный снимок без операций с ключами.
    def test_sync_catalog_saves_market_mapping(self):
        client, writes = self.create_client()
        remote_item = {
            "offer": {"offerId": "PSN-500", "name": "PSN 500", "archived": False, "downloadable": True, "basicPrice": {"value": 500, "currencyId": "RUR"}},
            "mapping": {"marketSku": 123, "marketCategoryName": "Игровые карты"},
        }
        with patch.object(yandex_market_catalog_api, "fetch_yandex_market_catalog_items", return_value=[remote_item]):
            with client:
                response = client.post("/marketplaces/yandex/catalog/sync")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["synced_items"], 1)
        inserts = [params for sql, params in writes if "INSERT INTO app.marketplace_yandex_catalog_items" in sql]
        self.assertEqual(inserts[0][1:4], ("PSN-500", 123, "PSN 500"))
        self.assertTrue(inserts[0][7])

    # Архивирование выбирает именно путь archive и сразу меняет признак в нашем снимке.
    def test_archive_catalog_item_updates_remote_and_local_snapshot(self):
        client, writes = self.create_client()
        with patch.object(yandex_market_catalog_api, "update_yandex_market_catalog_archive", return_value={}) as update_archive:
            with client:
                response = client.post("/marketplaces/yandex/catalog/PSN-500/archive")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"offer_id": "PSN-500", "archived": True})
        update_archive.assert_called_once_with("PSN-500", archived=True, store_code="asat")
        updates = [params for sql, params in writes if "SET archived=%s" in sql]
        self.assertEqual(updates[0], (True, "asat", "PSN-500"))

    # Лимит хранится локально, а отправка остатка происходит только с явным publish_stock=true.
    def test_publish_stock_calls_market_only_for_explicit_request(self):
        def q1_handler(sql, _params):
            if "FROM app.marketplace_yandex_stock_settings" in sql:
                return (7, 7, datetime(2026, 7, 25, tzinfo=timezone.utc))
            return None

        client, _writes = self.create_client(q1_handler=q1_handler)
        with patch.object(yandex_market_catalog_api, "update_yandex_market_stock", return_value={}) as update_stock:
            with client:
                saved = client.put("/marketplaces/yandex/catalog/PSN-500/stock-settings", json={"manual_stock_limit": 7})
                published = client.put("/marketplaces/yandex/catalog/PSN-500/stock-settings?publish_stock=true", json={"manual_stock_limit": 7})

        self.assertEqual(saved.status_code, 200)
        self.assertEqual(published.status_code, 200)
        update_stock.assert_called_once_with("PSN-500", 7, store_code="asat")

    # Открытие карточки читает доступный остаток методом POST и не передает новое значение через PUT.
    def test_stock_settings_reads_live_market_stock_without_publishing(self):
        client, _writes = self.create_client()
        market_stock = {"found": True, "available_stock": 4, "updated_at": "2026-07-25T11:33:00Z"}
        with patch.object(yandex_market_catalog_api, "fetch_yandex_market_stock", return_value=market_stock) as fetch_stock:
            with client:
                response = client.get("/marketplaces/yandex/catalog/PSN-500/stock-settings")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["market_available_stock"], 4)
        fetch_stock.assert_called_once_with("PSN-500", store_code="asat")

    # Синхронизация заказов сохраняет позиции локально и не запускает выдачу ключей.
    def test_sync_orders_saves_market_order_items(self):
        client, writes = self.create_client()
        remote_orders = [{
            "orderId": 501, "campaignId": 70940298, "status": "PROCESSING", "substatus": "STARTED",
            "creationDate": "2026-07-25T12:00:00Z", "updateDate": "2026-07-25T12:01:00Z",
            "items": [{"id": 99, "offerId": "PSN-500", "offerName": "PSN 500", "count": 2, "prices": {"payment": {"value": 500, "currencyId": "RUR"}}}],
        }]
        with patch.object(yandex_market_catalog_api, "fetch_yandex_market_orders", return_value={"orders": remote_orders, "pages_loaded": 1, "has_more": False}) as fetch_orders:
            with client:
                response = client.post("/marketplaces/yandex/catalog/PSN-500/orders/sync")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["imported_orders"], 1)
        self.assertIsNone(fetch_orders.call_args.kwargs["updated_from"])
        inserts = [params for sql, params in writes if "INSERT INTO app.marketplace_yandex_order_items" in sql]
        self.assertEqual(inserts[0][:7], ("asat", 501, 99, 70940298, "PSN-500", "PSN 500", 2))
        checkpoints = [params for sql, params in writes if "marketplace_yandex_order_sync_state" in sql]
        self.assertEqual(checkpoints[0][0], "asat")

    # История заказа отдается из локального снимка и не обращается к кабинету при открытии.
    def test_list_orders_returns_local_snapshot(self):
        row = (501, 99, "PSN-500", "PSN 500", 2, "PROCESSING", "STARTED", "500", "RUR", datetime(2026, 7, 25, tzinfo=timezone.utc), datetime(2026, 7, 25, 12, tzinfo=timezone.utc))
        client, _writes = self.create_client(rows=[row])
        with client:
            response = client.get("/marketplaces/yandex/catalog/PSN-500/orders")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["order_id"], 501)
        self.assertEqual(response.json()["items"][0]["quantity"], 2)

    # Ручная sandbox-выдача шифрует ключи локально и не вызывает API Маркета или Interhub.
    def test_sandbox_manual_delivery_saves_only_local_key_and_delivery(self):
        def q1_handler(sql, _params):
            if "FROM app.marketplace_yandex_order_items" in sql:
                return ("PSN-500", 2, "PROCESSING", True)
            if "marketplace_yandex_sandbox_deliveries" in sql:
                return None
            if "INSERT INTO app.marketplace_manual_key_pools" in sql:
                return (17,)
            if "FROM app.marketplace_manual_keys" in sql:
                return None
            return None

        client, writes = self.create_client(q1_handler=q1_handler)
        env = {
            "YANDEX_MARKET_TEST_INCLUDE_FAKE_ORDERS": "true",
            "YANDEX_MARKET_TEST_SANDBOX_ACTIONS_ENABLED": "true",
            "MARKETPLACE_KEY_POOL_SECRET": "x" * 32,
        }
        with patch.dict(os.environ, env, clear=False):
            with client:
                response = client.post(
                    "/marketplaces/yandex/sandbox/orders/501/items/99/deliver?store_code=test",
                    json={"codes": ["AAAA-1111", "BBBB-2222"]},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["delivery_source"], "manual")
        self.assertEqual(response.json()["status"], "locally_issued")
        self.assertTrue(any("INSERT INTO app.marketplace_manual_keys" in sql for sql, _params in writes))
        self.assertTrue(any("INSERT INTO app.marketplace_yandex_sandbox_deliveries" in sql for sql, _params in writes))

    # Выдача из пула берет весь комплект под блокировкой и не допускает частичную фиксацию.
    def test_sandbox_pool_delivery_marks_exact_number_of_local_keys(self):
        def q1_handler(sql, _params):
            if "FROM app.marketplace_yandex_order_items" in sql:
                return ("PSN-500", 2, "PROCESSING", True)
            if "marketplace_yandex_sandbox_deliveries" in sql:
                return None
            if "FROM app.marketplace_manual_key_pools" in sql:
                return (17,)
            return None

        client, writes = self.create_client(rows=[(41,), (42,)], q1_handler=q1_handler)
        env = {
            "YANDEX_MARKET_TEST_INCLUDE_FAKE_ORDERS": "true",
            "YANDEX_MARKET_TEST_SANDBOX_ACTIONS_ENABLED": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            with client:
                response = client.post("/marketplaces/yandex/sandbox/orders/501/items/99/issue-from-pool?store_code=test")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["issued_qty"], 2)
        pool_updates = [params for sql, params in writes if "UPDATE app.marketplace_manual_keys" in sql]
        self.assertEqual(pool_updates[0][1], [41, 42])

    # Контур не позволяет выдать обычный сохраненный заказ даже с включенным тестовым флагом.
    def test_sandbox_delivery_rejects_non_fake_order(self):
        def q1_handler(sql, _params):
            if "FROM app.marketplace_yandex_order_items" in sql:
                return ("PSN-500", 1, "PROCESSING", False)
            return None

        client, _writes = self.create_client(q1_handler=q1_handler)
        env = {
            "YANDEX_MARKET_TEST_INCLUDE_FAKE_ORDERS": "true",
            "YANDEX_MARKET_TEST_SANDBOX_ACTIONS_ENABLED": "true",
            "MARKETPLACE_KEY_POOL_SECRET": "x" * 32,
        }
        with patch.dict(os.environ, env, clear=False):
            with client:
                response = client.post(
                    "/marketplaces/yandex/sandbox/orders/501/items/99/deliver?store_code=test",
                    json={"codes": ["AAAA-1111"]},
                )

        self.assertEqual(response.status_code, 409)
        self.assertIn("только сохраненным fake-заказам", response.json()["detail"])

    # Все маршруты каталога остаются операцией владельца, как и Ozon на вкладке товаров.
    def test_routes_require_owner_role(self):
        required_roles = []
        self.create_client(required_roles=required_roles)

        self.assertGreaterEqual(len(required_roles), 8)
        self.assertTrue(all(roles == ("owner",) for roles in required_roles))
