import unittest
from datetime import datetime, timezone
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

import app as app_module


class _ScriptedCursor:
    def __init__(self, script, sql_collector=None):
        self._script = script
        self._current = None
        self.rowcount = 0
        self._sql_collector = sql_collector

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def execute(self, sql, params=None):
        # Сохраняем SQL в тестах, где нужно проверить дополнительные условия фильтрации.
        if self._sql_collector is not None:
            self._sql_collector.append(str(sql))
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
    def __init__(self, script, sql_collector=None):
        self._script = list(script)
        self._sql_collector = sql_collector

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def commit(self):
        return None

    def cursor(self):
        return _ScriptedCursor(self._script, sql_collector=self._sql_collector)


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

    # Карточка по id должна отдавать сделку в том же формате, что и список.
    def test_get_deal_success(self):
        script = [
            {
                "one": (
                    15,
                    "Услуга",
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
                    "cust-login",
                    "cust-pass",
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
                    False,
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
                res = client.get("/deals/15", headers=self._auth_headers(role="admin"))
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(body["deal_id"], 15)
            self.assertEqual(body["account_login"], "login1@gmail.com")
            self.assertEqual(body["product_id"], 21)
            self.assertEqual(body["order_number"], "ORD-1")

    # Успешная выдача сделок должна собирать account_login и total.
    def test_list_deals_success(self):
        script = [
            {"one": (1,)},  # total
            {
                "all": [
                    (
                        15,
                        "Услуга",
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
                        "cust-login",
                        "cust-pass",
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
                res = client.get("/deals?page=1&page_size=20", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(body["total"], 1)
            self.assertEqual(len(body["items"]), 1)
            self.assertEqual(body["items"][0]["deal_id"], 15)
            self.assertEqual(body["items"][0]["account_login"], "login1@gmail.com")
            self.assertEqual(body["items"][0]["login"], "cust-login")
            self.assertEqual(body["items"][0]["password"], "cust-pass")
            self.assertEqual(body["items"][0]["order_number"], "ORD-1")
            self.assertEqual(body["items"][0]["responsible_username"], "admin")
            self.assertEqual(body["items"][0]["is_refund"], True)

    # Для шеринга со сроком подписки API списка должен вернуть subscription_term_id.
    def test_list_deals_success_includes_subscription_term_id(self):
        script = [
            {"one": (1,)},  # total
            {
                "all": [
                    (
                        16,  # deal_id
                        "Шеринг",  # deal_type_name
                        "rental",  # deal_type_code
                        "Подтверждена",  # status_name
                        "completed",  # flow_status_code
                        "Завершен",  # flow_status_name
                        "ORD-2",  # order_number
                        "admin",  # responsible_username
                        "TR",  # region_code
                        8,  # account_id
                        "animal",  # login_name
                        "spsasa.com",  # domain_name
                        81,  # product_id
                        "EA PLAY",  # product_title
                        "EA",  # product_short_title
                        "ps5",  # platform_code
                        "Ruslan",  # customer_nickname
                        None,  # customer_login
                        None,  # customer_password
                        3,  # source_id
                        0.0,  # price
                        0.0,  # purchase_cost
                        datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc),  # purchase_at
                        datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc),  # created_at
                        datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc),  # completed_at
                        1,  # slots_used
                        "ps5_p3",  # slot_type_code
                        901,  # subscription_term_id
                        datetime(2026, 10, 28, 0, 0, tzinfo=timezone.utc),  # subscription_valid_until
                        None,  # reserve_key
                        "note",  # notes
                        None,  # product_link
                        False,  # is_refund
                        4,  # lock_version
                        None,  # messenger_id
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
            self.assertEqual(body["items"][0]["deal_id"], 16)
            self.assertEqual(body["items"][0]["subscription_term_id"], 901)
            self.assertEqual(body["items"][0]["subscription_valid_until"], "2026-10-28")

    # Для manager/operator возвратные сделки должны отсеиваться на уровне SQL.
    def test_list_deals_hides_refunds_for_manager(self):
        script = [
            {"one": (0,)},  # total
            {"all": []},  # rows
        ]
        sql_collector = []
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script, sql_collector=sql_collector)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get(
                    "/deals?page=1&page_size=20",
                    headers=self._auth_headers(role="manager", username="manager1"),
                )
            self.assertEqual(res.status_code, 200)
            self.assertTrue(any("di.returned_at IS NULL" in sql for sql in sql_collector))
            self.assertTrue(any("COALESCE(d.completed_at, di.purchase_at, d.created_at) >= %s" in sql for sql in sql_collector))

    # Для карточки аккаунта не режем completed по 24 часам: нужна полная история привязанных сделок.
    def test_list_deals_by_account_keeps_completed_history(self):
        script = [
            {"one": (0,)},  # total
            {"all": []},  # rows
        ]
        sql_collector = []
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script, sql_collector=sql_collector)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get(
                    "/deals?account_id=77&page=1&page_size=20",
                    headers=self._auth_headers(role="manager", username="manager1"),
                )
            self.assertEqual(res.status_code, 200)
            self.assertTrue(any("di.returned_at IS NULL" in sql for sql in sql_collector))
            self.assertFalse(any("COALESCE(d.completed_at, di.purchase_at, d.created_at) >= %s" in sql for sql in sql_collector))

    # Для admin/owner в общем списке не ограничиваем completed последними 24 часами.
    def test_list_deals_admin_keeps_completed_history_without_recent_limit(self):
        script = [
            {"one": (0,)},  # total
            {"all": []},  # rows
        ]
        sql_collector = []
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script, sql_collector=sql_collector)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get(
                    "/deals?page=1&page_size=20",
                    headers=self._auth_headers(role="admin", username="admin"),
                )
            self.assertEqual(res.status_code, 200)
            self.assertFalse(any("di.returned_at IS NULL" in sql for sql in sql_collector))
            self.assertFalse(any("COALESCE(d.completed_at, di.purchase_at, d.created_at) >= %s" in sql for sql in sql_collector))

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

    # Черновик продажи можно сохранить без обязательных полей.
    def test_create_deal_sale_draft_allows_empty_fields(self):
        script = [
            {"one": (1,)},  # flow_status lookup
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
                    json={"deal_type_code": "sale", "flow_status_code": "draft"},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"deal_id": 33})

    # Черновик шеринга можно сохранить без обязательных полей.
    def test_create_deal_rental_draft_allows_empty_fields(self):
        script = [
            {"one": (1,)},  # flow_status lookup
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
                    json={"deal_type_code": "rental", "flow_status_code": "draft"},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"deal_id": 33})

    # Успешная услуга должна вернуть deal_id.
    def test_create_deal_sale_success(self):
        script = [
            {"one": (1,)},  # ensure_messenger_exists
            {"one": (10,)},  # region_id by code
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
                        "messenger_id": 1,
                        "customer_nickname": "cust",
                        "price": 1000,
                        "purchase_cost": 400,
                    },
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"deal_id": 33})

    # Услуга по product_id должна работать для товара без доп. legacy-атрибутов.
    def test_create_deal_sale_with_product_only(self):
        script = [
            {"one": ("subscription", False)},  # product lookup
            {"one": (1,)},  # ensure_messenger_exists
            {"one": (10,)},  # region_id by code
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
                        "messenger_id": 1,
                        "product_id": 88,
                        "customer_nickname": "cust",
                        "price": 1000,
                        "purchase_cost": 400,
                    },
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"deal_id": 33})

    # Аренда по product_id должна работать для товара без доп. legacy-атрибутов.
    def test_create_deal_rental_with_product_only(self):
        script = [
            {"one": ("game", False)},  # product lookup
            {"one": (1,)},  # ensure_account_exists
            {"one": (1,)},  # ensure_messenger_exists
            {"one": ("ps5_p1", "ps5", "single", 1)},  # get_slot_type
            {"one": (2,)},  # get_platform_id
            {"one": (7,)},  # region from account
            {"one": (1,)},  # get_account_slot_free
            {"one": (33,)},  # deal insert
            {"one": (44,)},  # deal_item insert
            {"rowcount": 1},  # assignment insert
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
                        "product_id": 55,
                        "slot_type_code": "ps5_p1",
                        "messenger_id": 1,
                        "price": 500,
                    },
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"deal_id": 33})

    # Если фронт прислал занятый резерв, backend должен выбрать следующий свободный и сохранить сделку.
    def test_create_deal_rental_replaces_used_reserve(self):
        script = [
            {"one": ("game", False)},  # product lookup
            {"one": (1,)},  # ensure_account_exists
            {"one": (1,)},  # ensure_messenger_exists
            {"one": ("ps5_p1", "ps5", "single", 1)},  # get_slot_type
            {"one": (2,)},  # get_platform_id
            {"one": (7,)},  # region from account
            {"one": (22,)},  # customer insert
            {"one": (1,)},  # get_account_slot_free
            {"all": [("reserve1",)]},  # reserve1 already used
            {"all": [("reserve1", "cjE="), ("reserve2", "cjI=")]},  # account reserves
            {"all": [("reserve1",)]},  # used reserves for fallback selection
            {"one": (33,)},  # deal insert
            {"one": (44,)},  # deal_item insert with reserve2
            {"rowcount": 1},  # assignment insert
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
                        "product_id": 55,
                        "slot_type_code": "ps5_p1",
                        "messenger_id": 1,
                        "customer_nickname": "cust",
                        "reserve_key": "reserve1",
                        "price": 500,
                    },
                )

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"deal_id": 33})

    # Аренда по product_id должна поддерживать подписку как товар.
    def test_create_deal_rental_with_subscription_product(self):
        script = [
            {"one": ("subscription", False)},  # product lookup
            {"one": (1,)},  # ensure_account_exists
            {"one": (1,)},  # ensure_messenger_exists
            {"one": ("ps5_p1", "ps5", "single", 1)},  # get_slot_type
            {"one": (2,)},  # get_platform_id
            {"one": (7,)},  # region from account
            {"one": (1,)},  # get_account_slot_free
            {"one": (33,)},  # deal insert
            {"one": (44,)},  # deal_item insert
            {"rowcount": 1},  # assignment insert
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
                        "product_id": 55,
                        "slot_type_code": "ps5_p1",
                        "messenger_id": 1,
                        "price": 500,
                    },
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"deal_id": 33})

    # Для принудительного дубля слот снимаем только в момент сохранения сделки.
    def test_create_deal_rental_releases_duplicate_assignment_on_save(self):
        script = [
            {"one": ("game", False)},  # product lookup
            {"one": (1,)},  # ensure_account_exists
            {"one": (1,)},  # ensure_messenger_exists
            {"one": ("ps5_p1", "ps5", "single", 1)},  # get_slot_type
            {"one": (2,)},  # get_platform_id
            {"one": (7,)},  # region from account
            {"one": (9001, 7, "ps5_p1", 55, None, 501, None)},  # duplicate assignment validation
            {"one": (0,)},  # get_account_slot_free
            {"one": (33,)},  # deal insert
            {"one": (44,)},  # deal_item insert
            {"rowcount": 1},  # assignment insert
            {"rowcount": 1},  # duplicate assignment release
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
                        "product_id": 55,
                        "slot_type_code": "ps5_p1",
                        "messenger_id": 1,
                        "duplicate_assignment_id": 9001,
                        "price": 500,
                    },
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"deal_id": 33})

    # Для подписки по сроку 409 возвращаем при отсутствии свободного места в выбранном slot_type.
    def test_create_deal_rental_with_full_subscription_term_slot(self):
        script = [
            {"one": ("subscription", False)},  # product lookup
            {"one": (1,)},  # ensure_account_exists
            {"one": (1,)},  # ensure_messenger_exists
            {"one": ("ps5_p1", "ps5", "single", 1)},  # get_slot_type
            {"one": (2,)},  # get_platform_id
            {"one": (7,)},  # region from account
            {"one": (55, 7, False)},  # subscription term lookup
            {"one": ("play", 1)},  # target slot type for term capacity
            {"one": (1,)},  # occupied count for selected slot_type
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
                        "product_id": 55,
                        "slot_type_code": "ps5_p1",
                        "messenger_id": 1,
                        "subscription_term_id": 901,
                        "price": 500,
                    },
                )
            self.assertEqual(res.status_code, 409)

    # При создании сделки логин/пароль клиента должны сохраняться в новой записи покупателя.
    def test_create_deal_updates_customer_credentials_for_existing_customer(self):
        script = [
            {"one": (1,)},  # ensure_messenger_exists
            {"one": (10,)},  # region_id by code
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
                        "messenger_id": 1,
                        "customer_nickname": "cust",
                        "price": 1000,
                        "login": "cust-login",
                        "password": "cust-pass",
                    },
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"deal_id": 33})

    # Для аренды при нехватке слотов должен возвращаться 409.
    def test_create_deal_rental_not_enough_slots(self):
        script = [
            {"one": ("game", False)},  # product lookup
            {"one": (1,)},  # ensure_account_exists
            {"one": (1,)},  # ensure_messenger_exists
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
                        "product_id": 55,
                        "slot_type_code": "ps5_p1",
                        "messenger_id": 1,
                        "customer_nickname": "cust",
                        "price": 500,
                    },
                )
            self.assertEqual(res.status_code, 409)

    # Для market-источника номер заказа должен быть уникален в связке source+order+product.
    def test_create_deal_market_source_order_number_must_be_unique(self):
        script = [
            {"one": ("game", False)},  # product lookup
            {"one": (1,)},  # ensure_source_exists
            {"one": (1,)},  # ensure_messenger_exists
            {"one": (10,)},  # region_id by code
            {"one": (22,)},  # customer insert
            {"one": (5,)},  # customer source_id
            {"one": ("ym",)},  # source code
            {"one": (99,)},  # conflicting deal
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
                        "messenger_id": 1,
                        "source_id": 5,
                        "product_id": 55,
                        "order_number": "A-100",
                        "price": 1000,
                    },
                )
            self.assertEqual(res.status_code, 409)

    # Для market-источника одинаковый номер заказа допустим, если игра другая.
    def test_create_deal_market_source_order_number_allows_other_product(self):
        script = [
            {"one": ("game", False)},  # product lookup
            {"one": (1,)},  # ensure_source_exists
            {"one": (1,)},  # ensure_messenger_exists
            {"one": (10,)},  # region_id by code
            {"one": (22,)},  # customer insert
            {"one": (5,)},  # customer source_id
            {"one": ("ym",)},  # source code
            {"one": None},  # no conflict for source+order+other product
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
                        "messenger_id": 1,
                        "source_id": 5,
                        "product_id": 56,
                        "order_number": "A-100",
                        "price": 1000,
                    },
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"deal_id": 33})

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
                        "product_id": 55,
                        "customer_nickname": "cust",
                        "price": 500,
                    },
                )
            self.assertEqual(res.status_code, 400)

    # Успешный rental должен создать сделку и вернуть обновленные слоты.
    def test_create_rental_success(self):
        script = [
            {"one": ("game", False)},  # product lookup
            {"one": (7,)},  # SELECT region_id FROM accounts (проверка существования + region_id)
            {"one": ("ps5_p1", "ps5", "single", 1)},  # get_slot_type
            {"one": (2,)},  # get_platform_id
            {"one": (5, None)},  # customer exists
            {"one": (1,)},  # get_account_slot_free
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
                        "product_id": 55,
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
            {"one": ("game", False)},  # product lookup
            {"one": (1,)},  # ensure_account_exists
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
                        "product_id": 55,
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
            500.0,
            100.0,
            datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc),
            None,
            None,
            0,
            None,
            "note",
            None,
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
            500.0,
            100.0,
            datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc),
            None,
            None,
            0,
            None,
            "note",
            None,
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

    # В update сделки логин/пароль клиента должны сохраняться в app.customers.
    def test_update_deal_updates_customer_credentials(self):
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
            500.0,
            100.0,
            datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc),
            None,
            None,
            0,
            None,
            "note",
            None,
            None,
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # current deal row
            {"one": (1,)},  # ensure_messenger_exists
            {"rowcount": 1},  # update deals
            {"rowcount": 1},  # update deal_items
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
                    json={"messenger_id": 1, "login": "new-login", "password": "new-pass"},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})

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
            None,
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # current deal row
            {"one": (55,)},  # current product_id from deal_item
            {"one": (1,)},  # ensure_messenger_exists
            {"rowcount": 1},  # update deals
            {"rowcount": 1},  # update deal_items
            {"one": (900, 7, "ps5_p1", 5, 55)},  # assignment details
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
                    json={"deal_type_code": "rental", "slot_type_code": "ps5_p1", "account_id": 7, "product_id": 55, "messenger_id": 1},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})

    # При смене покупателя в rental не снимаем слот, а обновляем customer_id текущего назначения.
    def test_update_deal_rental_customer_rename_does_not_release_slot(self):
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
            None,
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # current deal row
            {"one": (55,)},  # current product_id from deal_item
            {"one": (1,)},  # ensure_messenger_exists
            {"one": (9, None)},  # ensure_customer -> existing customer_id
            {"rowcount": 1},  # update deals
            {"rowcount": 1},  # update deal_items
            {"one": (900, 7, "ps5_p1", 5, 55)},  # assignment details
            {"rowcount": 1},  # update assignment customer_id
        ]
        sql_collector = []
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script, sql_collector=sql_collector)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put(
                    "/deals/77",
                    headers=self._auth_headers(role="manager"),
                    json={"customer_nickname": "new-customer", "messenger_id": 1},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})
            self.assertFalse(any("SET released_at=now()" in sql for sql in sql_collector))
            self.assertTrue(any("SET customer_id=%s" in sql for sql in sql_collector))

    # Для update rental подписки отсутствие свободного места по сроку блокирует сохранение.
    def test_update_deal_rental_with_full_subscription_term_slot(self):
        current_row = (
            "rental",
            "confirmed",
            "pending",
            3,  # lock_version
            10,  # region_id
            5,  # customer_id
            500.0,  # total_amount
            "A-100",  # order_number
            "admin",  # responsible_username
            1,  # messenger_id
            77,  # deal_item_id
            7,  # account_id
            2,  # platform_id
            500.0,  # price
            100.0,  # purchase_cost
            datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc),  # purchase_at
            None,  # start_at
            None,  # end_at
            1,  # slots_used
            "ps5_p1",  # slot_type_code
            None,  # subscription_term_id
            None,  # reserve_key
            "note",  # notes
            None,  # game_link
            None,  # returned_at
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # current deal row
            {"one": (55,)},  # current product_id from deal_item
            {"one": (1,)},  # ensure_messenger_exists
            {"one": (55, 7, False)},  # subscription term lookup
            {"rowcount": 1},  # update deals
            {"rowcount": 1},  # update deal_items
            {"one": (900, 7, "ps5_p1", 5, 55, 777)},  # active assignment details
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
                    json={"subscription_term_id": 901},
                )
            self.assertEqual(res.status_code, 409)

    # При смене только ответственного у rental не проверяем емкость слотов повторно.
    def test_update_deal_rental_responsible_only_skips_slot_capacity_check(self):
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
            None,
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # current deal row
            {"one": (55,)},  # current product_id from deal_item
            {"one": (1,)},  # ensure_messenger_exists
            {"rowcount": 1},  # update deals
            {"rowcount": 1},  # update deal_items
            {"one": (900, 7, "ps5_p1", 5, 55)},  # assignment details
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
                    json={"responsible_username": "other_manager", "messenger_id": 1},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})

    # В update номер заказа тоже должен быть уникальным для market-источника в связке source+order+product.
    def test_update_deal_market_source_order_number_must_be_unique(self):
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
            500.0,
            100.0,
            datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc),
            None,
            None,
            0,
            None,
            "note",
            None,
            None,
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # current deal row
            {"one": (1,)},  # ensure_messenger_exists
            {"one": ("game", False)},  # product lookup
            {"one": (55,)},  # current deal_item product_id
            {"one": (5,)},  # customer source_id
            {"one": ("ym",)},  # source code
            {"one": (88,)},  # conflicting deal
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
                    json={"order_number": "a-100", "messenger_id": 1, "product_id": 55},
                )
            self.assertEqual(res.status_code, 409)

    # В update одинаковый номер market-заказа допустим при смене игры.
    def test_update_deal_market_source_order_number_allows_other_product(self):
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
            500.0,
            100.0,
            datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc),
            None,
            None,
            0,
            None,
            "note",
            None,
            None,
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # current deal row
            {"one": (1,)},  # ensure_messenger_exists
            {"one": ("game", False)},  # product lookup
            {"one": (55,)},  # current deal_item product_id
            {"one": (5,)},  # customer source_id
            {"one": ("ym",)},  # source code
            {"one": None},  # no conflict for source+order+other product
            {"rowcount": 1},  # update deals
            {"rowcount": 1},  # update deal_items
            {"one": None},  # no active assignment for sale
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
                    json={"order_number": "a-100", "messenger_id": 1, "product_id": 56},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})

    # Завершение возврата должно быть доступно только admin/owner.
    def test_update_deal_refund_completion_forbidden_for_manager(self):
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
            500.0,
            100.0,
            datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc),
            None,
            None,
            0,
            None,
            "note",
            None,
            datetime(2026, 2, 1, 13, 0, tzinfo=timezone.utc),
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # current deal row
            {"one": (1,)},  # flow_status lookup
            {"one": (1,)},  # ensure_messenger_exists
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
                    json={"flow_status_code": "completed", "messenger_id": 1},
                )
            self.assertEqual(res.status_code, 403)
            self.assertIn("не достаточно прав для проведения возврата", res.text)

    # Повторное сохранение возвратного шеринга не должно занимать слот обратно.
    def test_update_refunded_rental_completion_does_not_recreate_slot_assignment(self):
        current_row = (
            "rental",
            "confirmed",
            "pending",
            3,  # lock_version
            10,  # region_id
            5,  # customer_id
            500.0,  # total_amount
            "A-100",  # order_number
            "manager-name",  # responsible_username
            1,  # messenger_id
            77,  # deal_item_id
            2793,  # account_id
            2,  # platform_id
            500.0,  # price
            100.0,  # purchase_cost
            datetime(2026, 6, 1, 13, 51, tzinfo=timezone.utc),  # purchase_at
            None,  # start_at
            None,  # end_at
            1,  # slots_used
            "play_ps5",  # slot_type_code
            None,  # subscription_term_id
            "reserve4",  # reserve_key
            "note",  # notes
            None,  # game_link
            datetime(2026, 6, 1, 16, 54, tzinfo=timezone.utc),  # returned_at
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # current deal row
            {"one": (41,)},  # current product_id from deal_item
            {"one": (1,)},  # flow_status lookup
            {"one": (1,)},  # ensure_messenger_exists
            {"one": ("Owner Name", "owner_user")},  # owner name + username
            {"rowcount": 1},  # update deals
            {"rowcount": 1},  # update deal_items
        ]
        sql_collector = []
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script, sql_collector=sql_collector)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put(
                    "/deals/77",
                    headers=self._auth_headers(role="admin", username="admin"),
                    json={"flow_status_code": "completed", "messenger_id": 1, "lock_version": 3},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})
            self.assertFalse(any("INSERT INTO app.account_slot_assignments" in sql for sql in sql_collector))

    # Для completed сделки менеджеру запрещаем любое редактирование.
    def test_update_deal_refund_flag_can_be_changed_only_for_pending(self):
        current_row = (
            "sale",
            "confirmed",
            "completed",
            10,
            5,
            500.0,
            "A-100",
            "admin",
            77,
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
            None,
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # current deal row
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
                    headers=self._auth_headers(role="manager", username="manager1"),
                    json={"is_refund": True},
                )
            self.assertEqual(res.status_code, 403)

    # Для completed сделки admin/owner могут менять признак возврата.
    def test_update_deal_refund_flag_can_be_changed_in_completed_for_admin(self):
        current_row = (
            "sale",
            "confirmed",
            "completed",
            10,
            5,
            500.0,
            "A-100",
            "manager-name",
            77,
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
            None,
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # current deal row
            {"one": (1,)},  # ensure_messenger_exists
            {"one": ("Owner Name", "owner_user")},  # owner name + username
            {"rowcount": 1},  # update deals
            {"rowcount": 1},  # update deal_items
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
                    headers=self._auth_headers(role="admin", username="admin"),
                    json={"is_refund": True, "messenger_id": 1},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})

    # Для completed сделки admin/owner могут вручную править даты создания и завершения.
    def test_update_deal_completed_allows_manual_system_dates_for_admin(self):
        current_row = (
            "sale",
            "confirmed",
            "completed",
            10,
            5,
            500.0,
            "A-100",
            "manager-name",
            77,
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
            None,
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # current deal row
            {"one": (1,)},  # ensure_messenger_exists
            {"rowcount": 1},  # update deals
            {"rowcount": 1},  # update deal_items
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
                    headers=self._auth_headers(role="admin", username="admin"),
                    json={
                        "messenger_id": 1,
                        "created_at": "2026-02-01T10:30:00Z",
                        "completed_at": "2026-02-01T11:30:00Z",
                    },
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})

    # Для pending сделки admin/owner тоже могут вручную править системные даты.
    def test_update_deal_pending_allows_manual_system_dates_for_admin(self):
        current_row = (
            "sale",
            "confirmed",
            "pending",
            10,
            5,
            500.0,
            "A-100",
            "manager-name",
            77,
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
            None,
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # current deal row
            {"one": (1,)},  # ensure_messenger_exists
            {"rowcount": 1},  # update deals
            {"rowcount": 1},  # update deal_items
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
                    headers=self._auth_headers(role="admin", username="admin"),
                    json={
                        "messenger_id": 1,
                        "created_at": "2026-02-01T10:30:00Z",
                        "completed_at": "2026-02-01T11:30:00Z",
                    },
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})

    # Даже для admin/owner completed_at не должен быть раньше created_at при ручной правке.
    def test_update_deal_rejects_manual_system_dates_inverted_range(self):
        current_row = (
            "sale",
            "confirmed",
            "pending",
            10,
            5,
            500.0,
            "A-100",
            "manager-name",
            77,
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
            None,
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # current deal row
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
                    headers=self._auth_headers(role="admin", username="admin"),
                    json={
                        "created_at": "2026-02-01T12:30:00Z",
                        "completed_at": "2026-02-01T11:30:00Z",
                    },
                )
            self.assertEqual(res.status_code, 400)
            self.assertIn("completed_at must be >= created_at", str(res.json().get("detail", "")))

    # При установке признака возврата у продажи ответственный должен переключаться на owner.
    def test_update_deal_sale_refund_assigns_owner_responsible(self):
        current_row = (
            "sale",
            "confirmed",
            "pending",
            10,
            5,
            500.0,
            "A-100",
            "manager-name",
            77,
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
            None,
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # current deal row
            {"one": (1,)},  # ensure_messenger_exists
            {"one": ("Owner Name", "owner_user")},  # owner name + username
            {"rowcount": 1},  # update deals
            {"rowcount": 1},  # update deal_items
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
                    headers=self._auth_headers(role="manager", username="manager1"),
                    json={"is_refund": True, "messenger_id": 1},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})

    # Для completed сделки менеджеру запрещаем перевод через общий update.
    def test_update_deal_completed_to_pending_forbidden_for_manager(self):
        current_row = (
            "sale",
            "confirmed",
            "completed",
            10,
            5,
            500.0,
            "A-100",
            "admin",
            77,
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
            None,
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # current deal row
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
                    headers=self._auth_headers(role="manager", username="manager1"),
                    json={"flow_status_code": "pending", "is_refund": False},
                )
            self.assertEqual(res.status_code, 403)

    # Для продажи перевод из draft в pending без региона запрещаем.
    def test_update_deal_sale_draft_to_pending_requires_region(self):
        current_row = (
            "sale",
            "confirmed",
            "draft",
            None,
            None,
            0.0,
            None,
            "admin",
            77,
            None,
            None,
            0.0,
            0.0,
            None,
            None,
            None,
            0,
            None,
            None,
            None,
            None,
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # current deal row
            {"one": (1,)},  # flow_status lookup
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
                    json={"flow_status_code": "pending"},
                )
            self.assertEqual(res.status_code, 400)

    # Черновик в update разрешаем и для шеринга.
    def test_update_deal_rental_draft_is_allowed(self):
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
            None,
        )
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": current_row},  # current deal row
            {"one": (55,)},  # current product_id from deal_item
            {"one": (1,)},  # flow_status lookup
            {"rowcount": 1},  # update deals
            {"rowcount": 1},  # update deal_items
            {"rowcount": 1},  # release slot assignment
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
                    json={"flow_status_code": "draft"},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})

    # Возврат из completed в pending должен быть доступен любой роли.
    def test_return_completed_sale_to_pending_success(self):
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": ("sale", "completed", None)},  # deal state
            {"one": ("Owner Name", "owner_user")},  # owner name + username
            {"rowcount": 1},  # update deals
            {"rowcount": 1},  # update deal_items
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post("/deals/77/return", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})

    # Возврат завершенного шеринга в pending также должен работать.
    def test_return_completed_rental_to_pending_success(self):
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": ("rental", "completed", None)},  # deal state
            {"one": ("Owner Name", "owner_user")},  # owner name + username
            {"rowcount": 1},  # update deals
            {"rowcount": 1},  # update deal_items
            {"rowcount": 1},  # release slot assignments
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post("/deals/77/return", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})

    # Повторный возврат не разрешаем, если признак уже выставлен.
    def test_return_completed_sale_to_pending_forbidden_for_already_refund(self):
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": ("sale", "completed", datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc))},  # deal state
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post("/deals/77/return", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 400)

    # Возврат разрешаем только для завершенных сделок.
    def test_return_completed_sale_to_pending_requires_completed(self):
        script = [
            {"rowcount": 1},  # set_config('app.user', ...)
            {"one": ("sale", "pending", None)},  # deal state
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post("/deals/77/return", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 400)

    # Удалять сделку можно только в статусе черновик.
    def test_delete_deal_forbidden_for_non_draft(self):
        script = [
            {"one": ("pending",)},  # current flow_status
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.delete("/deals/77", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 400)

    # Черновик удаляется мягко: меняем status_code на cancelled.
    def test_delete_deal_draft_soft_delete_success(self):
        script = [
            {"one": ("draft",)},  # current flow_status
            {"rowcount": 1},  # update deals status_code=cancelled
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.delete("/deals/77", headers=self._auth_headers(role="manager"))
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"ok": True})


if __name__ == "__main__":
    unittest.main()
