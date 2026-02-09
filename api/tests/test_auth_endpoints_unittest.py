import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover - среда без httpx
    TestClient = None

import app as app_module


class _DummyConnCtx:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def commit(self):
        return None


@unittest.skipIf(TestClient is None, "fastapi.testclient requires httpx")
class AuthEndpointsTests(unittest.TestCase):
    # Удобный helper для клиента с отключенной startup-миграцией.
    def _client(self):
        return TestClient(app_module.app)

    # Логин должен возвращать токен и пользователя при валидных данных.
    def test_login_success(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "init_auth_schema", return_value=None),
            patch.object(app_module, "ensure_admin_user", return_value=None),
            patch.object(app_module, "get_user_by_username", return_value=(1, "admin", "hashed", "admin")),
            patch.object(app_module, "verify_password", return_value=True),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertIn("access_token", body)
            self.assertEqual(body["user"]["username"], "admin")
            self.assertEqual(body["user"]["role"], "admin")

    # При неверном пароле API должен отдавать 401.
    def test_login_invalid_credentials(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "init_auth_schema", return_value=None),
            patch.object(app_module, "ensure_admin_user", return_value=None),
            patch.object(app_module, "get_user_by_username", return_value=(1, "admin", "hashed", "admin")),
            patch.object(app_module, "verify_password", return_value=False),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
            self.assertEqual(res.status_code, 401)

    # /auth/me должен возвращать пользователя из токена.
    def test_auth_me_returns_user(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            token = app_module.create_access_token(7, "alice", "manager")
            with self._client() as client:
                res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(body["username"], "alice")
            self.assertEqual(body["role"], "manager")

    # Смена пароля должна вызвать UPDATE и вернуть ok=true.
    def test_change_password_success(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "get_user_by_username", return_value=(1, "admin", "old_hash", "admin")),
            patch.object(app_module, "verify_password", return_value=True),
            patch.object(app_module, "hash_password", return_value="new_hash"),
            patch.object(app_module, "exec1", return_value=1) as exec1_mock,
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            token = app_module.create_access_token(1, "admin", "admin")
            with self._client() as client:
                res = client.post(
                    "/auth/change-password",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"current_password": "old", "new_password": "new"},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})
            self.assertTrue(exec1_mock.called)


if __name__ == "__main__":
    unittest.main()
