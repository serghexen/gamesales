import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import psycopg

from scripts.maintain_statistics import main, maintain


class Result:
    def __init__(self, value):
        # Возвращаем только запрошенную форму ответа тестовой БД.
        self.value = value

    def fetchone(self):
        # Одна строка нужна проверкам блокировки и наличия таблицы.
        return self.value

    def fetchall(self):
        # Список имитирует найденные таблицы без статистики.
        return self.value


class FakeConnection:
    autocommit = True

    def __init__(self, *, locked=False, fail_table=None):
        # Сценарий задаёт занятость задачи и локальный отказ одной таблицы.
        self.locked = locked
        self.fail_table = fail_table
        self.commands = []

    def execute(self, query, params=()):
        # Проверяем поведение при ошибках без подключения к рабочей базе.
        text = query if isinstance(query, str) else query.as_string()
        self.commands.append(text)
        if 'pg_try_advisory_lock' in text:
            return Result((not self.locked,))
        if 'to_regclass' in text:
            return Result(('finance.entries',))
        if 'FROM pg_class' in text:
            return Result([('app', 'busy'), ('app', 'empty'), ('app', 'ready')])
        if 'SELECT EXISTS' in text:
            return Result(('"empty"' not in text,))
        if text.startswith('ANALYZE') and self.fail_table and self.fail_table in text:
            raise psycopg.errors.LockNotAvailable('test lock')
        return Result((True,))


class StatisticsMaintenanceTests(unittest.TestCase):
    def test_parallel_run_does_not_start_analyze(self):
        # Повторный запуск не конкурирует с уже работающим обслуживанием.
        conn = FakeConnection(locked=True)
        self.assertEqual(maintain(conn, log=lambda *a, **kw: None), 0)
        self.assertEqual(len(conn.commands), 1)

    def test_busy_table_is_reported_and_other_tables_continue(self):
        # Один конфликт блокировки не скрывает ошибку и не останавливает остальные таблицы.
        events = []
        conn = FakeConnection(fail_table='"busy"')
        code = maintain(conn, log=lambda event, **fields: events.append((event, fields)))
        self.assertEqual(code, 1)
        self.assertIn('ANALYZE "app"."ready"', conn.commands)
        self.assertNotIn('ANALYZE "app"."empty"', conn.commands)
        self.assertTrue(any(e == 'analyze_failed' and f['sqlstate'] == '55P03' for e, f in events))
        self.assertIn('pg_advisory_unlock', conn.commands[-1])

    def test_budget_stops_work_and_releases_lock(self):
        # Длинная очередь не превращается в бесконечное обслуживание.
        conn = FakeConnection()
        self.assertEqual(maintain(conn, log=lambda *a, **kw: None, budget_seconds=0), 1)
        self.assertFalse(any(c.startswith('ANALYZE') for c in conn.commands))
        self.assertIn('pg_advisory_unlock', conn.commands[-1])

    def test_transaction_mode_is_rejected(self):
        # Общая транзакция могла бы держать блокировки до конца задачи.
        conn = FakeConnection()
        conn.autocommit = False
        with self.assertRaises(ValueError):
            maintain(conn)
        self.assertEqual(conn.commands, [])

    def test_connection_failure_does_not_print_credentials(self):
        # Ошибки настройки остаются видны, но DSN и сообщения драйвера не попадают в журнал.
        output = io.StringIO()
        with patch.dict('os.environ', {'DATABASE_URL': 'private-dsn'}), \
                patch('scripts.maintain_statistics.psycopg.connect', side_effect=RuntimeError('private-dsn')), \
                redirect_stdout(output):
            self.assertEqual(main(), 1)
        self.assertNotIn('private-dsn', output.getvalue())
        self.assertIn('maintenance_failed', output.getvalue())


if __name__ == '__main__':
    unittest.main()
