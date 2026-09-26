"""Пачки Airpay проверяются без внешней сети, платежей и БД пользователя."""
from datetime import timedelta
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi import HTTPException, FastAPI
from fastapi.testclient import TestClient
from domains.airpay_api import mount_airpay_routes
from domains.airpay_batch import AirpayBatch
from domains.airpay_preparation import AirpayPreparation
from domains.airpay_purchase import AirpayPurchase, now_utc
from domains.airpay_repository import AirpayRepository
from tests.test_airpay_purchase_unittest import MemoryJournal


class AirpayBatchTests(unittest.TestCase):
    def setUp(self):
        # Каждый внешний вызов отвечает только через mock с ID текущей операции.
        self.service = MagicMock(payments_enabled=True)
        self.service.get_service.return_value = dict(service_id='A1', title='Voucher', inputs=[], displays=[], fixed_payment=True)
        self.service.get_balance.return_value = dict(configured=True, balance=1000, currency='RUB')
        self.service.check.side_effect = lambda body: dict(result=0, agentTransactionId=body['agentTransactionId'], transactionId=10, fixedPrice=12.50)
        self.service.pay.side_effect = lambda body: dict(result=0, agentTransactionId=body['agentTransactionId'], transactionId=11)
        self.service.get_voucher.side_effect = lambda body: dict(result=0, agentTransactionId=body['agentTransactionId'], transactionId=11, displays={'pinCode': str(body['agentTransactionId'])})
        self.repo = MemoryJournal()
        self.preparation = AirpayPreparation(self.service, lambda: 'long-test-signing-secret-for-airpay', self.repo)
        self.purchase = AirpayPurchase(self.service, self.repo, self.preparation)
        self.batch = AirpayBatch(self.service, self.repo, self.preparation, self.purchase)
        self.key = str(uuid4())

    def prepare(self, quantity=3):
        # Один ключ подготовки воспроизводит одну и ту же группу уникальных платежей.
        self.draft = self.preparation.prepare('owner', 'A1', {'account': 'seller@example.com'}, preparation_key=self.key, quantity=quantity)
        self.id = int(self.draft['agent_transaction_id'])
        return self.draft

    def check(self):
        # Подготовка каждого экземпляра сохраняется отдельно; сумма подтверждения агрегируется точно.
        self.prepare()
        return self.batch.check('owner', self.draft['preparation_token'])

    def test_check_total_and_separate_payments_and_vouchers(self):
        # Общее количество не отправляется в Airpay и не заменяется увеличенной суммой одного pay.
        result = self.check()
        self.assertEqual(result['quantity'], 3)
        self.assertEqual(result['purchase_amount'], '37.50')
        self.assertEqual(result['unit_amount'], '12.50')
        self.assertTrue(result['purchase_ready'])
        self.assertEqual(self.service.check.call_count, 3)
        self.service.pay.assert_not_called()
        paid = self.batch.pay('owner', self.id, '37.50')
        self.assertEqual(paid['paid_quantity'], 3)
        bodies = [call.args[0] for call in self.service.pay.call_args_list]
        self.assertEqual(len({body['agentTransactionId'] for body in bodies}), 3)
        for body in bodies:
            self.assertEqual(body['amountTo'], 12.5)
            self.assertNotIn('quantity', body)
            self.assertNotIn('_airpay_batch', body)
        self.assertEqual(self.batch.vouchers('owner', self.id)['received_quantity'], 3)
        self.batch.pay('owner', self.id, '37.50')
        self.batch.vouchers('owner', self.id)
        self.assertEqual(self.service.pay.call_count, 3)
        self.assertEqual(self.service.get_voucher.call_count, 3)

    def test_repeated_prepare_check_and_changed_quantity(self):
        # Потеря ответа не создаёт новые записи, а смена количества требует нового ключа подготовки.
        first = self.check()
        self.prepare()
        self.assertEqual(len(self.repo.rows), 3)
        second = self.batch.check('owner', self.draft['preparation_token'])
        self.assertEqual(first['batch']['batch_id'], second['batch']['batch_id'])
        self.assertEqual(self.service.check.call_count, 3)
        for quantity in (1, 2, 4):
            with self.assertRaises(HTTPException):
                self.prepare(quantity)

    def test_invalid_quantity_and_topup_are_rejected(self):
        # Прямой серверный вызов не обходит целочисленный лимит и запрет пакетного пополнения.
        for quantity in (0, 21, -1, 1.5, True, '2'):
            with self.subTest(quantity=quantity), self.assertRaises(HTTPException):
                self.prepare(quantity)
        self.service.get_service.return_value['fixed_payment'] = False
        with self.assertRaises(HTTPException):
            self.preparation.prepare('owner', 'A1', {'account': 'x'}, amount_to='10', quantity=2)
        self.assertEqual(len(self.repo.rows), 0)

    def test_overdraft_covers_batch_and_only_unpaid_remainder(self):
        # Кредит покрывает всю пачку; продолжение проверяет только ещё не оплаченные позиции.
        self.service.get_balance.return_value.update(balance=0, overdraft=37.5)
        result = self.check()
        self.assertTrue(result['purchase_ready'])
        ids = [int(row['agent_transaction_id']) for row in result['batch']['items']]
        self.repo.rows[ids[0]]['state'] = 'paid'
        self.service.get_balance.return_value['balance'] = -12.5
        self.assertEqual(self.batch.pay('owner', self.id, '37.50')['paid_quantity'], 3)
        self.assertEqual([call.args[0]['agentTransactionId'] for call in self.service.pay.call_args_list], ids[1:])
        self.service.get_voucher.assert_not_called()

    def test_credit_insufficient_for_total_and_reduced_after_check(self):
        # На один ключ кредита достаточно, но общая сумма также должна укладываться в лимит.
        self.service.get_balance.return_value.update(balance=0, overdraft=37.49)
        self.assertFalse(self.check()['purchase_ready'])
        self.service.pay.assert_not_called()
        self.setUp()
        self.service.get_balance.return_value.update(balance=0, overdraft=37.5)
        self.assertTrue(self.check()['purchase_ready'])
        self.service.get_balance.return_value['overdraft'] = 37.49
        with self.assertRaises(HTTPException): self.batch.pay('owner', self.id, '37.50')
        self.service.pay.assert_not_called()

    def test_total_balance_and_confirmation_enforced_before_pay(self):
        # Депозита может хватить на один ключ, но не на весь заказ.
        self.service.get_balance.return_value['balance'] = 20
        result = self.check()
        self.assertFalse(result['purchase_ready'])
        self.assertIn('всего количества', result['purchase_block_reason'])
        with self.assertRaises(HTTPException):
            self.batch.pay('owner', self.id, '37.50')
        self.service.get_balance.return_value['balance'] = 1000
        with self.assertRaises(HTTPException):
            self.batch.pay('owner', self.id, '12.50')
        with self.assertRaises(HTTPException):
            self.purchase.pay('owner', self.id, '12.50')
        self.service.pay.assert_not_called()

    def test_unknown_payment_stops_next_keys_and_recovery_never_rebuys_paid(self):
        # Временный статус останавливает пачку; после сверки продолжение пропускает уже оплаченные позиции.
        result = self.check()
        ids = [int(row['agent_transaction_id']) for row in result['batch']['items']]
        self.service.pay.side_effect = lambda body: dict(result=1 if body['agentTransactionId'] == ids[1] else 0,
                                                       agentTransactionId=body['agentTransactionId'], transactionId=11)
        pending = self.batch.pay('owner', self.id, '37.50')
        self.assertEqual(pending['state'], 'processing')
        self.assertEqual(self.service.pay.call_count, 2)
        self.batch.pay('owner', self.id, '37.50')
        self.assertEqual(self.service.pay.call_count, 2)
        self.repo.rows[ids[1]]['next_attempt_at'] = now_utc() - timedelta(seconds=1)
        self.service.pay.side_effect = lambda body: dict(result=0, agentTransactionId=body['agentTransactionId'], transactionId=11)
        self.purchase.reconcile('owner', ids[1])
        self.assertEqual(self.batch.read('owner', ids[2])['state'], 'partial')
        # Новый координатор после перезапуска продолжает те же строки журнала.
        restored = AirpayBatch(self.service, self.repo, self.preparation, self.purchase)
        self.assertEqual(restored.pay('owner', self.id, '37.50')['paid_quantity'], 3)
        paid_ids = [call.args[0]['agentTransactionId'] for call in self.service.pay.call_args_list]
        self.assertEqual(paid_ids, [ids[0], ids[1], ids[1], ids[2]])

    def test_failure_expiry_owner_and_lock_guards(self):
        # Отказ не покупает следующую позицию; чужой пользователь и параллельный запрос не получают доступ.
        self.check()
        with self.assertRaises(HTTPException):
            self.batch.read('other', self.id)
        with self.repo.batch_locked('owner', self.id), self.assertRaises(HTTPException):
            self.batch.pay('owner', self.id, '37.50')
        rows = list(self.repo.rows.values())
        rows[-1]['expires_at'] = now_utc() - timedelta(seconds=1)
        with self.assertRaises(HTTPException):
            self.batch.pay('owner', self.id, '37.50')
        self.service.pay.assert_not_called()
        rows[-1]['expires_at'] = now_utc() + timedelta(minutes=1)
        self.service.pay.side_effect = lambda body: dict(result=7, agentTransactionId=body['agentTransactionId'])
        self.assertEqual(self.batch.pay('owner', self.id, '37.50')['state'], 'failed')
        self.batch.pay('owner', self.id, '37.50')
        self.assertEqual(self.service.pay.call_count, 1)

    def test_interrupted_preparation_recovers_all_twenty_distinct_ids(self):
        # После обрыва между INSERT повтор достраивает пачку, сохраняя уже выданные номера.
        create = self.repo.create
        count = 0
        def interrupt_once(*args):
            # Имитируем единственный сбой записи перед третьей позицией.
            nonlocal count
            count += 1
            if count == 3:
                raise RuntimeError('database unavailable')
            return create(*args)
        self.repo.create = interrupt_once
        with self.assertRaises(RuntimeError):
            self.prepare(20)
        saved_ids = set(self.repo.rows)
        self.repo.create = create
        self.prepare(20)
        self.assertEqual(len(self.repo.rows), 20)
        self.assertTrue(saved_ids.issubset(set(self.repo.rows)))
        self.assertEqual(self.batch.read('owner', self.id)['quantity'], 20)
        self.service.check.assert_not_called()
        self.service.pay.assert_not_called()

    def test_lost_pay_response_and_failed_db_write_do_not_buy_next_key(self):
        # Даже если ответ или запись результата потеряны, следующая позиция не запускается.
        self.check()
        self.service.pay.side_effect = HTTPException(504, 'timeout')
        result = self.batch.pay('owner', self.id, '37.50')
        self.assertEqual(result['state'], 'processing')
        self.assertEqual(self.service.pay.call_count, 1)
        self.batch.pay('owner', self.id, '37.50')
        self.assertEqual(self.service.pay.call_count, 1)
        # Отдельная покупка моделирует падение сохранения после успешного ответа поставщика.
        self.key = str(uuid4())
        self.check()
        self.service.pay.side_effect = lambda body: dict(result=0, agentTransactionId=body['agentTransactionId'], transactionId=11)
        self.repo.fail_paid_write = True
        with self.assertRaises(RuntimeError):
            self.batch.pay('owner', self.id, '37.50')
        self.repo.fail_paid_write = False
        result = self.batch.pay('owner', self.id, '37.50')
        self.assertEqual(result['state'], 'processing')
        self.assertEqual(self.service.pay.call_count, 2)

    def test_check_retry_uses_saved_ids_and_skips_successful_positions(self):
        # Повтор временного check продолжает прежнюю группу, не проверяя успешные ключи повторно.
        self.prepare()
        rows = list(self.repo.rows.values())
        pending_id = rows[1]['agent_transaction_id']
        self.service.check.side_effect = lambda body: dict(result=1 if body['agentTransactionId'] == pending_id else 0,
            agentTransactionId=body['agentTransactionId'], transactionId=10, fixedPrice=12.50)
        result = self.batch.check('owner', self.draft['preparation_token'])
        self.assertTrue(result['retryable'])
        self.assertEqual(self.service.check.call_count, 2)
        self.repo.rows[pending_id]['next_attempt_at'] = now_utc() - timedelta(seconds=1)
        self.service.check.side_effect = lambda body: dict(result=0, agentTransactionId=body['agentTransactionId'], transactionId=10, fixedPrice=12.50)
        self.assertTrue(self.batch.check('owner', self.draft['preparation_token'])['purchase_ready'])
        self.assertEqual(self.service.check.call_count, 4)
        self.assertEqual(len(self.repo.rows), 3)

    def test_repository_orders_members_and_rejects_incomplete_or_changed_groups(self):
        # Настоящий репозиторий использует индексируемые ключи и проверяет сохранённый состав.
        self.prepare()
        root = self.repo.rows[self.id]
        connect = MagicMock()
        conn = connect.return_value.__enter__.return_value
        conn.execute.return_value.fetchall.return_value = list(reversed(list(self.repo.rows.values())))
        repository = AirpayRepository(connect)
        rows = repository.batch_rows('owner', root)
        self.assertEqual([row['service_snapshot']['_airpay_batch']['index'] for row in rows], [0, 1, 2])
        self.assertEqual(conn.execute.call_args.args[1][0], 'owner')
        conn.execute.return_value.fetchall.return_value = rows[:-1]
        with self.assertRaises(HTTPException):
            repository.batch_rows('owner', root)
        conn.execute.return_value.fetchall.return_value = rows
        rows[-1]['service_snapshot']['_airpay_batch']['index'] = 0
        with self.assertRaises(HTTPException):
            repository.batch_rows('owner', root)

    def test_different_unit_prices_are_summed_without_substituting_first_price(self):
        # Каждый ключ сохраняет свою цену; общий итог не вычисляется умножением первой цены.
        self.prepare()
        prices = {row_id: price for row_id, price in zip(self.repo.rows, (1.01, 2.02, 3.03))}
        self.service.check.side_effect = lambda body: dict(result=0, agentTransactionId=body['agentTransactionId'], transactionId=10,
                                                         fixedPrice=prices[body['agentTransactionId']])
        result = self.batch.check('owner', self.draft['preparation_token'])
        self.assertEqual(result['purchase_amount'], '6.06')
        self.assertEqual(result['unit_amount'], '')
        self.batch.pay('owner', self.id, '6.06')
        self.assertEqual([call.args[0]['amountTo'] for call in self.service.pay.call_args_list], [1.01, 2.02, 3.03])

    def test_disabled_transport_blocks_batch_pay_and_vouchers_before_journal_changes(self):
        # Флаг локального транспорта защищает пакетный координатор даже без HTTP-middleware.
        self.check()
        self.service.payments_enabled = False
        for action in (lambda: self.batch.pay('owner', self.id, '37.50'), lambda: self.batch.vouchers('owner', self.id)):
            with self.assertRaises(HTTPException) as raised:
                action()
            self.assertEqual(raised.exception.status_code, 403)
        self.assertTrue(all(row['state'] == 'checked' for row in self.repo.rows.values()))
        self.service.pay.assert_not_called()
        self.service.get_voucher.assert_not_called()

    def test_offline_routes_and_quantity_schema(self):
        # Количество можно проверить локально; новые маршруты оплаты и выдачи остаются запрещёнными.
        app = FastAPI()
        mount_airpay_routes(app, get_current_user=lambda: {'username': 'owner', 'role': 'owner'}, service=self.service,
                           get_secret=self.preparation.get_secret, repository=self.repo, offline=True)
        client = TestClient(app)
        base = {'service_id': 'A1', 'fields': {'account': 'x'}, 'preparation_key': self.key, 'quantity': 3}
        for quantity in (0, 21, 1.5, True, '2'):
            self.assertEqual(client.post('/integrations/airpay/prepare', json={**base, 'quantity': quantity}).status_code, 422)
        draft = client.post('/integrations/airpay/prepare', json=base).json()
        result = client.post('/integrations/airpay/check', json={'preparation_token': draft['preparation_token']})
        self.assertEqual(result.status_code, 200)
        for action in ('pay', 'vouchers'):
            response = client.post(f"/integrations/airpay/batches/{draft['agent_transaction_id']}/{action}", json={'confirmed_amount': '37.50'} if action == 'pay' else {})
            self.assertEqual(response.status_code, 403)
        self.service.pay.assert_not_called()
        self.service.get_voucher.assert_not_called()


if __name__ == '__main__':
    unittest.main()
