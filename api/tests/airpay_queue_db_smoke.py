"""Восстановление очереди на staging PostgreSQL: ни одного объекта транспорта поставщика."""
from datetime import datetime, timezone
from contextlib import contextmanager
from psycopg.rows import dict_row
from uuid import uuid4
from unittest.mock import MagicMock
import psycopg
from psycopg.conninfo import conninfo_to_dict
from fastapi import HTTPException
from domains.airpay_repository import AirpayRepository
from domains.airpay_jobs import AirpayJobStore


def run(dsn):
    # Согласованный staging-туннель и уникальный владелец исключают обработку чужих заданий.
    info = conninfo_to_dict(dsn)
    assert (info.get('host'), info.get('port'), info.get('dbname')) == ('127.0.0.1', '5433', 'gamesales_staging')
    owner = 'airpay-queue-smoke-' + uuid4().hex
    connect = lambda **kwargs: psycopg.connect(dsn, connect_timeout=5, **kwargs)
    repo, observer = AirpayRepository(connect), AirpayJobStore(connect)
    guard = connect(autocommit=True, row_factory=dict_row)
    second = connect(autocommit=True, row_factory=dict_row)
    @contextmanager
    def pinned(**kwargs):
        # Тот же тестовый сеанс повторно берёт свой advisory lock; фоновые worker его не получают.
        yield guard
    @contextmanager
    def pinned_second(**kwargs):
        # Второй сеанс проверяет реальную конкуренцию и обход занятых первых 32 записей.
        yield second
    store = AirpayJobStore(pinned)

    def fixture(action='check', holder=None):
        # Создаём запись прямо в журнале: сервис и check/pay здесь вообще не используются.
        transaction_id = uuid4().int % (2**62) + 1
        repo.create(owner, str(uuid4()), {'agentTransactionId': transaction_id, 'account': 'fixture@example.invalid', 'serviceId': 'TEST'},
                    {'service_id': 'TEST', 'title': 'Queue fixture', 'fixed_payment': True}, 'voucher', datetime.now(timezone.utc).timestamp() + 900)
        job_id = uuid4()
        holder = guard if holder is None else holder
        # Lock берётся до INSERT: работающий API никогда не увидит доступную ему фикстуру.
        holder.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))', ('airpay-job:' + str(job_id),))
        holder.execute('INSERT INTO app.airpay_jobs(id,created_by,transaction_id,action,payload) VALUES (%s,%s,%s,%s,%s)',
                       (job_id, owner, transaction_id, action, '{}'))
        return transaction_id, observer.get(owner, job_id)

    def denied(callback, expected):
        # Ошибки гонки и изоляции являются ожидаемой частью smoke-проверки.
        try: callback()
        except HTTPException as exc: assert exc.status_code == expected
        else: raise AssertionError('Expected rejection')

    try:
        execute = MagicMock(side_effect=AssertionError('No provider execution after crash'))
        for action, state in [('pay', 'processing'), ('reconcile', 'processing'), ('voucher', 'paid')]:
            transaction_id, job = fixture(action)
            with repo.locked(owner, transaction_id) as record:
                record.update(state=state, amount='10.00', currency='RUB')
            with connect() as conn:
                conn.execute("UPDATE app.airpay_jobs SET state='running',progress=1,updated_at=now()-interval '10 minutes' WHERE id=%s", (job['job_id'],))
            report = store.diagnostics(owner, False)
            assert any(item['job_id'] == job['job_id'] and item['stale'] for item in report['items'])
            assert store.run_one(('check', 'renew'), execute, owner=owner)
            assert store.get(owner, job['job_id'])['state'] == 'failed'
            assert repo.read(owner, transaction_id)['state'] == state
        execute.assert_not_called()
        transaction_id, job = fixture('pay')
        denied(lambda: observer.cancel(owner, job['job_id']), 409)
        assert not observer.run_one(('pay',), execute, owner=owner)
        held = next(item for item in observer.diagnostics(owner, True)['items'] if item['job_id'] == job['job_id'])
        assert held['worker_lock_held']
        denied(lambda: store.cancel(owner + '-foreign', job['job_id']), 404)
        report = store.diagnostics(owner, False)
        assert report['summary']['blocked_by_config'] == 1
        assert store.cancel(owner, job['job_id'])['state'] == 'failed'
        assert store.cancel(owner, job['job_id'])['state'] == 'failed'
        assert repo.read(owner, transaction_id)['state'] == 'prepared'
        # Занятые первые 32 работы не мешают 33-й; lock удерживается реальным другим соединением.
        fixtures = [fixture() for _ in range(32)] + [fixture(holder=second)]
        executed = []
        def complete(row, progress):
            # Имитируем только результат очереди, не создавая финансового результата.
            executed.append(str(row['id']))
            progress(1)
            return {'mock': True}
        assert AirpayJobStore(pinned_second).run_one(('check',), complete, owner=owner)
        assert executed == [fixtures[-1][1]['job_id']]
        assert store.latest(owner, fixtures[-1][0])['state'] == 'succeeded'
        assert store.diagnostics(owner + '-foreign', True)['items'] == []
        print('PASS: orphan pay/reconcile/voucher stopped, payment states preserved, pg_locks diagnostic, cancel/worker exclusion, owner isolation, queue beyond first 32')
    finally:
        # Удаляем только созданные этим smoke записи и их события; пользовательские данные не затрагиваем.
        with connect() as conn:
            conn.execute('DELETE FROM app.airpay_events WHERE actor=%s', (owner,))
            conn.execute('DELETE FROM app.airpay_jobs WHERE created_by=%s', (owner,))
            conn.execute('DELETE FROM app.airpay_transactions WHERE created_by=%s', (owner,))
        with connect() as conn:
            assert conn.execute('SELECT count(*) FROM app.airpay_transactions WHERE created_by=%s', (owner,)).fetchone()[0] == 0
        guard.close()
        second.close()
        print('Queue smoke fixtures removed')
