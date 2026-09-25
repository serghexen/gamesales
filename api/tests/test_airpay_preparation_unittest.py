"""Проверки подготовки Airpay без внешней сети и без pay."""

import json
import subprocess
import unittest
from unittest.mock import MagicMock, patch

import jwt
from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
from domains.airpay_api import mount_airpay_routes
from domains.airpay_preparation import AirpayPreparation, build_check_payload, normalize_check, validate_patterns
from domains.airpay_service import build_airpay_service


SECRET = 'test-airpay-preparation-signing-secret'


def service_description():
    # Шаблон услуги содержит основное поле и дополнительное поле из примеров документации.
    return {'service_id': 'A0002', 'title': 'Test', 'type': 0, 'fixed_payment': True,
            'inputs': [{'name': 'account', 'title': 'Аккаунт', 'required': True, 'regexp': r'^\d{4}$'},
                       {'name': 'ev_account1', 'title': 'Заказ', 'required': True, 'regexp': ''}],
            'displays': [{'name': 'fixedAmount', 'title': 'Сумма', 'required': True, 'regexp': ''}]}


class AirpayPreparationTests(unittest.TestCase):
    def setUp(self):
        # Сервис целиком подменён: тесты не читают .env.dev и не отправляют данные поставщику.
        self.service = MagicMock()
        self.service.get_service.return_value = service_description()
        self.flow = AirpayPreparation(self.service, lambda: SECRET)

    def prepare(self):
        # Получаем настоящий подписанный снимок для проверок повторов и прав владельца.
        return self.flow.prepare('owner', 'A0002', {'account': '1234', 'ev_account1': 'order-1'}, amount_from='12.00')

    def test_retries_preserve_server_id_date_and_extras(self):
        # Оба check отправляют один снимок; временный код не создаёт новый идентификатор.
        draft = self.prepare()
        decoded = jwt.decode(draft['preparation_token'], SECRET, algorithms=['HS256'], audience='airpay-preparation')
        request = decoded['request']
        self.assertEqual(request['extras'], {'account1': 'order-1'})
        self.assertNotIn('amountTo', request)
        self.assertEqual(request['amountFrom'], 12)
        self.assertRegex(request['agentTransactionDate'], r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$')
        self.service.check.side_effect = [{'result': 1, 'resultMessage': 'В обработке'},
            {'result': 0, 'agentTransactionId': request['agentTransactionId'], 'transactionId': 27,
             'displays': {'fixedAmount': '10.50'}}]
        self.assertTrue(self.flow.check('owner', draft['preparation_token'])['retryable'])
        result = self.flow.check('owner', draft['preparation_token'])
        self.assertTrue(result['success'])
        self.assertEqual(result['fixed_amount'], '10.50')
        self.assertEqual(result['displays'][0]['title'], 'Сумма')
        self.assertEqual(self.service.check.call_args_list[0], self.service.check.call_args_list[1])
        self.assertEqual(self.prepare()['agent_transaction_id'] == draft['agent_transaction_id'], False)

    def test_unsigned_modified_expired_and_other_owner_drafts_never_reach_provider(self):
        # Проверка подписи, срока и владельца выполняется до любого внешнего check.
        token = self.prepare()['preparation_token']
        for owner, value in (('other', token), ('owner', token[:-8] + 'tampered'), ('owner', 'invalid')):
            with self.subTest(owner=owner), self.assertRaises(HTTPException):
                self.flow.check(owner, value)
        decoded = jwt.decode(token, SECRET, algorithms=['HS256'], audience='airpay-preparation')
        decoded['exp'] = 1
        with self.assertRaises(HTTPException) as raised:
            self.flow.check('owner', jwt.encode(decoded, SECRET, algorithm='HS256'))
        self.assertEqual(raised.exception.status_code, 410)
        self.service.check.assert_not_called()

    def test_server_revalidates_required_fields_regex_and_money(self):
        # Браузер не может обойти обязательность, regexp, допустимые имена и точность сумм.
        self.service.get_service.return_value['fixed_payment'] = False
        for fields, amount in (({'account': '1234'}, '10'), ({'account': 'bad', 'ev_account1': 'x'}, '10'),
                              ({'account': '1234', 'ev_account1': 'x', 'unexpected': 'x'}, '10'),
                              ({'account': '1234', 'ev_account1': 'x'}, '0'),
                              ({'account': '1234', 'ev_account1': 'x'}, '1.001'),
                              ({'account': '1234', 'ev_account1': 'x'}, 'NaN')):
            with self.subTest(fields=fields, amount=amount), self.assertRaises(HTTPException):
                self.flow.prepare('owner', 'A0002', fields, amount)
        self.service.check.assert_not_called()

    def test_kind_and_amount_rules_cannot_be_overridden_by_client(self):
        # Проверяем серверную защиту при прямом запросе без ограничений HTML-формы.
        fields = {'account': '1234', 'ev_account1': 'x'}
        cases = [(True, 'topup', None), (False, 'voucher', '10'),
                 (True, None, '10'), (False, None, None), (False, None, ''),
                 (None, None, None), ('false', None, '10')]
        for fixed, kind, amount in cases:
            with self.subTest(fixed=fixed, kind=kind, amount=amount), self.assertRaises(HTTPException) as raised:
                self.service.get_service.return_value['fixed_payment'] = fixed
                self.flow.prepare('owner', 'A0002', fields, amount, purchase_kind=kind)
            self.assertEqual(raised.exception.status_code, 422)
        self.service.check.assert_not_called()

    def test_required_inputs_remain_required_for_vouchers_and_topups(self):
        # Автоматический тип меняет поле суммы, но не требования Airpay к реквизитам.
        for fixed, amount in ((True, None), (False, '10')):
            self.service.get_service.return_value['fixed_payment'] = fixed
            for fields in ({'account': '1234'}, {'ev_account1': 'x'}):
                with self.subTest(fixed=fixed, fields=fields), self.assertRaises(HTTPException):
                    self.flow.prepare('owner', 'A0002', fields, amount)
        self.service.check.assert_not_called()

    def test_invalid_or_slow_regex_fails_closed(self):
        # Ошибка или превышение времени regexp не пропускает невалидные реквизиты к поставщику.
        with self.assertRaises(HTTPException):
            validate_patterns([('Аккаунт', '[', '1234')])
        with patch('domains.airpay_preparation.subprocess.run', side_effect=subprocess.TimeoutExpired('python', 1)), self.assertRaises(HTTPException):
            validate_patterns([('Аккаунт', '(a+)+$', 'a' * 100 + 'b')])

    def test_account_is_required_even_when_not_listed(self):
        # Обязательный параметр check не заменяем выдуманным нулём для ваучеров.
        service = {**service_description(), 'inputs': []}
        with self.assertRaises(HTTPException):
            build_check_payload(service, {})
        self.assertEqual(build_check_payload(service, {'account': 'user'})['account'], 'user')

    def test_check_results_preserve_schemes_and_reject_wrong_transaction(self):
        # Сохраняем варианты выбора, но успешный ответ обязан относиться к нашему ID.
        request = {'agentTransactionId': 12}
        base = {'result': 0, 'agentTransactionId': 12, 'transactionId': 27}
        for code in (1, 153, 220, 255):
            self.assertTrue(normalize_check({'result': code}, request, service_description())['retryable'])
        for code in (4, 202, 215, 300, 999):
            self.assertFalse(normalize_check({'result': code}, request, service_description())['success'])
            self.assertFalse(normalize_check({'result': code}, request, service_description())['retryable'])
        contracts = [{'contractId': '0001', 'contractSum': '10.50'}]
        self.assertEqual(normalize_check({**base, 'contracts': contracts}, request, service_description())['scheme'], 'contracts')
        invoice = {'invoices': [{'invoiceId': '1', 'services': [{'subServiceId': 's', 'data': {'paySum': 10}}]}]}
        self.assertEqual(normalize_check({**base, 'invoice': invoice}, request, service_description())['invoice'], invoice)
        for response in ({**base, 'agentTransactionId': 99}, {**base, 'transactionId': None}, {**base, 'invoice': {'invoices': {}}}, {**base, 'contracts': [None]}):
            with self.assertRaises(HTTPException):
                normalize_check(response, request, service_description())

    def test_transport_check_sends_exact_amounts_and_service_parameters(self):
        # Запросы service и check используют POST и Basic, суммы имеют ровно два знака в JSON.
        upstream = build_airpay_service({'AIRPAY_USERNAME': 'test', 'AIRPAY_PASSWORD': 'test'})
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = json.dumps({'result': 1}).encode()
        with patch('domains.airpay_service.urllib.request.build_opener', return_value=opener):
            upstream.check({'serviceId': 'A0002', 'account': '1234', 'amountTo': 10.5, 'amountFrom': 12})
        request = opener.open.call_args.args[0]
        self.assertTrue(request.full_url.endswith('/check'))
        self.assertEqual(request.method, 'POST')
        self.assertIn('"amountTo":10.50', request.data.decode())
        self.assertIn('"amountFrom":12.00', request.data.decode())

    def test_owner_can_prepare_and_check_offline_without_payment_access(self):
        # Владелец проверяет реквизиты даже при запрете покупок; менеджер не получает это право.
        def user(authorization: str = Header(default='')):
            # Простой тестовый сеанс отделяет проверку ролей от БД и JWT приложения.
            if not authorization:
                raise HTTPException(401)
            return {'username': 'owner', 'role': authorization}

        for offline in (False, True):
            app = FastAPI()
            mount_airpay_routes(app, get_current_user=user, service=self.service, get_secret=lambda: SECRET, offline=offline)
            with TestClient(app) as client:
                self.assertNotIn('/integrations/airpay/pay', app.openapi()['paths'])
                self.assertEqual(client.post('/integrations/airpay/check', json={'preparation_token': 'x'}).status_code, 401)
                body = {'service_id': 'A0002', 'fields': {'account': '1234', 'ev_account1': 'x'}}
                self.assertEqual(client.post('/integrations/airpay/prepare', json=body, headers={'Authorization': 'manager'}).status_code, 403)
                response = client.post('/integrations/airpay/prepare', json=body, headers={'Authorization': 'owner'})
                self.assertEqual(response.status_code, 200)
                draft = response.json()
                self.service.check.return_value = {'result': 0, 'agentTransactionId': int(draft['agent_transaction_id']), 'transactionId': 12}
                check = client.post('/integrations/airpay/check', json={'preparation_token': draft['preparation_token']}, headers={'Authorization': 'owner'})
                self.assertEqual(check.status_code, 200)
                self.assertTrue(check.json()['success'])
                denied = client.post('/integrations/airpay/check', json={'preparation_token': draft['preparation_token']}, headers={'Authorization': 'manager'})
                self.assertEqual(denied.status_code, 403)
                if offline:
                    for action in ('pay', 'reconcile', 'voucher'):
                        response = client.post(f"/integrations/airpay/transactions/{draft['agent_transaction_id']}/{action}",
                                               json={'confirmed_amount': '10.00'} if action == 'pay' else {}, headers={'Authorization': 'owner'})
                        self.assertEqual(response.status_code, 403)
        self.service.pay.assert_not_called()
        self.service.get_voucher.assert_not_called()


if __name__ == '__main__':
    unittest.main()
