"""Контракт оплаты и готовности результата; вся работа происходит без сети."""
import unittest
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from domains.airpay_api import mount_airpay_routes
from domains.airpay_contract import CONTRACT_HEADER, CONTRACT_VERSION, transaction_outcome
from domains.airpay_purchase import public_transaction
from domains.airpay_repository import AirpayRepository


class AirpayContractTests(unittest.TestCase):
    def test_result_readiness_is_independent_of_successful_payment(self):
        # Ваучер ожидает код, а пополнение завершается по подтверждённой оплате.
        cases = [('voucher', 'processing', '', 'processing', 'unavailable', False),
                 ('voucher', 'paid', '', 'paid', 'pending', False),
                 ('voucher', 'paid', 'SECRET', 'paid', 'ready', True),
                 ('topup', 'paid', '', 'paid', 'not_required', True),
                 ('topup', 'processing', '', 'processing', 'not_required', False),
                 ('voucher', 'failed', '', 'failed', 'unavailable', False),
                 ('voucher', 'check_failed', '', 'not_started', 'unavailable', False)]
        for kind, state, code, payment, result, completed in cases:
            with self.subTest(kind=kind, state=state, result=result):
                outcome = transaction_outcome({'state': state, 'purchase_kind': kind, 'pin_code': code})
                self.assertEqual(outcome['payment_state'], payment)
                self.assertEqual(outcome['result_state'], result)
                self.assertEqual(outcome['completed'], completed)
                self.assertEqual(outcome['blocks_fallback'], state != 'failed')

    def test_public_transaction_never_contains_secret_even_without_route_filter(self):
        # Все потребители получают безопасную карточку сразу из сериализатора.
        row = {'state': 'paid', 'purchase_kind': 'voucher', 'pin_code': 'DO-NOT-LEAK',
               'agent_transaction_id': 9223372036854775807, 'service_snapshot': {}, 'service_id': 'A0217'}
        public = public_transaction(row, False)
        self.assertNotIn('DO-NOT-LEAK', str(public))
        self.assertNotIn('pin_code', public)
        self.assertEqual(public['agent_transaction_id'], '9223372036854775807')
        self.assertEqual(public['service_id'], 'A0217')
        self.assertEqual(public['provider_code'], 'airpay')
        self.assertTrue(public['result_available'])

    def test_contract_handshake_and_wrong_version_never_call_provider_or_database(self):
        # Неподдерживаемый POST отсекается на границе Hub до подготовки и оплаты.
        provider, repository = MagicMock(payments_enabled=False), MagicMock()
        app = FastAPI()
        mount_airpay_routes(app, get_current_user=lambda: {'username': 'owner', 'role': 'owner'},
                           service=provider, repository=repository, execution_backend='hub')
        client = TestClient(app)
        contract = client.get('/integrations/airpay/contract')
        self.assertEqual(contract.headers[CONTRACT_HEADER], CONTRACT_VERSION)
        self.assertEqual(contract.json()['execution_backend'], 'hub')
        self.assertFalse(contract.json()['payments_enabled'])
        for path in ('prepare', 'transactions/1/pay', 'transactions/1/reconcile', 'transactions/1/voucher'):
            for headers in ({}, {CONTRACT_HEADER: 'airpay.v99'}):
                self.assertEqual(client.post('/integrations/airpay/' + path, json={}, headers=headers).status_code, 409)
        self.assertEqual(client.get('/integrations/airpay/contract', headers={CONTRACT_HEADER: 'old'}).status_code, 409)
        self.assertFalse(provider.mock_calls)
        self.assertFalse(repository.mock_calls)

    def test_cutover_report_contains_only_global_counts(self):
        # Владелец получает причины запрета без раскрытия аккаунтов и кодов других пользователей.
        connect = MagicMock()
        connect.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = {
            'pending_payments': 0, 'missing_vouchers': 1, 'active_jobs': 0}
        report = AirpayRepository(connect).cutover_status()
        self.assertEqual(report, {'ready': False, 'pending_payments': 0, 'missing_vouchers': 1, 'active_jobs': 0})

    def test_cutover_is_available_before_switch_and_only_to_owner(self):
        # Диагностика прямого режима ничего не покупает и не раскрывается сотруднику без роли владельца.
        provider, repository = MagicMock(payments_enabled=False), MagicMock()
        repository.cutover_status.return_value = {'ready': True, 'pending_payments': 0, 'missing_vouchers': 0, 'active_jobs': 0}
        user = {'username': 'owner', 'role': 'owner'}
        app = FastAPI()
        mount_airpay_routes(app, get_current_user=lambda: user, service=provider, repository=repository)
        client = TestClient(app)
        self.assertEqual(client.get('/integrations/airpay/cutover').json(), repository.cutover_status.return_value)
        repository.cutover_status.assert_called_once()
        user['role'] = 'seller'
        self.assertEqual(client.get('/integrations/airpay/cutover').status_code, 403)
        repository.cutover_status.assert_called_once()
        self.assertFalse(provider.mock_calls)
