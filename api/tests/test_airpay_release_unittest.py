"""Проверки комплекта Airpay и команд preflight без Docker, сети и покупки."""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
from scripts.airpay_deploy_preflight import validate, run
from scripts.build_airpay_release import selected


def safe_config():
    # Минимальный раскрытый Compose используется без реальных env-файлов и credentials.
    return {'name': 'supplier-hub-airpay', 'networks': {'existing': {'external': True, 'name': 'test-network'}},
            'services': {name: {'environment': {'DATABASE_URL': 'unused', 'AIRPAY_PAYMENTS_ENABLED': 'false'},
                        'mem_limit': 268435456, 'cpus': 0.5,
                        **({'ports': [{'host_ip': '127.0.0.1', 'target': 8011}]} if name == 'airpay-api' else {})}
                         for name in ('airpay-api', 'airpay-migrate')}}


class AirpayReleaseTests(unittest.TestCase):
    def test_rejects_shared_services_payments_external_port_and_new_database(self):
        # Ошибка в плане должна остановить preflight до каких-либо действий с контейнерами.
        base = safe_config()
        self.assertEqual(validate(base), 'test-network')
        cases = []
        value = deepcopy(base); value['services']['worker'] = {}; cases.append(value)
        value = deepcopy(base); value['services']['airpay-api']['environment']['AIRPAY_PAYMENTS_ENABLED'] = 'true'; cases.append(value)
        value = deepcopy(base); value['services']['airpay-api']['ports'][0]['host_ip'] = '0.0.0.0'; cases.append(value)
        value = deepcopy(base); value['volumes'] = {'postgres': {}}; cases.append(value)
        value = deepcopy(base); value['services']['airpay-api']['depends_on'] = {'postgres': {}}; cases.append(value)
        value = deepcopy(base); value['networks']['existing']['external'] = False; cases.append(value)
        for config in cases:
            with self.assertRaises(ValueError): validate(config)

    def test_preflight_issues_only_config_and_network_inspect(self):
        # Даже успешная проверка не содержит build/up/run и не запускает мигратор.
        with patch('scripts.airpay_deploy_preflight.docker_json', side_effect=[safe_config(), [{'Containers': {'db': {}}}]]) as docker:
            run(Path('/tmp'))
        self.assertEqual([call.args[0] for call in docker.call_args_list], [
            ['compose', '-f', 'docker-compose.airpay.yml', 'config', '--format', 'json'], ['network', 'inspect', 'test-network']])

    def test_archive_has_no_environment_keys_or_dumps(self):
        # В архив входят исходники, но не секреты и не содержимое БД из рабочего каталога.
        for project in ('crm', 'hub'):
            for name in ('.env', '.env.prod', 'api/.env', 'backup.sql', 'private.key', 'api/private.key', 'api/__pycache__/module.pyc'):
                self.assertFalse(selected(name, project), (project, name))
        self.assertTrue(selected('api/domains/airpay_bootstrap.py', 'crm'))
        self.assertTrue(selected('api/airpay_runtime/manifest.json', 'hub'))
        self.assertTrue(selected('db/migrations/runtime/20260923_01_airpay_transactions.sql', 'crm'))
