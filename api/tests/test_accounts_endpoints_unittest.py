import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

import app as app_module


class _DummyConnCtx:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def commit(self):
        return None


class _ScriptedCursor:
    def __init__(self, script):
        self._script = script
        self._current = None
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def execute(self, sql, params=None):
        if not self._script:
            raise AssertionError(f"Unexpected SQL without scripted response: {sql}")
        self._current = self._script.pop(0)
        self.rowcount = int(self._current.get("rowcount", 0))

    def fetchone(self):
        if not self._current:
            return None
        return self._current.get("one")

    def fetchall(self):
        if not self._current:
            return []
        return self._current.get("all", [])


class _ScriptedConnCtx:
    def __init__(self, script):
        self._script = list(script)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def commit(self):
        return None

    def cursor(self):
        return _ScriptedCursor(self._script)


@unittest.skipIf(TestClient is None, "fastapi.testclient requires httpx")
class AccountsEndpointsTests(unittest.TestCase):
    def _client(self):
        return TestClient(app_module.app)

    def _auth_headers(self, role="admin", username="admin", user_id=1):
        token = app_module.create_access_token(user_id, username, role)
        return {"Authorization": f"Bearer {token}"}

    # Без токена список аккаунтов открываться не должен.
    def test_list_accounts_requires_auth(self):
        with patch.object(app_module, "ensure_analytics_schema", return_value=None):
            with self._client() as client:
                res = client.get("/accounts")
            self.assertEqual(res.status_code, 401)

    # Список аккаунтов должен возвращать агрегированные данные по слотам.
    def test_list_accounts_success(self):
        script = [
            {
                "all": [
                    (
                        7,
                        "RU",
                        "active",
                        "login1",
                        "gmail.com",
                        "2024-01-10",
                        "notes",
                        ["Game A"],
                        ["ps5"],
                        "ps5_p1",
                        "ps5",
                        "single",
                        1,
                        0,
                        1,
                        1,
                    )
                ]
            }
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/accounts", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(body["total"], 1)
            self.assertEqual(len(body["items"]), 1)
            self.assertEqual(body["items"][0]["account_id"], 7)
            self.assertEqual(body["items"][0]["login_full"], "login1@gmail.com")
            self.assertEqual(len(body["items"][0]["slot_status"]), 1)

    # Создание аккаунта должно валидировать обязательные поля.
    def test_create_account_validation_error(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/accounts",
                    headers=self._auth_headers(role="manager"),
                    json={"region_code": "RU", "login_name": "", "domain_code": ""},
                )
            self.assertEqual(res.status_code, 400)

    # Создание аккаунта должно вернуть карточку с платформами и статусом слотов.
    def test_create_account_success(self):
        script = [
            {"one": (2,)},  # get_region_id
            {"one": (3,)},  # get_domain_id
            {"one": (11,)},  # insert account
            {"one": (1, 2)},  # platform ps4
            {"one": (2, 2)},  # platform ps5
            {"rowcount": 1},  # upsert account_platforms
            {"all": [("ps5", 2, 0, 2)]},  # get_account_platform_slots
            {"all": [("ps5_p1", "ps5", "single", 1, 0, 1)]},  # get_account_slot_status
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/accounts",
                    headers=self._auth_headers(role="manager"),
                    json={
                        "region_code": "RU",
                        "login_name": "acc1",
                        "domain_code": "gmail.com",
                        "account_date": "2024-01-10",
                        "notes": "new",
                    },
                )
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(body["account_id"], 11)
            self.assertEqual(body["status"], "active")
            self.assertEqual(body["login_full"], "acc1@gmail.com")

    # Обновление аккаунта доступно только админу.
    def test_update_account_forbidden_for_manager(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put("/accounts/5", headers=self._auth_headers(role="manager"), json={"notes": "x"})
            self.assertEqual(res.status_code, 403)

    # Обновление аккаунта должно вернуть актуальную карточку.
    def test_update_account_success(self):
        script = [
            {"one": ("login1", 3, 2, "active", "2024-01-10", "old")},  # current
            {"rowcount": 1},  # update
            {"one": (5, "RU", "active", "login1", "gmail.com", "2024-01-10", "updated")},  # result row
            {"all": []},  # get_account_platform_slots
            {"all": []},  # get_account_slot_status
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put("/accounts/5", headers=self._auth_headers(role="admin"), json={"notes": "updated"})
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["notes"], "updated")

    # Архивирование несуществующего аккаунта должно вернуть 404.
    def test_archive_account_not_found(self):
        script = [{"one": None}]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.delete("/accounts/999", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 404)

    # Секрет должен сохраняться в base64 и возвращаться в ответе.
    def test_upsert_account_secret_success(self):
        script = [
            {"one": ("pwd", "c2VjcmV0", "2026-02-09T00:00:00Z")},
            {"one": ("pwd", "c2VjcmV0", "2026-02-09T00:00:00Z")},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/accounts/7/secrets",
                    headers=self._auth_headers(role="admin"),
                    json={"secret_key": "pwd", "secret_value": "secret"},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["secret_value_b64"], "c2VjcmV0")

    # Менеджер не должен управлять секретами аккаунта.
    def test_upsert_account_secret_forbidden_for_manager(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/accounts/7/secrets",
                    headers=self._auth_headers(role="manager"),
                    json={"secret_key": "pwd", "secret_value": "secret"},
                )
            self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
