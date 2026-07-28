import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

try:
    from api.domains.marketplace_key_pools_api import mount_marketplace_key_pool_routes
except ModuleNotFoundError:  # Запуск из папки api использует локальный пакет domains.
    from domains.marketplace_key_pools_api import mount_marketplace_key_pool_routes


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
class MarketplaceKeyPoolsApiTests(unittest.TestCase):
    # Поднимает общий API пула в памяти, чтобы не требовать мигрированную БД для проверки контрактов.
    def create_client(self, rows=None, required_roles=None, q1_values=None):
        app = FastAPI()
        writes = []
        sequence = iter(q1_values or [(11,), (2, 1, 3, 0, 6), (101,), (102,)])

        def fake_q1(_conn, _sql, _params=None):
            return next(sequence, None)

        def fake_qall(_conn, _sql, _params=None):
            return list(rows or [])

        def fake_exec1(_conn, sql, params=None):
            writes.append((sql, params))
            return 1

        def fake_require_role(*roles):
            if required_roles is not None:
                required_roles.append(roles)
            return lambda: SimpleNamespace(username="owner", role="owner")

        mount_marketplace_key_pool_routes(
            app, DB_DSN="postgresql://test", psycopg=_FakePsycopg(), q1=fake_q1,
            qall=fake_qall, exec1=fake_exec1, require_role=fake_require_role,
        )
        return TestClient(app), writes

    # Список пула должен вернуть только маску, чтобы браузер не получил полный ключ.
    def test_pool_list_masks_keys_and_keeps_marketplaces_separate(self):
        rows = [(1, "ABCD", "free", None, "", None, datetime(2026, 7, 25, tzinfo=timezone.utc))]
        client, _writes = self.create_client(rows=rows)
        with client:
            response = client.get("/marketplaces/key-pools/ozon/103?store_code=asat")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["marketplace"], "ozon")
        self.assertEqual(response.json()["items"][0]["masked_code"], "••••ABCD")
        self.assertNotIn("ABCD", str(response.json()["items"][0].get("code", "")))

    # Новые ключи шифруются SQL-функцией и не имеют маршрута, который отправляет их в Ozon или Маркет.
    def test_add_keys_uses_encrypted_storage_and_skips_duplicates(self):
        client, _writes = self.create_client()
        with patch.dict(os.environ, {"MARKETPLACE_KEY_POOL_SECRET": "x" * 32}, clear=False):
            with client:
                response = client.post(
                    "/marketplaces/key-pools/yandex_market/PSN-500/keys?store_code=asat",
                    json={"codes": ["CODE-ONE", "CODE-TWO", "CODE-ONE"]},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"added": 2, "duplicates": 1})

    # Выданный ключ тоже можно сверить: маршрут расшифровывает только одну строку из выбранного пула.
    def test_reveal_key_allows_owner_to_check_a_delivered_key(self):
        client, _writes = self.create_client(q1_values=[(11,), ("SENT-CODE-1234",)])
        with patch.dict(os.environ, {"MARKETPLACE_KEY_POOL_SECRET": "x" * 32}, clear=False):
            with client:
                response = client.post("/marketplaces/key-pools/ozon/103/keys/55/reveal?store_code=asat", json={})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"id": 55, "code": "SENT-CODE-1234"})

    # Операции с пулами остаются доступны только владельцу, как и операции выдачи ключей.
    def test_routes_require_owner_role(self):
        required_roles = []
        self.create_client(required_roles=required_roles)

        self.assertEqual(required_roles, [("owner",), ("owner",), ("owner",), ("owner",), ("owner",)])
