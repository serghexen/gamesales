"""Проверка диагностического журнала на отдельной одноразовой PostgreSQL, без API поставщика."""
import os
import time
from uuid import uuid4
import psycopg
from psycopg.conninfo import conninfo_to_dict
from fastapi import HTTPException
from airpay_runtime.airpay_diagnostics import AirpayDiagnosticStore, AirpayDiagnostics


def run():
    # Имя БД и loopback закреплены, чтобы сценарий нельзя было случайно выполнить на рабочем журнале.
    dsn = os.environ['DATABASE_URL']
    info = conninfo_to_dict(dsn)
    assert info.get('dbname') == 'airpay_diagnostics_test' and info.get('host') == '127.0.0.1'
    connect = lambda **kwargs: psycopg.connect(dsn, **kwargs)
    email = {'name': 'account', 'title': 'Email', 'required': True, 'regexp': ''}
    services = [{'service_id': name, 'title': name, 'fixed_payment': True, 'inputs': [email]} for name in ('OK', 'ERR', 'DIRECT')]
    services[-1] = {**services[-1], 'inputs': [{**email, 'title': 'ID игрока'}]}
    calls = []
    def check(payload):
        # Единственный заменитель внешнего запроса возвращает тестовый ответ и запоминает его ID.
        calls.append(payload)
        return {'result': 204, 'resultMessage': 'Валюта'} if payload['serviceId'] == 'ERR' else {'result': 0, 'fixedPrice': '656.18', 'transactionId': 42}
    def runner():
        # Новое соединение и объект имитируют возвращение в окно после перезапуска приложения.
        return AirpayDiagnostics(AirpayDiagnosticStore(connect), get_services=lambda: {'configured': True, 'items': services},
            get_service=lambda service_id: next(item for item in services if item['service_id'] == service_id), check=check)
    flow = runner()
    key = uuid4()
    first = flow.start('test-owner', key)
    assert flow.start('test-owner', key)['run']['id'] == first['run']['id']
    for owner in ('other-owner',):
        try: flow.step(owner, key)
        except HTTPException as exc: assert exc.status_code == 404
        else: raise AssertionError('Owner isolation failed')
    with flow.store.locked():
        try: runner().step('test-owner', key)
        except HTTPException as exc: assert exc.status_code == 409
        else: raise AssertionError('Concurrent step was accepted')
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        report = runner().step('test-owner', key)['run']
        if report['state'] == 'completed': break
        time.sleep(.3)
    assert report['state'] == 'completed'
    assert [row['state'] for row in report['items']] == ['ok', 'rejected', 'needs_input']
    assert len(calls) == 2
    assert report['items'][0]['fixed_price'] == '656.18'
    assert report['items'][1]['result'] == 204
    runner().step('test-owner', key)
    assert len(calls) == 2
    interrupted_key = uuid4()
    runner().start('test-owner', interrupted_key)
    with connect() as conn:
        conn.execute("UPDATE supplier_hub_airpay.airpay_diagnostic_items SET state='running' WHERE run_id=%s AND position=0", (interrupted_key,))
    snapshot = runner().step('test-owner', interrupted_key)['run']
    assert snapshot['items'][0]['state'] == 'interrupted' and len(calls) == 2
    assert runner().cancel('test-owner', interrupted_key)['run']['state'] == 'cancelled'
    with connect() as conn:
        assert conn.execute('SELECT count(*) FROM supplier_hub_airpay.airpay_transactions').fetchone()[0] == 0
    print('PASS: PostgreSQL migrations, persistence, restart, ownership, concurrent lock, interrupted check; payment journal empty')


if __name__ == '__main__':
    run()
