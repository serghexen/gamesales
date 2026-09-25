"""Проверка аудита и решений на staging PostgreSQL; транспорта поставщика здесь нет."""
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
from psycopg.conninfo import conninfo_to_dict
from fastapi import HTTPException
from domains.airpay_repository import AirpayRepository


def run(dsn):
    # Принимаем только разрешённый staging-туннель; все фикстуры принадлежат уникальному владельцу.
    info = conninfo_to_dict(dsn)
    assert (info.get('host'),info.get('port'),info.get('dbname')) == ('127.0.0.1','5433','gamesales_staging')
    owner = 'airpay-resolution-smoke-' + uuid4().hex
    connect = lambda **kwargs: psycopg.connect(dsn,connect_timeout=5,**kwargs)
    repo = AirpayRepository(connect,code_secret=lambda: 'fake-local-secret-for-resolution-smoke')
    ids = []

    def prepared(kind='voucher'):
        # Создаём только тестовую запись напрямую в журнале, без check и pay.
        transaction_id = uuid4().int % (2**62) + 1
        ids.append(transaction_id)
        repo.create(owner,str(uuid4()),{'agentTransactionId':transaction_id,'account':'test@example.invalid','serviceId':'TEST'},
            {'service_id':'TEST','title':'Fixture','fixed_payment':kind=='voucher'},kind,datetime.now(timezone.utc).timestamp()+900)
        with repo.locked(owner,transaction_id) as record:
            return record.update(state='processing',amount='12.50',currency='RUB',pay_attempts=1,requires_attention=True)

    def payload(row, **changes):
        # Основание вымышленное, код не представляет реального товара.
        return dict(request_id=str(uuid4()),expected_updated_at=row['updated_at'].isoformat(),decision='record_success',
            verified=True,evidence='TEST: имитация внешнего подтверждения',provider_transaction_id='TEST-71',code='FIXTURE-'+owner,**changes)

    def denied(callback, status):
        # Ожидаемый отказ не должен оставлять ни решение, ни изменение состояния.
        try: callback()
        except HTTPException as exc: assert exc.status_code==status
        else: raise AssertionError('Expected rejection')

    try:
        row = prepared()
        transaction_id = row['agent_transaction_id']
        decision = payload(row)
        denied(lambda:repo.resolve('other-owner',transaction_id,decision),404)
        with repo.locked(owner,transaction_id):
            denied(lambda:repo.resolve(owner,transaction_id,decision),409)
        with repo.locked(owner,transaction_id) as record:
            record.update(provider_message='TEST change')
        denied(lambda:repo.resolve(owner,transaction_id,decision),409)
        decision = payload(repo.read(owner,transaction_id))
        resolved = repo.resolve(owner,transaction_id,decision)
        assert resolved['state']=='paid' and resolved['pin_code']=='[stored]' and not resolved['requires_attention']
        assert repo.resolve(owner,transaction_id,decision)['state']=='paid'
        denied(lambda:repo.resolve(owner,transaction_id,{**decision,'evidence':'TEST other decision'}),409)
        events = repo.events(owner,transaction_id)
        assert sum(e['event_type']=='operator_resolved' for e in events['items'])==1
        assert decision['code'] not in str(events)
        assert repo.reveal(owner,transaction_id)['value']==decision['code']
        with connect() as conn:
            raw=conn.execute('SELECT pin_code,pin_ciphertext FROM app.airpay_transactions WHERE agent_transaction_id=%s',(transaction_id,)).fetchone()
            assert raw[0]=='' and raw[1]
            assert conn.execute('SELECT count(*) FROM app.airpay_operator_actions WHERE transaction_id=%s',(transaction_id,)).fetchone()[0]==1
        second = prepared()
        duplicate = payload(second)
        denied(lambda:repo.resolve(owner,second['agent_transaction_id'],duplicate),409)
        assert repo.read(owner,second['agent_transaction_id'])['state']=='processing'
        assert not any(e['event_type']=='operator_resolved' for e in repo.events(owner,second['agent_transaction_id'])['items'])
        failure = {**payload(second),'decision':'confirm_failed','code':'','provider_transaction_id':''}
        assert repo.resolve(owner,second['agent_transaction_id'],failure)['state']=='failed'
        topup = prepared('topup')
        success = {**payload(topup),'code':''}
        assert repo.resolve(owner,topup['agent_transaction_id'],success)['state']=='paid'
        # Сбой после записи решения откатывает и событие, и состояние той же транзакции.
        before=len(repo.events(owner,transaction_id)['items'])
        with repo.locked(owner,transaction_id) as record:
            try:
                with record.conn.transaction():
                    record.update(provider_message='TEST rollback')
                    raise RuntimeError('fixture rollback')
            except RuntimeError: pass
        assert len(repo.events(owner,transaction_id)['items'])==before
        print('Airpay DB audit smoke passed: locks, stale decision, idempotency, encryption, duplicate rollback, topup, atomic events')
    finally:
        # Удаляем исключительно созданные этим запуском тестовые строки, не пользовательские покупки.
        with connect() as conn:
            for table in ('airpay_events','airpay_operator_actions','airpay_result_access'):
                conn.execute(f'DELETE FROM app.{table} WHERE transaction_id IN (SELECT agent_transaction_id FROM app.airpay_transactions WHERE created_by=%s)',(owner,))
            conn.execute('DELETE FROM app.airpay_transactions WHERE created_by=%s',(owner,))
        with connect() as conn:
            assert conn.execute('SELECT count(*) FROM app.airpay_transactions WHERE created_by=%s',(owner,)).fetchone()[0]==0
        print('Own fixtures removed')
