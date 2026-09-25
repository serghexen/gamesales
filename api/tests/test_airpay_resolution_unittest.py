"""Решения и лимиты восстановления без сети и платёжного транспорта."""
from datetime import timedelta
from copy import deepcopy
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from domains.airpay_api import mount_airpay_routes
from domains.airpay_resolution import resolution_changes, resolution_fingerprint
from domains.airpay_purchase import now_utc
from tests import test_airpay_purchase_unittest as purchase_tests


class AirpayResolutionTests(unittest.TestCase):
    def setUp(self):
        # Сверка моделируется готовой строкой журнала, без экземпляра поставщика.
        self.row = {'state': 'processing', 'purchase_kind': 'voucher', 'pin_code': '', 'amount': '12.50',
                    'currency': 'RUB', 'updated_at': now_utc(), 'provider_transaction_id': ''}
        self.payload = {'request_id': str(uuid4()), 'decision': 'record_success',
            'expected_updated_at': self.row['updated_at'].isoformat(), 'verified': True,
            'evidence': 'Airpay подтвердил в обращении TEST-123', 'provider_transaction_id': '71', 'code': 'FAKE-CODE'}

    def test_success_restores_code_and_does_not_change_frozen_price(self):
        # Решение дополняет сохранённую покупку, не позволяет задать новую закупочную стоимость.
        changes = resolution_changes(self.row, self.payload)
        self.assertEqual(changes['state'], 'paid')
        self.assertEqual(changes['pin_code'], 'FAKE-CODE')
        self.assertFalse(changes['requires_attention'])
        self.assertNotIn('amount', changes)
        self.assertNotIn('pay_request', changes)
        self.assertNotIn('pay_attempts', changes)

    def test_failure_requires_unknown_payment_and_never_reverts_paid(self):
        # Внешне подтверждённый отказ разрешён только при неизвестном результате pay.
        payload = {**self.payload, 'decision': 'confirm_failed', 'code': '', 'provider_transaction_id': ''}
        self.assertEqual(resolution_changes(self.row, payload)['state'], 'failed')
        for state in ('paid', 'failed', 'checked', 'prepared'):
            with self.subTest(state=state), self.assertRaises(HTTPException):
                resolution_changes({**self.row, 'state': state}, payload)

    def test_stale_unverified_or_wrong_transaction_is_rejected(self):
        # Одновременное завершение worker и неверный номер оплаченной операции требуют нового просмотра.
        cases = [({**self.row, 'updated_at': now_utc()+timedelta(seconds=1)}, self.payload),
                 (self.row, {**self.payload, 'verified': False}),
                 ({**self.row, 'state': 'paid', 'provider_transaction_id': 'OTHER'}, self.payload),
                 (self.row, {**self.payload, 'code': ''}),
                 (self.row, {**self.payload, 'evidence': 'secret FAKE-CODE copied'}),
                 ({**self.row, 'state': 'paid', 'pin_code': '[stored]'}, self.payload)]
        for row, payload in cases:
            with self.subTest(row=row), self.assertRaises(HTTPException):
                resolution_changes(row, payload)

    def test_topup_does_not_accept_or_require_voucher(self):
        # Пополнение завершается без искусственного кода и без вызова voucher.
        row = {**self.row, 'purchase_kind': 'topup'}
        with self.assertRaises(HTTPException):
            resolution_changes(row, self.payload)
        changes = resolution_changes(row, {**self.payload, 'code': ''})
        self.assertEqual(changes['state'], 'paid')
        self.assertNotIn('pin_code', changes)

    def test_fingerprint_changes_for_different_decision_and_never_contains_code(self):
        # Повторный UUID нельзя использовать с другими реквизитами решения.
        digest = resolution_fingerprint(self.payload)
        self.assertEqual(digest, resolution_fingerprint(deepcopy(self.payload)))
        self.assertNotEqual(digest, resolution_fingerprint({**self.payload, 'code': 'OTHER'}))
        self.assertNotIn('FAKE-CODE', digest)

    def test_api_resolution_is_available_offline_without_provider_and_owner_only(self):
        # Операция меняет только журнал; даже выключенный платёжный транспорт не используется.
        provider, repository = MagicMock(payments_enabled=False), MagicMock()
        repository.resolve.return_value = {**self.row, 'state': 'paid', 'pin_code': '[stored]',
                                           'agent_transaction_id': 10, 'service_snapshot': {}}
        user = {'role': 'owner', 'username': 'owner'}
        app = FastAPI()
        mount_airpay_routes(app, get_current_user=lambda: user, service=provider, repository=repository, offline=True)
        client = TestClient(app)
        response = client.post('/integrations/airpay/transactions/10/resolve', json=self.payload)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['completed'])
        self.assertNotIn('pin_code', response.json())
        self.assertFalse(provider.mock_calls)
        user['role'] = 'seller'
        self.assertEqual(client.post('/integrations/airpay/transactions/10/resolve', json=self.payload).status_code, 403)
        repository.resolve.assert_called_once()


class AirpayAttentionTests(unittest.TestCase):
    setUp = purchase_tests.AirpayPurchaseTests.setUp
    prepare = purchase_tests.AirpayPurchaseTests.prepare
    checked = purchase_tests.AirpayPurchaseTests.checked

    def test_repeated_uncertain_pay_stops_at_limit(self):
        # После пятого подменённого запроса новые pay не выполняются даже при обходе UI.
        self.checked()
        row = self.journal.rows[self.id]
        row.update(state='processing', pay_request=row['request_payload'], pay_attempts=4, next_attempt_at=None)
        self.service.pay.side_effect = HTTPException(503, 'test outage')
        result = self.flow.reconcile('owner', self.id)
        self.assertTrue(result['requires_attention'])
        row['next_attempt_at'] = None
        with self.assertRaises(HTTPException):
            self.flow.reconcile('owner', self.id)
        self.service.pay.assert_called_once()

    def test_paid_without_code_stops_voucher_queries_not_payment_state(self):
        # Исчерпание выдачи не превращает оплаченный ваучер в отказ покупки.
        self.checked()
        row = self.journal.rows[self.id]
        row.update(state='paid', provider_transaction_id='71', voucher_attempts=4, next_attempt_at=None)
        self.service.get_voucher.side_effect = HTTPException(503, 'test outage')
        result = self.flow.voucher('owner', self.id)
        self.assertEqual(result['payment_state'], 'paid')
        self.assertTrue(result['requires_attention'])
        with self.assertRaises(HTTPException):
            self.flow.voucher('owner', self.id)
        self.service.get_voucher.assert_called_once()
        self.service.pay.assert_not_called()
