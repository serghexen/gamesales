"""Обновляет только статистику PostgreSQL, не меняя строки и схему приложения."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone

import psycopg
from psycopg import sql


LOCK_NAME = 'gamesales_statistics_maintenance'
PARENT = ('finance', 'entries')
MISSING_STATISTICS_SQL = """
SELECT n.nspname, c.relname
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname IN ('app', 'finance') AND c.relkind = 'r'
  AND (c.reltuples < 0 OR NOT EXISTS (
    SELECT 1 FROM pg_stats s
    WHERE s.schemaname = n.nspname AND s.tablename = c.relname
  ))
ORDER BY n.nspname, c.relname
"""


def emit(event, **fields):
    # Пишем только служебные результаты, без DSN и содержимого таблиц.
    print(json.dumps({'time': datetime.now(timezone.utc).isoformat(),
                      'event': event, **fields}), flush=True)


def maintain(conn, *, log=emit, clock=time.monotonic, budget_seconds=120):
    # Одна задача обслуживает родителя и пропущенные таблицы без долгой транзакции.
    if not conn.autocommit:
        raise ValueError('Statistics maintenance requires autocommit')
    if not conn.execute('SELECT pg_try_advisory_lock(hashtext(%s))', (LOCK_NAME,)).fetchone()[0]:
        log('already_running')
        return 0
    started = clock()
    failed = 0
    analyzed = 0
    try:
        parent_exists = conn.execute("SELECT to_regclass('finance.entries')").fetchone()[0]
        if not parent_exists:
            log('missing_parent', table='finance.entries')
            failed += 1
        targets = ([PARENT] if parent_exists else []) + list(conn.execute(MISSING_STATISTICS_SQL).fetchall())
        for schema, table in targets:
            if clock() - started >= budget_seconds:
                log('budget_exceeded', remaining_from=f'{schema}.{table}')
                failed += 1
                break
            name = sql.Identifier(schema, table)
            try:
                # Пустые новые таблицы пропускаем; родитель проверяется даже при пустых секциях.
                if (schema, table) != PARENT:
                    nonempty = conn.execute(sql.SQL('SELECT EXISTS (SELECT 1 FROM {} LIMIT 1)').format(name)).fetchone()[0]
                    if not nonempty:
                        continue
                before = clock()
                conn.execute(sql.SQL('ANALYZE {}').format(name))
                analyzed += 1
                log('analyzed', table=f'{schema}.{table}', duration_ms=round((clock() - before) * 1000, 2))
            except psycopg.Error as exc:
                # Ошибка одной таблицы видна мониторингу, остальные не остаются без обслуживания.
                failed += 1
                log('analyze_failed', table=f'{schema}.{table}', sqlstate=exc.sqlstate)
        log('complete', analyzed=analyzed, failed=failed,
            duration_ms=round((clock() - started) * 1000, 2))
        return 1 if failed else 0
    finally:
        conn.execute('SELECT pg_advisory_unlock(hashtext(%s))', (LOCK_NAME,))


def main():
    # Настройки берём из окружения контейнера; таймауты действуют только в этом соединении.
    dsn = os.environ.get('DATABASE_URL')
    if not dsn:
        emit('configuration_error', reason='DATABASE_URL is required')
        return 1
    try:
        with psycopg.connect(dsn, autocommit=True, connect_timeout=10,
                             application_name='gamesales_statistics_maintenance',
                             options='-c lock_timeout=1000 -c statement_timeout=30000') as conn:
            return maintain(conn)
    except Exception as exc:
        # Полный текст ошибки подключения может содержать реквизиты, поэтому его не выводим.
        emit('maintenance_failed', error_type=type(exc).__name__, sqlstate=getattr(exc, 'sqlstate', None))
        return 1


if __name__ == '__main__':
    sys.exit(main())
