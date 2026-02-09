import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

import app as app_module


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
class TelegramEndpointsTests(unittest.TestCase):
    def _client(self):
        return TestClient(app_module.app)

    def _auth_headers(self, role="admin", username="admin", user_id=1):
        token = app_module.create_access_token(user_id, username, role)
        return {"Authorization": f"Bearer {token}"}

    # Если общей сессии нет, API должен вернуть not_connected.
    def test_tg_status_not_connected(self):
        script = [{"one": None}]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/tg/status", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"status": "not_connected", "phone": ""})

    # При готовой сессии статус должен отдавать phone и has_session=true.
    def test_tg_status_ready(self):
        script = [{"one": ("ready", "+79990000000", "session-token")}]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/tg/status", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["status"], "ready")
            self.assertEqual(res.json()["phone"], "+79990000000")
            self.assertTrue(res.json()["has_session"])

    # Старт авторизации должен быть закрыт для manager (только admin).
    def test_tg_auth_start_forbidden_for_manager(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post("/tg/auth/start", headers=self._auth_headers(role="manager"), json={"phone": "+7999"})
            self.assertEqual(res.status_code, 403)

    # Невалидный статус диалога должен возвращать 400.
    def test_tg_dialog_status_invalid(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put(
                    "/tg/dialogs/100/status",
                    headers=self._auth_headers(role="manager"),
                    json={"status": "bad_status"},
                )
            self.assertEqual(res.status_code, 400)

    # Смена статуса диалога должна возвращать ok=true.
    def test_tg_dialog_status_set_success(self):
        script = [
            {"one": (5,)},  # get_user_id
            {"rowcount": 1},  # upsert status
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put(
                    "/tg/dialogs/100/status",
                    headers=self._auth_headers(role="manager"),
                    json={"status": "accepted"},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["ok"], True)
            self.assertEqual(res.json()["status"], "accepted")

    # Если контакта нет в БД, API должен вернуть пустые поля.
    def test_tg_contact_get_empty(self):
        script = [{"one": None}]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/tg/contact?sender_id=123", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"title": "", "info": ""})

    # Обновление контакта должно проходить и возвращать ok=true.
    def test_tg_contact_upsert_success(self):
        script = [
            {"one": (5,)},  # get_user_id
            {"rowcount": 1},  # upsert contact
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put(
                    "/tg/contact",
                    headers=self._auth_headers(role="manager"),
                    json={"sender_id": 123, "title": "Имя", "info": "Описание"},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})

    # Если Telegram не подключен, список диалогов должен возвращать 400.
    def test_tg_dialogs_not_connected(self):
        script = [{"one": (None, "pending")}]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/tg/dialogs", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 400)

    # Если Telegram не подключен, чтение сообщений тоже должно возвращать 400.
    def test_tg_messages_not_connected(self):
        script = [{"one": (None, "pending")}]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/tg/messages?chat_id=1", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 400)


if __name__ == "__main__":
    unittest.main()
