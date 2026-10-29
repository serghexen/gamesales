"""Проверки списка ответственных на изолированном SQL, без подключения к рабочей БД."""

import sqlite3
import unittest
from inspect import signature
from types import SimpleNamespace
from domains.auth_api import mount_auth_routes


class RouteRegistry:
    def __init__(self):
        # Регистрируем обработчики без запуска FastAPI, фоновых задач и окружения приложения.
        self.routes = {}

    def get(self, path, **kwargs):
        # Для проверки нужен настоящий обработчик GET /users, остальные только регистрируются.
        def register(endpoint):
            self.routes[('GET', path)] = endpoint
            return endpoint
        return register

    def post(self, path, **kwargs):
        # POST/PUT не вызываются в этих проверках чтения справочника.
        return lambda endpoint: endpoint

    put = post


class ResponsibleUsersTests(unittest.TestCase):
    def setUp(self):
        # Выполняем настоящий запрос маршрута на тестовых пользователях в памяти.
        self.conn = sqlite3.connect(':memory:')
        self.addCleanup(self.conn.close)
        self.conn.executescript("""
            ATTACH DATABASE ':memory:' AS app;
            CREATE TABLE app.users(user_id INTEGER, username TEXT, name TEXT, role_code TEXT, created_at TEXT);
            INSERT INTO app.users VALUES
                (1, 'operator1', 'Оператор', 'operator', '2026-10-28T00:00:00Z'),
                (2, 'lera', 'Валерия', 'manager', '2026-10-28T00:00:00Z'),
                (3, 'admin1', 'Администратор', 'admin', '2026-10-28T00:00:00Z'),
                (4, 'owner1', 'Владелец', 'owner', '2026-10-28T00:00:00Z');
        """)
        registry = RouteRegistry()
        deps = {name: SimpleNamespace for name in signature(mount_auth_routes).parameters if name != 'app'}
        deps.update(
            DB_DSN='test-in-memory',
            psycopg=SimpleNamespace(connect=lambda _: self.conn),
            qall=lambda conn, sql: conn.execute(sql).fetchall(),
            get_current_user=lambda: None,
            require_role=lambda *roles: (lambda: None),
        )
        mount_auth_routes(registry, **deps)
        self.endpoint = registry.routes[('GET', '/users')]

    def list_users(self, role):
        # Роль задаём явно; фильтрацию выполняет SQL из настоящего обработчика.
        return self.endpoint(user=SimpleNamespace(username='viewer', role=role))

    def test_managers_and_operators_see_admins_but_not_owner(self):
        # Список ответственных показывает администраторов обеим рабочим ролям.
        for role in ('manager', 'operator'):
            with self.subTest(role=role):
                self.assertEqual([user.username for user in self.list_users(role)], ['operator1', 'lera', 'admin1'])

    def test_promotion_keeps_employee_in_responsible_list(self):
        # Повторяем ситуацию из обращения: меняется роль, но имя остаётся доступным.
        before = [user.name for user in self.list_users('operator')]
        self.conn.execute("UPDATE app.users SET role_code='admin' WHERE username='lera'")
        after = self.list_users('operator')
        self.assertEqual([user.name for user in after], before)
        self.assertEqual(next(user.role for user in after if user.username == 'lera'), 'admin')

    def test_privileged_users_still_see_owner(self):
        # Исправление не сужает прежний справочник администратора и владельца.
        for role in ('admin', 'owner'):
            with self.subTest(role=role):
                self.assertEqual(len(self.list_users(role)), 4)


if __name__ == '__main__':
    unittest.main()
