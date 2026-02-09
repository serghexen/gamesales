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
class DealsEndpointsTests(unittest.TestCase):
    def _client(self):
        return TestClient(app_module.app)

    def _auth_headers(self, role="admin", username="admin", user_id=1):
        token = app_module.create_access_token(user_id, username, role)
        return {"Authorization": f"Bearer {token}"}

    # Без токена список сделок открываться не должен.
    def test_list_deals_requires_auth(self):
        with patch.object(app_module, "ensure_analytics_schema", return_value=None):
            with self._client() as client:
                res = client.get("/deals")
            self.assertEqual(res.status_code, 401)

    # Валидация списка: page должен быть >= 1.
    def test_list_deals_invalid_page(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/deals?page=0", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 400)

    # Валидация списка: page_size должен быть в диапазоне 1..200.
    def test_list_deals_invalid_page_size(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/deals?page=1&page_size=500", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 400)

    # Успешная выдача сделок должна собирать account_login и total.
    def test_list_deals_success(self):
        script = [
            {"one": (1,)},  # total
            {
                "all": [
                    (
                        15,
                        "Продажа",
                        "sale",
                        "Подтверждена",
                        "pending",
                        "В ожидании",
                        "ORD-1",
                        "admin",
                        "RU",
                        7,
                        "login1",
                        "gmail.com",
                        21,
                        "Game A",
                        "GA",
                        "ps5",
                        "cust1",
                        3,
                        1200.0,
                        500.0,
                        datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc),
                        datetime(2026, 2, 1, 11, 0, tzinfo=timezone.utc),
                        None,
                        0,
                        None,
                        "note",
                        "https://game",
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
                res = client.get("/deals?page=1&page_size=20", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(body["total"], 1)
            self.assertEqual(len(body["items"]), 1)
            self.assertEqual(body["items"][0]["deal_id"], 15)
            self.assertEqual(body["items"][0]["account_login"], "login1@gmail.com")
            self.assertEqual(body["items"][0]["order_number"], "ORD-1")
            self.assertEqual(body["items"][0]["responsible_username"], "admin")

    # Валидация create_deal: тип сделки должен быть sale/rental.
    def test_create_deal_invalid_type(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/deals",
                    headers=self._auth_headers(role="manager"),
                    json={"deal_type_code": "other", "customer_nickname": "cust", "price": 100},
                )
            self.assertEqual(res.status_code, 400)

    # Для sale обязателен region_code.
    def test_create_deal_sale_requires_region(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/deals",
                    headers=self._auth_headers(role="manager"),
                    json={"deal_type_code": "sale", "customer_nickname": "cust", "price": 100},
                )
            self.assertEqual(res.status_code, 400)

    # Успешная продажа должна вернуть deal_id.
    def test_create_deal_sale_success(self):
        script = [
            {"one": (10,)},  # region_id by code
            {"one": None},  # customer lookup
            {"one": (22,)},  # customer insert
            {"one": (33,)},  # deal insert
            {"one": (44,)},  # deal_item insert
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/deals",
                    headers=self._auth_headers(role="manager"),
                    json={
                        "deal_type_code": "sale",
                        "region_code": "RU",
                        "customer_nickname": "cust",
                        "price": 1000,
                        "purchase_cost": 400,
                    },
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"deal_id": 33})

    # Для аренды при нехватке слотов должен возвращаться 409.
    def test_create_deal_rental_not_enough_slots(self):
        script = [
            {"one": (1,)},  # ensure_account_exists
            {"one": (1,)},  # ensure_game_active
            {"one": ("ps5_p1", "ps5", "single", 1)},  # get_slot_type
            {"one": (2,)},  # get_platform_id
            {"one": (7,)},  # region from account
            {"one": (5, None)},  # customer exists
            {"one": (0,)},  # get_account_slot_free
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/deals",
                    headers=self._auth_headers(role="manager"),
                    json={
                        "deal_type_code": "rental",
                        "account_id": 7,
                        "game_id": 21,
                        "slot_type_code": "ps5_p1",
                        "customer_nickname": "cust",
                        "price": 500,
                    },
                )
            self.assertEqual(res.status_code, 409)

    # Для rentals обязателен slot_type_code.
    def test_create_rental_requires_slot_type(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/rentals",
                    headers=self._auth_headers(role="manager"),
                    json={
                        "account_id": 7,
                        "game_id": 21,
                        "customer_nickname": "cust",
                        "price": 500,
                    },
                )
            self.assertEqual(res.status_code, 400)

    # Успешный rental должен создать сделку и вернуть обновленные слоты.
    def test_create_rental_success(self):
        script = [
            {"one": (1,)},  # ensure_account_exists
            {"one": (1,)},  # ensure_game_active
            {"one": ("ps5_p1", "ps5", "single", 1)},  # get_slot_type
            {"one": (2,)},  # get_platform_id
            {"one": (5, None)},  # customer exists
            {"one": (1,)},  # get_account_slot_free
            {"one": (7,)},  # region from account
            {"one": (33,)},  # deal insert
            {"one": (44,)},  # deal_item insert
            {"rowcount": 1},  # assignment insert
            {"one": (1, 1)},  # slots_summary
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/rentals",
                    headers=self._auth_headers(role="manager"),
                    json={
                        "account_id": 7,
                        "game_id": 21,
                        "slot_type_code": "ps5_p1",
                        "customer_nickname": "cust",
                        "price": 500,
                    },
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["deal_id"], 33)
            self.assertEqual(res.json()["occupied_slots"], 1)
            self.assertEqual(res.json()["free_slots"], 1)

    # rental через /rentals должен отдавать 409 при нехватке слотов.
    def test_create_rental_not_enough_slots(self):
        script = [
            {"one": (1,)},  # ensure_account_exists
            {"one": (1,)},  # ensure_game_active
            {"one": ("ps5_p1", "ps5", "single", 1)},  # get_slot_type
            {"one": (2,)},  # get_platform_id
            {"one": (5, None)},  # customer exists
            {"one": (0,)},  # get_account_slot_free
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/rentals",
                    headers=self._auth_headers(role="manager"),
                    json={
                        "account_id": 7,
                        "game_id": 21,
                        "slot_type_code": "ps5_p1",
                        "customer_nickname": "cust",
                        "price": 500,
                    },
                )
            self.assertEqual(res.status_code, 409)

    # update_deal должен отдавать 404, если сделка не найдена.
    def test_update_deal_not_found(self):
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": None},  # select current deal
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put("/deals/999", headers=self._auth_headers(role="manager"), json={"notes": "upd"})
            self.assertEqual(res.status_code, 404)

    # update_deal должен валидировать допустимые значения типа сделки.
    def test_update_deal_invalid_type(self):
        current_row = (
            "sale",
            "confirmed",
            "pending",
            10,
            5,
            500.0,
            "A-100",
            "admin",
            77,
            None,
            None,
            None,
            500.0,
            100.0,
            datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc),
            None,
            None,
            0,
            None,
            "note",
            None,
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # select current deal
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put(
                    "/deals/77",
                    headers=self._auth_headers(role="manager"),
                    json={"deal_type_code": "invalid"},
                )
            self.assertEqual(res.status_code, 400)

    # При переключении сделки в sale без региона API должен вернуть 400.
    def test_update_deal_sale_requires_region(self):
        current_row = (
            "sale",
            "confirmed",
            "pending",
            None,
            5,
            500.0,
            "A-100",
            "admin",
            77,
            None,
            None,
            None,
            500.0,
            100.0,
            datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc),
            None,
            None,
            0,
            None,
            "note",
            None,
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # select current deal
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put("/deals/77", headers=self._auth_headers(role="manager"), json={"deal_type_code": "sale"})
            self.assertEqual(res.status_code, 400)

    # Успешный update rental должен завершаться ok=true.
    def test_update_deal_rental_success(self):
        current_row = (
            "rental",
            "confirmed",
            "pending",
            10,
            5,
            500.0,
            "A-100",
            "admin",
            77,
            7,
            21,
            2,
            500.0,
            100.0,
            datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc),
            None,
            None,
            1,
            "ps5_p1",
            "note",
            None,
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # current deal row
            {"one": ("ps5_p1", "ps5", "single", 1)},  # get_slot_type
            {"one": (2,)},  # get_platform_id
            {"one": (1,)},  # ensure_account_exists
            {"one": (1,)},  # ensure_game_exists
            {"one": (0,)},  # get_account_slot_free
            {"one": (7, "ps5_p1")},  # current assignment for free_adjusted
            {"rowcount": 1},  # update deals
            {"rowcount": 1},  # update deal_items
            {"one": (900, 7, "ps5_p1", 5, 21)},  # assignment details
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put(
                    "/deals/77",
                    headers=self._auth_headers(role="manager"),
                    json={"deal_type_code": "rental", "slot_type_code": "ps5_p1", "account_id": 7, "game_id": 21},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})


if __name__ == "__main__":
    unittest.main()
