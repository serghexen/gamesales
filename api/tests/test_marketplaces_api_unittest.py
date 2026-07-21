import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

from api.domains.marketplaces_api import mount_marketplaces_routes


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
class MarketplacesApiTests(unittest.TestCase):
    # Поднимает маршрут с памятью вместо БД, чтобы проверять контракт без доступа к Ozon.
    def create_client(self, rows=None, writes=None):
        app = FastAPI()
        stored_rows = list(rows or [])
        write_log = writes if writes is not None else []

        def fake_qall(_conn, _sql, _params=None):
            return stored_rows

        def fake_exec1(_conn, sql, params=None):
            write_log.append((sql, params))

        mount_marketplaces_routes(
            app,
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=lambda *_args, **_kwargs: None,
            qall=fake_qall,
            exec1=fake_exec1,
            get_current_user=lambda: SimpleNamespace(username="owner", role="owner"),
            require_role=lambda *_roles: (lambda: SimpleNamespace(username="owner", role="owner")),
        )
        return TestClient(app), write_log

    # Чтение снимка не должно выполнять запрос к внешнему кабинету Ozon.
    def test_list_catalog_returns_local_snapshot(self):
        client, writes = self.create_client(
            rows=[(101, "steam-1000", "Steam 1000", "VISIBLE", "sale", datetime(2026, 7, 21, tzinfo=timezone.utc))]
        )
        with client:
            response = client.get("/marketplaces/ozon/catalog")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["external_product_id"], 101)
        self.assertEqual(response.json()["items"][0]["offer_id"], "steam-1000")
        self.assertTrue(writes, "schema was not prepared")

    # Синхронизация сохраняет данные локально и не отдает клиенту секреты или сырой payload.
    def test_sync_catalog_saves_remote_items_locally(self):
        client, writes = self.create_client()
        with patch(
            "api.domains.marketplaces_api.fetch_ozon_catalog_items",
            return_value=[{"product_id": 202, "offer_id": "psn-500", "name": "PSN 500", "visibility": "VISIBLE"}],
        ):
            with client:
                response = client.post("/marketplaces/ozon/catalog/sync")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["synced_items"], 1)
        insert_calls = [params for sql, params in writes if "INSERT INTO app.marketplace_ozon_catalog_items" in sql]
        self.assertEqual(len(insert_calls), 1)
        self.assertEqual(insert_calls[0][1:4], (202, "psn-500", "PSN 500"))


if __name__ == "__main__":
    unittest.main()
