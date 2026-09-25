"""Восстановление и переоценка без реальных оплат и подключения к поставщику."""
from copy import deepcopy
from datetime import timedelta
import unittest
from unittest.mock import MagicMock

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from domains.airpay_api import mount_airpay_routes
from domains.airpay_jobs import AirpayJobs, AirpayJobStore, hide_codes
from domains.airpay_purchase import now_utc
from tests import test_airpay_batch_unittest as batch_tests


class AirpayWorkflowTests(unittest.TestCase):
    # Переиспользуем фикстуру, не запускаем повторно чужие тесты пачки.
    setUp = batch_tests.AirpayBatchTests.setUp
    prepare = batch_tests.AirpayBatchTests.prepare
    check = batch_tests.AirpayBatchTests.check
    def test_renewal_replaces_only_unpaid_and_is_idempotent(self):
        # Оплаченная позиция и её ID остаются прежними; остаток проходит новое подтверждение.
        self.check()
        rows = list(self.repo.rows.values())
        rows[0].update(state='paid', pin_code='TEST-SAVED')
        rows[1]['expires_at'] = now_utc() - timedelta(minutes=1)
        renewed = self.batch.renew('owner', self.id)
        self.assertEqual(renewed['batch']['quantity'], 2)
        self.assertEqual(self.repo.rows[rows[0]['agent_transaction_id']]['pin_code'], 'TEST-SAVED')
        self.assertNotIn('replacement_key', self.repo.rows[rows[0]['agent_transaction_id']])
        self.assertTrue(all(row['replacement_key'] for row in rows[1:]))
        with self.assertRaises(HTTPException):
            self.batch.pay('owner', self.id, '37.50')
        again = self.batch.renew('owner', self.id)
        self.assertEqual(again['draft']['agent_transaction_id'], renewed['draft']['agent_transaction_id'])
        self.assertEqual(len(self.repo.rows), 5)
        checked = self.batch.check('owner', renewed['draft']['preparation_token'])
        self.assertEqual(checked['purchase_amount'], '25.00')
        self.service.pay.assert_not_called()

    def test_single_remainder_keeps_group_and_pending_pay_cannot_be_replaced(self):
        # Последний один ключ тоже имеет связь продолжения, а неизвестный платёж запрещает замену.
        self.check()
        rows = list(self.repo.rows.values())
        rows[0]['state'] = 'processing'
        with self.assertRaises(HTTPException):
            self.batch.renew('owner', self.id)
        self.assertEqual(len(self.repo.rows), 3)
        rows[0]['state'] = rows[1]['state'] = 'paid'
        renewed = self.batch.renew('owner', self.id)
        self.assertEqual(renewed['batch']['quantity'], 1)
        self.assertEqual(self.batch.check('owner', renewed['draft']['preparation_token'])['purchase_amount'], '12.50')
        self.service.pay.assert_not_called()

    def test_progress_is_readable_while_batch_is_locked(self):
        # История читает сохранённое состояние без конкуренции за сетевой lock покупки.
        self.check()
        child = list(self.repo.rows)[1]
        with self.repo.batch_locked('owner', self.id):
            self.assertEqual(self.batch.read('owner', child)['quantity'], 3)
        self.service.pay.assert_not_called()

    def test_history_hides_codes_and_reveal_is_audited_without_supplier(self):
        # Открытие истории не раскрывает секрет; отдельное действие читает только локальную запись.
        self.check()
        self.repo.rows[self.id].update(state='paid', pin_code='SAVED-SECRET')
        app = FastAPI()
        mount_airpay_routes(app, get_current_user=lambda: {'role': 'owner', 'username': 'owner'}, service=self.service,
                           repository=self.repo, get_secret=self.preparation.get_secret)
        client = TestClient(app)
        history = client.get('/integrations/airpay/transactions').json()
        self.assertNotIn('SAVED-SECRET', str(history))
        self.assertTrue(history['items'][0]['result_available'])
        result = client.post(f'/integrations/airpay/transactions/{self.id}/result').json()
        self.assertEqual(result['value'], 'SAVED-SECRET')
        self.assertEqual(self.repo.accesses, [('owner', self.id)])
        self.service.get_voucher.assert_not_called()
        self.service.pay.assert_not_called()

    def test_worker_resumes_processing_without_buying_next_key(self):
        # Возобновлённое задание останавливается на прежнем processing, не повторяет pay само.
        self.check()
        self.repo.rows[self.id]['state'] = 'processing'
        jobs = AirpayJobs(MagicMock(), self.preparation, self.purchase, self.batch)
        result = jobs.execute({'created_by': 'owner', 'transaction_id': self.id, 'action': 'pay', 'payload': {'confirmed_amount': '37.50'}}, MagicMock())
        self.assertEqual(result['state'], 'processing')
        self.service.pay.assert_not_called()
        self.service.payments_enabled = False
        jobs.run_one()
        self.assertEqual(jobs.store.run_one.call_args.args[0], ('check', 'renew'))

    def test_repeated_single_check_does_not_bypass_result_access_audit(self):
        # Повтор старого check после оплаты не должен раскрывать сохранённый код через карточку transaction.
        draft = self.prepare(1)
        self.purchase.check('owner', draft['preparation_token'])
        self.repo.rows[self.id].update(state='paid', pin_code='SAVED-PRIVATE')
        app = FastAPI()
        mount_airpay_routes(app, get_current_user=lambda: {'role': 'owner', 'username': 'owner'}, service=self.service,
                           repository=self.repo, get_secret=self.preparation.get_secret)
        response = TestClient(app).post('/integrations/airpay/check', json={'preparation_token': draft['preparation_token']})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('SAVED-PRIVATE', response.text)
        self.assertTrue(response.json()['transaction']['result_available'])
        self.service.pay.assert_not_called()

    def test_enqueue_returns_before_check_and_active_job_is_read_only(self):
        # POST сохраняет задание; работа поставщика отсутствует до отдельного запуска worker.
        draft = self.prepare()
        store = MagicMock()
        store.enqueue.return_value = {'job_id': 'd2a900f9-f0c1-4b32-9687-105fd9fd45f1', 'state': 'queued', 'progress': 0}
        app = FastAPI()
        mount_airpay_routes(app, get_current_user=lambda: {'role': 'owner', 'username': 'owner'}, service=self.service,
                           repository=self.repo, get_secret=self.preparation.get_secret, job_store=store)
        client = TestClient(app)
        response = client.post('/integrations/airpay/check', json={'preparation_token': draft['preparation_token']})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['job']['state'], 'queued')
        self.service.check.assert_not_called()
        self.service.pay.assert_not_called()


class AirpayJobStoreTests(unittest.TestCase):
    def test_job_result_has_no_plaintext_code_and_datetime_is_serializable(self):
        # Worker фиксирует безопасный JSON и освобождает межпроцессную блокировку.
        connection = MagicMock()
        conn = connection.return_value.__enter__.return_value
        conn.execute.return_value.fetchall.return_value = [{'id': 'job'}]
        conn.execute.return_value.fetchone.side_effect = [{'ok': True}, {'id': 'job', 'action': 'check', 'state': 'queued'}]
        store = AirpayJobStore(connection)
        self.assertTrue(store.run_one(('check',), lambda row, progress: {'created_at': now_utc(), 'pin_code': 'SECRET'}))
        calls = conn.execute.call_args_list
        update = next(call for call in calls if "state='succeeded'" in call.args[0])
        self.assertNotIn('pin_code', update.args[1][0].obj)
        self.assertIsInstance(update.args[1][0].obj['created_at'], str)
        self.assertIn('pg_advisory_unlock', calls[-1].args[0])

    def test_codes_are_removed_recursively(self):
        # Результат пачки не обходит защиту списка через вложенные карточки.
        value = {'items': [{'pin_code': 'SECRET', 'result_available': True}]}
        self.assertEqual(hide_codes(deepcopy(value)), {'items': [{'result_available': True}]})
