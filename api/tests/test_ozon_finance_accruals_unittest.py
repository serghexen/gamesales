import os
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException

from api.domains import ozon_service


def money(amount):
    # Повторяем денежный объект API, чтобы тесты проверяли разбор строк и валюты.
    return {"amount": str(amount), "currency": "RUB"}


class OzonFinanceAccrualsTest(unittest.TestCase):
    def setUp(self):
        # Исключаем зависимость тестов от настоящих ключей и локальных настроек.
        env = patch.dict(os.environ, {
            "OZON_ASAT_CLIENT_ID": "test-client",
            "OZON_ASAT_API_KEY": "test-key",
            "OZON_TRANSACTION_MAX_PAGES": "10",
        })
        env.start()
        self.addCleanup(env.stop)
        self.day = date(2026, 9, 29)

    def test_daily_totals_include_returns_discounts_and_all_fee_categories(self):
        # Разные категории влияют на выплату один раз; баллы не увеличивают готовую реализацию.
        accruals = [
            {
                "accrual_id": 101, "date": "2026-09-29", "accrued_category": "POSTING",
                "unit_number": "sale-1", "total_amount": money("780.00"),
                "posting": {"products": [{
                    "commission": {
                        "seller_price": money("500"), "sale_price": money("450"),
                        "sale_amount": money("1000"), "bonus": money("80"), "coinvestment": money("20"),
                        "sale_commission": money("-200"), "commission": money("-150"),
                    },
                    "delivery": {"total_accrued": money("-70"), "services": [{"accrued": money("-70"), "type_id": 1}]},
                }]},
            },
            {
                "accrual_id": 102, "accrued_category": "POSTING", "unit_number": "return-1",
                "total_amount": money("-180"),
                "posting": {"products": [{
                    "commission": {"sale_amount": money("-200"), "sale_commission": money("40"), "commission": money("30")},
                    "delivery": {"total_accrued": money("-10")},
                }]},
            },
            {"accrual_id": 103, "accrued_category": "ITEM", "total_amount": money("-12"),
             "item_fees": {"fees": [{"sku": 123, "fees": [{"type_id": 1, "accrued": money("-12")}]}]}},
            {"accrual_id": 104, "accrued_category": "NON_ITEM", "total_amount": money("25.50"),
             "unit_number": "contract-1", "non_item_fee": {"type_id": 10, "accrued": money("25.50")}},
            {"accrual_id": 105, "accrued_category": "CONTAINER_FEES", "total_amount": money("-3"),
             "container_fees": {"fees": [{"type_id": 20, "accrued": money("-3")}]}},
        ]
        with patch.object(ozon_service, "_request_json", return_value={"accruals": accruals, "last_id": ""}):
            rows = ozon_service.fetch_ozon_finance_transactions(self.day, self.day)
        daily = ozon_service.aggregate_ozon_finance_transactions(rows, fallback_date=self.day)
        self.assertEqual(len(daily), 1)
        result = daily[0]
        self.assertEqual(result["gross_amount"], Decimal("1000"))
        self.assertEqual(result["payout_amount"], Decimal("610.50"))
        self.assertEqual(result["expense_amount"], Decimal("389.50"))
        self.assertEqual(result["external_key_base"], "ozon:asat:finance-transactions:daily:2026-09-29")
        details = result["payload_json"]
        self.assertEqual(details["report_type"], "finance_accrual_by_day_v1")
        self.assertEqual(Decimal(details["returns"]), Decimal("200"))
        self.assertEqual(Decimal(details["sale_commission"]), Decimal("-120"))
        self.assertEqual(Decimal(details["service_expenses"]), Decimal("95"))
        self.assertEqual(Decimal(details["service_income"]), Decimal("25.50"))
        self.assertEqual(details["posting_numbers"], ["return-1", "sale-1"])
        self.assertEqual(details["operation_ids"], ["101", "102", "103", "104", "105"])

    def test_unknown_category_preserves_total_and_compensation_only_day(self):
        # Новый тип начисления не должен пропадать из выплаты даже без известной детализации.
        row = ozon_service._normalize_finance_accrual({"accrued_category": "FUTURE", "total_amount": money("125.50")}, self.day)
        result = ozon_service.aggregate_ozon_finance_transactions([row], fallback_date=self.day)[0]
        self.assertEqual(result["gross_amount"], Decimal("125.50"))
        self.assertEqual(result["expense_amount"], Decimal("0"))

    def test_discount_fields_do_not_change_sale_or_refund_amount(self):
        # Встреченный в production ответ содержит баллы, уже учтённые в готовых суммах.
        for sign in (1, -1):
            with self.subTest(sign=sign):
                row = ozon_service._normalize_finance_accrual({
                    "accrued_category": "POSTING", "total_amount": money(sign * 850),
                    "posting": {"products": [{"commission": {
                        "sale_amount": money(sign * 1000), "seller_price": money(sign * 1000),
                        "bonus": money(sign * 80), "coinvestment": money(sign * 20),
                        "sale_commission": money(sign * -150), "commission": money(sign * -150),
                    }}]},
                }, self.day)
                self.assertEqual(row["accruals_for_sale"], Decimal(sign * 1000))
                self.assertEqual(row["sale_commission"], Decimal(sign * -150))
                self.assertEqual(row["amount"], Decimal(sign * 850))

    def test_final_commission_may_be_zero_with_nonzero_list_commission(self):
        # Нулевая итоговая комиссия не должна подменяться ненулевым тарифом.
        row = ozon_service._normalize_finance_accrual({
            "accrued_category": "POSTING", "total_amount": money("1000"),
            "posting": {"products": [{"commission": {
                "sale_amount": money("1000"), "sale_commission": money("-150"),
                "commission": money("0"), "bonus": money("150"),
            }}]},
        }, self.day)
        self.assertEqual(row["sale_commission"], Decimal("0"))
        self.assertEqual(row["accruals_for_sale"], Decimal("1000"))

    def test_empty_page_with_cursor_does_not_skip_following_page(self):
        # Даже пустая промежуточная страница не означает конец, пока сервер возвращает курсор.
        with patch.object(ozon_service, "_request_json", side_effect=[
            {"accruals": [], "last_id": "next"},
            {"accruals": [{"total_amount": money("1")}], "last_id": ""},
        ]) as request:
            rows = ozon_service.fetch_ozon_finance_transactions(self.day, self.day)
        self.assertEqual(len(rows), 1)
        self.assertEqual(request.call_count, 2)

    def test_repeated_or_cycling_cursor_fails_without_partial_result(self):
        # Зацикленный ответ не должен удваивать проводки или маскировать неполную загрузку.
        for cursors in (["a", "a"], ["a", "b", "a"]):
            with self.subTest(cursors=cursors), patch.object(ozon_service, "_request_json", side_effect=[
                {"accruals": [], "last_id": cursor} for cursor in cursors
            ]):
                with self.assertRaisesRegex(HTTPException, "pagination did not advance"):
                    ozon_service.fetch_ozon_finance_transactions(self.day, self.day)

    def test_page_limit_fails_without_partial_result(self):
        # Ограничитель страниц завершает задачу ошибкой, а не успешным неполным отчётом.
        with patch.dict(os.environ, {"OZON_TRANSACTION_MAX_PAGES": "1"}), patch.object(
            ozon_service, "_request_json", return_value={"accruals": [], "last_id": "next"}
        ):
            with self.assertRaisesRegex(HTTPException, "exceeded 1 pages"):
                ozon_service.fetch_ozon_finance_transactions(self.day, self.day)

    def test_malformed_response_fails(self):
        # Сломанный контракт не принимаем за пустой день и не записываем нулевые суммы.
        for response in ({}, {"accruals": None}, {"accruals": [None]}, {"accruals": []},
                         {"accruals": [], "last_id": 5}, {"accruals": [{}], "last_id": ""}):
            with self.subTest(response=response), patch.object(ozon_service, "_request_json", return_value=response):
                with self.assertRaises(HTTPException):
                    ozon_service.fetch_ozon_finance_transactions(self.day, self.day)

    def test_invalid_money_or_currency_fails(self):
        # Не допускаем тихого округления ошибок, бесконечности и смешивания валют.
        for value in (None, {}, money("invalid"), money("NaN"), money("Infinity"),
                      {"amount": "10", "currency": "USD"}):
            with self.subTest(value=value), self.assertRaises(HTTPException):
                ozon_service._normalize_finance_accrual({"total_amount": value}, self.day)

    def test_inconsistent_posting_total_fails_before_saving(self):
        # Не угадываем выручку, если состав начисления перестал сходиться с итогом Ozon.
        with self.assertRaisesRegex(HTTPException, "не совпадает"):
            ozon_service._normalize_finance_accrual({
                "accrued_category": "POSTING", "total_amount": money("800"),
                "posting": {"products": [{"commission": {"sale_amount": money("1000")}}]},
            }, self.day)

    def test_other_date_fails_and_reverse_range_never_calls_api(self):
        # Не переносим начисления за чужой день и отсекаем перевёрнутый период до запроса.
        with self.assertRaisesRegex(HTTPException, "date differs"):
            ozon_service._normalize_finance_accrual({"date": "2026-09-28", "total_amount": money("1")}, self.day)
        with patch.object(ozon_service, "_request_json") as request:
            with self.assertRaises(HTTPException):
                ozon_service.fetch_ozon_finance_transactions(self.day, date(2026, 9, 28))
            request.assert_not_called()
