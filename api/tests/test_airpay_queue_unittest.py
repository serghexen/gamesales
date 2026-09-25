"""Сбой исполнителя не является разрешением повторить платёжное действие."""
from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock
from uuid import uuid4
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from domains.airpay_jobs import AirpayJobStore, AirpayJobs, INTERRUPTED
from domains.airpay_api import mount_airpay_routes
from domains.airpay_queue import queue_diagnostics


class AirpayQueueTests(unittest.TestCase):
    def store(self, action, state):
        # Независимые результаты SQL позволяют проверить развилки между lock, чтением и исполнением.
        connection = MagicMock()
        conn = connection.return_value.__enter__.return_value
        row = {'id': str(uuid4()), 'action': action, 'state': state}
        conn.execute.return_value.fetchall.return_value = [{'id': row['id']}]
        conn.execute.return_value.fetchone.side_effect = [{'ok': True}, row]
        return AirpayJobStore(connection), conn, row

    def test_interrupted_sensitive_actions_never_execute_even_when_payments_disabled(self):
        # Даже после сохранённого успеха или частичной пачки прежнее running завершаем без повтора.
        for action in ('pay', 'reconcile', 'voucher'):
            for actions in (('check', 'renew'), ('check', 'renew', 'pay', 'reconcile', 'voucher')):
                store, conn, row = self.store(action, 'running')
                execute = MagicMock(side_effect=AssertionError('No provider call'))
                self.assertTrue(store.run_one(actions, execute))
                execute.assert_not_called()
                updates = [call for call in conn.execute.call_args_list if "state='failed'" in call.args[0]]
                self.assertEqual(len(updates), 1)
                self.assertEqual(updates[0].args[1], (INTERRUPTED, row['id']))
                self.assertIn('pg_advisory_unlock', conn.execute.call_args_list[-1].args[0])

    def test_running_safe_action_resumes_but_queued_paid_action_respects_flag(self):
        # Проверка восстанавливается; новое платёжное задание не запускается при запрете.
        store, conn, _ = self.store('check', 'running')
        execute = MagicMock(return_value={'success': True})
        self.assertTrue(store.run_one(('check', 'renew'), execute))
        execute.assert_called_once()
        store, conn, _ = self.store('pay', 'queued')
        execute = MagicMock()
        self.assertFalse(store.run_one(('check',), execute))
        execute.assert_not_called()

    def test_new_confirmed_job_runs_once_and_persists_progress(self):
        # Подтверждённое queued действие исполняется один раз; результат не раскрывает код.
        store, conn, _ = self.store('pay', 'queued')
        def execute(row, progress):
            # Прогресс имитирует сохранение одной позиции без внешнего поставщика.
            progress(1)
            return {'pin_code': 'PRIVATE', 'paid_quantity': 1}
        self.assertTrue(store.run_one(('pay',), execute))
        result = next(call for call in conn.execute.call_args_list if "state='succeeded'" in call.args[0])
        self.assertEqual(result.args[1][0].obj, {'paid_quantity': 1})

    def test_locked_first_page_does_not_starve_next_job(self):
        # За 32 занятыми заданиями читается следующая страница по стабильному курсору.
        connection = MagicMock()
        conn = connection.return_value.__enter__.return_value
        stamp = datetime.now(timezone.utc)
        rows = [{'id': str(uuid4()), 'created_at': stamp} for _ in range(33)]
        conn.execute.return_value.fetchall.side_effect = [rows[:32], rows[32:]]
        conn.execute.return_value.fetchone.side_effect = [{'ok': False}] * 32 + [{'ok': True}, {**rows[32], 'state': 'queued', 'action': 'check'}]
        execute = MagicMock(return_value={})
        self.assertTrue(AirpayJobStore(connection).run_one(('check',), execute, owner='test-owner'))
        execute.assert_called_once()
        selects = [call for call in conn.execute.call_args_list if 'SELECT id,created_at' in call.args[0]]
        self.assertEqual(len(selects), 2)
        self.assertEqual(selects[1].args[1][-3:], (stamp, stamp, rows[31]['id']))
        self.assertEqual(selects[1].args[1][2:4], ('test-owner', 'test-owner'))

    def test_shutdown_stops_before_next_position(self):
        # Начавшаяся позиция сохраняется, затем запрос остановки не разрешает следующую.
        purchase, batch = MagicMock(), MagicMock()
        jobs = AirpayJobs(MagicMock(), MagicMock(), purchase, batch)
        def operation(owner, transaction_id, amount, progress):
            # Подмена изображает остановку сразу после сохранения первой позиции.
            jobs.stop_event.set()
            progress(1)
            self.fail('Should not start another position')
        batch.pay.side_effect = operation
        with self.assertRaises(HTTPException):
            jobs.execute({'created_by': 'owner', 'transaction_id': 1, 'action': 'pay', 'payload': {'confirmed_amount': '10'}}, MagicMock())
        batch.pay.assert_called_once()
        batch.reset_mock()
        with self.assertRaises(HTTPException):
            jobs.execute({'created_by': 'owner', 'transaction_id': 1, 'action': 'pay', 'payload': {}}, MagicMock())
        batch.pay.assert_not_called()

    def test_diagnostics_is_read_only_and_owner_scoped(self):
        # Чтение pg_locks лишь различает потерянный и ещё занятый worker, не освобождая блокировки.
        connection = MagicMock()
        conn = connection.return_value.__enter__.return_value
        conn.execute.return_value.fetchone.return_value = {'queued': 1, 'running': 2, 'stale': 1, 'blocked_by_config': 1, 'failed_24h': 1}
        conn.execute.return_value.fetchall.return_value = [
            {'state': 'running', 'action': 'pay', 'stale': True, 'worker_lock_held': False},
            {'state': 'running', 'action': 'pay', 'stale': True, 'worker_lock_held': True},
            {'state': 'queued', 'action': 'pay', 'stale': False, 'worker_lock_held': False},
            {'state': 'failed', 'action': 'check', 'stale': False, 'worker_lock_held': False}]
        report = queue_diagnostics(connection, 'alice', False)
        self.assertEqual([row['reason'] for row in report['items']], ['interrupted', 'stale', 'payments_disabled', 'failed'])
        for call in conn.execute.call_args_list:
            self.assertTrue(call.args[0].lstrip().startswith('SELECT'))
            self.assertIn('alice', call.args[1])
            self.assertNotIn('payload', call.args[0])

    def test_diagnostics_api_requires_owner_and_never_executes_worker(self):
        # Даже пустой журнал читается только владельцем, без вызова execute/run_one.
        for role, expected in [('owner', 200), ('seller', 403)]:
            store, service = MagicMock(), MagicMock(payments_enabled=False)
            store.diagnostics.return_value = {'summary': {}, 'items': []}
            app = FastAPI()
            mount_airpay_routes(app, get_current_user=lambda: {'role': role, 'username': 'alice'}, service=service,
                                job_store=store, repository=MagicMock())
            response = TestClient(app).get('/integrations/airpay/queue')
            self.assertEqual(response.status_code, expected)
            if role == 'owner': store.diagnostics.assert_called_once_with('alice', False)
            else: store.diagnostics.assert_not_called()
            store.run_one.assert_not_called()
            self.assertEqual(service.mock_calls, [])

    def test_cancel_checks_owner_lock_and_state_without_touching_purchase(self):
        # Отмена не может перегнать worker или завершить чужое/уже запущенное задание.
        connection = MagicMock()
        conn = connection.return_value.__enter__.return_value
        store = AirpayJobStore(connection)
        conn.execute.return_value.fetchone.return_value = None
        with self.assertRaises(HTTPException) as err: store.cancel('alice', uuid4())
        self.assertEqual(err.exception.status_code, 404)
        row = dict(id=uuid4(), action='pay', state='queued', transaction_id=1, progress=0, result=None, error='', error_status=None)
        conn.execute.return_value.fetchone.side_effect = [row, {'ok': False}]
        with self.assertRaises(HTTPException) as err: store.cancel('alice', row['id'])
        self.assertEqual(err.exception.status_code, 409)
        conn.execute.return_value.fetchone.side_effect = [row, {'ok': True}, {**row, 'state': 'running'}]
        with self.assertRaises(HTTPException) as err: store.cancel('alice', row['id'])
        self.assertEqual(err.exception.status_code, 409)
        cancelled = {**row, 'state': 'failed', 'error': 'Запуск задания отменён владельцем. Сохранённые оплаты и результаты не изменены.'}
        conn.execute.return_value.fetchone.side_effect = [row, {'ok': True}, row, cancelled]
        self.assertEqual(store.cancel('alice', row['id'])['state'], 'failed')
        conn.execute.return_value.fetchone.side_effect = [cancelled, {'ok': True}, cancelled]
        self.assertEqual(store.cancel('alice', row['id'])['state'], 'failed')
        for call in conn.execute.call_args_list:
            self.assertNotIn('airpay_transactions', call.args[0])
