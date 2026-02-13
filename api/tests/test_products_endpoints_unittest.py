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
class ProductsEndpointsTests(unittest.TestCase):
    def _client(self):
        return TestClient(app_module.app)

    def _auth_headers(self, role="admin", username="admin", user_id=1):
        token = app_module.create_access_token(user_id, username, role)
        return {"Authorization": f"Bearer {token}"}

    def test_list_products_requires_auth(self):
        with patch.object(app_module, "ensure_analytics_schema", return_value=None):
            with self._client() as client:
                res = client.get("/products")
            self.assertEqual(res.status_code, 401)

    def test_list_products_success(self):
        script = [
            {
                "all": [
                    (
                        55,
                        "game",
                        "Game A",
                        "GA",
                        "RU",
                        "https://game",
                        "ru",
                        "ru",
                        "no",
                        None,
                        None,
                        None,
                        ["ps4", "ps5"],
                        1,
                    )
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
                res = client.get("/products", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["total"], 1)
            self.assertEqual(res.json()["items"][0]["product_id"], 55)
            self.assertEqual(res.json()["items"][0]["platform_codes"], ["ps4", "ps5"])

    def test_list_slot_types_success(self):
        script = [
            {
                "all": [
                    ("activate_ps4", "П3 (PS4)", "ps4", "activate", 2),
                    ("play_ps5", "П2 (PS5)", "ps5", "play", 1),
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
                res = client.get("/slot-types", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(len(body), 2)
            self.assertEqual(body[0]["platform_code"], "ps4")
            self.assertEqual(body[1]["platform_code"], "ps5")

    def test_create_subscription_product_success(self):
        script = [
            {"one": (1,)},  # product type exists
            {"one": (10,)},  # region_id by code
            {"one": (77,)},  # new product_id
            {"rowcount": 1},  # subscription insert
            {
                "one": (
                    77,
                    "subscription",
                    "PS Plus",
                    "PLUS",
                    "RU",
                    None,
                    None,
                    None,
                    None,
                    None,
                    "sony",
                    "month",
                    "base",
                )
            },
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/products",
                    headers=self._auth_headers(role="manager"),
                    json={
                        "type_code": "subscription",
                        "title": "PS Plus",
                        "short_title": "PLUS",
                        "region_code": "RU",
                        "provider": "sony",
                        "billing_period": "month",
                        "subscription_notes": "base",
                    },
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["product_id"], 77)
            self.assertEqual(res.json()["type_code"], "subscription")

if __name__ == "__main__":
    unittest.main()
