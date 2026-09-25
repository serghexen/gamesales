"""Неисправный Airpay не останавливает общие маршруты CRM и не включает fallback."""
import ast
import builtins
import logging
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from domains.airpay_bootstrap import mount_airpay_isolated


class AirpayBootstrapTests(unittest.TestCase):
    def start(self, env, broken_import=None):
        # Выполняем настоящий защитный блок app.py без остальных процессов CRM и внешних соединений.
        app = FastAPI()
        @app.get('/integrations/interhub/probe')
        def existing():
            # Маркер ранее зарегистрированного маршрута проверяет сохранность приложения.
            return {'existing': True}
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'app.py').read_text())
        block = next(node for node in tree.body if isinstance(node, ast.Try) and any(
            isinstance(child, ast.ImportFrom) and child.module == 'domains.airpay_bootstrap' for child in node.body))
        scope = dict(app=app, get_current_user=lambda: {'username': 'owner', 'role': 'owner'}, os=MagicMock(environ=env),
                     psycopg=MagicMock(), DB_DSN='unused', JWT_SECRET='test-only-secret', _LOCAL_UI_MODE=True,
                     _SUPPLIER_OFFLINE=False, Depends=Depends, HTTPException=HTTPException, logging=logging)
        native_import = builtins.__import__
        def guarded(name, *args, **kwargs):
            # Имитируем неполную поставку, не удаляя рабочие файлы из репозитория.
            if name == broken_import: raise ImportError('private-secret-must-not-be-logged')
            return native_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=guarded):
            exec(compile(ast.Module(body=[block], type_ignores=[]), 'app.py', 'exec'), scope)
        return app, TestClient(app)

    def test_invalid_backend_and_missing_module_disable_only_airpay(self):
        # Пустой/ошибочный режим, отсутствующий bootstrap и внутренний модуль дают одинаковый безопасный отказ.
        cases = [({'AIRPAY_BACKEND': 'typo'}, None), ({'AIRPAY_BACKEND': ''}, None),
                 ({}, 'domains.airpay_bootstrap'), ({}, 'domains.airpay_repository')]
        for env, missing in cases:
            with self.subTest(env=env, missing=missing), self.assertLogs(level='ERROR') as logs:
                app, client = self.start(env, missing)
            self.assertEqual(client.get('/integrations/interhub/probe').json(), {'existing': True})
            for method, path in [('get', 'balance'), ('post', 'transactions/1/pay'), ('post', 'check')]:
                response = getattr(client, method)('/integrations/airpay/' + path)
                self.assertEqual(response.status_code, 503)
                self.assertNotIn('private-secret', response.text)
            self.assertNotIn('private-secret', ''.join(logs.output))
            self.assertEqual(app.state.airpay_backend, 'unavailable')

    def test_bad_hub_settings_never_register_direct_provider(self):
        # Hub без настроек не превращается в прямого исполнителя CRM.
        with patch('domains.airpay_service.build_airpay_service') as direct, self.assertLogs(level='ERROR'):
            app, client = self.start({'AIRPAY_BACKEND': 'hub'})
        direct.assert_not_called()
        self.assertEqual(client.get('/integrations/airpay/contract').status_code, 503)
        self.assertEqual(client.get('/integrations/interhub/probe').status_code, 200)

    def test_partial_registration_is_discarded(self):
        # Исключение в середине регистрации не оставляет доступный pay или lifecycle worker.
        def broken(candidate, **kwargs):
            # Подмена имитирует частично подключённый опасный маршрут до сбоя сборки.
            candidate.add_api_route('/integrations/airpay/transactions/1/pay', lambda: {'unsafe': True}, methods=['POST'])
            candidate.router.lifespan_context = MagicMock(side_effect=AssertionError('Must not run'))
            raise RuntimeError('setup failed')
        with patch('domains.airpay_api.mount_airpay_routes', side_effect=broken), self.assertLogs(level='ERROR'):
            app, client = self.start({})
        self.assertEqual(client.post('/integrations/airpay/transactions/1/pay').status_code, 503)
        self.assertFalse(app.user_middleware)

    def test_hub_mode_imports_no_direct_worker_and_keeps_shared_lifespan(self):
        # Исполнитель выбирается один раз; действующий lifecycle CRM остаётся прежним.
        app = FastAPI()
        lifecycle = app.router.lifespan_context
        with patch('domains.airpay_service.build_airpay_service') as direct:
            mount_airpay_isolated(app, get_current_user=lambda: {},
                environ={'AIRPAY_BACKEND': 'hub', 'AIRPAY_HUB_URL': 'http://airpay:8011', 'AIRPAY_HUB_CLIENT_ID': 'crm', 'AIRPAY_HUB_CLIENT_KEY': 'k'*32},
                connect=MagicMock(), get_secret=lambda: 'secret', code_secret=lambda: 'secret', local_ui=False, offline=False)
        direct.assert_not_called()
        self.assertIs(app.router.lifespan_context, lifecycle)
        self.assertEqual(app.state.airpay_backend, 'hub')

    def test_valid_crm_registers_routes_without_database_or_supplier_access(self):
        # Успешное подключение сохраняет OpenAPI и не выполняет работу при импорте.
        app, client = self.start({})
        self.assertEqual(client.get('/integrations/airpay/contract').status_code, 200)
        self.assertFalse(client.get('/integrations/airpay/contract').json()['payments_enabled'])
        self.assertIn('/integrations/airpay/transactions/{transaction_id}/pay', client.get('/openapi.json').json()['paths'])
