"""Проверки SSH-маршрута: локальный TCP, исходный TLS-host и отсутствие прямого fallback."""

import os
import ssl
import unittest
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from domains.interhub_service import build_interhub_service
from domains.interhub_ssh_transport import NoTunnelRedirects, TunnelHTTPSConnection, TunnelHTTPSHandler
from scripts.run_interhub_tunnel import build_tunnel_command


class InterhubSshTransportTests(unittest.TestCase):
    def test_ssh_forwards_to_supplier_instead_of_missing_server_proxy(self):
        # Удалённый адрес берём из URL поставщика; устаревший REMOTE_PORT больше не используется.
        with patch.dict(os.environ, {'INTERHUB_API_URL': 'https://api.interhub.ae',
                                     'INTERHUB_TUNNEL_HOST': 'example-ssh',
                                     'INTERHUB_TUNNEL_LOCAL_PORT': '3128',
                                     'INTERHUB_TUNNEL_REMOTE_PORT': '3128'}, clear=True):
            command = build_tunnel_command()
        self.assertEqual(command[-2:], ['127.0.0.1:3128:api.interhub.ae:443', 'example-ssh'])

    def test_tunnel_configuration_rejects_plain_http(self):
        # Нельзя случайно передать токен без TLS через ошибочный адрес поставщика.
        with patch.dict(os.environ, {'INTERHUB_API_URL': 'http://api.interhub.ae',
                                     'INTERHUB_TUNNEL_HOST': 'example-ssh'}, clear=True):
            with self.assertRaises(ValueError):
                build_tunnel_command()

    def test_tls_uses_supplier_name_while_tcp_uses_local_tunnel(self):
        # TCP-адрес и имя сертификата должны различаться: localhost не попадает в SNI.
        context = ssl.create_default_context()
        connection = TunnelHTTPSConnection('api.interhub.ae', tunnel_port=3128, timeout=8, context=context)
        with patch('domains.interhub_ssh_transport.socket.create_connection') as connect, \
             patch.object(context, 'wrap_socket') as wrap:
            connection.connect()
            connect.assert_called_once_with(('127.0.0.1', 3128), 8, None)
            wrap.assert_called_once_with(connect.return_value, server_hostname='api.interhub.ae')
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)

    def test_tls_failure_closes_socket_without_fallback(self):
        # Ошибка сертификата закрывает локальный сокет и не создаёт соединение напрямую.
        context = ssl.create_default_context()
        connection = TunnelHTTPSConnection('api.interhub.ae', tunnel_port=3128, context=context)
        with patch('domains.interhub_ssh_transport.socket.create_connection') as connect, \
             patch.object(context, 'wrap_socket', side_effect=ssl.SSLError('bad certificate')):
            with self.assertRaises(ssl.SSLError):
                connection.connect()
            connect.assert_called_once()
            connect.return_value.close.assert_called_once()

    def test_opener_disables_environment_proxy_and_never_retries_directly(self):
        # Закрытый SSH-туннель остаётся ошибкой, даже если настроен другой HTTP proxy.
        service = build_interhub_service(
            HTTPException=HTTPException, interhub_api_url='https://api.interhub.ae', interhub_token='test',
            timeout_sec=5, ssl_verify=True, ca_cert_path='', proxy_url='http://unused:3128', ssh_tunnel_port=3128,
            calculate_path='/calculate', check_path='/check', deposit_path='/deposit',
        )
        opener = MagicMock()
        opener.open.side_effect = urllib.error.URLError('tunnel unavailable')
        with patch('domains.interhub_service.urllib.request.build_opener', return_value=opener) as build, \
             patch('domains.interhub_service.urllib.request.urlopen') as direct:
            with self.assertRaises(HTTPException) as raised:
                service.get_services()
            self.assertEqual(raised.exception.status_code, 502)
            self.assertEqual(build.call_args.args[0].proxies, {})
            self.assertIsInstance(build.call_args.args[1], TunnelHTTPSHandler)
            direct.assert_not_called()

    def test_redirect_cannot_escape_ssh_or_forward_token(self):
        # Отклоняем и HTTPS-редирект, и смену протокола до передачи следующего запроса.
        for url in ['http://api.interhub.ae/', 'https://elsewhere.invalid/']:
            with self.assertRaises(urllib.error.URLError):
                NoTunnelRedirects().redirect_request(None, None, 302, '', {}, url)
