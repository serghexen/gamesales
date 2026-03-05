import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

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

    def executemany(self, sql, seq_of_params):
        if not self._script:
            self._current = None
            self.rowcount = len(list(seq_of_params or []))
            return
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

    # В списке аккаунтов поле товаров должно заполняться и для подписок.
    def test_list_accounts_includes_subscription_products(self):
        script = [
            {
                "all": [
                    (
                        8,
                        "RU",
                        "active",
                        "sub1",
                        "gmail.com",
                        "2024-01-10",
                        "notes",
                        ["PS Plus"],
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
            self.assertEqual(body["items"][0]["product_titles"], ["PS Plus"])

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

    # При создании аккаунта базовые поля карточки должны быть обязательны.
    def test_create_account_requires_region_and_date(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/accounts",
                    headers=self._auth_headers(role="manager"),
                    json={
                        "login_name": "acc1",
                        "domain_code": "gmail.com",
                    },
                )
            self.assertEqual(res.status_code, 400)
            self.assertIn("region_code", str(res.json().get("detail", "")))
            self.assertIn("account_date", str(res.json().get("detail", "")))

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

    # Обновление аккаунта доступно менеджеру.
    def test_update_account_allowed_for_manager(self):
        script = [
            {"one": ("login1", 3, 2, "active", "2024-01-10", "old")},  # current
            {"rowcount": 1},  # update
            {"one": (5, "RU", "active", "login1", "gmail.com", "2024-01-10", "x")},  # result row
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
                res = client.put("/accounts/5", headers=self._auth_headers(role="manager"), json={"notes": "x"})
            self.assertEqual(res.status_code, 200)

    # Менеджер не может менять статус аккаунта.
    def test_update_account_forbidden_status_change_for_manager(self):
        script = [
            {"one": ("login1", 3, 2, "active", "2024-01-10", "old")},  # current
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put("/accounts/5", headers=self._auth_headers(role="manager"), json={"status_code": "archived"})
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

    # Деактивация должна выставлять флаг и даты в карточке аккаунта.
    def test_update_account_deactivation_success(self):
        script = [
            {"one": ("login1", 3, 2, "active", "2024-01-10", "old", False, None, None)},  # current
            {"rowcount": 1},  # update
            {
                "one": (
                    5,
                    "RU",
                    "active",
                    "login1",
                    "gmail.com",
                    "2024-01-10",
                    "updated",
                    True,
                    "2026-03-04T10:00:00Z",
                    "2026-09-03T10:00:00Z",
                )
            },  # result row
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
                res = client.put(
                    "/accounts/5",
                    headers=self._auth_headers(role="manager"),
                    json={"notes": "updated", "is_deactivated": True},
                )
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(body["is_deactivated"], True)
            self.assertEqual(body["deactivated_at"], "2026-03-04T10:00:00Z")
            self.assertEqual(body["next_activation_at"], "2026-09-03T10:00:00Z")

    # Повторная активация разрешена сразу: деактивация — только визуальная пометка.
    def test_update_account_reactivate_before_timer_is_allowed(self):
        future_date = datetime.now(timezone.utc) + timedelta(days=10)
        script = [
            {"one": ("login1", 3, 2, "active", "2024-01-10", "old", True, "2026-03-01T00:00:00Z", future_date)},
            {"rowcount": 1},
            {"one": (5, "RU", "active", "login1", "gmail.com", "2024-01-10", "old", False, None, None)},
            {"all": []},
            {"all": []},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put(
                    "/accounts/5",
                    headers=self._auth_headers(role="manager"),
                    json={"is_deactivated": False},
                )
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(body["is_deactivated"], False)
            self.assertEqual(body["deactivated_at"], None)
            self.assertEqual(body["next_activation_at"], None)

    # Оператору запрещено менять флаг деактивации аккаунта.
    def test_update_account_operator_cannot_change_deactivation_flag(self):
        script = [
            {"one": ("login1", 3, 2, "active", "2024-01-10", "old", False, None, None)},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put(
                    "/accounts/5",
                    headers=self._auth_headers(role="operator"),
                    json={"is_deactivated": True},
                )
            self.assertEqual(res.status_code, 403)
            self.assertIn("deactivation", str(res.json().get("detail", "")).lower())

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

    # Менеджеру разрешено управлять секретами аккаунта.
    def test_upsert_account_secret_allowed_for_manager(self):
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
                    headers=self._auth_headers(role="manager"),
                    json={"secret_key": "pwd", "secret_value": "secret"},
                )
            self.assertEqual(res.status_code, 200)

    # Проверяем новый безопасный сценарий: доступность слотов по product_id.
    def test_slot_availability_for_deal_supports_product_id(self):
        script = [
            {"one": ("game", False)},
            {"all": [("ps5_p1", True), ("ps5_p2", False)]},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get(
                    "/accounts/for-deal/availability?product_id=55",
                    headers=self._auth_headers(role="manager"),
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(res.json()), 2)
            self.assertEqual(res.json()[0]["slot_type_code"], "ps5_p1")

    # Product-first: доступность слотов должна работать для товара по product_id.
    def test_slot_availability_for_deal_supports_product_only(self):
        script = [
            {"one": ("game", False)},
            {"all": [("ps5_p1", True)]},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get(
                    "/accounts/for-deal/availability?product_id=55",
                    headers=self._auth_headers(role="manager"),
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(res.json()), 1)
            self.assertEqual(res.json()[0]["slot_type_code"], "ps5_p1")

    # Список аккаунтов для шеринга должен поддерживать выбор по product_id.
    def test_list_accounts_for_deal_supports_product_id(self):
        script = [
            {"one": ("game", False)},
            {
                "all": [
                    (
                        7,
                        "RU",
                        "active",
                        "acc1",
                        "gmail.com",
                        "2024-01-10",
                        "notes",
                        ["ps5"],
                        "ps5",
                        2,
                        1,
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
                res = client.get(
                    "/accounts/for-deal?product_id=55&slot_type_code=ps5_p1",
                    headers=self._auth_headers(role="manager"),
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(res.json()), 1)
            self.assertEqual(res.json()[0]["account_id"], 7)

    # Product-first: список аккаунтов для шеринга должен работать по product_id.
    def test_list_accounts_for_deal_supports_product_only(self):
        script = [
            {"one": ("game", False)},
            {
                "all": [
                    (
                        7,
                        "RU",
                        "active",
                        "acc1",
                        "gmail.com",
                        "2024-01-10",
                        "notes",
                        ["ps5"],
                        "ps5",
                        2,
                        1,
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
                res = client.get(
                    "/accounts/for-deal?product_id=55&slot_type_code=ps5_p1",
                    headers=self._auth_headers(role="manager"),
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(res.json()), 1)
            self.assertEqual(res.json()[0]["account_id"], 7)

    # Для подписки список аккаунтов для шеринга тоже должен возвращаться.
    def test_list_accounts_for_deal_supports_subscription_product(self):
        script = [
            {"one": ("subscription", False)},
            {
                "all": [
                    (
                        9,
                        "RU",
                        "active",
                        "subacc",
                        "gmail.com",
                        "2024-02-01",
                        "notes",
                        ["ps5"],
                        "ps5",
                        2,
                        0,
                        2,
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
                    "/accounts/for-deal?product_id=88&slot_type_code=ps5_p1",
                    headers=self._auth_headers(role="manager"),
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(res.json()), 1)
            self.assertEqual(res.json()[0]["account_id"], 9)

    # Для подписки endpoint доступности слотов тоже должен работать.
    def test_slot_availability_for_deal_supports_subscription_product(self):
        script = [
            {"one": ("subscription", False)},
            {"all": [("ps5_p1", True)]},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get(
                    "/accounts/for-deal/availability?product_id=88",
                    headers=self._auth_headers(role="manager"),
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()[0]["slot_type_code"], "ps5_p1")

    # Новый endpoint по товару должен возвращать назначения слотов с product-полями.
    def test_list_product_slot_assignments_success(self):
        script = [
            {"one": (21,)},
            {
                "all": [
                    (
                        10,
                        7,
                        "acc1",
                        "gmail.com",
                        "ps5_p1",
                        20,
                        "cust",
                        55,
                        "Product A",
                        1001,
                        2002,
                        "2026-02-12T10:00:00Z",
                        None,
                        "admin",
                        None,
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
                    "/products/55/slot-assignments",
                    headers=self._auth_headers(role="manager"),
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(res.json()), 1)
            self.assertEqual(res.json()[0]["product_id"], 55)
            self.assertEqual(res.json()[0]["product_title"], "Product A")

    # Product endpoint больше не включает legacy назначения без product_id.
    def test_list_product_slot_assignments_ignores_legacy_without_product_id(self):
        script = [
            {"one": (1,)},
            {"all": []},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get(
                    "/products/55/slot-assignments",
                    headers=self._auth_headers(role="manager"),
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), [])

    # Product endpoint больше не включает legacy сделки без product_id.
    def test_list_product_accounts_ignores_legacy_without_product_id(self):
        script = [
            {"one": (1,)},
            {"all": []},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get(
                    "/products/55/accounts",
                    headers=self._auth_headers(role="manager"),
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), [])

    # Для подписки endpoint доступных аккаунтов должен возвращать "свободные" аккаунты.
    def test_list_accounts_available_for_subscription_returns_free_accounts(self):
        script = [
            {"all": [(6, "hex", "test.com")]},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get(
                    "/accounts/available-for-product?type_code=subscription",
                    headers=self._auth_headers(role="manager"),
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(res.json()), 1)
            self.assertEqual(res.json()[0]["account_id"], 6)
            self.assertEqual(res.json()[0]["login_full"], "hex@test.com")

    # В редактировании подписки endpoint должен сохранять в списке текущую привязку товара.
    def test_list_accounts_available_for_subscription_edit_keeps_current_binding(self):
        script = [
            {"all": [(6, "hex", "test.com")]},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get(
                    "/accounts/available-for-product?type_code=subscription&product_id=77",
                    headers=self._auth_headers(role="manager"),
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(res.json()), 1)
            self.assertEqual(res.json()[0]["account_id"], 6)

    # Новый endpoint должен отдавать товары аккаунта в product-формате.
    def test_list_account_products_success(self):
        script = [
            {"one": (1,)},
            {"all": [(55, "game", "Game A", "GA", "RU", ["ps5"])]},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get(
                    "/accounts/7/products",
                    headers=self._auth_headers(role="manager"),
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(res.json()), 1)
            self.assertEqual(res.json()[0]["product_id"], 55)
            self.assertEqual(res.json()[0]["platform_codes"], ["ps5"])

    # Endpoint товаров аккаунта должен возвращать подписки так же, как игры.
    def test_list_account_products_includes_subscription(self):
        script = [
            {"one": (1,)},
            {"all": [(88, "subscription", "PS Plus", "PS+", "RU", ["ps5"])]},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get(
                    "/accounts/7/products",
                    headers=self._auth_headers(role="manager"),
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(res.json()), 1)
            self.assertEqual(res.json()[0]["product_id"], 88)
            self.assertEqual(res.json()[0]["type_code"], "subscription")

    # Назначения слотов аккаунта должны отдавать product-поля.
    def test_list_account_slot_assignments_includes_product_fields(self):
        script = [
            {"one": (1,)},
            {
                "all": [
                    (
                        10,
                        7,
                        "acc1",
                        "gmail.com",
                        "ps5_p1",
                        20,
                        "cust",
                        55,
                        "Product A",
                        1001,
                        2002,
                        "2026-02-12T10:00:00Z",
                        None,
                        "admin",
                        None,
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
                    "/accounts/7/slot-assignments",
                    headers=self._auth_headers(role="manager"),
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(res.json()), 1)
            self.assertEqual(res.json()[0]["product_id"], 55)
            self.assertEqual(res.json()[0]["product_title"], "Product A")

    # Account endpoint больше не включает legacy назначения без product_id.
    def test_list_account_slot_assignments_ignores_legacy_without_product_id(self):
        script = [
            {"one": (1,)},
            {"all": []},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get(
                    "/accounts/7/slot-assignments",
                    headers=self._auth_headers(role="manager"),
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), [])

    # Обновление привязок товаров должно поддерживать product_ids.
    def test_set_account_products_success(self):
        script = [
            {"one": (1,)},
            {"all": [(55, "game", False)]},
            {"rowcount": 1},
            {"rowcount": 1},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put(
                    "/accounts/7/products",
                    headers=self._auth_headers(role="admin"),
                    json={"product_ids": [55]},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["ok"], True)

    # Менеджеру также разрешено обновлять привязки товаров аккаунта.
    def test_set_account_products_allowed_for_manager(self):
        script = [
            {"one": (1,)},
            {"all": [(55, "game", False)]},
            {"rowcount": 1},
            {"rowcount": 1},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put(
                    "/accounts/7/products",
                    headers=self._auth_headers(role="manager"),
                    json={"product_ids": [55]},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["ok"], True)

    # Product-first: привязка товара к аккаунту должна работать по product_id.
    def test_set_account_products_supports_product_only(self):
        script = [
            {"one": (1,)},
            {"all": [(55, "game", False)]},
            {"rowcount": 1},
            {"rowcount": 1},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put(
                    "/accounts/7/products",
                    headers=self._auth_headers(role="admin"),
                    json={"product_ids": [55]},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["ok"], True)

    # Привязка товаров аккаунта должна принимать подписки как обычный товар.
    def test_set_account_products_supports_subscription_type(self):
        script = [
            {"one": (1,)},
            {"all": [(88, "subscription", False)]},
            {"rowcount": 1},
            {"rowcount": 1},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put(
                    "/accounts/7/products",
                    headers=self._auth_headers(role="admin"),
                    json={"product_ids": [88]},
                )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["ok"], True)

    # Legacy game_ids больше не поддерживаются в обновлении товаров аккаунта.
    def test_set_account_products_rejects_legacy_game_ids(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put(
                    "/accounts/7/products",
                    headers=self._auth_headers(role="admin"),
                    json={"game_ids": [21]},
                )
            self.assertEqual(res.status_code, 422)

    # Даже при наличии product_ids legacy game_ids должны отклоняться явно.
    def test_set_account_products_rejects_mixed_product_and_legacy_ids(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put(
                    "/accounts/7/products",
                    headers=self._auth_headers(role="admin"),
                    json={"product_ids": [55], "game_ids": [21]},
                )
            self.assertEqual(res.status_code, 422)


if __name__ == "__main__":
    unittest.main()
