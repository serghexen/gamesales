"""Явный staging smoke Airpay: настоящий PostgreSQL и только подменённый поставщик."""
from datetime import timedelta
from pathlib import Path
import threading
from unittest.mock import MagicMock
from uuid import uuid4

import psycopg
from psycopg.conninfo import conninfo_to_dict
from fastapi import HTTPException
from domains.airpay_repository import AirpayRepository
from domains.airpay_preparation import AirpayPreparation
from domains.airpay_purchase import AirpayPurchase, now_utc
from domains.airpay_batch import AirpayBatch
from domains.airpay_jobs import AirpayJobs, AirpayJobStore


def run(dsn):
    # Допускается только согласованный staging-туннель; DSN и содержимое кодов не печатаются.
    info = conninfo_to_dict(dsn)
    assert info.get('host') == '127.0.0.1' and info.get('port') == '5433' and info.get('dbname') == 'gamesales_staging'
    owner = 'airpay-smoke-' + uuid4().hex
    secret = uuid4().hex + uuid4().hex
    connect = lambda **kwargs: psycopg.connect(dsn, connect_timeout=5, **kwargs)
    repo = AirpayRepository(connect, code_secret=lambda: secret)
    provider = MagicMock(payments_enabled=True)
    provider.get_service.return_value = dict(service_id='SMOKE-AIRPAY', title='Smoke only', fixed_payment=True, inputs=[], displays=[])
    provider.get_balance.return_value = dict(configured=True, balance=1000, currency='RUB')
    provider.check.side_effect = lambda body: dict(result=0, agentTransactionId=body['agentTransactionId'], transactionId=10, fixedPrice=10)
    provider.pay.side_effect = lambda body: dict(result=0, agentTransactionId=body['agentTransactionId'], transactionId=body['agentTransactionId'])
    provider.get_voucher.side_effect = lambda body: dict(result=0, agentTransactionId=body['agentTransactionId'], transactionId=body['agentTransactionId'], displays={'pinCode': 'SMOKE-' + str(body['agentTransactionId'])})
    preparation = AirpayPreparation(provider, lambda: secret, repo)
    purchase = AirpayPurchase(provider, repo, preparation)
    batch = AirpayBatch(provider, repo, preparation, purchase)
    store = AirpayJobStore(connect)
    jobs = AirpayJobs(store, preparation, purchase, batch)
    # Worker smoke может взять только свои фикстуры, даже если пользователь одновременно создал задание.
    run_one = lambda: store.run_one(('check', 'pay', 'voucher', 'renew'), jobs.execute, owner=owner)
    release, entered = threading.Event(), threading.Event()
    worker = None
    errors = []
    try:
        draft = preparation.prepare(owner, 'SMOKE-AIRPAY', {'account': 'test@example.invalid'}, preparation_key=str(uuid4()), quantity=3)
        root = int(draft['agent_transaction_id'])
        check_job = store.enqueue(owner, root, 'check', {'token': draft['preparation_token']})
        duplicate = store.enqueue(owner, root, 'check', {'token': draft['preparation_token']})
        assert duplicate['job_id'] == check_job['job_id']
        assert run_one()
        assert store.get(owner, check_job['job_id'])['result']['purchase_amount'] == '30.00'
        pay_job = store.enqueue(owner, root, 'pay', {'confirmed_amount': '30.00'})
        def blocked_pay(body):
            # Останавливаем fake-ответ, пока второй worker и история проверяют реальные DB-locks.
            entered.set()
            if not release.wait(20):
                raise RuntimeError('fake provider timed out')
            return dict(result=0, agentTransactionId=body['agentTransactionId'], transactionId=body['agentTransactionId'])
        provider.pay.side_effect = blocked_pay
        def run_worker():
            # Исключение потока сохраняем для явной проверки в основном сценарии.
            try:
                run_one()
            except Exception as exc:
                errors.append(type(exc).__name__)
        worker = threading.Thread(target=run_worker)
        worker.start()
        assert entered.wait(15)
        assert not run_one(), 'second worker acquired active job'
        snapshot = batch.read(owner, root)
        assert snapshot['state'] == 'processing'
        assert store.get(owner, pay_job['job_id'])['state'] == 'running'
        release.set()
        worker.join(30)
        assert not worker.is_alive() and not errors
        result = store.get(owner, pay_job['job_id'])
        assert result['state'] == 'succeeded', result['error']
        assert result['result']['paid_quantity'] == 3
        assert provider.pay.call_count == 3
        store.enqueue(owner, root, 'pay', {'confirmed_amount': '30.00'})
        run_one()
        assert provider.pay.call_count == 3, 'paid item repeated'
        code_job = store.enqueue(owner, root, 'voucher', {})
        run_one()
        code_result = store.get(owner, code_job['job_id'])
        assert code_result['state'] == 'succeeded', code_result['error']
        assert code_result['result']['received_quantity'] == 3
        assert 'pin_code' not in str(code_result['result'])
        with connect() as conn:
            rows = conn.execute('SELECT pin_code,pin_ciphertext,result_hash,voucher_response FROM app.airpay_transactions WHERE created_by=%s', (owner,)).fetchall()
            assert all(not row[0] and row[1] and len(row[2]) == 64 and 'pinCode' not in str(row[3]) for row in rows)
        assert repo.reveal(owner, root)['value'] == 'SMOKE-' + str(root)
        try:
            repo.reveal('other-owner', root)
            raise AssertionError('foreign reveal allowed')
        except HTTPException as exc:
            assert exc.status_code == 404
        with connect() as conn:
            assert conn.execute('SELECT count(*) FROM app.airpay_result_access WHERE viewed_by=%s', (owner,)).fetchone()[0] == 1
        # Вторая пачка проверяет реальную транзакционную связь переоценки одного оставшегося ключа.
        other = preparation.prepare(owner, 'SMOKE-AIRPAY', {'account': 'test@example.invalid'}, preparation_key=str(uuid4()), quantity=2)
        other_id = int(other['agent_transaction_id'])
        batch.check(owner, other['preparation_token'])
        purchase.pay(owner, other_id, '10.00', batch=True)
        with connect() as conn:
            conn.execute("UPDATE app.airpay_transactions SET expires_at=%s WHERE created_by=%s AND state='checked'", (now_utc() - timedelta(minutes=1), owner))
        renewed = batch.renew(owner, other_id)
        assert renewed['batch']['quantity'] == 1
        assert batch.renew(owner, other_id)['draft']['agent_transaction_id'] == renewed['draft']['agent_transaction_id']
        try:
            batch.pay(owner, other_id, '20.00')
            raise AssertionError('replaced group could be paid')
        except HTTPException as exc:
            assert exc.status_code == 409
        assert batch.check(owner, renewed['draft']['preparation_token'])['purchase_ready']
        print('PASS: durable queue, concurrent workers, readable progress, retry, encrypted codes, audited reveal, remainder renewal')
    finally:
        release.set()
        if worker:
            worker.join(30)
        # Удаляем только собственные фикстуры с уникальным владельцем; пользовательские операции не затрагиваются.
        with connect() as conn:
            conn.execute('DELETE FROM app.airpay_events WHERE actor=%s', (owner,))
            conn.execute('DELETE FROM app.airpay_operator_actions WHERE decided_by=%s', (owner,))
            conn.execute('DELETE FROM app.airpay_result_access WHERE viewed_by=%s', (owner,))
            conn.execute('DELETE FROM app.airpay_jobs WHERE created_by=%s', (owner,))
            conn.execute('DELETE FROM app.airpay_renewals WHERE created_by=%s', (owner,))
            conn.execute('DELETE FROM app.airpay_transactions WHERE created_by=%s', (owner,))
        with connect() as conn:
            assert conn.execute('SELECT count(*) FROM app.airpay_transactions WHERE created_by=%s', (owner,)).fetchone()[0] == 0
        print('Smoke fixtures removed')


if __name__ == '__main__':
    # Скрипт не входит в автообнаружение unittest и запускается отдельно по согласованному staging-сценарию.
    from dotenv import dotenv_values
    run(dotenv_values(Path(__file__).resolve().parents[2] / '.env.dev')['DATABASE_URL'])
