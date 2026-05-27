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

    # Обновление роли пользователя должно писать новый role_code и возвращать профиль.
    def test_update_user_role_success(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "role_exists", return_value=True),
            patch.object(app_module, "get_user_by_username", return_value=(12, "manager1", "hash", "manager")),
            patch.object(app_module, "exec1", return_value=1) as exec1_mock,
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            token = app_module.create_access_token(1, "admin", "admin")
            with self._client() as client:
                res = client.put(
                    "/users/manager1/role",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"role_code": "operator"},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"username": "manager1", "role": "operator"})
            self.assertTrue(exec1_mock.called)

    # Создание пользователя должно сохранять заполненное имя.
    def test_create_user_with_name_success(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "role_exists", return_value=True),
            patch.object(app_module, "get_user_by_username", return_value=None),
            patch.object(app_module, "hash_password", return_value="hash"),
            patch.object(app_module, "exec1", return_value=1) as exec1_mock,
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            token = app_module.create_access_token(1, "admin", "admin")
            with self._client() as client:
                res = client.post(
                    "/users",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"username": "manager2", "password": "qwerty", "name": "Иван", "role_code": "manager"},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"username": "manager2", "role": "manager"})
            sql_text, params = exec1_mock.call_args[0][1], exec1_mock.call_args[0][2]
            self.assertIn("name", sql_text.lower())
            self.assertEqual(params[2], "Иван")

    # Полное обновление пользователя должно менять имя и роль.
    def test_update_user_success(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_DummyConnCtx()),
            patch.object(app_module, "role_exists", return_value=True),
            patch.object(app_module, "get_user_by_username", return_value=(12, "manager1", "hash", "manager")),
            patch.object(app_module, "exec1", return_value=1) as exec1_mock,
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            token = app_module.create_access_token(1, "admin", "admin")
            with self._client() as client:
                res = client.put(
                    "/users/manager1",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"name": "Новое имя", "role_code": "operator"},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"username": "manager1", "role": "operator"})
            self.assertTrue(exec1_mock.called)
            sql_text, params = exec1_mock.call_args[0][1], exec1_mock.call_args[0][2]
            self.assertIn("set name=%s, role_code=%s", sql_text.lower())
            self.assertEqual(params[0], "Новое имя")
            self.assertEqual(params[1], "operator")


if __name__ == "__main__":
    unittest.main()
