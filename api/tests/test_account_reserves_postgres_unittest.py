"""Проверки на восстановленной копии PostgreSQL; production DSN использовать запрещено."""

import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import psycopg
from fastapi import HTTPException

from domains.account_reserves import AccountReserves


DSN = os.getenv('GAMESALES_RESERVES_TEST_DSN')


def one(conn, sql, params=()):
    # Исполняем настоящий PostgreSQL без подмены синтаксиса или блокировок.
    return conn.execute(sql, params).fetchone()


def all_rows(conn, sql, params=()):
    # Сохраняем контракт запросов сервиса без импорта фоновых задач API.
    return conn.execute(sql, params).fetchall()


def execute(conn, sql, params=()):
    # Изменения входят в транзакцию вызывающего теста.
    return conn.execute(sql, params).rowcount


@unittest.skipUnless(DSN, 'Requires an isolated restored PostgreSQL database')
class ReservePostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Допускаем только отдельную тестовую БД с явным именем и уже применённой миграцией.
        with psycopg.connect(DSN) as conn:
            if one(conn, 'SELECT current_database()')[0] != 'gamesales_reserves_test':
                raise RuntimeError('Only gamesales_reserves_test is allowed')
            if not one(conn, "SELECT to_regclass('app.account_reserve_codes')")[0]:
                raise RuntimeError('Apply migrations to the restored copy first')

    def setUp(self):
        # Создаём отдельный синтетический аккаунт, не затрагивая строки из резервной копии.
        self.service = AccountReserves(one, all_rows, execute)
        self.deals = []
        with self.connection() as conn:
            self.account = one(conn, 'INSERT INTO app.accounts DEFAULT VALUES RETURNING account_id')[0]
            self.keys = self.service.replace(conn, self.account, ['TEST-A', 'TEST-B'], 'test-alice')

    def connection(self):
        # Ограничиваем ожидание, чтобы ошибка блокировок не подвесила проверку релиза.
        return psycopg.connect(DSN, options='-c statement_timeout=10000 -c lock_timeout=5000')

    def tearDown(self):
        # Удаляем только собственные синтетические строки в изолированной копии.
        with self.connection() as conn:
            execute(conn, 'DELETE FROM app.account_reserve_events WHERE reserve_id IN (SELECT reserve_id FROM app.account_reserve_codes WHERE account_id=%s)', (self.account,))
            execute(conn, 'DELETE FROM app.account_reserve_claims WHERE account_id=%s', (self.account,))
            execute(conn, 'DELETE FROM app.deal_items WHERE account_id=%s', (self.account,))
            for deal in self.deals:
                execute(conn, 'DELETE FROM app.deals WHERE deal_id=%s', (deal,))
            execute(conn, 'DELETE FROM app.account_secrets WHERE account_id=%s', (self.account,))
            execute(conn, 'DELETE FROM app.account_reserve_codes WHERE account_id=%s', (self.account,))
            execute(conn, 'DELETE FROM app.accounts WHERE account_id=%s', (self.account,))

    def bind(self, conn, key, actor='test-alice'):
        # Назначаем резерв в том же порядке и транзакции, что обработчик создания сделки.
        selected = self.service.select(conn, self.account, key, actor, auto=False)
        deal = one(conn, "INSERT INTO app.deals(deal_type_code) VALUES ('rental') RETURNING deal_id")[0]
        self.deals.append(deal)
        execute(conn, 'INSERT INTO app.deal_items(deal_id,account_id,reserve_key) VALUES (%s,%s,%s)', (deal, self.account, selected))
        self.service.assigned(conn, self.account, selected, actor, deal)
        return deal

    def race(self, operation):
        # Два независимых соединения начинают выдачу одновременно.
        barrier = threading.Barrier(2)

        def worker(actor):
            # Каждый запрос коммитится отдельно, как два параллельных HTTP-запроса.
            try:
                with self.connection() as conn:
                    barrier.wait(timeout=5)
                    operation(conn, actor)
                return 200
            except HTTPException as error:
                return error.status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            return sorted(pool.map(worker, ['test-alice', 'test-bob']))

    def test_concurrent_claim_has_one_winner(self):
        # Два сотрудника не могут получить один и тот же свободный код.
        self.assertEqual(self.race(lambda conn, actor: self.service.claim(conn, self.account, self.keys[0], actor)), [200, 409])

    def test_concurrent_assignment_has_one_winner(self):
        # Проверяем блокировку вместе с сохранением настоящей связи deal_items.
        self.assertEqual(self.race(lambda conn, actor: self.bind(conn, self.keys[0], actor)), [200, 409])

    def test_concurrent_edit_rejects_stale_snapshot(self):
        # Второй редактор после ожидания видит новый список и получает конфликт.
        expected = dict(zip(self.keys, ['TEST-A', 'TEST-B']))
        self.assertEqual(self.race(lambda conn, actor: self.service.replace(conn, self.account, [actor], actor, expected)), [200, 409])

    def test_replacement_and_completion_keep_new_value(self):
        # Замена занятой ячейки не переносит занятость, завершение удаляет прежний код.
        with self.connection() as conn:
            deal = self.bind(conn, self.keys[0])
            self.service.claim(conn, self.account, self.keys[0], 'test-alice', deal)
            new_key = self.service.replace(conn, self.account, ['TEST-NEW'], 'test-alice')[0]
            self.assertNotIn(new_key, self.service.used(conn, self.account))
            execute(conn, "UPDATE app.deals SET flow_status_code='completed' WHERE deal_id=%s", (deal,))
            self.service.finish_deal(conn, deal, 'test-alice')
            self.service.finish_deal(conn, deal, 'test-alice')
            rows = {row[1]: row for row in self.service.rows(conn, self.account)}
            self.assertIsNone(rows[self.keys[0]][6])
            self.assertIsNotNone(rows[new_key][6])
            self.assertEqual(one(conn, "SELECT count(*) FROM app.account_reserve_events WHERE deal_id=%s AND event_type='consumed'", (deal,))[0], 1)

    def test_completion_rollback_keeps_value_and_status(self):
        # Откат удаляет промежуточное списание вместе с изменением статуса сделки.
        with self.connection() as conn:
            deal = self.bind(conn, self.keys[0])
        with self.assertRaises(RuntimeError):
            with self.connection() as conn:
                execute(conn, "UPDATE app.deals SET flow_status_code='completed' WHERE deal_id=%s", (deal,))
                self.service.finish_deal(conn, deal, 'test-alice')
                raise RuntimeError('Simulated failure before commit')
        with self.connection() as conn:
            self.assertEqual(one(conn, 'SELECT flow_status_code FROM app.deals WHERE deal_id=%s', (deal,))[0], 'pending')
            self.assertIsNotNone(self.service.rows(conn, self.account)[0][6])

    def test_http_account_navigation_and_reserve_replacement(self):
        # Проверяем реальные маршруты и SQL вместе, без запуска фоновых задач или внешних сервисов.
        from fastapi.testclient import TestClient

        with patch('dotenv.load_dotenv', return_value=False), patch.dict(os.environ, {
            'DATABASE_URL': DSN, 'JWT_SECRET': 'isolated-reserves-test', 'GAMESALES_SUPPLIER_OFFLINE': '1',
        }):
            import app
        # Поднимаем только настоящий пул БД; полный lifespan запустил бы фоновые интеграции.
        pool = app.ConnectionPool(DSN, min_size=1, max_size=2)
        self.addCleanup(pool.close)
        pool_patch = patch.object(app, '_pool', pool)
        pool_patch.start()
        self.addCleanup(pool_patch.stop)
        app.app.dependency_overrides[app.get_current_user] = lambda: app.UserOut(username='test-alice', role='owner')
        try:
            # Без context manager TestClient не запускает lifespan приложения.
            client = TestClient(app.app)
            self.addCleanup(client.close)
            account_path = f'/accounts/{self.account}'
            response = client.get(account_path)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['account_id'], self.account)
            self.assertEqual(client.get(account_path + '/secrets').status_code, 200)
            claim = client.post(account_path + f'/reserves/{self.keys[0]}/claim', json={})
            self.assertEqual(claim.status_code, 200)
            response = client.post(account_path + '/secrets', json={'secret_key': self.keys[0], 'secret_value': ' TEST-NEW '})
            self.assertEqual(response.status_code, 200)
            new_key = response.json()['secret_key']
            self.assertNotEqual(new_key, self.keys[0])
            usage = client.get(account_path + '/reserve-usage')
            self.assertEqual(usage.status_code, 200)
            self.assertIn(self.keys[0], usage.json()['used_reserve_keys'])
            self.assertNotIn(new_key, usage.json()['used_reserve_keys'])
        finally:
            app.app.dependency_overrides.pop(app.get_current_user, None)


if __name__ == '__main__':
    unittest.main()
