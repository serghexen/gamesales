"""CRM выбирает одного исполнителя Airpay и не делает fallback при ошибке Hub."""
import json
import unittest
import urllib.error
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from domains.airpay_hub_client import mount_airpay_hub_proxy
from domains.airpay_contract import CONTRACT_HEADER, CONTRACT_VERSION, describe_contract


class AirpayHubClientTests(unittest.TestCase):
    def setUp(self):
        # Подключение Hub подменяется до создания клиента; реальные credentials не читаются.
        self.env = {'AIRPAY_HUB_URL': 'http://airpay-api:8011', 'AIRPAY_HUB_CLIENT_ID': 'crm', 'AIRPAY_HUB_CLIENT_KEY': 'test-server-key'}
        self.opener = MagicMock()
        self.response = self.opener.open.return_value.__enter__.return_value
        self.response.status = 200
        self.response.headers = {CONTRACT_HEADER: CONTRACT_VERSION}
        self.response.read.return_value = json.dumps({**describe_contract('hub', True), 'items': []}).encode()
        self.patcher = patch('domains.airpay_hub_client.urllib.request.build_opener', return_value=self.opener)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def client(self, *, restricted=False, role='owner', legacy=None):
        # Одинаковая авторизация применяется ко всем маршрутам-прокси и архиву.
        app = FastAPI()
        mount_airpay_hub_proxy(app, get_current_user=lambda: {'username': 'owner', 'role': role}, environ=self.env,
                              restricted=restricted, legacy_connect=legacy)
        return TestClient(app)

    def test_diagnostics_are_owner_only_and_available_without_payment_permission(self):
        # Новый маршрут использует тот же Hub и handshake, сохраняя запрет любых платёжных методов локально.
        run_id = 'bbf9af7b-4f3e-4847-9574-ef2e9cc27cf5'
        client = self.client(restricted=True)
        for path in ('diagnostics', f'diagnostics/{run_id}/next', f'diagnostics/{run_id}/cancel'):
            self.assertEqual(client.post('/integrations/airpay/' + path, json={}).status_code, 200)
        self.opener.open.reset_mock()
        self.assertEqual(self.client(role='manager').get('/integrations/airpay/diagnostics').status_code, 403)
        self.opener.open.assert_not_called()

    def test_server_credentials_and_same_payload_are_forwarded(self):
        # CRM Bearer не передаётся поставщику, а idempotency key сохраняется без подмены.
        response = self.client().post('/integrations/airpay/prepare', json={'preparation_key': 'stable'}, headers={'Authorization': 'Bearer CRM-SECRET'})
        self.assertEqual(response.status_code, 200)
        request = self.opener.open.call_args.args[0]
        self.assertEqual(json.loads(request.data), {'preparation_key': 'stable'})
        self.assertEqual(request.get_header('X-hub-key'), 'test-server-key')
        self.assertEqual(request.get_header('X-airpay-contract'), CONTRACT_VERSION)
        self.assertIsNone(request.get_header('Authorization'))
        self.assertTrue(self.opener.open.call_args_list[0].args[0].full_url.endswith('/contract'))

    def test_local_mode_blocks_every_paid_action_before_network(self):
        # Удалённый Hub не может обойти локальный запрет pay, reconcile и выдачи ваучеров.
        client = self.client(restricted=True)
        for path in ('transactions/1/pay', 'transactions/1/reconcile', 'transactions/1/voucher', 'batches/1/pay', 'batches/1/vouchers'):
            self.assertEqual(client.post('/integrations/airpay/' + path, json={}).status_code, 403)
        self.opener.open.assert_not_called()
        self.assertFalse(client.get('/integrations/airpay/transactions').json()['payments_enabled'])

    def test_outage_does_not_fallback_to_direct_airpay(self):
        # Недоступность единственного выбранного исполнителя возвращает ошибку, а не новую покупку.
        self.opener.open.side_effect = urllib.error.URLError('unavailable')
        response = self.client().post('/integrations/airpay/transactions/1/pay', json={'confirmed_amount': '10.00'})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.opener.open.call_count, 1)
        self.assertTrue(self.opener.open.call_args.args[0].full_url.startswith(self.env['AIRPAY_HUB_URL']))

    def test_pending_legacy_payment_prevents_cutover(self):
        # До завершения прежнего processing нельзя начать новую покупку через другой сервис.
        legacy = MagicMock()
        legacy.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = {
            'pending_payments': 1, 'missing_vouchers': 0, 'active_jobs': 0}
        response = self.client(legacy=legacy).post('/integrations/airpay/prepare', json={})
        self.assertEqual(response.status_code, 409)
        self.opener.open.assert_not_called()

    def test_paid_legacy_without_code_blocks_all_new_work_but_not_reads(self):
        # Закрываем обход через готовый ID, но не запрещаем завершить уже начатую операцию Hub.
        legacy = MagicMock()
        legacy.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = {
            'pending_payments': 0, 'missing_vouchers': 1, 'active_jobs': 0}
        client = self.client(legacy=legacy)
        for path in ('prepare', 'check', 'transactions/1/pay', 'batches/1/pay', 'batches/1/renew', 'batches/1/check'):
            self.assertEqual(client.post('/integrations/airpay/' + path, json={}).status_code, 409)
        self.opener.open.assert_not_called()
        report = client.get('/integrations/airpay/cutover')
        self.assertEqual(report.json(), {'ready': False, 'pending_payments': 0, 'missing_vouchers': 1, 'active_jobs': 0})
        self.opener.open.assert_not_called()
        self.assertEqual(client.get('/integrations/airpay/transactions/1').status_code, 200)
        self.assertEqual(client.post('/integrations/airpay/transactions/1/result').status_code, 200)

    def test_old_or_wrong_backend_is_rejected_before_post(self):
        # Handshake со старым API или прямым CRM не отправляет исходное платёжное действие.
        cases = [({}, describe_contract('hub', True)),
                 ({CONTRACT_HEADER: CONTRACT_VERSION}, describe_contract('crm', True)),
                 ({CONTRACT_HEADER: CONTRACT_VERSION}, {'contract_version': 'future'})]
        for headers, payload in cases:
            with self.subTest(payload=payload):
                self.opener.open.reset_mock()
                self.response.headers = headers
                self.response.read.return_value = json.dumps(payload).encode()
                response = self.client().post('/integrations/airpay/transactions/1/pay', json={'confirmed_amount': '10.00'})
                self.assertEqual(response.status_code, 502)
                self.opener.open.assert_called_once()
                self.assertEqual(self.opener.open.call_args.args[0].method, 'GET')

    def test_completed_legacy_allows_hub_and_active_check_job_blocks_it(self):
        # Даже старый check-worker должен завершиться до смены исполнителя.
        legacy = MagicMock()
        counts = {'pending_payments': 0, 'missing_vouchers': 0, 'active_jobs': 1}
        legacy.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = counts
        client = self.client(legacy=legacy)
        self.assertEqual(client.post('/integrations/airpay/prepare', json={}).status_code, 409)
        self.opener.open.assert_not_called()
        counts['active_jobs'] = 0
        self.assertTrue(client.get('/integrations/airpay/cutover').json()['ready'])
        self.assertEqual(client.post('/integrations/airpay/prepare', json={}).status_code, 200)

    def test_non_owner_and_unknown_routes_are_rejected_before_network(self):
        # Catch-all не расширяет набор разрешённых операций и не даёт служебных credentials продавцу.
        client = self.client(role='seller')
        self.assertEqual(client.post('/integrations/airpay/prepare', json={}).status_code, 403)
        self.assertEqual(client.get('/integrations/airpay/transactions').status_code, 403)
        self.assertEqual(client.get('/integrations/airpay/unsupported').status_code, 404)
        self.opener.open.assert_not_called()

    def test_export_forwards_read_only_binary_and_filters(self):
        # Прокси передаёт XLSX, не превращая GET в проверку, оплату или раскрытие кода.
        from domains.airpay_history import XLSX_TYPE
        self.response.headers['Content-Type'] = XLSX_TYPE
        self.response.read.return_value = b'PK-test-workbook'
        client = self.client(restricted=True)
        response = client.get('/integrations/airpay/transactions/export?status=processing&date_to=2026-09-23')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'PK-test-workbook')
        self.assertEqual(response.headers['content-type'], XLSX_TYPE)
        self.opener.open.assert_called_once()
        request = self.opener.open.call_args.args[0]
        self.assertEqual(request.method, 'GET')
        self.assertIn('status=processing&date_to=2026-09-23', request.full_url)
        self.assertEqual(client.post('/integrations/airpay/transactions/export').status_code, 403)

    def test_archive_filter_and_export_never_contact_hub(self):
        # Архив с совпадающими ID остаётся локальным, включая Excel и фильтры.
        from io import BytesIO
        from openpyxl import load_workbook
        from tests.test_airpay_history_unittest import saved_row
        legacy = MagicMock()
        legacy.return_value.__enter__.return_value.execute.return_value.fetchall.return_value = [saved_row()]
        client = self.client(legacy=legacy)
        query = '?archive=crm&q=A0217&status=paid&kind=voucher&date_from=2026-09-23'
        self.assertEqual(client.get('/integrations/airpay/transactions' + query).status_code, 200)
        response = client.get('/integrations/airpay/transactions/export' + query)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(load_workbook(BytesIO(response.content)).active['A2'].value, '1645129032053759724')
        self.opener.open.assert_not_called()
        sql, args = legacy.return_value.__enter__.return_value.execute.call_args.args
        self.assertIn('created_by=%s', sql)
        self.assertIn('state=%s', sql)
        self.assertEqual(args[0], 'owner')
        self.assertEqual(args[-2:], (10001, 0))
        legacy.reset_mock()
        self.assertEqual(client.get('/integrations/airpay/transactions/export?archive=crm&status=oops').status_code, 422)
        legacy.assert_not_called()

    def test_export_rejects_wrong_content_and_preserves_limit_error(self):
        # Ошибку лимита показываем пользователю; JSON или HTML не скачиваются как Excel.
        self.assertEqual(self.client().get('/integrations/airpay/transactions/export').status_code, 502)
        from io import BytesIO
        self.opener.open.side_effect = urllib.error.HTTPError('http://hub', 422, 'Too many', {}, BytesIO(b'{"detail":"Narrow filters"}'))
        response = self.client().get('/integrations/airpay/transactions/export')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['detail'], 'Narrow filters')

    def test_queue_diagnostics_and_queued_cancel_are_allowed_locally(self):
        # Диагностика и отмена ожидающего запуска не дают локальному UI оплатить или сверить платёж.
        client = self.client(restricted=True)
        self.assertEqual(client.get('/integrations/airpay/queue').status_code, 200)
        self.assertEqual(client.post('/integrations/airpay/jobs/11111111-1111-4111-8111-111111111111/cancel').status_code, 200)
        self.assertEqual(self.opener.open.call_args.args[0].method, 'POST')
        self.assertTrue(self.opener.open.call_args.args[0].full_url.endswith('/cancel'))
        self.assertEqual(self.client(role='seller').get('/integrations/airpay/queue').status_code, 403)
        self.assertEqual(self.client(role='seller').post('/integrations/airpay/jobs/11111111-1111-4111-8111-111111111111/cancel').status_code, 403)
