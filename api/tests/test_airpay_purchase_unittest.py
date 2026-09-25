"""Сценарии покупки Airpay на подменённом транспорте и журнале, без сети и внешней БД."""

from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta, datetime, timezone
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

from domains.airpay_api import mount_airpay_routes
from domains.airpay_preparation import AirpayPreparation
from domains.airpay_purchase import AirpayPurchase, now_utc
from domains.airpay_repository import AirpayRepository
from domains.airpay_service import build_airpay_service
from scripts.run_migrations import split_sql_statements, is_no_transaction_migration


class MemoryJournal:
    def __init__(self):
        # Храним снимки независимо от объектов бизнес-логики, имитируя перезапуск API.
        self.rows, self.locks = {}, set()
        self.fail_paid_write = False
        self.renewals, self.accesses = {}, []

    def create(self, owner, key, request, service, kind, expires_at):
        # Дубль клиентского ключа возвращает тот же ID, не заменяя сохранённые реквизиты.
        for row in self.rows.values():
            if (row['created_by'], row['preparation_key']) == (owner, key):
                original = {k: v for k, v in row['request_payload'].items() if k not in {'agentTransactionId', 'agentTransactionDate'}}
                incoming = {k: v for k, v in request.items() if k not in {'agentTransactionId', 'agentTransactionDate'}}
                if original != incoming or row['purchase_kind'] != kind or row['service_snapshot'].get('_airpay_batch') != service.get('_airpay_batch'):
                    raise HTTPException(409, 'Preparation key conflict')
                return deepcopy(row)
        row = dict(agent_transaction_id=request['agentTransactionId'], created_by=owner, preparation_key=key,
                   request_payload=deepcopy(request), service_snapshot=deepcopy(service), purchase_kind=kind,
                   service_id=service['service_id'], service_title=service['title'], account=request['account'],
                   state='prepared', expires_at=datetime.fromtimestamp(expires_at, timezone.utc), created_at=now_utc(), updated_at=now_utc(),
                   check_attempts=0, pay_attempts=0, voucher_attempts=0, next_attempt_at=None, check_result=None,
                   check_response=None, pay_request=None, pay_response=None, voucher_response=None, pin_code='', amount=None, currency='', provider_transaction_id='')
        self.rows[row['agent_transaction_id']] = row
        return deepcopy(row)

    @contextmanager
    def locked(self, owner, transaction_id):
        # Одновременный доступ к той же записи отклоняется, как при advisory lock в PostgreSQL.
        if transaction_id in self.locks:
            raise HTTPException(409, 'busy')
        row = self.rows.get(transaction_id)
        if not row or row['created_by'] != owner:
            raise HTTPException(404)
        self.locks.add(transaction_id)
        journal = self

        class Record:
            def __init__(self):
                # Читаем отдельный снимок, чтобы тест не менял журнал без update.
                self.row = deepcopy(row)

            def update(self, **changes):
                # Сбой коммита после ответа pay оставляет ранее сохранённый processing.
                if journal.fail_paid_write and changes.get('state') == 'paid':
                    raise RuntimeError('database write failed')
                row.update(deepcopy(changes))
                self.row = deepcopy(row)
                return self.row

        try:
            yield Record()
        finally:
            self.locks.remove(transaction_id)

    def batch_rows(self, owner, root):
        # Ищем те же ключи, что PostgreSQL, и проверяем полноту сохранённой пачки.
        from domains.airpay_batch import batch_metadata, preparation_keys
        meta = batch_metadata(root)
        keys = preparation_keys(meta['key'], meta['quantity'])
        by_key = {str(row['preparation_key']): row for row in self.rows.values() if row['created_by'] == owner}
        if any(key not in by_key for key in keys):
            raise HTTPException(409, 'Incomplete batch')
        return [deepcopy(by_key[key]) for key in keys]

    @contextmanager
    def batch_locked(self, owner, transaction_id):
        # Независимая блокировка защищает всю группу при сохранении отдельных операций.
        from domains.airpay_batch import batch_metadata
        row = self.rows.get(transaction_id)
        if not row or row['created_by'] != owner or not batch_metadata(row):
            raise HTTPException(404)
        root_key = batch_metadata(row)['key']
        root = next(item for item in self.rows.values() if str(item['preparation_key']) == root_key and item['created_by'] == owner)
        lock_id = -root['agent_transaction_id']
        if lock_id in self.locks:
            raise HTTPException(409, 'Batch busy')
        self.locks.add(lock_id)
        try:
            yield self.batch_rows(owner, root)
        finally:
            self.locks.remove(lock_id)

    def history(self, owner, limit, offset, filters=None):
        # Возвращаем только свой журнал, сохраняя границы страницы.
        return [deepcopy(row) for row in self.rows.values() if row['created_by'] == owner][offset:offset + limit]

    def read(self, owner, transaction_id):
        # Чтение не требует блокировки исполняющейся покупки.
        row = self.rows.get(transaction_id)
        if not row or row['created_by'] != owner:
            raise HTTPException(404)
        return deepcopy(row)

    def batch_root(self, owner, transaction_id):
        # Восстанавливаем корень по метаданным любой позиции.
        row = self.read(owner, transaction_id)
        key = row['service_snapshot']['_airpay_batch']['key']
        return deepcopy(next(row for row in self.rows.values() if row['created_by'] == owner and row['preparation_key'] == key))

    def replacement(self, owner, source_id):
        # Ссылка на продолжение не содержит новых платёжных действий.
        return self.renewals.get((owner, source_id), {}).get('replacement_id')

    def renew(self, owner, rows):
        # Модель сохраняет связь и закрывает старый остаток, как транзакция PostgreSQL.
        from uuid import uuid4
        key = (owner, rows[0]['agent_transaction_id'])
        if key in self.renewals:
            return self.renewals[key]
        if any(row['state'] == 'processing' for row in rows):
            raise HTTPException(409)
        pending = [row for row in rows if row['state'] != 'paid']
        if not pending:
            raise HTTPException(409)
        renewal = dict(preparation_key=str(uuid4()), quantity=len(pending), source_transaction_id=pending[0]['agent_transaction_id'])
        self.renewals[key] = renewal
        for row in pending:
            self.rows[row['agent_transaction_id']]['replacement_key'] = renewal['preparation_key']
        return renewal

    def finish_renewal(self, owner, source_id, replacement_id):
        # Повтор запроса возвращает ту же новую пачку после потери HTTP-ответа.
        self.renewals[(owner, source_id)]['replacement_id'] = str(replacement_id)

    def reveal(self, owner, transaction_id):
        # Модель аудита проверяет доступ владельца и наличие сохранённого кода.
        row = self.read(owner, transaction_id)
        if row['state'] != 'paid' or not row['pin_code']:
            raise HTTPException(404)
        self.accesses.append((owner, transaction_id))
        return {'value': row['pin_code'], 'agent_transaction_id': str(transaction_id)}


class AirpayPurchaseTests(unittest.TestCase):
    def setUp(self):
        # Никакие значения .env и реальный транспорт в тестах не используются.
        self.service = MagicMock(payments_enabled=True)
        self.service.get_service.return_value = dict(service_id='A0008', title='Voucher', inputs=[], displays=[], fixed_payment=True)
        self.service.get_balance.return_value = dict(configured=True, balance=1000, currency='RUB')
        self.journal = MemoryJournal()
        self.preparation = AirpayPreparation(self.service, lambda: 'test-signing-key-for-airpay-transactions', self.journal)
        self.flow = AirpayPurchase(self.service, self.journal, self.preparation)

    def prepare(self, **kwargs):
        # Форма получает настоящую подпись и запись, а поставщик отвечает только через mock.
        draft = self.preparation.prepare('owner', 'A0008', {'account': '12345'}, preparation_key='test-key', **kwargs)
        self.id = int(draft['agent_transaction_id'])
        self.service.check.return_value = {'result': 0, 'agentTransactionId': self.id, 'transactionId': 10, 'fixedPrice': 12.50,
                                         'finalAmount': 99.99, 'currency': 'USD'}
        self.service.pay.return_value = {'result': 0, 'agentTransactionId': self.id, 'transactionId': 11}
        self.service.get_voucher.return_value = {'result': 0, 'agentTransactionId': self.id, 'transactionId': 11, 'displays': {'pinCode': 'TEST-CODE'}}
        return draft

    def checked(self):
        # Получаем подготовленную операцию, не выполняя оплату автоматически.
        draft = self.prepare()
        result = self.flow.check('owner', draft['preparation_token'])
        self.assertTrue(result['purchase_ready'])
        return result

    def allow_retry(self):
        # Управляем временем журнала, не ждём реальные интервалы в тесте.
        self.journal.rows[self.id]['next_attempt_at'] = now_utc() - timedelta(seconds=1)

    def test_purchase_kind_is_inferred_and_saved_for_both_payment_types(self):
        # Журнал хранит тип из актуального service, даже когда клиент его не передал.
        for fixed, kind, amount in ((True, 'voucher', None), (False, 'topup', '15.25')):
            with self.subTest(kind=kind):
                self.service.get_service.return_value['fixed_payment'] = fixed
                draft = self.preparation.prepare('owner', 'A0008', {'account': '12345'}, amount)
                row = self.journal.rows[int(draft['agent_transaction_id'])]
                self.assertEqual(row['purchase_kind'], kind)
                self.assertEqual(row['request_payload'].get('amountTo'), float(amount) if amount else None)
        self.service.pay.assert_not_called()
        self.service.get_voucher.assert_not_called()

    def test_fixed_price_and_same_id_used_through_pay_and_voucher(self):
        # finalAmount не становится закупочной суммой; код запрашивается только после pay.
        result = self.checked()
        self.assertEqual(result['purchase_amount'], '12.50')
        self.assertEqual(result['purchase_currency'], 'RUB')
        self.service.pay.assert_not_called()
        self.service.get_voucher.assert_not_called()
        self.assertEqual(self.flow.pay('owner', self.id, '12.50')['state'], 'paid')
        request = self.service.pay.call_args.args[0]
        self.assertEqual(request['amountTo'], 12.5)
        self.assertNotIn('amountFrom', request)
        self.assertEqual(request['agentTransactionId'], self.id)
        self.assertTrue(self.flow.voucher('owner', self.id)['result_available'])
        self.assertEqual(self.journal.rows[self.id]['pin_code'], 'TEST-CODE')
        self.assertEqual(self.service.get_voucher.call_args.args[0], request)
        self.flow.voucher('owner', self.id)
        self.service.get_voucher.assert_called_once()
        self.flow.pay('owner', self.id, '12.50')
        self.service.pay.assert_called_once()

    def test_missing_or_invalid_fixed_price_never_allows_voucher_payment(self):
        # Номинал, fixedAmount и сумма конвертации не подменяют подтверждённый fixedPrice.
        for price in (None, 'NaN', '0', '1.001'):
            self.setUp()
            draft = self.prepare()
            self.service.check.return_value.pop('fixedPrice')
            self.service.check.return_value['displays'] = {'fixedAmount': '15.00'}
            if price is not None:
                self.service.check.return_value['fixedPrice'] = price
            result = self.flow.check('owner', draft['preparation_token'])
            self.assertFalse(result['purchase_ready'])
            with self.assertRaises(HTTPException):
                self.flow.pay('owner', self.id, '15.00')
            self.service.pay.assert_not_called()

    def test_fixed_price_in_displays_and_amount_from_constraint(self):
        # Учитываем оба контейнера цены и правило amountFrom >= amountTo из переписки.
        draft = self.prepare(amount_from='10')
        self.service.check.return_value.pop('fixedPrice')
        self.service.check.return_value['displays'] = {'fixedPrice': '12.50'}
        result = self.flow.check('owner', draft['preparation_token'])
        self.assertFalse(result['purchase_ready'])
        self.assertIn('меньше', result['purchase_block_reason'])

    def test_contracts_invoices_and_conflicting_prices_block_payment(self):
        # Недокументированные тела pay и противоречивые цены не проходят в платный шаг.
        for extra in ({'contracts': [{'contractId': '01', 'contractSum': 12.5}]},
                      {'invoice': {'invoices': []}}, {'displays': {'fixedPrice': '99.00'}}):
            self.setUp()
            draft = self.prepare()
            self.service.check.return_value.update(extra)
            result = self.flow.check('owner', draft['preparation_token'])
            self.assertFalse(result['purchase_ready'])
            with self.assertRaises(HTTPException):
                self.flow.pay('owner', self.id, '12.50')
            self.service.pay.assert_not_called()

    def test_topup_uses_checked_amount_and_never_requests_voucher(self):
        # Пополнение завершено после pay и не нуждается в отдельном коде.
        self.service.get_service.return_value['fixed_payment'] = False
        draft = self.preparation.prepare('owner', 'A0008', {'account': '12345'}, '10.20', '10.20', purchase_kind='topup')
        self.id = int(draft['agent_transaction_id'])
        self.service.check.return_value = {'result': 0, 'agentTransactionId': self.id, 'transactionId': 10}
        result = self.flow.check('owner', draft['preparation_token'])
        self.assertTrue(result['purchase_ready'])
        self.assertEqual(result['purchase_amount'], '10.20')
        self.service.pay.return_value = {'result': 0, 'agentTransactionId': self.id, 'transactionId': 11}
        self.flow.pay('owner', self.id, '10.20')
        with self.assertRaises(HTTPException):
            self.flow.voucher('owner', self.id)
        self.service.get_voucher.assert_not_called()

    def test_timeout_restart_and_retry_keep_frozen_body(self):
        # Процесс может исчезнуть после отправки: следующий экземпляр берёт прежний запрос из БД.
        self.checked()
        self.service.pay.side_effect = HTTPException(504, 'timeout')
        result = self.flow.pay('owner', self.id, '12.50')
        self.assertEqual(result['state'], 'processing')
        first = deepcopy(self.service.pay.call_args.args[0])
        with self.assertRaises(HTTPException):
            self.flow.reconcile('owner', self.id)
        self.allow_retry()
        restarted = AirpayPurchase(self.service, self.journal, self.preparation)
        self.service.pay.side_effect = None
        self.assertEqual(restarted.reconcile('owner', self.id)['state'], 'paid')
        self.assertEqual(self.service.pay.call_args.args[0], first)

    def test_database_failure_after_pay_does_not_lose_request(self):
        # Успешный внешний ответ при недоступной БД оставляет восстанавливаемую операцию.
        self.checked()
        self.journal.fail_paid_write = True
        with self.assertRaises(RuntimeError):
            self.flow.pay('owner', self.id, '12.50')
        self.assertEqual(self.journal.rows[self.id]['state'], 'processing')
        self.assertEqual(self.journal.rows[self.id]['pay_request']['amountTo'], 12.5)
        self.journal.fail_paid_write = False
        self.allow_retry()
        self.assertEqual(self.flow.reconcile('owner', self.id)['state'], 'paid')

    def test_parallel_pay_and_price_tampering_are_rejected_before_network(self):
        # Защита действует на сервере независимо от отключённой кнопки браузера.
        self.checked()
        with self.journal.locked('owner', self.id), self.assertRaises(HTTPException):
            self.flow.pay('owner', self.id, '12.50')
        with self.assertRaises(HTTPException):
            self.flow.pay('owner', self.id, '0.01')
        self.service.pay.assert_not_called()

    def test_expiry_insufficient_balance_other_owner_and_no_check(self):
        # Права, свежесть цены и депозит проверяются до списания.
        self.prepare()
        with self.assertRaises(HTTPException):
            self.flow.pay('owner', self.id, '12.50')
        self.checked()
        with self.assertRaises(HTTPException):
            self.flow.pay('other', self.id, '12.50')
        self.service.get_balance.return_value['balance'] = 0
        with self.assertRaises(HTTPException):
            self.flow.pay('owner', self.id, '12.50')
        self.service.get_balance.return_value['balance'] = 1000
        self.journal.rows[self.id]['expires_at'] = now_utc() - timedelta(seconds=1)
        with self.assertRaises(HTTPException):
            self.flow.pay('owner', self.id, '12.50')
        self.service.pay.assert_not_called()

    def test_temporary_unknown_duplicate_and_202_after_pending_stay_processing(self):
        # Не выдаём повторную покупку при неопределённом ответе поставщика.
        for code in (1, 153, 220, 255, 215, 999):
            self.setUp()
            self.checked()
            self.service.pay.return_value = {'result': code}
            self.assertEqual(self.flow.pay('owner', self.id, '12.50')['state'], 'processing')
            self.allow_retry()
            self.service.pay.return_value = {'result': 202}
            self.assertEqual(self.flow.reconcile('owner', self.id)['state'], 'processing')

    def test_final_failure_and_mismatched_success_never_issue_voucher(self):
        # Финальный отказ сохраняется; чужой успешный ответ остаётся на сверке.
        for response, state in (({'result': 5}, 'failed'), ({'result': 202}, 'failed'),
                                ({'result': 0, 'transactionId': 9, 'agentTransactionId': 0}, 'processing')):
            self.setUp()
            self.checked()
            self.service.pay.return_value = response
            self.assertEqual(self.flow.pay('owner', self.id, '12.50')['state'], state)
            with self.assertRaises(HTTPException):
                self.flow.voucher('owner', self.id)
            self.service.get_voucher.assert_not_called()

    def test_voucher_error_retains_paid_and_retries_only_voucher(self):
        # Ошибка отдельного сервиса кода не становится ошибкой оплаты.
        self.checked()
        self.flow.pay('owner', self.id, '12.50')
        self.service.get_voucher.side_effect = HTTPException(502, 'voucher error')
        self.assertEqual(self.flow.voucher('owner', self.id)['state'], 'paid')
        self.allow_retry()
        self.service.get_voucher.side_effect = None
        self.assertTrue(self.flow.voucher('owner', self.id)['result_available'])
        self.assertEqual(self.journal.rows[self.id]['pin_code'], 'TEST-CODE')
        self.service.pay.assert_called_once()

    def test_voucher_wrong_transaction_or_missing_pin_is_not_delivered(self):
        # Код другого платежа не выдаётся даже при успешном result.
        self.checked()
        self.flow.pay('owner', self.id, '12.50')
        for response in ({'result': 0, 'agentTransactionId': self.id, 'transactionId': 999, 'displays': {'pinCode': 'WRONG'}},
                         {'result': 0, 'agentTransactionId': self.id, 'transactionId': 11}):
            self.allow_retry()
            self.service.get_voucher.return_value = response
            result = self.flow.voucher('owner', self.id)
            self.assertFalse(result['result_available'])
            self.assertNotIn('pin_code', result)
            self.assertEqual(result['state'], 'paid')

    def test_check_retry_uses_server_delay_and_records_failure(self):
        # Временный check сохраняется, повтор не меняет ID, финальный отказ блокирует pay.
        draft = self.prepare()
        self.service.check.return_value = {'result': 1}
        self.assertTrue(self.flow.check('owner', draft['preparation_token'])['retryable'])
        with self.assertRaises(HTTPException):
            self.flow.check('owner', draft['preparation_token'])
        self.allow_retry()
        self.service.check.return_value = {'result': 5}
        self.assertFalse(self.flow.check('owner', draft['preparation_token'])['success'])
        self.assertEqual(self.journal.rows[self.id]['state'], 'check_failed')
        self.assertEqual(self.service.check.call_args_list[0], self.service.check.call_args_list[1])

    def test_http_owner_guards_history_and_disabled_payment_calls(self):
        # API не раскрывает коды менеджеру и блокирует локальные вызовы до сети.
        def user(authorization: str = Header(default='')):
            # Тестовая авторизация не требует настоящих токенов или БД пользователей.
            if not authorization:
                raise HTTPException(401)
            return {'role': authorization, 'username': authorization}
        self.checked()
        self.service.payments_enabled = False
        app = FastAPI()
        mount_airpay_routes(app, get_current_user=user, service=self.service, repository=self.journal, get_secret=lambda: 'test')
        with TestClient(app) as client:
            path = f'/integrations/airpay/transactions/{self.id}'
            self.assertEqual(client.get(path).status_code, 401)
            self.assertEqual(client.get(path, headers={'Authorization': 'manager'}).status_code, 403)
            for action, body in (('pay', {'confirmed_amount': '12.50'}), ('reconcile', {}), ('voucher', {})):
                self.assertEqual(client.post(f'{path}/{action}', json=body, headers={'Authorization': 'owner'}).status_code, 403)
            data = client.get('/integrations/airpay/transactions', headers={'Authorization': 'owner'}).json()['items'][0]
            self.assertNotIn('request_payload', data)
            self.assertNotIn('check_response', data)
        self.service.pay.assert_not_called()
        self.service.get_voucher.assert_not_called()


class AirpayTransportAndJournalTests(unittest.TestCase):
    def test_local_offline_and_default_disable_pay_and_voucher_before_network(self):
        # Даже разрешающий флаг не обходит локальный и staging-запреты.
        for local, extra in ((True, {'AIRPAY_PAYMENTS_ENABLED': 'true'}),
                             (False, {'AIRPAY_PAYMENTS_ENABLED': 'true', 'GAMESALES_SUPPLIER_OFFLINE': 'true'}), (False, {})):
            service = build_airpay_service({'AIRPAY_USERNAME': 'test', 'AIRPAY_PASSWORD': 'test', **extra}, local_ui=local)
            with patch('domains.airpay_service.urllib.request.build_opener') as opener:
                for method in (service.pay, service.get_voucher):
                    with self.assertRaises(HTTPException):
                        method({'agentTransactionId': 12})
                opener.assert_not_called()

    def test_voucher_transport_uses_separate_url_and_string_id(self):
        # URL взят из переписки; преобразуется только ID, суммы остаются JSON-числами.
        service = build_airpay_service({'AIRPAY_USERNAME': 'test', 'AIRPAY_PASSWORD': 'test', 'AIRPAY_PAYMENTS_ENABLED': 'true'})
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = b'{"result":0}'
        with patch('domains.airpay_service.urllib.request.build_opener', return_value=opener):
            service.get_voucher({'agentTransactionId': 9223372036854775806, 'amountTo': 12.5})
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, 'https://partner.airpay.kz:9969/api/Payment/getVoucherCodeByPaymentId')
        self.assertIn(b'"agentTransactionId":"9223372036854775806"', request.data)
        self.assertIn(b'"amountTo":12.50', request.data)

    def test_repository_uses_committed_session_lock_and_releases_on_exception(self):
        # Блокировка переживает фиксацию состояния, но освобождается при любом исходе.
        connect = MagicMock()
        conn = connect.return_value.__enter__.return_value
        conn.execute.return_value.fetchone.side_effect = [{'acquired': True}, {'agent_transaction_id': 12}, None]
        repository = AirpayRepository(connect)
        with self.assertRaises(RuntimeError):
            with repository.locked('owner', 12):
                raise RuntimeError('network process interrupted')
        self.assertTrue(connect.call_args.kwargs['autocommit'])
        self.assertEqual(conn.execute.call_args.args, ('SELECT pg_advisory_unlock(%s)', (12,)))

    def test_repository_preparation_key_reuses_original_id_and_rejects_changes(self):
        # Проверяем настоящий репозиторий: ON CONFLICT сохраняет первую запись и сравнивает её реквизиты.
        connect = MagicMock()
        conn = connect.return_value.__enter__.return_value
        request = {'agentTransactionId': 12, 'agentTransactionDate': '2026-09-23T10:00:00', 'account': '123', 'serviceId': 'A1'}
        row = {'request_payload': request, 'purchase_kind': 'voucher', 'agent_transaction_id': 12, 'service_snapshot': {}}
        conn.execute.return_value.fetchone.return_value = row
        repository = AirpayRepository(connect)
        service = {'service_id': 'A1', 'title': 'Voucher'}
        reused = repository.create('owner', 'key', {**request, 'agentTransactionId': 13}, service, 'voucher', 2000000000)
        self.assertEqual(reused['agent_transaction_id'], 12)
        self.assertIn('ON CONFLICT (created_by, preparation_key) DO NOTHING', conn.execute.call_args_list[0].args[0])
        with self.assertRaises(HTTPException):
            repository.create('owner', 'key', {**request, 'account': 'changed'}, service, 'voucher', 2000000000)

    def test_migrations_use_runtime_files_and_concurrent_history_index(self):
        # Мигратор должен разделить создание журнала и конкурентный индекс на корректные шаги.
        root = Path(__file__).resolve().parents[2] / 'db/migrations/runtime'
        table = (root / '20260923_01_airpay_transactions.sql').read_text()
        index = (root / '20260923_02_airpay_history_index.sql').read_text()
        self.assertEqual(len(split_sql_statements(table)), 1)
        self.assertIn('UNIQUE (created_by, preparation_key)', table)
        self.assertTrue(is_no_transaction_migration(index))
        self.assertIn('CREATE INDEX CONCURRENTLY', index)


if __name__ == '__main__':
    unittest.main()
