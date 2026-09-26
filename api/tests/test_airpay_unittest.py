"""Изолированные проверки Airpay без сети и подключения к БД."""

import base64
import json
import ssl
import unittest
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
from domains.airpay_api import mount_airpay_routes
from domains.airpay_service import build_airpay_service, normalize_airpay_balance, normalize_airpay_services, available_airpay_funds
from domains.interhub_ssh_transport import NoTunnelRedirects, TunnelHTTPSHandler
from scripts.run_airpay_tunnel import build_tunnel_command


def balance_payload(**overrides):
    # Повторяем подтверждённый контракт поставщика, включая настоящий нулевой баланс.
    return {'result': 0, 'resultMessage': 'Успешно', 'agent': {
        'agentId': 112, 'agentName': 'Тестовый агент', 'balance': 0,
        'overdraft': 5000, 'notification': 0, 'currency': 'RUB', **overrides,
    }}


def service_payload(**overrides):
    # Пример со строковым ID и параметрами повторяет документацию services.
    return {'serviceId': 'A0002', 'type': 0, 'name': 'Test Service', 'group': 'Онлайн игры',
            'country': 'КАЗАХСТАН', 'fixedPayment': True,
            'inputs': [{'name': 'account', 'title': 'Номер аккаунта', 'required': True, 'regexp': r'^\d{10}$'}],
            'displays': [{'name': 'fixedAmount', 'title': '', 'required': True}], **overrides}


class AirpayServiceTests(unittest.TestCase):
    def setUp(self):
        # Только тестовые Basic-реквизиты; окружение разработчика не используется.
        self.env = {'AIRPAY_USERNAME': 'test-agent', 'AIRPAY_PASSWORD': 'test-password'}
        self.opener = MagicMock()
        self.opener.open.return_value.__enter__.return_value.read.return_value = json.dumps(balance_payload()).encode()
        self.patcher = patch('domains.airpay_service.urllib.request.build_opener', return_value=self.opener)
        self.build_opener = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_available_funds_validate_credit_and_preserve_decimal_precision(self):
        # Не используем некорректный лимит и не превращаем отрицательный кредит в доступные деньги.
        from decimal import Decimal
        self.assertEqual(available_airpay_funds({'configured': True, 'balance': '-4343.82', 'overdraft': '5000'}), Decimal('656.18'))
        self.assertEqual(available_airpay_funds({'configured': True, 'balance': '0.10', 'overdraft': '.20'}), Decimal('.30'))
        self.assertEqual(available_airpay_funds({'configured': True, 'balance': '-5001', 'overdraft': '5000'}), Decimal('-1'))
        for value in (None, True, -1, 'NaN', 'Infinity', 'wrong'):
            with self.subTest(value=value), self.assertRaises(HTTPException):
                available_airpay_funds({'configured': True, 'balance': 0, 'overdraft': value})

    def test_balance_basic_auth_and_no_private_agent_fields(self):
        # Basic уходит только поставщику, а UI получает суммы без имени и ID агента.
        result = build_airpay_service(self.env).get_balance()
        self.assertEqual(result, {'configured': True, 'balance': 0, 'overdraft': 5000, 'currency': 'RUB'})
        request = self.opener.open.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.airpay.kz/AirPayService/api/v20/balance')
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.data, b'')
        self.assertEqual(request.get_header('Content-type'), 'application/json')
        expected = base64.b64encode(b'test-agent:test-password').decode()
        self.assertEqual(request.get_header('Authorization'), f'Basic {expected}')
        self.assertEqual(self.build_opener.call_args.args[0].proxies, {})
        self.assertIsInstance(self.build_opener.call_args.args[2], NoTunnelRedirects)

    def test_missing_credentials_do_not_call_provider_or_fake_zero(self):
        # Настройка доступа должна завершиться до первого запроса в сеть.
        for env in ({}, {'AIRPAY_USERNAME': 'test'}, {'AIRPAY_PASSWORD': 'test'}):
            with self.subTest(env=env):
                result = build_airpay_service(env).get_balance()
                self.assertFalse(result['configured'])
                self.assertIsNone(result['balance'])
                self.assertEqual(build_airpay_service(env).get_services(), {'configured': False, 'items': [], 'total': 0})
        self.opener.open.assert_not_called()

    def test_local_ui_uses_separate_tunnel_and_verified_tls(self):
        # Даже заданный CONNECT-proxy не обходит явный маршрут локального UI.
        service = build_airpay_service({**self.env, 'AIRPAY_PROXY_URL': 'http://unused:3128'}, local_ui=True)
        service.get_balance()
        proxy, handler, redirects = self.build_opener.call_args.args
        self.assertEqual(proxy.proxies, {})
        self.assertIsInstance(handler, TunnelHTTPSHandler)
        self.assertEqual(handler.tunnel_port, 3129)
        self.assertTrue(handler._context.check_hostname)
        self.assertIsInstance(redirects, NoTunnelRedirects)

    def test_proxy_is_scoped_to_airpay(self):
        # Обычный режим использует только явно заданный proxy для этого поставщика.
        build_airpay_service({**self.env, 'AIRPAY_PROXY_URL': 'http://localhost:8181'}).get_balance()
        self.assertEqual(self.build_opener.call_args.args[0].proxies, {'https': 'http://localhost:8181'})

    def test_ssl_verify_applies_to_every_transport(self):
        # Явное отключение и включение проверки одинаково работают напрямую, через proxy и SSH.
        for local_ui, proxy in ((False, ''), (False, 'http://localhost:8181'), (True, '')):
            for setting, enabled in (('true', True), ('1', True), (' YES ', True), ('on', True),
                                     ('', True), ('false', False), ('0', False), ('no', False), ('off', False)):
                with self.subTest(local_ui=local_ui, proxy=proxy, setting=setting):
                    env = {**self.env, 'AIRPAY_SSL_VERIFY': setting, 'AIRPAY_PROXY_URL': proxy}
                    build_airpay_service(env, local_ui=local_ui).get_balance()
                    context = self.build_opener.call_args.args[1]._context
                    self.assertEqual(context.check_hostname, enabled)
                    self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED if enabled else ssl.CERT_NONE)

    def test_invalid_ssl_verify_does_not_silently_disable_verification(self):
        # Опечатка в настройке должна остановить запрос до передачи Basic-реквизитов.
        with self.assertRaises(HTTPException) as raised:
            build_airpay_service({**self.env, 'AIRPAY_SSL_VERIFY': 'typo'}).get_balance()
        self.assertEqual(raised.exception.status_code, 503)
        self.opener.open.assert_not_called()

    def test_tunnel_failure_never_falls_back_or_exposes_transport_details(self):
        # Закрытый туннель остаётся ошибкой, а диагностическая строка с секретами скрывается.
        self.opener.open.side_effect = urllib.error.URLError('proxy-user:proxy-secret@host')
        with patch('urllib.request.urlopen') as direct, self.assertRaises(HTTPException) as raised:
            build_airpay_service(self.env, local_ui=True).get_balance()
        self.assertEqual(raised.exception.status_code, 502)
        self.assertNotIn('proxy-secret', raised.exception.detail)
        self.opener.open.assert_called_once()
        direct.assert_not_called()

    def test_http_errors_are_sanitized_and_do_not_log_out_crm_user(self):
        # Ошибка Basic у поставщика не должна стать 401 CRM или раскрыть тело ответа.
        self.opener.open.side_effect = urllib.error.HTTPError('https://example.invalid', 401, 'secret', {}, BytesIO(b'secret'))
        with self.assertRaises(HTTPException) as raised:
            build_airpay_service(self.env).get_balance()
        self.assertEqual(raised.exception.status_code, 502)
        self.assertIn('авторизацию', raised.exception.detail)
        self.assertNotIn('secret', raised.exception.detail)

    def test_timeout_and_invalid_json_are_explicit_errors(self):
        # Ответ с неверным JSON и отсутствие ответа не превращаются в успешный баланс.
        self.opener.open.side_effect = TimeoutError()
        with self.assertRaises(HTTPException) as raised:
            build_airpay_service(self.env).get_balance()
        self.assertEqual(raised.exception.status_code, 504)
        self.opener.open.side_effect = None
        self.opener.open.return_value.__enter__.return_value.read.return_value = b'<html>error</html>'
        with self.assertRaises(HTTPException) as raised:
            build_airpay_service(self.env).get_balance()
        self.assertEqual(raised.exception.status_code, 502)

    def test_bad_configuration_is_rejected_before_sending_credentials(self):
        # Basic запрещён для HTTP, URL с реквизитами, невалидного таймаута или локального порта.
        for setting in ({'AIRPAY_API_URL': 'http://api.airpay.kz'},
                        {'AIRPAY_API_URL': 'https://user:secret@api.airpay.kz'},
                        {'AIRPAY_TIMEOUT_SEC': 'bad'}, {'AIRPAY_TUNNEL_LOCAL_PORT': '0'}):
            with self.subTest(setting=setting), self.assertRaises(HTTPException):
                build_airpay_service({**self.env, **setting}, local_ui=True).get_balance()
        self.opener.open.assert_not_called()

    def test_provider_error_missing_amounts_and_nonfinite_numbers_are_rejected(self):
        # Не угадываем отсутствующие суммы или валюту и не показываем NaN в UI.
        for payload in ({'result': 1, 'resultMessage': 'secret'}, {'result': False, 'agent': {}},
                        {'result': 0}, {'result': 0, 'agent': {'overdraft': 5000, 'currency': 'RUB'}},
                        balance_payload(balance=None), balance_payload(balance=True),
                        balance_payload(balance='NaN'), balance_payload(overdraft='Infinity'),
                        balance_payload(currency='invalid'), balance_payload(currency=123)):
            with self.subTest(payload=payload), self.assertRaises(HTTPException):
                normalize_airpay_balance(payload)
        self.assertEqual(normalize_airpay_balance(balance_payload(balance='-12.50'))['balance'], -12.5)

    def test_optional_currency_is_not_guessed(self):
        # Документация разрешает пропустить валюту; показываем сумму без выдуманного RUB.
        payload = balance_payload()
        del payload['agent']['currency']
        self.assertEqual(normalize_airpay_balance(payload)['currency'], '')

    def test_services_use_authenticated_post_without_payment_parameters(self):
        # Метод справочника использует тот же защищённый транспорт, сохраняя ID и правила полей.
        payload = {'result': 0, 'services': [service_payload()]}
        self.opener.open.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        result = build_airpay_service(self.env, local_ui=True).get_services()
        request = self.opener.open.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.airpay.kz/AirPayService/api/v20/services')
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.data, b'')
        self.assertTrue(request.get_header('Authorization').startswith('Basic '))
        self.assertEqual(request.get_header('Content-type'), 'application/json')
        self.assertEqual(result['total'], 1)
        item = result['items'][0]
        self.assertEqual(item['service_id'], 'A0002')
        self.assertEqual(item['inputs'][0]['regexp'], r'^\d{10}$')
        self.assertTrue(item['inputs'][0]['required'])
        self.assertEqual(item['displays'][0]['name'], 'fixedAmount')
        self.assertTrue(item['fixed_payment'])
        self.assertEqual(item['type'], 0)
        self.assertIsInstance(self.build_opener.call_args.args[1], TunnelHTTPSHandler)

    def test_catalog_preserves_empty_list_and_optional_parameters(self):
        # Пустой доступный каталог допустим, а отсутствие fixedPayment не означает false.
        self.assertEqual(normalize_airpay_services({'result': 0, 'services': []}), [])
        minimal = {'serviceId': '0007', 'type': 3, 'name': 'Minimal'}
        item = normalize_airpay_services({'result': 0, 'services': [minimal]})[0]
        self.assertEqual(item['service_id'], '0007')
        self.assertEqual(item['inputs'], [])
        self.assertEqual(item['displays'], [])
        self.assertIsNone(item['fixed_payment'])

    def test_bad_catalog_is_not_silently_replaced_with_empty_or_partial_list(self):
        # Дубли ID и повреждённые строки должны дать ошибку вместо частичной выдачи.
        for payload in ({'result': 1, 'services': []}, {'result': 0}, {'result': 0, 'services': {}},
                        {'result': 0, 'services': [service_payload(), service_payload()]},
                        *({'result': 0, 'services': [service_payload(**override)]} for override in (
                            {'serviceId': None}, {'name': ''}, {'type': True}, {'fixedPayment': 'false'},
                            {'inputs': {}}, {'inputs': [{'name': 'account', 'required': 'false'}]},
                        ))):
            with self.subTest(payload=payload), self.assertRaises(HTTPException):
                normalize_airpay_services(payload)

    def test_redirects_never_forward_basic_credentials(self):
        # Запрет действует и для HTTPS-перенаправлений, и для смены протокола.
        build_airpay_service(self.env).get_balance()
        redirects = self.build_opener.call_args.args[2]
        for target in ('https://elsewhere.invalid', 'http://api.airpay.kz'):
            with self.assertRaises(urllib.error.URLError):
                redirects.redirect_request(None, None, 302, '', {}, target)


class AirpayTunnelTests(unittest.TestCase):
    def test_same_ssh_server_uses_airpay_host_and_distinct_port(self):
        # По умолчанию берём сервер Interhub, но forward ведёт именно к Airpay.
        command = build_tunnel_command({'INTERHUB_TUNNEL_HOST': 'test-ssh'})
        self.assertEqual(command[-2:], ['127.0.0.1:3129:api.airpay.kz:443', 'test-ssh'])
        self.assertIn('ExitOnForwardFailure=yes', command)
        self.assertEqual(build_tunnel_command({'AIRPAY_TUNNEL_HOST': 'airpay-ssh', 'AIRPAY_TUNNEL_LOCAL_PORT': '3130'})[-2:],
                         ['127.0.0.1:3130:api.airpay.kz:443', 'airpay-ssh'])

    def test_bad_tunnel_settings_fail_before_ssh(self):
        # Не запускаем SSH с отсутствующим сервером, небезопасным URL или некорректным портом.
        for env in ({}, {'AIRPAY_TUNNEL_HOST': 'ssh', 'AIRPAY_API_URL': 'http://api.airpay.kz'},
                    {'AIRPAY_TUNNEL_HOST': 'ssh', 'AIRPAY_TUNNEL_LOCAL_PORT': 'wrong'}):
            with self.subTest(env=env), self.assertRaises(ValueError):
                build_tunnel_command(env)


class AirpayEndpointTests(unittest.TestCase):
    def test_endpoint_requires_crm_auth_and_filters_response_fields(self):
        # Изолированный FastAPI проверяет зависимость авторизации без запуска БД и фоновых задач.
        def current_user(authorization: str = Header(default='')):
            # В тесте принимаем только CRM Bearer, а не Basic-реквизиты внешнего поставщика.
            if authorization != 'Bearer crm-token':
                raise HTTPException(401, 'Unauthorized')
            return {'username': 'manager'}

        app = FastAPI()
        service = MagicMock()
        service.get_balance.return_value = {**normalize_airpay_balance(balance_payload()), 'agentName': 'private'}
        service.get_services.return_value = {'configured': True, 'total': 1,
            'items': [{**normalize_airpay_services({'result': 0, 'services': [service_payload()]})[0], 'raw': 'private'}]}
        mount_airpay_routes(app, get_current_user=current_user, service=service)
        with TestClient(app) as client:
            self.assertEqual(client.get('/integrations/airpay/balance').status_code, 401)
            service.get_balance.assert_not_called()
            self.assertEqual(client.get('/integrations/airpay/services').status_code, 401)
            service.get_services.assert_not_called()
            response = client.get('/integrations/airpay/balance', headers={'Authorization': 'Bearer crm-token'})
            catalog = client.get('/integrations/airpay/services', headers={'Authorization': 'Bearer crm-token'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'configured': True, 'balance': 0, 'overdraft': 5000, 'currency': 'RUB'})
        self.assertEqual(catalog.status_code, 200)
        self.assertEqual(catalog.json()['items'][0]['service_id'], 'A0002')
        self.assertNotIn('raw', catalog.json()['items'][0])


if __name__ == '__main__':
    unittest.main()
