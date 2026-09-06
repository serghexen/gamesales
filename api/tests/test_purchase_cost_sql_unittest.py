import sqlite3
import unittest

from domains.purchase_cost_sql import purchase_cost_rate_sql


class PurchaseCostSqlTests(unittest.TestCase):
    def setUp(self):
        # Выполняем общий CASE/EXISTS на локальных данных без доступа к рабочей БД.
        self.conn = sqlite3.connect(":memory:")
        self.addCleanup(self.conn.close)
        self.conn.executescript("""
            ATTACH DATABASE ':memory:' AS app;
            CREATE TABLE app.interhub_transactions (deal_id INTEGER, state TEXT);
            CREATE TABLE deals (deal_id INTEGER, deal_type_code TEXT);
            CREATE TABLE regions (code TEXT, purchase_cost_rate NUMERIC);
            INSERT INTO deals VALUES (42, 'sale');
            INSERT INTO regions VALUES ('TR', 2.5);
        """)

    def cost_and_rate(self, cost=100, qty=1, legacy_rate_sql=None):
        # Проверяем и итоговую сумму, и коэффициент, который показывается в детализации.
        rate = purchase_cost_rate_sql() if legacy_rate_sql is None else purchase_cost_rate_sql(legacy_rate_sql)
        return self.conn.execute(f"""
            SELECT SUM(? * ? * {rate}), MAX({rate}), COUNT(*)
            FROM deals d CROSS JOIN regions rd
        """, (cost, qty)).fetchone()

    def test_paid_vouchers_use_rubles_in_turkey_and_poland(self):
        # Две покупки одной сделки подтверждают валюту, но не удваивают расход.
        self.conn.executemany("INSERT INTO app.interhub_transactions VALUES (?, ?)", [(42, "paid"), (42, "paid")])
        for region in ("TR", "PL"):
            with self.subTest(region=region):
                self.conn.execute("UPDATE regions SET code=?", (region,))
                self.assertEqual(self.cost_and_rate(cost=1911.36, qty=2), (3822.72, 1, 1))

    def test_historical_and_unpaid_deals_keep_regional_rate(self):
        # Чужая оплата и любые неоплаченные покупки не меняют старый валютный закуп.
        self.conn.execute("INSERT INTO app.interhub_transactions VALUES (99, 'paid')")
        for region in ("TR", "PL"):
            self.conn.execute("UPDATE regions SET code=?", (region,))
            for state in (None, "checked", "processing", "failed", "cancelled"):
                with self.subTest(region=region, state=state):
                    self.conn.execute("DELETE FROM app.interhub_transactions WHERE deal_id=42")
                    if state:
                        self.conn.execute("INSERT INTO app.interhub_transactions VALUES (42, ?)", (state,))
                    self.assertEqual(self.cost_and_rate(qty=2), (500, 2.5, 1))

    def test_other_regions_and_rental_keep_previous_rule(self):
        # Наличие связи с поставщиком не меняет правила других регионов и шеринга.
        self.conn.execute("INSERT INTO app.interhub_transactions VALUES (42, 'paid')")
        for region, deal_type in (("UA", "sale"), ("TR", "rental"), ("PL", "rental")):
            with self.subTest(region=region, deal_type=deal_type):
                self.conn.execute("UPDATE regions SET code=?", (region,))
                self.conn.execute("UPDATE deals SET deal_type_code=?", (deal_type,))
                self.assertEqual(self.cost_and_rate(), (250, 2.5, 1))

    def test_missing_rate_and_analytics_fallback_are_preserved(self):
        # Аналитика сохраняет запасной коэффициент региона аккаунта для старых сделок.
        self.conn.execute("UPDATE regions SET purchase_cost_rate=NULL")
        self.assertEqual(self.cost_and_rate(), (100, 1, 1))
        fallback = "COALESCE(rd.purchase_cost_rate, 3.0, 1.0)"
        self.assertEqual(self.cost_and_rate(legacy_rate_sql=fallback), (300, 3, 1))
        self.conn.execute("INSERT INTO app.interhub_transactions VALUES (42, 'paid')")
        self.assertEqual(self.cost_and_rate(legacy_rate_sql=fallback), (100, 1, 1))

    def test_paid_and_historical_costs_aggregate_independently(self):
        # В одном периоде рублёвый ваучер и старая валютная сделка считают каждый свой расход.
        self.conn.execute("INSERT INTO deals VALUES (43, 'sale')")
        self.conn.execute("INSERT INTO app.interhub_transactions VALUES (42, 'paid')")
        self.assertEqual(self.cost_and_rate(), (350, 2.5, 2))

    def test_screenshot_cost_is_not_converted_twice(self):
        # Сумма со скриншота остаётся закупом в рублях и даёт положительный результат.
        self.conn.execute("INSERT INTO app.interhub_transactions VALUES (42, 'paid')")
        expense, rate, _ = self.cost_and_rate(cost=29626.08)
        self.assertEqual(rate, 1)
        self.assertAlmostEqual(expense, 29626.08)
        self.assertAlmostEqual(48800 - expense, 19173.92)
