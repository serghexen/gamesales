import unittest
from datetime import date, datetime, timezone
from io import BytesIO
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

from openpyxl import Workbook

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

    def executemany(self, sql, seq_of_params):
        for params in seq_of_params:
            self.execute(sql, params)

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

    # Собирает xlsx-файл для проверок импорта товаров.
    def _build_games_import_xlsx(self, *, active_title="Sheet", include_games_sheet=True):
        wb = Workbook()
        ws_active = wb.active
        ws_active.title = active_title
        ws_active.append(["Товар", "Платформа"])
        ws_active.append(["Wrong Active Row", "ps5"])
        if include_games_sheet:
            ws_games = wb.create_sheet("Игры")
            ws_games.append(["Игры", "Платформа"])
            ws_games.append(["EA FC 26", "ps5"])
            ws_games.append(["PS Plus Подписка", "ps5"])
            ws_games.append(["Mega ПЛЮС", "ps4"])
        buf = BytesIO()
        wb.save(buf)
        return buf.getvalue()

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

    def test_list_subscription_products_with_free_slot_success(self):
        script = [
            {"one": ("ps5",)},
            {"all": [(77,), (88,)]},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get(
                    "/products/subscriptions/free-by-slot?slot_type_code=ps5_p1",
                    headers=self._auth_headers(role="manager"),
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), [77, 88])

    def test_list_subscription_products_with_free_slot_unknown_slot(self):
        script = [
            {"one": None},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get(
                    "/products/subscriptions/free-by-slot?slot_type_code=missing_slot",
                    headers=self._auth_headers(role="manager"),
                )
            self.assertEqual(res.status_code, 400)

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
            },  # load_product row
            {"all": []},  # load_product platform_codes
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
            self.assertEqual(res.json()["platform_codes"], [])

    def test_update_subscription_product_saves_platform_codes(self):
        script = [
            {
                "one": (
                    "subscription",  # type_code
                    "PS Plus",  # title
                    "PLUS",  # short_title
                    10,  # region_id
                    None,  # gp.link
                    None,  # gp.text_lang
                    None,  # gp.audio_lang
                    None,  # gp.vr_support
                    "sony",  # sp.provider
                    "month",  # sp.billing_period
                    "base",  # sp.notes
                )
            },  # select existing product
            {"rowcount": 1},  # update app.products
            {"rowcount": 1},  # upsert subscription_products
            {"rowcount": 1},  # delete old product_platforms
            {"one": (5,)},  # platform_id for ps5
            {"rowcount": 1},  # insert app.product_platforms via executemany
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
            },  # load_product row
            {"all": [("ps5",)]},  # load_product platform_codes
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put(
                    "/products/77",
                    headers=self._auth_headers(role="manager"),
                    json={"platform_codes": ["ps5"]},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["product_id"], 77)
            self.assertEqual(res.json()["type_code"], "subscription")
            self.assertEqual(res.json()["platform_codes"], ["ps5"])

    # Список сроков подписки должен возвращать данные аккаунта и признак занятости.
    def test_list_subscription_terms_success(self):
        script = [
            {"one": (1,)},  # ensure_subscription_product
            {
                "all": [
                    (
                        101,
                        77,
                        7,
                        "user1",
                        "gmail.com",
                        date(2027, 1, 13),
                        "first",
                        False,
                        datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
                        True,
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
                res = client.get(
                    "/products/subscriptions/77/terms",
                    headers=self._auth_headers(role="manager"),
                )
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(len(body), 1)
            self.assertEqual(body[0]["term_id"], 101)
            self.assertEqual(body[0]["login_full"], "user1@gmail.com")
            self.assertEqual(body[0]["occupied"], True)

    # Доступные сроки должны фильтроваться по slot_type_code и возвращаться только свободные.
    def test_list_available_subscription_terms_success(self):
        script = [
            {"one": (1,)},  # ensure_subscription_product
            {"one": (1,)},  # slot exists
            {
                "all": [
                    (
                        201,
                        77,
                        7,
                        "user2",
                        "mail.ru",
                        date(2027, 2, 5),
                        "note",
                        False,
                        datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc),
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
                res = client.get(
                    "/products/subscriptions/77/terms/available?slot_type_code=ps5_p1",
                    headers=self._auth_headers(role="manager"),
                )
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(len(body), 1)
            self.assertEqual(body[0]["term_id"], 201)
            self.assertEqual(body[0]["occupied"], False)

    # Валидация должна читать лист "Игры" и предупреждать о пропуске подписок.
    def test_products_import_validate_prefers_games_sheet_and_skips_subscriptions(self):
        script = [
            {"all": [("ps4",), ("ps5",)]},  # platform codes
        ]
        content = self._build_games_import_xlsx(active_title="Свод", include_games_sheet=True)
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/products/import/validate",
                    headers=self._auth_headers(role="admin"),
                    files={"file": ("games.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                )
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(body["ok"], True)
            self.assertEqual(body["total"], 3)
            warning_messages = [str(w.get("message") or "") for w in body.get("warnings", [])]
            self.assertEqual(sum("подпиской/плюсом" in msg for msg in warning_messages), 2)

    # Если листа "Игры" нет, валидация должна использовать активный лист.
    def test_products_import_validate_falls_back_to_active_sheet(self):
        script = [
            {"all": [("ps5",)]},  # platform codes
        ]
        content = self._build_games_import_xlsx(active_title="products", include_games_sheet=False)
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/products/import/validate",
                    headers=self._auth_headers(role="admin"),
                    files={"file": ("games.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                )
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(body["total"], 1)

if __name__ == "__main__":
    unittest.main()
