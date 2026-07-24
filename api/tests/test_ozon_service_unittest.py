import io
import json
import os
import unittest
import urllib.error
from datetime import date, datetime, timezone
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

    # Каталог и архив должны читаться постранично, чтобы UI не смешивал активные карточки со снятыми с продажи.
    def test_fetch_catalog_reads_active_and_archived_pages(self):
        responses = [
            _Response({"result": {"items": [{"product_id": 101, "offer_id": "steam-1000"}], "last_id": "next"}}),
            _Response({"result": {"items": [{"product_id": 102, "offer_id": "psn-500"}], "last_id": ""}}),
            _Response({"result": {"items": [{"product_id": 103, "offer_id": "psn-old", "archived": True}], "last_id": ""}}),
            _Response({"items": [
                {"id": 101, "name": "Steam 1000", "status": {"state": "sale"}},
                {"id": 102, "name": "PSN 500", "status": {"state": "sale"}},
                {"id": 103, "name": "PSN old", "status": {"state": "sale"}},
            ]}),
            _Response({"items": [
                {"product_id": 101, "price": {"price": 1000, "currency_code": "RUB"}},
                {"product_id": 102, "price": {"price": 500, "currency_code": "RUB"}},
                {"product_id": 103, "price": {"price": 100, "currency_code": "RUB"}},
            ]}),
            _Response({"items": [
                {"product_id": 101, "stocks": [{"type": "fbs", "present": 3}]},
                {"product_id": 102, "stocks": [{"type": "fbo", "present": 2}]},
                {"product_id": 103, "stocks": []},
            ]}),
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

        self.assertEqual([row["product_id"] for row in rows], [101, 102, 103])
        self.assertEqual([row["name"] for row in rows], ["Steam 1000", "PSN 500", "PSN old"])
        self.assertEqual(rows[2]["visibility"], "ARCHIVED")
        self.assertEqual(rows[0]["ozon_price"], {"price": 1000, "currency_code": "RUB"})
        self.assertEqual(rows[1]["ozon_stocks"], [{"type": "fbo", "present": 2}])
        self.assertEqual(urlopen.call_args_list[0].args[0].full_url, "https://api-seller.ozon.ru/v3/product/list")
        self.assertEqual(urlopen.call_args_list[3].args[0].full_url, "https://api-seller.ozon.ru/v3/product/info/list")
        self.assertEqual(urlopen.call_args_list[4].args[0].full_url, "https://api-seller.ozon.ru/v5/product/info/prices")
        self.assertEqual(urlopen.call_args_list[5].args[0].full_url, "https://api-seller.ozon.ru/v4/product/info/stocks")
        first_payload = json.loads(urlopen.call_args_list[0].args[0].data.decode("utf-8"))
        second_payload = json.loads(urlopen.call_args_list[1].args[0].data.decode("utf-8"))
        archive_payload = json.loads(urlopen.call_args_list[2].args[0].data.decode("utf-8"))
        details_payload = json.loads(urlopen.call_args_list[3].args[0].data.decode("utf-8"))
        prices_payload = json.loads(urlopen.call_args_list[4].args[0].data.decode("utf-8"))
        stocks_payload = json.loads(urlopen.call_args_list[5].args[0].data.decode("utf-8"))
        self.assertEqual(first_payload["filter"]["visibility"], "ALL")
        self.assertEqual(second_payload["last_id"], "next")
        self.assertEqual(archive_payload["filter"]["visibility"], "ARCHIVED")
        self.assertEqual(details_payload["product_id"], [101, 102, 103])
        self.assertEqual(prices_payload["filter"]["product_id"], [101, 102, 103])
        self.assertEqual(stocks_payload["filter"]["with_quant"], {"created": True, "exists": True})

    # Для цифровой карточки Ozon должен получить артикул и лимит, а не локальные ключи.
    def test_update_digital_stock_uses_offer_id(self):
        with (
            patch.dict(os.environ, {"OZON_CLIENT_ID": "client-1", "OZON_API_KEY": "secret-1"}, clear=False),
            patch.object(ozon_service.urllib.request, "urlopen", return_value=_Response({"status": [{"updated": True}]})) as urlopen,
        ):
            ozon_service.update_ozon_digital_stock("PS5-6", 1)

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api-seller.ozon.ru/v1/product/digital/stocks/import")
        self.assertEqual(json.loads(request.data.decode("utf-8")), {"stocks": [{"offer_id": "PS5-6", "stock": 1}]})

    # Архивация и восстановление должны использовать один ID карточки, а не артикул продавца.
    def test_update_catalog_archive_uses_product_id_and_expected_endpoint(self):
        with (
            patch.dict(os.environ, {"OZON_CLIENT_ID": "client-1", "OZON_API_KEY": "secret-1"}, clear=False),
            patch.object(ozon_service.urllib.request, "urlopen", return_value=_Response({})) as urlopen,
        ):
            ozon_service.update_ozon_catalog_archive(5224093734, archived=True)

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api-seller.ozon.ru/v1/product/archive")
        self.assertEqual(json.loads(request.data.decode("utf-8")), {"product_id": [5224093734]})

    # При неполном снимке артикул должен восстанавливаться точечным запросом по ID карточки.
    def test_fetch_catalog_offer_id_reads_single_product(self):
        with (
            patch.dict(os.environ, {"OZON_CLIENT_ID": "client-1", "OZON_API_KEY": "secret-1"}, clear=False),
            patch.object(
                ozon_service.urllib.request,
                "urlopen",
                return_value=_Response({"items": [{"product_id": 5224093734, "offer_id": "Joy1"}]}),
            ) as urlopen,
        ):
            offer_id = ozon_service.fetch_ozon_catalog_offer_id(5224093734)

        self.assertEqual(offer_id, "Joy1")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api-seller.ozon.ru/v3/product/info/list")
        self.assertEqual(json.loads(request.data.decode("utf-8"))["product_id"], [5224093734])

    # Ручная выдача должна передавать код в конкретное отправление и его SKU.
    def test_upload_digital_codes_targets_posting_and_sku(self):
        with (
            patch.dict(os.environ, {"OZON_CLIENT_ID": "client-1", "OZON_API_KEY": "secret-1"}, clear=False),
            patch.object(ozon_service.urllib.request, "urlopen", return_value=_Response({"exemplars_by_sku": [{"sku": 555, "received_qty": 1}]})) as urlopen,
        ):
            ozon_service.upload_ozon_digital_codes(posting_number="123-0001", sku=555, codes=["PSN-CODE-1"])

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api-seller.ozon.ru/v1/posting/digital/codes/upload")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "posting_number": "123-0001",
                "exemplars_by_sku": [{"sku": 555, "exemplar_qty": 1, "not_available_exemplar_qty": 0, "exemplar_keys": ["PSN-CODE-1"]}],
            },
        )

    # Синхронизация цифровых заказов должна читать все страницы с временным фильтром.
    def test_fetch_digital_postings_reads_cursor_pages(self):
        responses = [
            _Response({"postings": [{"posting_number": "first"}], "has_next": True, "cursor": "next"}),
            _Response({"postings": [{"posting_number": "second"}], "has_next": False, "cursor": ""}),
        ]
        with (
            patch.dict(os.environ, {"OZON_CLIENT_ID": "client-1", "OZON_API_KEY": "secret-1", "OZON_DIGITAL_POSTINGS_PAGE_SIZE": "1000"}, clear=False),
            patch.object(ozon_service.urllib.request, "urlopen", side_effect=responses) as urlopen,
        ):
            postings = ozon_service.fetch_ozon_digital_postings(
                datetime(2026, 7, 1, tzinfo=timezone.utc),
                datetime(2026, 7, 2, tzinfo=timezone.utc),
            )

        self.assertEqual([posting["posting_number"] for posting in postings], ["first", "second"])
        self.assertEqual(json.loads(urlopen.call_args_list[0].args[0].data.decode("utf-8"))["limit"], 100)
        self.assertEqual(json.loads(urlopen.call_args_list[1].args[0].data.decode("utf-8"))["cursor"], "next")


if __name__ == "__main__":
    unittest.main()
