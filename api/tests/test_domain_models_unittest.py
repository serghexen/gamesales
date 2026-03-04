import unittest
from datetime import date, datetime, timezone

from domains.accounts_models import AccountCreate, AccountOut, AccountUpdate
from domains.analytics_models import (
    RepeatCustomersOut,
    SalesAnalyticsByType,
    SalesAnalyticsOut,
    SalesAnalyticsPoint,
    SalesAnalyticsTotals,
    SourcesAnalyticsOut,
)
from domains.deals_models import DealCreate, DealUpdate, RentalCreate
from domains.telegram_models import TelegramDialogsOut


class AccountsModelsTests(unittest.TestCase):
    # account_date из datetime в полуночь должен конвертироваться в date.
    def test_account_create_normalizes_midnight_datetime_to_date(self):
        model = AccountCreate(account_date=datetime(2026, 2, 9, 0, 0))
        self.assertEqual(model.account_date, date(2026, 2, 9))

    # account_date из datetime в полуночь должен конвертироваться в date и в update-модели.
    def test_account_update_normalizes_midnight_datetime_to_date(self):
        model = AccountUpdate(account_date=datetime(2026, 2, 9, 0, 0))
        self.assertEqual(model.account_date, date(2026, 2, 9))

    # datetime с временем также должен нормализоваться в date.
    def test_account_date_normalizes_inexact_datetime(self):
        model = AccountCreate(account_date=datetime(2026, 2, 9, 12, 30))
        self.assertEqual(model.account_date, date(2026, 2, 9))

    # Проверяем, что list-поле не "шарится" между экземплярами.
    def test_account_out_slot_status_not_shared_between_instances(self):
        first = AccountOut(
            account_id=1,
            region_code="RU",
            status="active",
            login_name="a",
            domain_code="x.com",
            login_full="a@x.com",
            platform_slots=[],
        )
        second = AccountOut(
            account_id=2,
            region_code="RU",
            status="active",
            login_name="b",
            domain_code="x.com",
            login_full="b@x.com",
            platform_slots=[],
        )
        first.slot_status.append({"slot_type_code": "primary", "platform_code": "ps5", "mode": "single", "capacity": 1, "occupied": 0, "free": 1})
        self.assertEqual(len(second.slot_status), 0)
        self.assertEqual(first.is_deactivated, False)


class DealsModelsTests(unittest.TestCase):
    # purchase_at из date должен стать datetime в UTC.
    def test_rental_create_normalizes_date_to_utc_datetime(self):
        model = RentalCreate(account_id=1, customer_nickname="nick", purchase_at=date(2026, 2, 9))
        self.assertEqual(model.purchase_at, datetime(2026, 2, 9, 0, 0, tzinfo=timezone.utc))

    # naive datetime должен получить UTC tzinfo.
    def test_deal_create_normalizes_naive_datetime_to_utc(self):
        model = DealCreate(deal_type_code="sale", customer_nickname="nick", purchase_at=datetime(2026, 2, 9, 12, 0))
        self.assertEqual(model.purchase_at.tzinfo, timezone.utc)

    # aware datetime должен остаться без изменения tzinfo.
    def test_deal_update_preserves_aware_datetime(self):
        aware = datetime(2026, 2, 9, 12, 0, tzinfo=timezone.utc)
        model = DealUpdate(purchase_at=aware)
        self.assertEqual(model.purchase_at, aware)

    # Для черновика покупатель может быть пустым, поэтому поле не является обязательным в модели.
    def test_deal_create_allows_empty_customer_nickname(self):
        model = DealCreate(deal_type_code="sale")
        self.assertIsNone(model.customer_nickname)


class AnalyticsModelsTests(unittest.TestCase):
    # Проверяем сборку вложенной аналитики.
    def test_sales_analytics_out_builds_nested_payload(self):
        model = SalesAnalyticsOut(
            totals=SalesAnalyticsTotals(
                revenue=1000,
                purchase_cost=400,
                margin=600,
                count=10,
                avg_check=100,
            ),
            by_day=[
                SalesAnalyticsPoint(
                    date=date(2026, 2, 9),
                    revenue=500,
                    purchase_cost=200,
                    margin=300,
                    count=5,
                )
            ],
            by_type=[
                SalesAnalyticsByType(
                    deal_type_code="sale",
                    revenue=1000,
                    purchase_cost=400,
                    margin=600,
                    count=10,
                )
            ],
        )
        self.assertEqual(model.totals.count, 10)
        self.assertEqual(model.by_day[0].date, date(2026, 2, 9))
        self.assertEqual(model.by_type[0].deal_type_code, "sale")

    # Проверяем сборку аналитики источников.
    def test_sources_analytics_out_builds_nested_payload(self):
        model = SourcesAnalyticsOut(
            top_by_count=[],
            top_by_revenue=[],
            repeat_customers=RepeatCustomersOut(repeat_count=2, total_customers=10, repeat_share=0.2),
        )
        self.assertEqual(model.repeat_customers.repeat_count, 2)


class TelegramModelsTests(unittest.TestCase):
    # Проверяем дефолты и отсутствие общего mutable-состояния между экземплярами.
    def test_telegram_dialogs_out_defaults_and_not_shared(self):
        first = TelegramDialogsOut(items=[])
        second = TelegramDialogsOut(items=[])

        self.assertEqual(first.counts, {})
        self.assertEqual(second.counts, {})
        self.assertEqual(first.sync_running, False)
        self.assertEqual(first.sync_loaded, 0)
        self.assertEqual(first.sync_batches, 0)

        first.counts["new"] = 1
        self.assertEqual(second.counts, {})


if __name__ == "__main__":
    unittest.main()
