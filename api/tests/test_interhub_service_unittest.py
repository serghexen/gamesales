import json
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from domains.interhub_service import build_interhub_service


class _Response:
    def __init__(self, payload):
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self):
        # Имитируем байтовый ответ urllib без обращения к реальному InterHub.
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class InterHubServiceTests(unittest.TestCase):
    def test_catalog_normalizes_nested_service_and_dynamic_fields(self):
        # Преобразуем типовой ответ провайдера в контракт, удобный для динамической формы.
        payload = {
            "success": True,
            "data": [
                {
                    "service_id": 7,
                    "name": "Mobile top up",
                    "category_name": "Mobile",
                    "type": "TOP_UP_FIXED",
                    "min_amount": "10.50",
                    "max_amount": 100,
                    "fields": [
                        {
                            "name": "nominal",
                            "type": "LIST",
                            "required": True,
                            "value_list": [{"id": 15, "title": "15"}],
                        }
                    ],
                }
            ],
        }
        service = build_interhub_service(
            HTTPException=HTTPException,
            interhub_api_url="https://api.interhub.ae",
            interhub_token="test-token",
            timeout_sec=20,
            ssl_verify=False,
            ca_cert_path="",
        )
        with patch("domains.interhub_service.urllib.request.urlopen", return_value=_Response(payload)) as urlopen_mock:
            items = service.get_services()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["service_id"], 7)
        self.assertEqual(items[0]["min_amount"], 10.5)
        self.assertTrue(items[0]["fields"][0]["required"])
        request = urlopen_mock.call_args.args[0]
        self.assertEqual(request.get_header("Token"), "test-token")
        self.assertTrue(request.full_url.endswith("/api/agent/service/list"))

    def test_catalog_rejects_empty_token_before_network_call(self):
        # Блокируем запрос, если секрет не задан в серверном окружении.
        service = build_interhub_service(
            HTTPException=HTTPException,
            interhub_api_url="https://api.interhub.ae",
            interhub_token="",
            timeout_sec=20,
            ssl_verify=True,
            ca_cert_path="",
        )
        with self.assertRaises(HTTPException) as error:
            service.get_services()
        self.assertEqual(error.exception.status_code, 500)


if __name__ == "__main__":
    unittest.main()
