import unittest
from datetime import date

from app import build_deals_filters


def call_build_deals_filters(**overrides):
    base = dict(
        account_id=None,
        game_id=None,
        platform_code=None,
        q=None,
        deal_type_code=None,
        status_code=None,
        flow_status_code=None,
        customer_q=None,
        source_id=None,
        purchase_from=None,
        purchase_to=None,
        price_min=None,
        price_max=None,
        notes_q=None,
        account_q=None,
        region_q=None,
        game_q=None,
        platform_q=None,
        type_q=None,
        status_q=None,
        flow_status_q=None,
        source_q=None,
        date_q=None,
        price_q=None,
    )
    base.update(overrides)
    return build_deals_filters(**base)


class DealsFiltersTests(unittest.TestCase):
    # Без фильтров возвращаются пустые where и параметры.
    def test_build_deals_filters_empty(self):
        where_sql, params = call_build_deals_filters()
        self.assertEqual(where_sql, "")
        self.assertEqual(params, [])

    # Проверяем базовые прямые фильтры по id/коду.
    def test_build_deals_filters_simple_fields(self):
        where_sql, params = call_build_deals_filters(
            account_id=11,
            game_id=22,
            platform_code="ps5",
            deal_type_code="sale",
            status_code="open",
            flow_status_code="new",
            source_id=5,
        )
        self.assertIn("di.account_id = %s", where_sql)
        self.assertIn("di.game_id = %s", where_sql)
        self.assertIn("p.code = %s", where_sql)
        self.assertIn("d.deal_type_code = %s", where_sql)
        self.assertIn("d.status_code = %s", where_sql)
        self.assertIn("d.flow_status_code = %s", where_sql)
        self.assertIn("c.source_id = %s", where_sql)
        self.assertEqual(params, [11, 22, "ps5", "sale", "open", "new", 5])

    # Текстовый q должен добавлять 7 ILIKE-параметров с одним и тем же шаблоном.
    def test_build_deals_filters_global_query(self):
        where_sql, params = call_build_deals_filters(q="test")
        self.assertIn("c.nickname ILIKE %s", where_sql)
        self.assertIn("COALESCE(di.purchase_at, d.created_at)::text ILIKE %s", where_sql)
        self.assertEqual(params, ["%test%"] * 7)

    # Фильтры диапазонов по дате и цене должны попасть в where и params.
    def test_build_deals_filters_ranges(self):
        where_sql, params = call_build_deals_filters(
            purchase_from=date(2026, 2, 1),
            purchase_to=date(2026, 2, 9),
            price_min=100,
            price_max=500,
        )
        self.assertIn("COALESCE(di.purchase_at, d.created_at)::date >= %s", where_sql)
        self.assertIn("COALESCE(di.purchase_at, d.created_at)::date <= %s", where_sql)
        self.assertIn("di.price >= %s", where_sql)
        self.assertIn("di.price <= %s", where_sql)
        self.assertEqual(params, [date(2026, 2, 1), date(2026, 2, 9), 100, 500])

    # Для account_q должны использоваться сразу 2 поля (логин и домен).
    def test_build_deals_filters_account_q_expands_to_two_like_params(self):
        where_sql, params = call_build_deals_filters(account_q="sony")
        self.assertIn("(a.login_name ILIKE %s OR dm.name ILIKE %s)", where_sql)
        self.assertEqual(params, ["%sony%", "%sony%"])


if __name__ == "__main__":
    unittest.main()
