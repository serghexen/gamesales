import io
import json
import os
import unittest
import urllib.error
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from api.domains import ozon_service


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class OzonServiceTest(unittest.TestCase):
    # Локальный диагностический флаг должен отключать проверку проблемной SSL-цепочки.
    def test_ssl_context_can_disable_verification(self):
        sentinel = object()
        with (
            patch.dict(os.environ, {"OZON_SSL_VERIFY": "false"}),
            patch.object(ozon_service.ssl, "_create_unverified_context", return_value=sentinel) as create_context,
        ):
            context = ozon_service._ssl_context()

        self.assertIs(context, sentinel)
        create_context.assert_called_once_with()

    # Явный CA-файл должен иметь приоритет над системным хранилищем сертификатов.
    def test_ssl_context_uses_configured_ca_file(self):
        sentinel = object()
        with (
            patch.dict(os.environ, {"OZON_SSL_VERIFY": "true", "OZON_CA_CERT_PATH": "/tmp/company-ca.pem"}),
            patch.object(ozon_service.ssl, "create_default_context", return_value=sentinel) as create_context,
        ):
            context = ozon_service._ssl_context()

        self.assertIs(context, sentinel)
        create_context.assert_called_once_with(cafile="/tmp/company-ca.pem")

    # Пагинация должна передавать кабинетные заголовки и собирать все операции.
    def test_fetch_transactions_reads_all_pages(self):
        responses = [
            _Response({"result": {"operations": [{"operation_id": 1}], "page_count": 2}}),
            _Response({"result": {"operations": [{"operation_id": 2}], "page_count": 2}}),
        ]
        with (
            patch.dict(
                os.environ,
                {
                    "OZON_CLIENT_ID": "client-1",
                    "OZON_API_KEY": "secret-1",
                    "OZON_TRANSACTION_PAGE_SIZE": "1",
                },
                clear=False,
            ),
            patch.object(ozon_service.urllib.request, "urlopen", side_effect=responses) as urlopen,
        ):
            rows = ozon_service.fetch_ozon_finance_transactions(date(2026, 6, 1), date(2026, 6, 2))

        self.assertEqual([row["operation_id"] for row in rows], [1, 2])
        first_request = urlopen.call_args_list[0].args[0]
        self.assertEqual(first_request.headers["Client-id"], "client-1")
        self.assertEqual(first_request.headers["Api-key"], "secret-1")
        first_payload = json.loads(first_request.data.decode("utf-8"))
        self.assertEqual(first_payload["filter"]["transaction_type"], "all")
        self.assertEqual(first_payload["page_size"], 1)

    # Дневная агрегация должна сохранять равенство gross минус expense итоговой выплате Ozon.
    def test_aggregate_transactions_builds_daily_gross_and_expense(self):
        rows = [
            {
                "operation_id": 101,
                "operation_date": "2026-06-03T10:00:00Z",
                "operation_type": "OperationAgentDeliveredToCustomer",
                "accruals_for_sale": "1000.00",
                "sale_commission": "-150.00",
                "amount": "780.00",
                "delivery_charge": "0",
                "return_delivery_charge": "0",
                "posting": {"posting_number": "100-1"},
                "services": [
                    {"name": "MarketplaceServiceItemDirectFlowLogistic", "price": "-70.00"},
                ],
            },
            {
                "operation_id": 102,
                "operation_date": "2026-06-03T12:00:00Z",
                "operation_type": "OperationItemReturn",
                "accruals_for_sale": "-200.00",
                "sale_commission": "30.00",
                "amount": "-180.00",
                "posting": {"posting_number": "100-2"},
                "services": [{"name": "MarketplaceServiceItemReturnFlowLogistic", "price": "-10.00"}],
            },
        ]

        daily = ozon_service.aggregate_ozon_finance_transactions(
            rows,
            fallback_date=date(2026, 6, 1),
            store_code="asat",
        )

        self.assertEqual(len(daily), 1)
        self.assertEqual(daily[0]["gross_amount"], Decimal("1000.00"))
        self.assertEqual(daily[0]["expense_amount"], Decimal("400.00"))
        self.assertEqual(daily[0]["payout_amount"], Decimal("600.00"))
        self.assertEqual(daily[0]["external_key_base"], "ozon:asat:finance-transactions:daily:2026-06-03")
        self.assertEqual(daily[0]["payload_json"]["returns"], "200.00")
        self.assertEqual(daily[0]["payload_json"]["sale_commission"], "-120.00")
        self.assertEqual(daily[0]["payload_json"]["sale_commission_expense"], "150.00")
        self.assertEqual(daily[0]["payload_json"]["service_expenses"], "80.00")
        self.assertEqual(daily[0]["payload_json"]["posting_numbers"], ["100-1", "100-2"])

    # Компенсации сверх продаж должны увеличивать gross, чтобы итог дня не терялся.
    def test_aggregate_transactions_keeps_positive_compensation(self):
        daily = ozon_service.aggregate_ozon_finance_transactions(
            [
                {
                    "operation_id": 201,
                    "operation_date": "2026-06-04T00:00:00Z",
                    "operation_type": "OperationMarketplaceServicePremiumCashbackIndividualPoints",
                    "accruals_for_sale": "0",
                    "amount": "125.50",
                    "services": [],
                }
            ],
            fallback_date=date(2026, 6, 4),
        )

        self.assertEqual(daily[0]["gross_amount"], Decimal("125.50"))
        self.assertEqual(daily[0]["expense_amount"], Decimal("0.00"))
        self.assertEqual(daily[0]["payload_json"]["other_income"], "125.50")

    # Ошибка лимита должна вернуть пользователю время безопасного повтора.
    def test_request_json_maps_rate_limit(self):
        error = urllib.error.HTTPError(
            url="https://api-seller.ozon.ru/v3/finance/transaction/list",
            code=429,
            msg="Too Many Requests",
            hdrs={"Retry-After": "5"},
            fp=io.BytesIO(b'{"message":"rate limit"}'),
        )
        with patch.object(ozon_service.urllib.request, "urlopen", side_effect=error):
            with self.assertRaisesRegex(Exception, "через 5 сек"):
                ozon_service._request_json(
                    "https://api-seller.ozon.ru/v3/finance/transaction/list",
                    client_id="client-1",
                    api_key="secret-1",
                    payload={},
                    timeout=5,
                )

    # Несуществующий кабинет Ozon не должен приниматься даже при прямом вызове backend.
    def test_normalize_store_code_rejects_sps(self):
        with self.assertRaisesRegex(Exception, "must be asat"):
            ozon_service.normalize_ozon_store_code("sps")

    # Каталог должен читаться постранично, чтобы первый импорт не терял карточки большого магазина.
    def test_fetch_catalog_reads_all_pages(self):
        responses = [
            _Response({"result": {"items": [{"product_id": 101, "offer_id": "steam-1000"}], "last_id": "next"}}),
            _Response({"result": {"items": [{"product_id": 102, "offer_id": "psn-500"}], "last_id": ""}}),
        ]
        with (
            patch.dict(
                os.environ,
                {
                    "OZON_CLIENT_ID": "client-1",
                    "OZON_API_KEY": "secret-1",
                    "OZON_CATALOG_PAGE_SIZE": "1",
                },
                clear=False,
            ),
            patch.object(ozon_service.urllib.request, "urlopen", side_effect=responses) as urlopen,
        ):
            rows = ozon_service.fetch_ozon_catalog_items()

        self.assertEqual([row["product_id"] for row in rows], [101, 102])
        first_payload = json.loads(urlopen.call_args_list[0].args[0].data.decode("utf-8"))
        second_payload = json.loads(urlopen.call_args_list[1].args[0].data.decode("utf-8"))
        self.assertEqual(first_payload["filter"]["visibility"], "ALL")
        self.assertEqual(second_payload["last_id"], "next")


if __name__ == "__main__":
    unittest.main()
