from unittest.mock import patch
import json
import unittest

from fastapi import HTTPException

from domains.supplier_hub_service import build_supplier_hub_operator_client


class _Response:
    def __init__(self, payload):
        # Имитируем ответ urllib как контекстный менеджер.
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class SupplierHubServiceTests(unittest.TestCase):
    def build_client(self, **overrides):
        # Собираем backend-only клиент с тестовыми операторскими реквизитами.
        values = {
            "HTTPException": HTTPException,
            "base_url": "http://127.0.0.1:8010",
            "operator_id": "crm-owner",
            "operator_key": "secret",
            "timeout_sec": 10,
        }
        values.update(overrides)
        return build_supplier_hub_operator_client(**values)

    def test_history_uses_operator_headers_and_never_calls_purchase_endpoint(self):
        client = self.build_client()
        captured = {}

        def fake_urlopen(request, timeout):
            # Запоминаем сформированный read-only запрос без сетевого вызова.
            captured["request"] = request
            captured["timeout"] = timeout
            return _Response({"items": [], "total": 0, "total_amount": "0"})

        with patch("domains.supplier_hub_service.urllib.request.urlopen", side_effect=fake_urlopen):
            client.list_transactions({"limit": 25, "query": "11125"})

        request = captured["request"]
        self.assertEqual(request.get_method(), "GET")
        self.assertIn("/v1/operator/transactions", request.full_url)
        self.assertNotIn("/v1/purchases", request.full_url)
        self.assertEqual(request.get_header("X-hub-operator"), "crm-owner")
        self.assertEqual(request.get_header("X-hub-operator-key"), "secret")

    def test_result_uses_post_and_explicit_request_id(self):
        client = self.build_client()
        captured = {}

        def fake_urlopen(request, timeout):
            # Проверяем отдельный маршрут раскрытия без методов оплаты.
            captured["request"] = request
            return _Response({"purchase_id": "purchase-1", "value": "TEST-CODE"})

        with patch("domains.supplier_hub_service.urllib.request.urlopen", side_effect=fake_urlopen):
            client.reveal_result("purchase-1", "crm:result:owner:1")

        request = captured["request"]
        self.assertEqual(request.get_method(), "POST")
        self.assertTrue(request.full_url.endswith("/v1/operator/purchases/purchase-1/result"))
        self.assertEqual(request.get_header("X-request-id"), "crm:result:owner:1")

    def test_missing_operator_credentials_fail_before_network(self):
        client = self.build_client(operator_key="")

        with self.assertRaises(HTTPException) as error:
            client.list_transactions({})

        self.assertEqual(error.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
