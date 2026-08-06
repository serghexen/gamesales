import unittest
from datetime import date
from types import SimpleNamespace

from fastapi import FastAPI
from pydantic import BaseModel

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

from domains.interhub_api import mount_interhub_routes


class _FakeCursor:
    def __init__(self, queries):
        # Храним общий журнал SQL, чтобы проверка видела параметры маршрута.
        self.queries = queries

    def __enter__(self):
        # Поддерживаем контекстный менеджер так же, как настоящий курсор psycopg.
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Не подавляем ошибки, чтобы тест сразу показывал проблему в маршруте.
        return False

    def execute(self, sql, params):
        # Сохраняем запрос, чтобы проверить временные границы без настоящей БД.
        self.queries.append((sql, params))

    def fetchall(self):
        # История пуста: тест проверяет только границы запроса, а не данные БД.
        return []

    def fetchone(self):
        # Возвращаем пустые итоги для агрегатного запроса истории.
        return (0, 0)


class _FakeConnection:
    def __init__(self, queries):
        # Передаём журнал курсорам одного тестового подключения.
        self.queries = queries

    def __enter__(self):
        # Имитируем открытие соединения через конструкцию with.
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Оставляем исключения видимыми для unittest.
        return False

    def cursor(self):
        # Для каждого SQL-запроса создаём отдельный курсор с общим журналом вызовов.
        return _FakeCursor(self.queries)


class _FakePsycopg:
    def __init__(self, queries):
        # Сохраняем журнал, который получит созданное соединение.
        self.queries = queries

    def connect(self, _dsn):
        # Подменяем соединение, чтобы тест оставался изолированным от PostgreSQL.
        return _FakeConnection(self.queries)


@unittest.skipIf(TestClient is None, "fastapi.testclient requires httpx")
class InterhubApiTests(unittest.TestCase):
    def create_client(self):
        # Собираем изолированный маршрут с подменённым подключением к PostgreSQL.
        app = FastAPI()
        queries = []
        user = SimpleNamespace(username="operator", role="operator")
        mount_interhub_routes(
            app,
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(queries),
            get_current_user=lambda: user,
            require_role=lambda *_roles: lambda: user,
            UserOut=_ApiModel,
            InterHubServiceListOut=_ApiModel,
            InterHubBalanceOut=_ApiModel,
            InterHubPaymentRequestIn=_ApiModel,
            InterHubPaymentCheckOut=_ApiModel,
            InterHubPayRequestIn=_ApiModel,
            InterHubVoucherBatchPayRequestIn=_ApiModel,
            interhub_get_services=lambda: [],
            interhub_get_balance=lambda: {"balance": 0},
            interhub_calculate=lambda _payload: {},
            interhub_check=lambda _payload: {},
            interhub_pay=lambda _payload: {},
            interhub_check_status=lambda _transaction_id: {},
        )
        return TestClient(app), queries

    # Период из интерфейса должен начинаться и заканчиваться в полуночь МСК, а не UTC.
    def test_paid_history_uses_moscow_day_boundaries(self):
        client, queries = self.create_client()

        with client:
            response = client.get("/integrations/interhub/transactions/paid?date_from=2026-08-03&date_to=2026-08-03")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"total": 0, "total_amount": 0.0, "page": 1, "page_size": 25, "items": []})
        self.assertEqual(len(queries), 2)
        totals_sql, totals_params = queries[0]
        page_sql, page_params = queries[1]
        self.assertIn("created_at >= (%s::date::timestamp AT TIME ZONE 'Europe/Moscow')", totals_sql)
        self.assertIn("created_at < ((%s::date + 1)::timestamp AT TIME ZONE 'Europe/Moscow')", totals_sql)
        self.assertIn("SELECT COUNT(*), COALESCE(SUM(amount), 0)", totals_sql)
        self.assertIn("LIMIT %s OFFSET %s", page_sql)
        self.assertEqual(totals_params, [date(2026, 8, 3), date(2026, 8, 3)])
        self.assertEqual(page_params, [date(2026, 8, 3), date(2026, 8, 3), 25, 0])

    # Поиск, сортировка и номер страницы должны применяться на сервере ко всей истории.
    def test_paid_history_applies_server_pagination_search_and_sort(self):
        client, queries = self.create_client()

        with client:
            response = client.get(
                "/integrations/interhub/transactions/paid?search=Steam%25_&sort_by=price&sort_direction=asc&page=3&page_size=50"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(queries), 2)
        totals_sql, totals_params = queries[0]
        page_sql, page_params = queries[1]
        self.assertIn("service_title ILIKE %s", totals_sql)
        self.assertIn("ORDER BY amount ASC, agent_transaction_id ASC", page_sql)
        self.assertEqual(totals_params, [r"%Steam\%\_%", r"%Steam\%\_%", r"%Steam\%\_%"])
        self.assertEqual(page_params, [r"%Steam\%\_%", r"%Steam\%\_%", r"%Steam\%\_%", 50, 100])


class _ApiModel(BaseModel):
    pass
