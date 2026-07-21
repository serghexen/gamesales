import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

import app as app_module


@unittest.skipIf(TestClient is None, "fastapi.testclient requires httpx")
class InterHubEndpointsTests(unittest.TestCase):
    def _client(self):
        return TestClient(app_module.app)

    def _auth_headers(self):
        # Выпускаем токен приложения, чтобы тестировать доступ к внутреннему endpoint.
        token = app_module.create_access_token(2, "manager", "manager")
        return {"Authorization": f"Bearer {token}"}

    def test_services_requires_auth(self):
        # Каталог InterHub не должен быть доступен анонимному пользователю.
        with patch.object(app_module, "ensure_analytics_schema", return_value=None):
            with self._client() as client:
                response = client.get("/integrations/interhub/services")
        self.assertEqual(response.status_code, 401)

    def test_openapi_builds_interhub_payment_routes(self):
        # Схема API должна собираться, иначе FastAPI не сможет корректно обработать новые модели оплаты.
        with patch.object(app_module, "ensure_analytics_schema", return_value=None):
            with self._client() as client:
                response = client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/integrations/interhub/pay", response.json()["paths"])

    def test_services_returns_normalized_catalog(self):
        # Endpoint должен передать в UI тип услуги и динамические поля формы.
        services = [
            {
                "service_id": 9983,
                "title": "Vodafone",
                "category": "Мобильные операторы",
                "type": "TOP_UP_FIXED",
                "min_amount": 11350.0,
                "max_amount": 11350000.0,
                "fields": [
                    {
                        "name": "nominal",
                        "type": "LIST",
                        "required": True,
                        "value_list": [{"id": 3333, "title": "TRY 80.00"}],
                        "raw": {"name": "nominal"},
                    }
                ],
                "raw": {"id": 9983},
            }
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.interhub_service, "get_services", return_value=services),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                response = client.get("/integrations/interhub/services", headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["type"], "TOP_UP_FIXED")
        self.assertEqual(payload["items"][0]["fields"][0]["value_list"][0]["id"], 3333)


if __name__ == "__main__":
    unittest.main()
