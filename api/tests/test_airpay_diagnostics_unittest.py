"""Диагностика каталога: только подменённые service/check, без сетевых оплат."""
from copy import deepcopy
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from domains.airpay_api import mount_airpay_routes
from domains.airpay_diagnostics import AirpayDiagnostics, diagnostic_payload, diagnostic_result

SERVICE = {'service_id': 'A1', 'title': 'Example', 'fixed_payment': True,
           'inputs': [{'name': 'account', 'title': 'Введите Email', 'required': True, 'regexp': r'.+@.+\..+'}]}


class DiagnosticPayloadTests(unittest.TestCase):
    def test_email_only_and_no_amount_or_purchase_type(self):
        # Фиксированная цена не объявляется ваучером; формируется только тело check.
        payload, reason = diagnostic_payload(SERVICE)
        self.assertEqual(payload, {'serviceId': 'A1', 'account': 'seller@homtech.ru'})
        self.assertEqual(reason, '')

    def test_skips_player_id_variable_amount_and_extra_required_fields(self):
        # Не создаём фиктивные аккаунты и не угадываем сумму для произвольных услуг.
        player = deepcopy(SERVICE); player['inputs'][0]['title'] = 'Номер аккаунта'
        extra = deepcopy(SERVICE); extra['inputs'].append({'name': 'server', 'title': 'Сервер', 'required': True, 'regexp': ''})
        for service in (player, extra, {**SERVICE, 'fixed_payment': False}, {**SERVICE, 'fixed_payment': None}, {**SERVICE, 'inputs': []}):
            with self.subTest(service=service):
                payload, reason = diagnostic_payload(service)
                self.assertIsNone(payload)
                self.assertTrue(reason)

    def test_email_must_pass_provider_regexp(self):
        # Одного слова Email недостаточно, если поставщик ограничивает формат другим выражением.
        service = deepcopy(SERVICE); service['inputs'][0]['regexp'] = r'\d+'
        self.assertIsNone(diagnostic_payload(service)[0])

    def test_result_keeps_204_and_does_not_leak_arbitrary_payload(self):
        # Для обращения к поддержке достаточно кода, сообщения и ID, без секретов из произвольных полей.
        value = diagnostic_result({'result': 204, 'resultMessage': 'Валюта', 'transactionId': 123, 'secret': 'hidden', 'displays': {'pinCode': 'hidden'}})
        self.assertEqual(value['state'], 'rejected')
        self.assertEqual(value['provider_transaction_id'], '123')
        self.assertEqual(value['result'], 204)
        self.assertNotIn('hidden', str(value))

    def test_fixed_price_never_comes_from_conversion_amount(self):
        # Успешный check без fixedPrice не превращает finalAmount в закупочную цену.
        value = diagnostic_result({'result': 0, 'finalAmount': .12, 'currency': 'USD'})
        self.assertEqual(value['state'], 'ok')
        self.assertNotIn('fixed_price', value)
        self.assertIn('price_warning', value)
        value = diagnostic_result({'result': 0, 'fixedPrice': 12.5, 'displays': {'fixedPrice': 13}})
        self.assertNotIn('fixed_price', value)
        self.assertIn('price_warning', value)
        self.assertEqual(diagnostic_result({'result': 0, 'displays': {'fixedPrice': '654.03'}})['fixed_price'], '654.03')
        self.assertEqual(diagnostic_result({'result': 1})['state'], 'pending_response')
        self.assertEqual(diagnostic_result({'result': True})['state'], 'invalid_response')


class DiagnosticStepTests(unittest.TestCase):
    def setUp(self):
        # Подменяем БД и поставщика до создания исполнителя, не читая настройки окружения.
        self.conn = MagicMock()
        self.store = MagicMock()
        self.store.locked.return_value.__enter__.return_value = self.conn
        self.run_id = uuid4()
        self.store.read.return_value = {'run': {'state': 'active'}}
        self.get_service = MagicMock(return_value=SERVICE)
        self.check = MagicMock(return_value={'result': 204, 'resultMessage': 'Валюта'})
        self.runner = AirpayDiagnostics(self.store, get_services=MagicMock(), get_service=self.get_service, check=self.check)
        def query(sql, params=()):
            # Ответы имитируют один свободный шаг; сохранение остаётся наблюдаемым до внешнего check.
            cursor = MagicMock()
            cursor.fetchone.return_value = {'position': 0, 'service_id': 'A1'} if "state='pending' ORDER BY" in sql else None
            return cursor
        self.conn.execute.side_effect = query

    def test_records_running_before_check_and_never_creates_payment(self):
        # Даже отказ 204 сохраняется как диагностический результат вне таблицы покупок.
        def check(payload):
            statements = [call.args[0] for call in self.conn.execute.call_args_list]
            self.assertTrue(any("state='running',started_at" in sql for sql in statements))
            self.assertEqual(payload['account'], 'seller@homtech.ru')
            self.assertIsInstance(payload['agentTransactionId'], int)
            self.assertNotIn('amountTo', payload)
            return {'result': 204, 'resultMessage': 'Валюта'}
        self.check.side_effect = check
        self.runner.step('owner', self.run_id)
        self.check.assert_called_once()
        sql = ' '.join(call.args[0] for call in self.conn.execute.call_args_list)
        self.assertNotIn('airpay_transactions', sql)
        saved = next(call.args[1][1].obj for call in self.conn.execute.call_args_list if 'SET state=%s,report=' in call.args[0])
        self.assertEqual(saved['result'], 204)

    def test_missing_fields_skip_check_and_transport_failure_is_saved(self):
        # Необходимость ручного аккаунта и ошибка транспорта не становятся отказом оплаты.
        self.get_service.return_value = {**SERVICE, 'fixed_payment': False}
        self.runner.step('owner', self.run_id)
        self.check.assert_not_called()
        self.get_service.side_effect = OSError('secret-address')
        self.runner.step('owner', self.run_id)
        saved = [call.args[1][1].obj for call in self.conn.execute.call_args_list if 'SET state=%s,report=' in call.args[0]][-1]
        self.assertEqual(saved['state'], 'transport_error')
        self.assertNotIn('secret-address', str(saved))

    def test_finished_or_foreign_run_does_not_call_provider(self):
        # Владелец проверяется до сети, завершённый запуск не выполняется повторно.
        self.store.read.return_value = {'run': {'state': 'completed'}}
        self.runner.step('owner', self.run_id)
        self.store.read.side_effect = HTTPException(404, 'not found')
        with self.assertRaises(HTTPException): self.runner.step('other', self.run_id)
        self.get_service.assert_not_called()
        self.check.assert_not_called()

    def test_no_pending_items_does_not_repeat_interrupted_check(self):
        # После потери процесса неопределённая позиция помечается прерванной, повторный check не отправляется.
        self.conn.execute.side_effect = None
        self.conn.execute.return_value.fetchone.return_value = None
        self.runner.step('owner', self.run_id)
        self.get_service.assert_not_called()
        self.check.assert_not_called()


class DiagnosticRouteTests(unittest.TestCase):
    def test_owner_only_and_independent_of_payment_permission(self):
        # Проверки доступны владельцу при выключенной оплате; менеджер не читает даже отчёт.
        for role, expected in [('owner', 200), ('manager', 403)]:
            app = FastAPI()
            provider = MagicMock(payments_enabled=False)
            repo = MagicMock()
            mount_airpay_routes(app, get_current_user=lambda: {'role': role, 'username': 'test'}, service=provider, repository=repo, offline=True)
            with patch('domains.airpay_api.AirpayDiagnosticStore') as store:
                store.return_value.read.return_value = {'run': None}
                with TestClient(app) as client:
                    response = client.get('/integrations/airpay/diagnostics')
                self.assertEqual(response.status_code, expected)
                provider.check.assert_not_called()
                provider.pay.assert_not_called()
                provider.get_voucher.assert_not_called()


class DiagnosticStorageTests(unittest.TestCase):
    def test_advisory_lock_blocks_concurrent_scans_and_is_released_on_error(self):
        # Даже разные API-процессы должны сериализовать диагностические вызовы через PostgreSQL.
        from domains.airpay_diagnostics import AirpayDiagnosticStore
        connect = MagicMock()
        conn = connect.return_value.__enter__.return_value
        conn.execute.return_value.fetchone.return_value = {'acquired': False}
        store = AirpayDiagnosticStore(connect)
        with self.assertRaises(HTTPException):
            with store.locked(): self.fail('lock should block')
        conn.execute.return_value.fetchone.return_value = {'acquired': True}
        with self.assertRaises(ValueError):
            with store.locked(): raise ValueError('test')
        self.assertIn('pg_advisory_unlock', conn.execute.call_args.args[0])

    def test_repeated_start_reads_existing_run_without_fetching_catalog(self):
        # Потеря ответа запуска не должна перечитывать каталог и создавать новые ID проверок.
        store = MagicMock()
        conn = store.locked.return_value.__enter__.return_value
        conn.execute.return_value.fetchone.return_value = {'id': 'existing'}
        store.read.return_value = {'run': {'id': 'existing'}}
        catalog = MagicMock()
        runner = AirpayDiagnostics(store, get_services=catalog, get_service=MagicMock(), check=MagicMock())
        self.assertEqual(runner.start('owner', uuid4()), store.read.return_value)
        catalog.assert_not_called()

    def test_storage_read_filters_owner_and_keeps_big_ids_as_strings(self):
        # Отчёт нельзя взять по чужому UUID, а длинный ID не теряет точность JavaScript.
        from domains.airpay_diagnostics import AirpayDiagnosticStore
        conn = MagicMock()
        run_id = uuid4()
        conn.execute.return_value.fetchone.return_value = {'id': run_id, 'created_by': 'owner', 'state': 'active'}
        conn.execute.return_value.fetchall.return_value = [{'report': {'result': 204}, 'service_id': 'A1', 'title': 'Example',
            'state': 'rejected', 'agent_transaction_id': 9223372036854775800, 'started_at': None, 'finished_at': None}]
        value = AirpayDiagnosticStore(MagicMock()).read('owner', run_id, conn)
        self.assertEqual(value['run']['items'][0]['agent_transaction_id'], '9223372036854775800')
        self.assertEqual(value['run']['processed'], 1)
        self.assertEqual(conn.execute.call_args_list[0].args[1], ('owner', run_id))
        conn.execute.return_value.fetchone.return_value = None
        with self.assertRaises(HTTPException) as error:
            AirpayDiagnosticStore(MagicMock()).read('other', run_id, conn)
        self.assertEqual(error.exception.status_code, 404)
