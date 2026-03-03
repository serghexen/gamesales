import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

import app as app_module


@unittest.skipIf(TestClient is None, "fastapi.testclient requires httpx")
class NsGiftEndpointsTests(unittest.TestCase):
    def _client(self):
        return TestClient(app_module.app)

    def _auth_headers(self, role="manager", username="manager", user_id=2):
        token = app_module.create_access_token(user_id, username, role)
        return {"Authorization": f"Bearer {token}"}

    # Проверяем, что endpoint баланса требует авторизацию.
    def test_balance_requires_auth(self):
        with patch.object(app_module, "ensure_analytics_schema", return_value=None):
            with self._client() as client:
                res = client.get("/integrations/ns-gift/balance")
            self.assertEqual(res.status_code, 401)

    # Баланс должен пробрасываться в нормализованном виде.
    def test_balance_success(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.ns_gift_service, "get_balance", return_value={"balance": 1234.56, "currency": "rub"}),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/integrations/ns-gift/balance", headers=self._auth_headers())
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), {"balance": 1234.56, "currency": "RUB"})

    # Каталог должен возвращать total и нормализованные элементы.
    def test_services_success(self):
        services = [
            {
                "service_id": 10,
                "title": "Steam Gift",
                "category": "steam",
                "price": 500.0,
                "currency": "RUB",
                "min_quantity": 1.0,
                "max_quantity": 10.0,
                "raw": {"service_id": 10},
            }
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.ns_gift_service, "get_services", return_value=services),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/integrations/ns-gift/services", headers=self._auth_headers())
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["total"], 1)
            self.assertEqual(res.json()["items"][0]["service_id"], 10)

    # Категории должны возвращаться как список строк.
    def test_categories_success(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.ns_gift_service, "get_categories", return_value=[{"category_id": 2, "name": "Steam"}, {"category_id": 3, "name": "PSN"}]),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/integrations/ns-gift/categories", headers=self._auth_headers())
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), [{"category_id": 2, "name": "Steam"}, {"category_id": 3, "name": "PSN"}])

    # Курсы Steam должны пробрасываться без искажений.
    def test_steam_currency_rate_success(self):
        payload = {"date": "2026-03-02", "rub/usd": "76.93", "kzt/usd": "500.41", "uah/usd": "43.23"}
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.ns_gift_service, "get_steam_currency_rate", return_value=payload),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/integrations/ns-gift/steam/currency-rate", headers=self._auth_headers())
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), payload)

    # Расчет суммы Steam должен принимать amount из query.
    def test_steam_amount_success(self):
        payload = {"exchange_rate": 76.93, "usd_price": 0.02}
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.ns_gift_service, "get_steam_amount", return_value=payload) as amount_mock,
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get("/integrations/ns-gift/steam/amount?amount=1", headers=self._auth_headers())
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), payload)
            amount_mock.assert_called_once_with(1.0)

    # Создание заказа должно валидировать service_id.
    def test_create_order_validation_error(self):
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/integrations/ns-gift/orders",
                    headers=self._auth_headers(),
                    json={"service_id": 0, "quantity": 1, "data": "", "auto_pay": True},
                )
            self.assertEqual(res.status_code, 400)

    # Успешный заказ должен вернуть custom_id и payload create/paid.
    def test_create_order_success(self):
        fake_response = {
            "custom_id": "abc-123",
            "auto_pay": True,
            "created": {"ok": True, "order_id": 55},
            "paid": {"ok": True},
        }
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.ns_gift_service, "create_order_and_pay", return_value=fake_response) as order_mock,
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/integrations/ns-gift/orders",
                    headers=self._auth_headers(),
                    json={"service_id": 15, "quantity": 2, "data": "steam_login", "auto_pay": True},
                )
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(body["custom_id"], "abc-123")
            self.assertEqual(body["created"]["order_id"], 55)
            order_mock.assert_called_once_with(15, 2.0, "steam_login", True)


if __name__ == "__main__":
    unittest.main()
