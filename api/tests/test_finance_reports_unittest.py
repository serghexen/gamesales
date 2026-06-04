import os
import unittest
from datetime import date, datetime
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

import app as app_module
from domains import finance_api as finance_api_module


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
                    "/finance/reports/sources?date_from=2026-06-01&date_to=2026-06-30&region_id=10&region_id=11&source_id=99&source_id=100",
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
        self.assertTrue(any("CASE WHEN d.deal_type_code = 'rental' THEN NULL ELSE fdr.region_id END AS region_id" in sql for sql in sql_collector))
        self.assertTrue(any("WHEN d.deal_type_code = 'rental'" in sql and "THEN di.purchase_cost * di.qty" in sql for sql in sql_collector))
        self.assertTrue(any("WHEN d.deal_type_code = 'sale'" in sql for sql in sql_collector))
        self.assertTrue(any("d.flow_status_code = 'completed'" in sql for sql in sql_collector))
        self.assertTrue(any("di.returned_at IS NULL" in sql for sql in sql_collector))
        self.assertTrue(any("FROM finance.entry_postings p" in sql for sql in sql_collector))
        self.assertTrue(any("e.input_channel IN ('manual', 'api', 'import')" in sql for sql in sql_collector))
        self.assertTrue(any("JOIN finance.section_types st ON st.type_id = o.type_id" in sql for sql in sql_collector))
        self.assertTrue(any("st.code = 'revenue' AND p.metric_code = 'revenue'" in sql for sql in sql_collector))
        self.assertTrue(any("st.code = 'direct_expense' AND p.metric_code = 'direct_expense'" in sql for sql in sql_collector))
        self.assertFalse(any("p.metric_code IN ('revenue', 'direct_expense')" in sql for sql in sql_collector))
        self.assertFalse(any("p.metric_code IN ('revenue', 'direct_expense', 'indirect_expense')" in sql for sql in sql_collector))
        self.assertTrue(any("region_id = ANY(%s)" in sql for sql in sql_collector))
        self.assertTrue(any("source_id = ANY(%s)" in sql for sql in sql_collector))
        self.assertTrue(any("HAVING COALESCE(SUM(revenue), 0) <> 0" in sql for sql in sql_collector))

    # Детализация строки отчета должна возвращать сделки/проводки с теми же фильтрами, что и агрегат.
    def test_finance_sources_report_details_success(self):
        script = [
            {
                "all": [
                    (
                        "deal",
                        16308,
                        None,
                        date(2026, 6, 2),
                        None,
                        "LifeGuard58",
                        None,
                        None,
                        "Без источника",
                        10,
                        "TR",
                        "Turkey",
                        "Услуга",
                        "item-16308",
                        "1",
                        "5810.00",
                        "1660.00",
                        "2.5",
                        "4150.00",
                        None,
                        None,
                        ["577", "578"],
                        ["SKU-1", "SKU-2"],
                        2,
                        2,
                        "Источник клиента не привязан к finance source",
                    ),
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
                    "/finance/reports/sources/details?date_from=2026-06-02&date_to=2026-06-02&source_empty=1&region_id=10",
                    headers=self._auth_headers(role="manager"),
                )

        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["totals"]["revenue"], "5810.00")
        self.assertEqual(body["totals"]["direct_expense"], "4150.00")
        self.assertEqual(body["totals"]["operating_profit"], "1660.00")
        self.assertEqual(body["items"][0]["deal_id"], 16308)
        self.assertEqual(body["items"][0]["customer_name"], "LifeGuard58")
        self.assertEqual(body["items"][0]["purchase_cost_rate"], "2.5")
        self.assertEqual(body["items"][0]["order_ids"], ["577", "578"])
        self.assertEqual(body["items"][0]["orders_count"], 2)
        self.assertTrue(any("source_id IS NULL" in sql for sql in sql_collector))
        self.assertTrue(any("region_id = %s" in sql for sql in sql_collector))
        self.assertTrue(any("JOIN finance.section_types st ON st.type_id = o.type_id" in sql for sql in sql_collector))
        self.assertTrue(any("st.code = 'revenue' AND p.metric_code = 'revenue'" in sql for sql in sql_collector))
        self.assertTrue(any("st.code = 'direct_expense' AND p.metric_code = 'direct_expense'" in sql for sql in sql_collector))
        self.assertFalse(any("p.metric_code IN ('revenue', 'direct_expense')" in sql for sql in sql_collector))
        self.assertFalse(any("p.metric_code IN ('revenue', 'direct_expense', 'indirect_expense')" in sql for sql in sql_collector))

    # Cash Flow должен отдавать поступления/расходы отдельными строками и считать остатки.
    def test_finance_cash_flow_report_success(self):
        script = [
            {
                "all": [
                    ("revenue", "Продажа TR", 15000.0),
                    ("revenue", "Продажа Шеринг", 5000.0),
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
        self.assertTrue(any("WHEN d.deal_type_code = 'rental' THEN 'Продажа Шеринг'" in sql for sql in sql_collector))
        self.assertTrue(any("'Закуп Шеринг' AS line_name" in sql for sql in sql_collector))
        self.assertTrue(any("CONCAT('Закуп '" in sql for sql in sql_collector))
        self.assertTrue(any("e.input_channel IN ('manual', 'api', 'import')" in sql for sql in sql_collector))

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

    # Смена типа операции должна пересобрать postings, чтобы отчеты не жили со старой классификацией.
    def test_finance_update_operation_rebuilds_entry_postings_on_type_change(self):
        script = [
            {
                "one": (
                    15,
                    2,
                    None,
                    "zakup_shering",
                    "Закуп шеринг",
                    "mixed",
                    False,
                    False,
                    False,
                    False,
                    False,
                    0,
                    True,
                ),
            },
            {"one": (1,)},  # type lookup
            {
                "one": (
                    15,
                    3,
                    None,
                    "zakup_shering",
                    "Закуп шеринг",
                    "mixed",
                    False,
                    False,
                    False,
                    False,
                    False,
                    0,
                    True,
                ),
            },
            {"one": ("indirect_expense",)},  # rebuild metric lookup
            {},
            {},
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
                    "/finance/catalogs/operations/15",
                    json={"type_id": 3},
                    headers=self._auth_headers(role="admin"),
                )

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["type_id"], 3)
        self.assertTrue(any("DELETE FROM finance.entry_postings p" in sql for sql in sql_collector))
        self.assertTrue(any("p.formula_id IS NULL" in sql for sql in sql_collector))
        self.assertTrue(any("INSERT INTO finance.entry_postings" in sql for sql in sql_collector))

    # Ручная синхронизация Яндекса должна сворачивать строки заказов в дневные gross/commission проводки.
    def test_finance_yandex_sync_creates_daily_gross_and_commission_entries(self):
        yandex_rows = [
            {
                "biz_date": date(2026, 6, 1),
                "amount": "123.45",
                "order_id": "577",
                "shop_sku": "SKU-1",
                "external_key": "yandex-market:united-orders:70940298:577:SKU-1:2026-06-01",
                "payload_json": {
                    "provider": "yandex_market",
                    "campaign_id": 70940298,
                    "raw": {
                        "incomeWithoutServices": 123.45,
                        "sumBillingPriceOfItems": 200,
                        "summaryCommission": 76.55,
                    },
                },
            },
            {
                "biz_date": date(2026, 6, 1),
                "amount": "76.55",
                "order_id": "578",
                "shop_sku": "SKU-2",
                "external_key": "yandex-market:united-orders:70940298:578:SKU-2:2026-06-01",
                "payload_json": {
                    "provider": "yandex_market",
                    "campaign_id": 70940298,
                    "raw": {
                        "incomeWithoutServices": 76.55,
                        "sumBillingPriceOfItems": 100,
                        "summaryCommission": 23.45,
                    },
                },
            },
        ]
        script = [
            {"one": (99,)},  # source
            {"one": (1,)},  # project
            {"one": (7,)},  # revenue operation
            {"one": (7, 2, "revenue_marketplace_api", "Продажи маркетплейсов", "api", False, False, False, False, False, 10, True, "revenue")},
            {"one": (1,)},  # source lookup
            {"one": (1,)},  # project lookup
            {"one": (1,)},  # status lookup
            {"one": None},  # no dedupe
            {
                "one": (
                    701,
                    date(2026, 6, 1),
                    7,
                    None,
                    99,
                    1,
                    "1",
                    "300.00",
                    "RUB",
                    "api",
                    "yandex-market:united-orders:70940298:daily:2026-06-01:gross",
                    "confirmed",
                    "Yandex Market; доставленные за 2026-06-01; строк 2; поступления gross",
                    "admin",
                    datetime(2026, 6, 2, 10, 0, 0),
                    datetime(2026, 6, 2, 10, 0, 0),
                ),
            },
            {},
            {},
            {},
            {"one": (8,)},  # commission operation
            {"one": (8, 3, "direct_marketplace_commission_api", "Комиссии маркетплейсов", "api", False, False, False, False, False, 20, True, "direct_expense")},
            {"one": (1,)},  # source lookup
            {"one": (1,)},  # project lookup
            {"one": (1,)},  # status lookup
            {"one": None},  # no dedupe
            {
                "one": (
                    702,
                    date(2026, 6, 1),
                    8,
                    None,
                    99,
                    1,
                    "1",
                    "100.00",
                    "RUB",
                    "api",
                    "yandex-market:united-orders:70940298:daily:2026-06-01:commission",
                    "confirmed",
                    "Yandex Market; доставленные за 2026-06-01; строк 2; комиссии и услуги",
                    "admin",
                    datetime(2026, 6, 2, 10, 0, 0),
                    datetime(2026, 6, 2, 10, 0, 0),
                ),
            },
            {},
            {},
            {},
        ]
        sql_collector = []
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script, sql_collector=sql_collector)),
            patch.object(finance_api_module, "fetch_yandex_market_order_economics", return_value=yandex_rows),
            patch.dict(os.environ, {"FINANCE_YANDEX_SYNC_INLINE": "1"}),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/finance/integrations/yandex/sync",
                    json={"date_from": "2026-06-01", "date_to": "2026-06-01"},
                    headers=self._auth_headers(role="admin"),
                )

        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["status"], "done")
        self.assertEqual(body["result"]["total_rows"], 2)
        self.assertEqual(body["result"]["created_rows"], 1)
        self.assertEqual(body["result"]["skipped_rows"], 0)
        self.assertTrue(any("finance.entries" in sql and "input_channel" in sql for sql in sql_collector))
        self.assertTrue(any("finance.entry_dedupe_keys" in sql for sql in sql_collector))

    # Повторная синхронизация Яндекса должна обновлять дневной итог, если отчет пересчитался.
    def test_finance_yandex_sync_updates_existing_daily_entry(self):
        yandex_rows = [
            {
                "biz_date": date(2026, 6, 1),
                "amount": "300.00",
                "order_id": "577",
                "shop_sku": "SKU-1",
                "external_key": "yandex-market:united-orders:70940298:577:SKU-1:2026-06-01",
                "payload_json": {
                    "provider": "yandex_market",
                    "campaign_id": 70940298,
                    "raw": {
                        "incomeWithoutServices": 300,
                        "sumBillingPriceOfItems": 300,
                        "summaryCommission": 0,
                    },
                },
            },
        ]
        existing_created_at = datetime(2026, 6, 2, 10, 0, 0)
        existing_updated_at = datetime(2026, 6, 2, 10, 0, 0)
        refreshed_updated_at = datetime(2026, 6, 3, 10, 0, 0)
        script = [
            {"one": (99,)},  # source
            {"one": (1,)},  # project
            {"one": (7,)},  # revenue operation
            {"one": (7, 2, "revenue_marketplace_api", "Продажи маркетплейсов", "api", False, False, False, False, False, 10, True, "revenue")},
            {"one": (1,)},  # source lookup
            {"one": (1,)},  # project lookup
            {"one": (1,)},  # status lookup
            {
                "one": (
                    701,
                    date(2026, 6, 1),
                    7,
                    None,
                    99,
                    1,
                    "1",
                    "250.00",
                    "RUB",
                    "api",
                    "yandex-market:united-orders:70940298:daily:2026-06-01:gross",
                    "confirmed",
                    "old yandex gross",
                    "admin",
                    existing_created_at,
                    existing_updated_at,
                ),
            },
            {"one": (7, 2, "revenue_marketplace_api", "Продажи маркетплейсов", "api", False, False, False, False, False, 10, True, "revenue")},
            {
                "one": (
                    701,
                    date(2026, 6, 1),
                    7,
                    None,
                    99,
                    1,
                    "1",
                    "300.00",
                    "RUB",
                    "api",
                    "yandex-market:united-orders:70940298:daily:2026-06-01:gross",
                    "confirmed",
                    "Yandex Market; доставленные за 2026-06-01; строк 1; поступления gross",
                    "admin",
                    existing_created_at,
                    refreshed_updated_at,
                ),
            },
            {},
            {},
            {},
        ]
        sql_collector = []
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script, sql_collector=sql_collector)),
            patch.object(finance_api_module, "fetch_yandex_market_order_economics", return_value=yandex_rows),
            patch.dict(os.environ, {"FINANCE_YANDEX_SYNC_INLINE": "1"}),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/finance/integrations/yandex/sync",
                    json={"date_from": "2026-06-01", "date_to": "2026-06-01"},
                    headers=self._auth_headers(role="admin"),
                )

        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["result"]["created_rows"], 0)
        self.assertEqual(body["result"]["updated_rows"], 1)
        self.assertEqual(body["result"]["skipped_rows"], 0)
        self.assertTrue(any("UPDATE finance.entries" in sql for sql in sql_collector))
        self.assertTrue(any("DELETE FROM finance.entry_postings" in sql for sql in sql_collector))

    # Если стандартной операции Яндекса нет, backend должен создать ее сам.
    def test_finance_yandex_sync_creates_missing_revenue_operation(self):
        yandex_rows = [
            {
                "biz_date": date(2026, 6, 1),
                "amount": "77.00",
                "order_id": "578",
                "shop_sku": "SKU-2",
                "external_key": "yandex-market:united-orders:70940298:578:SKU-2:2026-06-01",
                "payload_json": {"provider": "yandex_market", "campaign_id": 70940298, "raw": {"incomeWithoutServices": 77}},
            },
        ]
        script = [
            {"one": (99,)},  # source
            {"one": None},  # no project
            {"one": None},  # no operation by code
            {"one": (2,)},  # inserted revenue type
            {},  # inserted revenue section
            {"one": (7,)},  # inserted operation
            {"one": (7, 2, "revenue_marketplace_api", "Продажи маркетплейсов", "api", False, False, False, False, False, 10, True, "revenue")},
            {"one": (1,)},  # source lookup
            {"one": (1,)},  # status lookup
            {"one": None},  # no dedupe
            {
                "one": (
                    702,
                    date(2026, 6, 1),
                    7,
                    None,
                    99,
                    None,
                    "1",
                    "77.00",
                    "RUB",
                    "api",
                    "yandex-market:united-orders:70940298:daily:2026-06-01:gross",
                    "confirmed",
                    "Yandex Market; доставленные за 2026-06-01; строк 1; поступления gross",
                    "admin",
                    datetime(2026, 6, 2, 10, 0, 0),
                    datetime(2026, 6, 2, 10, 0, 0),
                ),
            },
            {},
            {},
            {},
        ]
        sql_collector = []
        with (
            patch.object(app_module, "ensure_analytics_schema", return_value=None),
            patch.object(app_module.psycopg, "connect", return_value=_ScriptedConnCtx(script, sql_collector=sql_collector)),
            patch.object(finance_api_module, "fetch_yandex_market_order_economics", return_value=yandex_rows),
            patch.dict(os.environ, {"FINANCE_YANDEX_SYNC_INLINE": "1"}),
            patch.object(app_module, "JWT_SECRET", "test-secret"),
            patch.object(app_module, "JWT_ALG", "HS256"),
        ):
            with self._client() as client:
                res = client.post(
                    "/finance/integrations/yandex/sync",
                    json={"date_from": "2026-06-01", "date_to": "2026-06-01"},
                    headers=self._auth_headers(role="admin"),
                )

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["result"]["created_rows"], 1)
        self.assertTrue(any("INSERT INTO finance.operations" in sql for sql in sql_collector))

    # Журнал должен уметь фильтровать ручной ввод по input_channel без падения endpoint.
    def test_finance_entries_journal_filters_manual_channel(self):
        created_at = datetime(2026, 6, 2, 10, 0, 0)
        script = [
            {"one": (1,)},
            {
                "all": [
                    (
                        77,
                        date(2026, 6, 2),
                        7,
                        None,
                        None,
                        None,
                        "1.00",
                        "100.00",
                        "RUB",
                        "manual",
                        "ui-test",
                        "confirmed",
                        "manual add",
                        "admin",
                        created_at,
                        created_at,
                    ),
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
                    "/finance/entries?input_channel=manual",
                    headers=self._auth_headers(role="admin"),
                )

        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["items"][0]["input_channel"], "manual")
        self.assertTrue(any("e.input_channel = %s" in sql for sql in sql_collector))


if __name__ == "__main__":
    unittest.main()
