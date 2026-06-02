import unittest
from datetime import date, datetime
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

import app as app_module


class _ScriptedCursor:
    def __init__(self, script, sql_collector=None):
        self._script = script
        self._current = None
        self.rowcount = 0
        self._sql_collector = sql_collector

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def execute(self, sql, params=None):
        if self._sql_collector is not None:
            self._sql_collector.append(str(sql))
        if not self._script:
            raise AssertionError(f"Unexpected SQL without scripted response: {sql}")
        self._current = self._script.pop(0)

    def fetchone(self):
        if not self._current:
            return None
        return self._current.get("one")

    def fetchall(self):
        if not self._current:
            return []
        return self._current.get("all", [])


class _ScriptedConnCtx:
    def __init__(self, script, sql_collector=None):
        self._script = list(script)
        self._sql_collector = sql_collector

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def commit(self):
        return None

    def cursor(self):
        return _ScriptedCursor(self._script, sql_collector=self._sql_collector)


@unittest.skipIf(TestClient is None, "fastapi.testclient requires httpx")
class FinanceReportsTests(unittest.TestCase):
    def _client(self):
        return TestClient(app_module.app)

    def _auth_headers(self, role="admin", username="admin", user_id=1):
        token = app_module.create_access_token(user_id, username, role)
        return {"Authorization": f"Bearer {token}"}

    # Отчет по источникам должен считать услуги, шеринг с суммой продажи и ручные finance-проводки.
    def test_finance_sources_report_success(self):
        script = [
            {
                "all": [
                    (99, "asat", "ASAT", 10, "TR", "Turkey", 10000.0, 7000.0, 2),
                ],
            },
        ]
        sql_collector = []
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script, sql_collector=sql_collector)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get(
                    "/finance/reports/sources?date_from=2026-06-01&date_to=2026-06-30",
                    headers=self._auth_headers(role="manager"),
                )

        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["totals"]["revenue"], "10000.00")
        self.assertEqual(body["totals"]["direct_expense"], "7000.00")
        self.assertEqual(body["totals"]["operating_profit"], "3000.00")
        self.assertEqual(body["items"][0]["cash_flow"], "3000.00")
        self.assertTrue(any("d.deal_type_code = 'sale'" in sql for sql in sql_collector))
        self.assertTrue(any("d.deal_type_code = 'rental' AND COALESCE(di.price, 0) > 0" in sql for sql in sql_collector))
        self.assertTrue(any("WHEN d.deal_type_code = 'sale'" in sql for sql in sql_collector))
        self.assertTrue(any("d.flow_status_code = 'completed'" in sql for sql in sql_collector))
        self.assertTrue(any("di.returned_at IS NULL" in sql for sql in sql_collector))
        self.assertTrue(any("FROM finance.entry_postings p" in sql for sql in sql_collector))
        self.assertTrue(any("e.input_channel = 'manual'" in sql for sql in sql_collector))
        self.assertTrue(any("HAVING COALESCE(SUM(revenue), 0) <> 0" in sql for sql in sql_collector))

    # Cash Flow должен отдавать поступления/расходы отдельными строками и считать остатки.
    def test_finance_cash_flow_report_success(self):
        script = [
            {
                "all": [
                    ("revenue", "Продажа TR", 15000.0),
                    ("revenue", "Шеринг TR", 5000.0),
                    ("expense", "Закуп TR", 6000.0),
                    ("expense", "Маркетинг", 1000.0),
                ],
            },
            {"one": (date(2026, 6, 1), 3000.0)},
        ]
        sql_collector = []
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script, sql_collector=sql_collector)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get(
                    "/finance/reports/cash-flow?month=2026-06",
                    headers=self._auth_headers(role="manager"),
                )

        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["totals"]["revenue"], "20000.00")
        self.assertEqual(body["totals"]["expense"], "7000.00")
        self.assertEqual(body["totals"]["cash_flow"], "13000.00")
        self.assertEqual(body["totals"]["opening_balance"], "3000.00")
        self.assertEqual(body["totals"]["current_balance"], "16000.00")
        self.assertEqual(body["totals"]["opening_balance_month"], "2026-06-01")
        self.assertEqual(body["totals"]["opening_balance_manual"], True)
        self.assertEqual(body["revenues"][0]["name"], "Продажа TR")
        self.assertEqual(body["expenses"][0]["name"], "Закуп TR")
        self.assertTrue(any("d.deal_type_code = 'rental' AND COALESCE(di.price, 0) > 0" in sql for sql in sql_collector))
        self.assertTrue(any("CONCAT('Закуп '" in sql for sql in sql_collector))
        self.assertTrue(any("e.input_channel = 'manual'" in sql for sql in sql_collector))

    # Если у месяца нет ручного остатка, берем ближайший прошлый и добавляем накопленный cash flow.
    def test_finance_cash_flow_report_uses_previous_opening_balance(self):
        script = [
            {"all": [("revenue", "Продажа TR", 1000.0)]},
            {"one": (date(2026, 5, 1), 5000.0)},
            {"one": (700.0,)},
        ]
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.get(
                    "/finance/reports/cash-flow?month=2026-07",
                    headers=self._auth_headers(role="manager"),
                )

        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["totals"]["opening_balance"], "5700.00")
        self.assertEqual(body["totals"]["current_balance"], "6700.00")
        self.assertEqual(body["totals"]["opening_balance_month"], "2026-05-01")
        self.assertEqual(body["totals"]["opening_balance_manual"], False)

    # Начальный остаток Cash Flow должен сохраняться на первое число месяца.
    def test_finance_cash_flow_opening_balance_upsert(self):
        script = [
            {"one": (date(2026, 7, 1), 12345.67, "start", datetime(2026, 6, 2, 10, 0, 0))},
        ]
        sql_collector = []
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script, sql_collector=sql_collector)),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.put(
                    "/finance/cash-flow/opening-balance",
                    json={"month": "2026-07", "amount": "12345.67", "comment": "start"},
                    headers=self._auth_headers(role="admin"),
                )

        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["month"], "2026-07-01")
        self.assertEqual(body["amount"], "12345.67")
        self.assertTrue(any("finance.cash_flow_opening_balances" in sql for sql in sql_collector))


if __name__ == "__main__":
    unittest.main()
