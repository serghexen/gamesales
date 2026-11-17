"""Интеграционные проверки только в отдельной gamesales_statistics_test."""

import os
from pathlib import Path
import time
import unittest

import psycopg
from psycopg import sql

from scripts.maintain_statistics import LOCK_NAME, maintain


DSN = os.environ.get('GAMESALES_STATISTICS_TEST_DSN')
ROOT = Path(__file__).resolve().parents[2]
REFERENCES = {
    'app': ['account_statuses', 'asset_types', 'deal_flow_statuses', 'deal_statuses',
            'deal_types', 'domains', 'messengers', 'platforms', 'product_types',
            'regions', 'sources', 'subscription_products', 'user_roles',
            'voucher_catalog_suppliers', 'slot_types'],
    'finance': ['dim_regions', 'dim_sources', 'entry_statuses', 'projects',
                'section_types', 'sections'],
}


@unittest.skipUnless(DSN, 'Requires an isolated PostgreSQL test database')
class StatisticsPostgresTests(unittest.TestCase):
    def setUp(self):
        # Неподходящее имя базы отклоняем до создания и удаления тестовых объектов.
        self.conn = psycopg.connect(DSN, autocommit=True,
                                   options='-c lock_timeout=100 -c statement_timeout=5000')
        self.addCleanup(self.conn.close)
        if self.conn.execute('SELECT current_database()').fetchone()[0] != 'gamesales_statistics_test':
            raise RuntimeError('Only gamesales_statistics_test is allowed')
        self.conn.execute('DROP SCHEMA IF EXISTS app CASCADE; DROP SCHEMA IF EXISTS finance CASCADE')
        self.conn.execute('CREATE SCHEMA app; CREATE SCHEMA finance')
        for schema, tables in REFERENCES.items():
            for table in tables:
                name = sql.Identifier(schema, table)
                self.conn.execute(sql.SQL('CREATE TABLE {} (id int PRIMARY KEY, label text)').format(name))
                self.conn.execute(sql.SQL("INSERT INTO {} SELECT n, 'sample-' || n FROM generate_series(1,4) n").format(name))
        self.conn.execute("""
            CREATE TABLE finance.entries (id int, label text) PARTITION BY RANGE(id);
            CREATE TABLE finance.entries_sample PARTITION OF finance.entries FOR VALUES FROM (0) TO (100);
            INSERT INTO finance.entries VALUES (1, 'entry');
            CREATE TABLE app.needs_stats (id int, label text);
            INSERT INTO app.needs_stats VALUES (1, 'unchanged');
            CREATE TABLE app.empty_ref (id int);
            CREATE TABLE app.already_analyzed (id int);
            INSERT INTO app.already_analyzed VALUES (1);
            ANALYZE app.already_analyzed;
        """)

    def snapshot(self):
        # Сравниваем реальные строки всех непустых таблиц, а не только число записей.
        result = {}
        for schema, table in self.conn.execute("""
            SELECT schemaname, tablename FROM pg_tables
            WHERE schemaname IN ('app','finance') ORDER BY 1,2
        """).fetchall():
            result[(schema, table)] = self.conn.execute(
                sql.SQL('SELECT * FROM {} ORDER BY 1').format(sql.Identifier(schema, table))).fetchall()
        return result

    def test_analyze_preserves_rows_and_skips_known_or_empty_tables(self):
        # Проверяем родителя, первичный сбор и повторный запуск на настоящем PostgreSQL.
        before = self.snapshot()
        events = []
        log = lambda event, **fields: events.append((event, fields))
        self.assertEqual(maintain(self.conn, log=log), 0)
        names = {f['table'] for e, f in events if e == 'analyzed'}
        self.assertIn('finance.entries', names)
        self.assertIn('app.needs_stats', names)
        self.assertNotIn('app.empty_ref', names)
        self.assertNotIn('app.already_analyzed', names)
        self.assertEqual(before, self.snapshot())
        self.assertTrue(self.conn.execute("SELECT EXISTS (SELECT 1 FROM pg_stats WHERE schemaname='finance' AND tablename='entries' AND inherited)").fetchone()[0])
        events.clear()
        self.assertEqual(maintain(self.conn, log=log), 0)
        self.assertEqual([f['table'] for e, f in events if e == 'analyzed'], ['finance.entries'])

    def test_real_lock_timeout_does_not_change_data(self):
        # Занятая таблица даёт контролируемый отказ, остальные анализируются без изменения строк.
        before = self.snapshot()
        with psycopg.connect(DSN) as blocker:
            blocker.execute('LOCK TABLE app.needs_stats IN ACCESS EXCLUSIVE MODE')
            events = []
            self.assertEqual(maintain(self.conn, log=lambda e, **f: events.append((e, f))), 1)
            self.assertTrue(any(e == 'analyze_failed' and f['table'] == 'app.needs_stats' for e, f in events))
        self.assertEqual(before, self.snapshot())
        self.assertEqual(maintain(self.conn, log=lambda *a, **kw: None), 0)

    def test_advisory_lock_prevents_overlapping_run(self):
        # Два соединения не запускают одно обслуживание одновременно.
        with psycopg.connect(DSN, autocommit=True) as blocker:
            blocker.execute('SELECT pg_advisory_lock(hashtext(%s))', (LOCK_NAME,))
            events = []
            self.assertEqual(maintain(self.conn, log=lambda e, **f: events.append((e, f))), 0)
            self.assertEqual(events, [('already_running', {})])

    def test_migration_preserves_data_and_enables_autoanalyze(self):
        # Миграция меняет только параметры; фоновый PostgreSQL анализирует четыре строки без ручного ANALYZE.
        before = self.snapshot()
        migration = (ROOT / 'db/migrations/runtime/20261117_01_reference_autoanalyze.sql').read_text()
        with self.conn.transaction():
            self.conn.execute(migration)
        self.assertEqual(before, self.snapshot())
        configured = self.conn.execute("""
            SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname IN ('app','finance')
              AND c.reloptions @> ARRAY['autovacuum_analyze_threshold=0','autovacuum_analyze_scale_factor=0']
        """).fetchone()[0]
        self.assertEqual(configured, 21)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            done = self.conn.execute("SELECT last_autoanalyze IS NOT NULL FROM pg_stat_user_tables WHERE schemaname='app' AND relname='slot_types'").fetchone()[0]
            if done:
                return
            time.sleep(0.25)
        self.fail('autoanalyze did not run: isolated PostgreSQL needs autovacuum_naptime=1s')


if __name__ == '__main__':
    unittest.main()
