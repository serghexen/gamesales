from types import SimpleNamespace
import unittest

from fastapi import FastAPI

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

from domains.supplier_hub_api import mount_supplier_hub_routes


class _FakeSupplierHubClient:
    def __init__(self):
        # Сохраняем запросы для проверки границ даты и явного раскрытия результата.
        self.list_queries = []
        self.result_requests = []

    def list_transactions(self, query):
        # Возвращаем безопасные строки без секретного результата и учитываем серверную пагинацию.
        self.list_queries.append(dict(query))
        items = [{
            "id": "b0a7b2f4-950d-4359-a718-0da94b651528",
            "consumer_id": "seller",
            "provider_code": "interhub",
            "service_id": 11125,
            "nominal_id": "28632",
            "amount": "464.53",
            "state": "succeeded",
            "result_available": True,
            "created_at": "2026-08-26T10:00:00Z",
        }, {
            "id": "44444444-950d-4359-a718-0da94b651528",
            "consumer_id": "seller",
            "provider_code": "interhub",
            "service_id": 22222,
            "nominal_id": "99999",
            "amount": "100",
            "state": "succeeded",
            "result_available": False,
            "created_at": "2026-08-25T10:00:00Z",
        }]
        offset = int(query.get("offset") or 0)
        limit = int(query.get("limit") or 25)
        return {
            "total": len(items),
            "total_amount": "464.53",
            "items": items[offset:offset + limit],
        }

    def reveal_result(self, purchase_id, request_id):
        # Имитируем только аудируемое чтение уже купленного результата.
        self.result_requests.append((purchase_id, request_id))
        return {"purchase_id": purchase_id, "value": "TEST-CODE", "access_created": True}


@unittest.skipIf(TestClient is None, "fastapi.testclient requires httpx")
class SupplierHubApiTests(unittest.TestCase):
    def create_client(self):
        # Монтируем только owner-маршруты без CRM и настоящей сети.
        app = FastAPI()
        hub = _FakeSupplierHubClient()
        user = SimpleNamespace(username="owner", role="owner")
        mount_supplier_hub_routes(
            app,
            require_role=lambda *_roles: lambda: user,
            UserOut=object,
            supplier_hub_client=hub,
            interhub_get_services=lambda: [{
                "service_id": 11125,
                "title": "Steam Wallet",
                "fields": [{"name": "nominal", "value_list": [{"id": 28632, "title": "TRY 400"}]}],
            }, {
                "service_id": 22222,
                "title": "Apple Gift Card",
                "fields": [{"name": "nominal", "value_list": [{"id": 99999, "title": "USD 10"}]}],
            }],
        )
        return TestClient(app), hub

    def test_history_uses_moscow_date_boundaries_and_maps_safe_fields(self):
        client, hub = self.create_client()

        response = client.get(
            "/integrations/supplier-hub/transactions"
            "?date_from=2026-08-26&date_to=2026-08-26&sort_by=price&sort_direction=asc"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 2)
        self.assertEqual(payload["items"][0]["purchase_id"], "b0a7b2f4-950d-4359-a718-0da94b651528")
        self.assertEqual(payload["items"][0]["service_title"], "Steam Wallet")
        self.assertEqual(payload["items"][0]["nominal_title"], "TRY 400")
        self.assertNotIn("value", payload["items"][0])
        self.assertEqual(hub.list_queries[0]["sort_by"], "amount")
        self.assertEqual(hub.list_queries[0]["created_from"], "2026-08-26T00:00:00+03:00")
        self.assertEqual(hub.list_queries[0]["created_to"], "2026-08-27T00:00:00+03:00")

    def test_history_searches_visible_catalog_labels_and_ignores_short_uuid_matches(self):
        client, hub = self.create_client()

        by_title = client.get("/integrations/supplier-hub/transactions?search=steam")
        by_short_value = client.get("/integrations/supplier-hub/transactions?search=4")

        self.assertEqual(by_title.status_code, 200)
        self.assertEqual(by_title.json()["total"], 1)
        self.assertEqual(by_title.json()["items"][0]["service_title"], "Steam Wallet")
        self.assertEqual(by_short_value.json()["total"], 1)
        self.assertEqual(by_short_value.json()["items"][0]["nominal_title"], "TRY 400")
        self.assertTrue(all("query" not in query for query in hub.list_queries))

    def test_result_is_revealed_only_by_explicit_post_with_correlation_id(self):
        client, hub = self.create_client()
        purchase_id = "b0a7b2f4-950d-4359-a718-0da94b651528"

        response = client.post(f"/integrations/supplier-hub/transactions/{purchase_id}/result")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["value"], "TEST-CODE")
        self.assertEqual(hub.result_requests[0][0], purchase_id)
        self.assertTrue(hub.result_requests[0][1].startswith("crm:result:owner:"))


if __name__ == "__main__":
    unittest.main()
