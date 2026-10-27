"""Проверки жизненного цикла на SQL в памяти; блокировки PostgreSQL проверяются отдельно."""

import base64
import re
import sqlite3
import unittest

from fastapi import HTTPException
from domains.account_reserves import AccountReserves


class ReserveLifecycleTests(unittest.TestCase):
    def setUp(self):
        # Используем изолированную БД без сетевого доступа и настоящих кодов.
        self.conn = sqlite3.connect(':memory:')
        self.addCleanup(self.conn.close)
        self.conn.execute("ATTACH DATABASE ':memory:' AS app")
        self.conn.create_function('now', 0, lambda: '2026-10-26T12:00:00')
        self.conn.executescript('''
            CREATE TABLE app.accounts(account_id INTEGER PRIMARY KEY);
            INSERT INTO app.accounts VALUES(1),(2);
            CREATE TABLE app.account_secrets(account_id INT, secret_key TEXT, secret_value TEXT, UNIQUE(account_id,secret_key));
            CREATE TABLE app.account_reserve_codes(reserve_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INT, reserve_key TEXT, value_hash TEXT, is_listed BOOLEAN DEFAULT true,
                issued_at TEXT, issued_by TEXT, consumed_at TEXT, UNIQUE(account_id,reserve_key));
            CREATE TABLE app.account_reserve_claims(claim_token TEXT PRIMARY KEY,account_id INT,reserve_key TEXT,
                claimed_by TEXT,reused_at TEXT,UNIQUE(account_id,reserve_key));
            CREATE TABLE app.account_reserve_events(reserve_id INT,deal_id INT,event_type TEXT,actor TEXT);
            CREATE TABLE app.deals(deal_id INT PRIMARY KEY,deal_type_code TEXT DEFAULT 'rental',
                status_code TEXT DEFAULT 'confirmed',flow_status_code TEXT DEFAULT 'pending');
            CREATE TABLE app.deal_items(deal_id INT,account_id INT,reserve_key TEXT);
        ''')
        self.service = AccountReserves(self.one, self.all, self.execute)

    def cursor(self, conn, sql, params):
        # Адаптируем только синтаксис драйвера; бизнес-запросы исполняются настоящим SQL-движком.
        sql = sql.replace(' FOR UPDATE', '').replace('::bigint', '').replace('::text', '')
        sql = sql.replace("substring(c.reserve_key from '[0-9]+$')", 'CAST(substr(c.reserve_key,8) AS INTEGER)')
        parts, flattened, arguments = [], [], iter(params)
        for part in re.split(r'(=ANY\(%s\)|%s)', sql):
            if part == '%s':
                parts.append('?')
                flattened.append(next(arguments))
            elif part == '=ANY(%s)':
                values = next(arguments)
                parts.append(' IN (' + (','.join('?' for _ in values) if values else 'SELECT NULL WHERE 0') + ')')
                flattened.extend(values)
            else:
                parts.append(part)
        return conn.execute(''.join(parts), flattened)

    def one(self, conn, sql, params=()):
        # Повторяем контракт q1 приложения.
        return self.cursor(conn, sql, params).fetchone()

    def all(self, conn, sql, params=()):
        # Повторяем контракт qall приложения.
        return self.cursor(conn, sql, params).fetchall()

    def execute(self, conn, sql, params=()):
        # Возвращаем число изменённых строк как exec1 приложения.
        return self.cursor(conn, sql, params).rowcount

    def add(self, values, account=1, expected=None):
        # Создаём тестовый набор через тот же путь, что редактор и импорт.
        return self.service.replace(self.conn, account, values, 'alice', expected)

    def bind(self, key, deal=1, account=1, status='pending'):
        # Фиксируем связь сделки так же, как API после успешного выбора кода.
        self.conn.execute('INSERT INTO app.deals(deal_id,flow_status_code) VALUES(?,?)', (deal,status))
        self.conn.execute('INSERT INTO app.deal_items VALUES(?,?,?)', (deal,account,key))
        self.service.assigned(self.conn,account,key,'alice',deal)

    def test_replace_used_value_keeps_old_deal_and_creates_free_identity(self):
        old = self.add(['OLD'])[0]
        self.bind(old)
        new = self.add(['NEW'], expected={old:'OLD'})[0]
        self.assertNotEqual(old,new)
        self.assertEqual(self.conn.execute('SELECT reserve_key FROM app.deal_items').fetchone()[0], old)
        self.assertEqual(base64.b64decode(self.service.rows(self.conn,1)[0][6]), b'OLD')
        self.assertNotIn(new,self.service.used(self.conn,1))

    def test_reorder_and_remove_do_not_move_identity(self):
        first, second = self.add(['A','B'])
        self.assertEqual(self.add(['B','A']), [second,first])
        self.assertEqual(self.add(['B']), [second])
        third = self.add(['B','C'])[1]
        self.assertNotIn(third,(first,second))

    def test_stale_editor_cannot_overwrite_changed_list(self):
        key = self.add(['A'])[0]
        self.add(['B'])
        with self.assertRaises(HTTPException) as err:
            self.add(['C'], expected={key:'A'})
        self.assertEqual(err.exception.status_code,409)

    def test_duplicate_values_rejected(self):
        with self.assertRaises(HTTPException):
            self.add(['A','A'])

    def test_completion_deletes_only_original_value(self):
        old = self.add(['OLD'])[0]
        self.bind(old,status='completed')
        new = self.add(['NEW'])[0]
        self.service.finish(self.conn,1,old,'alice',1)
        rows = {r[1]:r for r in self.service.rows(self.conn,1)}
        self.assertIsNone(rows[old][6])
        self.assertIsNotNone(rows[old][5])
        self.assertEqual(base64.b64decode(rows[new][6]),b'NEW')
        self.service.finish(self.conn,1,old,'alice',1)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM app.account_reserve_events WHERE event_type='consumed'").fetchone()[0],1)
        with self.assertRaises(HTTPException):
            self.add(['OLD'])

    def test_legacy_shared_code_survives_until_last_active_deal_finishes(self):
        key = self.add(['A'])[0]
        self.bind(key,1,status='completed')
        self.bind(key,2)
        self.service.finish(self.conn,1,key,'alice',1)
        self.assertIsNotNone(self.service.rows(self.conn,1)[0][6])
        self.conn.execute("UPDATE app.deals SET flow_status_code='completed' WHERE deal_id=2")
        self.service.finish(self.conn,1,key,'alice',2)
        self.assertIsNone(self.service.rows(self.conn,1)[0][6])

    def test_copy_from_account_can_be_attached_by_its_owner(self):
        key = self.add(['A'])[0]
        claim = self.service.claim(self.conn,1,key,'alice')
        self.assertIn(key,self.service.used(self.conn,1))
        self.assertNotIn(key,self.service.used(self.conn,1,owner='alice'))
        with self.assertRaises(HTTPException):
            self.service.select(self.conn,1,key,'bob')
        self.assertEqual(self.service.select(self.conn,1,key,'alice',token=claim['claim_token']),key)
        self.bind(key)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM app.account_reserve_claims').fetchone()[0],0)
        self.assertNotIn(key,self.service.used(self.conn,1,exclude_deal_id=1,owner='alice'))

    def test_saved_deal_does_not_bypass_claim_for_changed_account(self):
        old = self.add(['OLD'])[0]
        self.bind(old)
        new = self.add(['NEW'],account=2)[0]
        self.service.claim(self.conn,2,new,'bob')
        with self.assertRaises(HTTPException):
            self.service.claim(self.conn,2,new,'alice',deal_id=1)

    def test_copy_existing_assignment_marks_it_issued(self):
        key = self.add(['A'])[0]
        self.bind(key)
        result = self.service.claim(self.conn,1,key,'alice',deal_id=1)
        self.assertTrue(result['assigned'])
        self.conn.execute("UPDATE app.deals SET status_code='cancelled' WHERE deal_id=1")
        self.assertIn(key,self.service.used(self.conn,1))

    def test_cancel_unissued_assignment_returns_code_to_available(self):
        key = self.add(['A'])[0]
        self.bind(key)
        self.conn.execute("UPDATE app.deals SET status_code='cancelled' WHERE deal_id=1")
        self.assertNotIn(key,self.service.used(self.conn,1))

    def test_repeated_claim_cannot_be_released_by_first_failed_copy(self):
        key = self.add(['A'])[0]
        first = self.service.claim(self.conn,1,key,'alice')
        second = self.service.claim(self.conn,1,key,'alice')
        self.assertEqual(first['claim_token'],second['claim_token'])
        self.assertTrue(second['reused'])
        self.service.release(self.conn,1,key,first['claim_token'],'alice')
        self.assertIn(key,self.service.used(self.conn,1))

    def test_failed_first_copy_releases_only_own_claim(self):
        key = self.add(['A'])[0]
        claim = self.service.claim(self.conn,1,key,'alice')
        self.service.release(self.conn,1,key,claim['claim_token'],'bob')
        self.assertIn(key,self.service.used(self.conn,1))
        self.service.release(self.conn,1,key,claim['claim_token'],'alice')
        self.assertNotIn(key,self.service.used(self.conn,1))

    def test_missing_or_busy_explicit_selection_does_not_fallback(self):
        key, _ = self.add(['A','B'])
        self.bind(key)
        for requested in (key,'reserve999','bad-key'):
            with self.assertRaises(HTTPException):
                self.service.select(self.conn,1,requested,'alice')

    def test_draft_assignment_and_empty_selection(self):
        key = self.add(['A'])[0]
        self.bind(key,status='draft')
        self.assertIn(key,self.service.used(self.conn,1))
        self.assertEqual(self.service.select(self.conn,1,key,'alice',deal_id=1),key)
        self.assertIsNone(self.service.select(self.conn,1,None,'alice',auto=False))

    def test_legacy_secret_api_preserves_identity(self):
        key = self.add(['OLD'])[0]
        self.bind(key)
        keys = self.service.patch_legacy(self.conn,1,{key:'NEW'},[],'alice')
        self.assertNotEqual(keys,[key])
        self.assertEqual(base64.b64decode(self.service.rows(self.conn,1)[0][6]),b'OLD')

    def test_failed_completion_transaction_keeps_status_and_value(self):
        # Сбой после очистки не должен оставить завершение и удаление в разных состояниях.
        key = self.add(['A'])[0]
        self.bind(key)
        self.conn.commit()
        with self.assertRaises(RuntimeError):
            with self.conn:
                self.conn.execute("UPDATE app.deals SET flow_status_code='completed' WHERE deal_id=1")
                self.service.finish(self.conn,1,key,'alice',1)
                raise RuntimeError('failed before commit')
        self.assertEqual(self.conn.execute('SELECT flow_status_code FROM app.deals').fetchone()[0],'pending')
        self.assertIsNotNone(self.service.rows(self.conn,1)[0][6])
        self.assertIsNone(self.service.rows(self.conn,1)[0][5])

    def test_completion_cleans_previous_codes_of_same_deal(self):
        # Смена резерва внутри сделки не оставляет старое выданное значение после её завершения.
        first, second = self.add(['A','B'])
        self.bind(first)
        self.service.claim(self.conn,1,first,'alice',deal_id=1)
        self.conn.execute('UPDATE app.deal_items SET reserve_key=? WHERE deal_id=1',(second,))
        self.service.detached(self.conn,1,first,'alice',1)
        self.service.assigned(self.conn,1,second,'alice',1)
        self.conn.execute("UPDATE app.deals SET flow_status_code='completed' WHERE deal_id=1")
        self.service.finish_deal(self.conn,1,'alice')
        self.assertTrue(all(r[6] is None and r[5] is not None for r in self.service.rows(self.conn,1)))


if __name__ == '__main__':
    unittest.main()
