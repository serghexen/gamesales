import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

import app as app_module


@unittest.skipIf(TestClient is None, "fastapi.testclient requires httpx")
class InterHubEndpointsTests(unittest.TestCase):
    def setUp(self):
        # Полностью подменяем пул: тест маршрутов не подключается даже к staging.
        for target, value in [('ConnectionPool', None), ('_SUPPLIER_OFFLINE', False)]:
            patcher = patch.object(app_module, target) if value is None else patch.object(app_module, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(app_module.shared_supplier_catalog, 'offline', False)
        patcher.start()
        self.addCleanup(patcher.stop)

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
        self.assertIn("/integrations/interhub/vouchers/pay-batch", response.json()["paths"])
        self.assertIn("/integrations/interhub/vouchers/batches/{batch_id}", response.json()["paths"])
        self.assertIn("/integrations/interhub/prices/refresh", response.json()["paths"])
        self.assertIn("/integrations/interhub/prices/export", response.json()["paths"])
        self.assertIn("/deals/{deal_id}/interhub/prepare", response.json()["paths"])
        self.assertIn("/deals/{deal_id}/interhub/pay", response.json()["paths"])

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

class StagingSupplierGuardTests(unittest.TestCase):
    def test_airpay_preparation_passes_staging_guard_but_still_requires_owner(self):
        # Проверяем настоящую middleware и авторизацию; сеть и запись в журнал заменены заглушками.
        with patch.object(app_module, '_SUPPLIER_OFFLINE', True), patch.object(app_module, 'ConnectionPool'), \
             patch.object(app_module, '_LOCAL_UI_MODE', False), \
             patch('domains.airpay_api.AirpayPreparation.prepare', return_value={'preparation_token': 'signed'}) as prepare, \
             patch('domains.airpay_api.AirpayPreparation.read_draft', return_value={'service': {}}), \
             patch('domains.airpay_api.AirpayPurchase.check', return_value={'success': True, 'payments_enabled': False}) as check:
            owner = {'Authorization': f"Bearer {app_module.create_access_token(1, 'owner', 'owner')}"}
            manager = {'Authorization': f"Bearer {app_module.create_access_token(2, 'manager', 'manager')}"}
            with TestClient(app_module.app) as client:
                for path, body in (('/integrations/airpay/prepare', {'service_id': 'A1', 'fields': {'account': '123'}}),
                                   ('/integrations/airpay/check', {'preparation_token': 'signed'})):
                    self.assertEqual(client.post(path, json=body).status_code, 401)
                    self.assertEqual(client.post(path, json=body, headers=manager).status_code, 403)
                    self.assertEqual(client.post(path, json=body, headers=owner).status_code, 200)
            prepare.assert_called_once()
            check.assert_called_once_with('owner', 'signed')

    def test_staging_allows_owner_review_but_keeps_authorization(self):
        # Отметка просмотренного меняет только нашу БД и остаётся доступной владельцу на staging.
        with patch.object(app_module, '_SUPPLIER_OFFLINE', True), patch.object(app_module, 'ConnectionPool'), \
             patch.object(app_module, '_LOCAL_UI_MODE', False), \
             patch.object(app_module.shared_supplier_catalog, 'review') as review:
            token = app_module.create_access_token(1, 'owner', 'owner')
            entries = [{'service_id': '10', 'nominal_id': '1', 'review_revision': 1}]
            with TestClient(app_module.app) as client:
                self.assertEqual(client.post('/integrations/interhub/catalog/review', json=entries).status_code, 401)
                response = client.post('/integrations/interhub/catalog/review', json=entries,
                                       headers={'Authorization': f'Bearer {token}'})
                self.assertEqual(response.status_code, 200)
            review.assert_called_once_with(entries)

    def test_staging_guard_blocks_purchase_and_refresh_before_routes(self):
        # Запрещённые URL останавливаются до авторизации, БД и запуска фонового потока.
        with patch.object(app_module, '_SUPPLIER_OFFLINE', True), patch.object(app_module, 'ConnectionPool'), patch.object(app_module, '_LOCAL_UI_MODE', False):
            with TestClient(app_module.app) as client:
                for path in ['/integrations/interhub/pay', '/integrations/interhub/check',
                             '/integrations/interhub/prices/refresh', '/deals/1/interhub/prepare',
                             '/integrations/interhub/vouchers/pay-batch',
                             '/integrations/airpay/transactions/1/pay', '/integrations/airpay/transactions/1/reconcile',
                             '/integrations/airpay/transactions/1/voucher', '/integrations/airpay/check/pay',
                             '/integrations/airpay/batches/1/pay', '/integrations/airpay/batches/1/vouchers']:
                    self.assertEqual(client.post(path, json={}).status_code, 403)

    def test_staging_reads_live_services_and_balance_without_using_saved_catalog(self):
        # Ограничения опросов не должны подменять список услуг старой БД или баланс нулём.
        services = [{'service_id': 7, 'title': 'Live', 'category': '', 'type': 'VOUCHER',
                     'min_amount': 0, 'max_amount': 0, 'fields': [], 'raw': {}}]
        with patch.object(app_module, '_SUPPLIER_OFFLINE', True), patch.object(app_module, 'ConnectionPool'), \
             patch.object(app_module, '_LOCAL_UI_MODE', False), \
             patch.object(app_module.shared_supplier_catalog, 'offline', True), \
             patch.object(app_module.shared_supplier_catalog, 'services') as saved, \
             patch.object(app_module.interhub_service, 'get_services', return_value=services) as live, \
             patch.object(app_module.interhub_service, 'get_balance', return_value={'balance': 123, 'currency': 'RUB'}) as balance:
            token = app_module.create_access_token(2, 'manager', 'manager')
            headers = {'Authorization': f'Bearer {token}'}
            with TestClient(app_module.app) as client:
                response = client.get('/integrations/interhub/services', headers=headers)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['items'][0]['service_id'], 7)
                response = client.get('/integrations/interhub/balance', headers=headers)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['balance'], 123)
            saved.assert_not_called()
            live.assert_called_once()
            balance.assert_called_once()
