import unittest
from datetime import datetime, timezone
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
class AnalyticsEndpointsTests(unittest.TestCase):
    def _client(self):
        return TestClient(app_module.app)

    def _auth_headers(self, role="admin", username="admin", user_id=1):
        token = app_module.create_access_token(user_id, username, role)
        return {"Authorization": f"Bearer {token}"}

    # Без токена аналитика продаж должна быть недоступна.
    def test_analytics_sales_requires_auth(self):
        with patch.object(app_module, "ensure_analytics_schema", return_value=None):
            with self._client() as client:
                res = client.get("/analytics/sales")
            self.assertEqual(res.status_code, 401)

    # Аналитика продаж должна корректно считать totals и отдавать ряды.
    def test_analytics_sales_success(self):
        script = [
            {"one": (1500.0, 600.0, 3)},  # totals_row
            {"all": [("2026-02-08", 1000.0, 400.0, 2), ("2026-02-09", 500.0, 200.0, 1)]},  # by_day
            {"all": [("sale", 1500.0, 600.0, 3)]},  # by_type
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/analytics/sales", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(body["totals"]["count"], 3)
            self.assertEqual(body["totals"]["margin"], 900.0)
            self.assertEqual(len(body["by_day"]), 2)
            self.assertEqual(len(body["by_type"]), 1)

    # Аналитика источников должна вернуть оба топа и долю повторных клиентов.
    def test_analytics_sources_success(self):
        script = [
            {"all": [(1, "tg", "Telegram", 5, 7000.0)]},  # top_by_count
            {"all": [(2, "site", "Website", 3, 9000.0)]},  # top_by_revenue
            {"one": (2, 5)},  # repeat_row
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/analytics/sources", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(body["top_by_count"][0]["source_code"], "tg")
            self.assertEqual(body["top_by_revenue"][0]["source_code"], "site")
            self.assertEqual(body["repeat_customers"]["repeat_count"], 2)
            self.assertEqual(body["repeat_customers"]["repeat_share"], 0.4)

    # В audit ограничение limit должно валидироваться.
    def test_analytics_audit_invalid_limit(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/analytics/audit?limit=0", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 400)

    # Audit должен возвращать total и список последних изменений.
    def test_analytics_audit_success(self):
        script = [
            {"one": (2,)},  # total
            {
                "all": [
                    (101, "deal_items", "update", datetime(2026, 2, 9, 10, 0, tzinfo=timezone.utc), "admin"),
                    (100, "deals", "insert", datetime(2026, 2, 9, 9, 0, tzinfo=timezone.utc), "admin"),
                ]
            },
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/analytics/audit?limit=50", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(body["total"], 2)
            self.assertEqual(len(body["items"]), 2)
            self.assertEqual(body["items"][0]["table_name"], "deal_items")


if __name__ == "__main__":
    unittest.main()
