import os
from datetime import datetime, timezone
import unittest
from unittest.mock import patch

try:
    from api.domains import yandex_market_catalog_service
except ModuleNotFoundError:  # Запуск из папки api использует локальный пакет domains.
    from domains import yandex_market_catalog_service


class YandexMarketCatalogServiceTests(unittest.TestCase):
    # Снимок кабинета не должен подтягивать товары FBY, когда настроен конкретный DBS-магазин.
    def test_catalog_keeps_only_configured_campaign_items(self):
        responses = [
            {"result": {"offerMappings": [
                {"offer": {"offerId": "DBS-SKU", "campaigns": [{"campaignId": 70940298}]}},
                {"offer": {"offerId": "FBY-SKU", "campaigns": [{"campaignId": 50826885}]}},
            ], "paging": {}}},
            {"result": {"offerMappings": [], "paging": {}}},
        ]
        settings = {
            "YANDEX_MARKET_ASAT_TOKEN": "test-token",
            "YANDEX_MARKET_ASAT_BUSINESS_ID": "48186803",
            "YANDEX_MARKET_ASAT_CAMPAIGN_ID": "70940298",
        }
        with (
            patch.dict(os.environ, settings, clear=False),
            patch.object(yandex_market_catalog_service, "_request_json", side_effect=responses) as request_json,
        ):
            rows = yandex_market_catalog_service.fetch_yandex_market_catalog_items("asat")

        self.assertEqual([row["offer"]["offerId"] for row in rows], ["DBS-SKU"])
        self.assertEqual(request_json.call_count, 2)

    # Публикация остатка использует campaignId выбранного DBS-магазина и точный SKU продавца.
    def test_update_stock_sends_campaign_specific_payload(self):
        settings = {
            "YANDEX_MARKET_ASAT_TOKEN": "test-token",
            "YANDEX_MARKET_ASAT_BUSINESS_ID": "48186803",
            "YANDEX_MARKET_ASAT_CAMPAIGN_ID": "70940298",
        }
        with (
            patch.dict(os.environ, settings, clear=False),
            patch.object(yandex_market_catalog_service, "_request_json", return_value={}) as request_json,
        ):
            yandex_market_catalog_service.update_yandex_market_stock("PSN-500", 3, store_code="asat")

        args, kwargs = request_json.call_args
        self.assertEqual(args[0], "PUT")
        self.assertIn("/campaigns/70940298/offers/stocks", args[1])
        self.assertEqual(kwargs["payload"]["skus"][0]["sku"], "PSN-500")
        self.assertEqual(kwargs["payload"]["skus"][0]["items"][0]["count"], 3)

    # Передача цифрового товара идет точным DBS-методом с позициями и ключами в одном запросе.
    def test_deliver_digital_goods_sends_order_item_codes(self):
        settings = {
            "YANDEX_MARKET_TEST_TOKEN": "test-token",
            "YANDEX_MARKET_TEST_BUSINESS_ID": "216926720",
            "YANDEX_MARKET_TEST_CAMPAIGN_ID": "149196813",
        }
        with (
            patch.dict(os.environ, settings, clear=False),
            patch.object(yandex_market_catalog_service, "_request_json", return_value={"status": "OK"}) as request_json,
        ):
            yandex_market_catalog_service.deliver_yandex_market_digital_goods(
                501,
                item_id=99,
                codes=["TEST-CODE-1"],
                slip="Активируйте код на странице погашения.",
                store_code="test",
            )

        args, kwargs = request_json.call_args
        self.assertEqual(args[0], "POST")
        self.assertIn("/v2/campaigns/149196813/orders/501/deliverDigitalGoods", args[1])
        self.assertEqual(kwargs["payload"]["items"][0]["id"], 99)
        self.assertEqual(kwargs["payload"]["items"][0]["codes"], ["TEST-CODE-1"])
        self.assertEqual(kwargs["payload"]["items"][0]["slip"], "Активируйте код на странице погашения.")

    # Чтение остатков использует POST и суммирует только доступный для продажи тип AVAILABLE.
    def test_fetch_stock_reads_available_count_without_update(self):
        settings = {
            "YANDEX_MARKET_ASAT_TOKEN": "test-token",
            "YANDEX_MARKET_ASAT_BUSINESS_ID": "48186803",
            "YANDEX_MARKET_ASAT_CAMPAIGN_ID": "70940298",
        }
        response = {"result": {"warehouses": [{"warehouseId": 1, "offers": [{
            "offerId": "PSN-500", "updatedAt": "2026-07-25T11:33:00Z", "stocks": [
                {"type": "AVAILABLE", "count": 4}, {"type": "FREEZE", "count": 1},
            ],
        }]}]}}
        with (
            patch.dict(os.environ, settings, clear=False),
            patch.object(yandex_market_catalog_service, "_request_json", return_value=response) as request_json,
        ):
            stock = yandex_market_catalog_service.fetch_yandex_market_stock("PSN-500", store_code="asat")

        args, kwargs = request_json.call_args
        self.assertEqual(args[0], "POST")
        self.assertIn("/campaigns/70940298/offers/stocks", args[1])
        self.assertEqual(kwargs["payload"], {"offerIds": ["PSN-500"], "withTurnover": False})
        self.assertEqual(stock["available_stock"], 4)

    # Заказы читаются новым методом кабинета и не используют методы выдачи цифровых товаров.
    def test_fetch_orders_reads_configured_dbs_campaign(self):
        settings = {
            "YANDEX_MARKET_ASAT_TOKEN": "test-token",
            "YANDEX_MARKET_ASAT_BUSINESS_ID": "48186803",
            "YANDEX_MARKET_ASAT_CAMPAIGN_ID": "70940298",
        }
        response = {"orders": [
            {"orderId": 11, "campaignId": 70940298, "items": []},
            {"orderId": 12, "campaignId": 50826885, "items": []},
        ], "paging": {}}
        with (
            patch.dict(os.environ, settings, clear=False),
            patch.object(yandex_market_catalog_service, "_request_json", return_value=response) as request_json,
        ):
            snapshot = yandex_market_catalog_service.fetch_yandex_market_orders("asat")

        args, kwargs = request_json.call_args
        self.assertEqual(args[0], "POST")
        self.assertIn("/v1/businesses/48186803/orders", args[1])
        self.assertEqual(kwargs["payload"], {"campaignIds": [70940298], "programTypes": ["DBS"], "fake": False})
        self.assertEqual([order["orderId"] for order in snapshot["orders"]], [11])
        self.assertEqual(snapshot["pages_loaded"], 1)
        self.assertFalse(snapshot["has_more"])

    # Повторная загрузка берет изменения с небольшим запасом, а не перечитывает всю историю заказов.
    def test_fetch_orders_uses_update_checkpoint_with_overlap(self):
        settings = {
            "YANDEX_MARKET_ASAT_TOKEN": "test-token",
            "YANDEX_MARKET_ASAT_BUSINESS_ID": "48186803",
            "YANDEX_MARKET_ASAT_CAMPAIGN_ID": "70940298",
        }
        checkpoint = datetime(2026, 7, 25, 12, 10, tzinfo=timezone.utc)
        with (
            patch.dict(os.environ, settings, clear=False),
            patch.object(yandex_market_catalog_service, "_request_json", return_value={"orders": [], "paging": {}}) as request_json,
        ):
            yandex_market_catalog_service.fetch_yandex_market_orders("asat", updated_from=checkpoint)

        self.assertEqual(
            request_json.call_args.kwargs["payload"]["dates"],
            {"updateDateFrom": "2026-07-25T12:05:00Z"},
        )

    # Уведомление читает ровно свой заказ современным read-only методом бизнес-кабинета.
    def test_fetch_single_order_reads_only_requested_order(self):
        settings = {
            "YANDEX_MARKET_ASAT_TOKEN": "test-token",
            "YANDEX_MARKET_ASAT_BUSINESS_ID": "48186803",
            "YANDEX_MARKET_ASAT_CAMPAIGN_ID": "70940298",
        }
        response = {"orders": [{"orderId": 101, "campaignId": 70940298, "items": []}], "paging": {}}
        with (
            patch.dict(os.environ, settings, clear=False),
            patch.object(yandex_market_catalog_service, "_request_json", return_value=response) as request_json,
        ):
            order = yandex_market_catalog_service.fetch_yandex_market_order(101, store_code="asat")

        args, kwargs = request_json.call_args
        self.assertEqual(args[0], "POST")
        self.assertIn("/v1/businesses/48186803/orders?limit=1", args[1])
        self.assertEqual(
            kwargs["payload"],
            {"campaignIds": [70940298], "orderIds": [101], "programTypes": ["DBS"], "fake": False},
        )
        self.assertEqual(order["orderId"], 101)

    # Тестовый кабинет возвращает тестовые заказы только при явном флаге окружения.
    def test_fetch_single_order_includes_fake_orders_only_when_enabled(self):
        settings = {
            "YANDEX_MARKET_ASAT_TOKEN": "test-token",
            "YANDEX_MARKET_ASAT_BUSINESS_ID": "48186803",
            "YANDEX_MARKET_ASAT_CAMPAIGN_ID": "70940298",
            "YANDEX_MARKET_INCLUDE_FAKE_ORDERS": "true",
        }
        response = {"orders": [{"orderId": 101, "campaignId": 70940298, "items": []}], "paging": {}}
        with (
            patch.dict(os.environ, settings, clear=False),
            patch.object(yandex_market_catalog_service, "_request_json", return_value=response) as request_json,
        ):
            yandex_market_catalog_service.fetch_yandex_market_order(101, store_code="asat")

        self.assertTrue(request_json.call_args.kwargs["payload"]["fake"])

    # Отдельный тестовый магазин читает fake-заказы по своему флагу и не затрагивает ASAT.
    def test_test_store_reads_fake_orders_with_its_own_settings(self):
        settings = {
            "YANDEX_MARKET_TEST_TOKEN": "test-token",
            "YANDEX_MARKET_TEST_BUSINESS_ID": "216926720",
            "YANDEX_MARKET_TEST_CAMPAIGN_ID": "149196813",
            "YANDEX_MARKET_TEST_INCLUDE_FAKE_ORDERS": "true",
        }
        response = {"orders": [{"orderId": 101, "campaignId": 149196813, "items": []}], "paging": {}}
        with (
            patch.dict(os.environ, settings, clear=True),
            patch.object(yandex_market_catalog_service, "_request_json", return_value=response) as request_json,
        ):
            order = yandex_market_catalog_service.fetch_yandex_market_order(101, store_code="test")

        args, kwargs = request_json.call_args
        self.assertIn("/v1/businesses/216926720/orders?limit=1", args[1])
        self.assertEqual(kwargs["payload"]["campaignIds"], [149196813])
        self.assertTrue(kwargs["payload"]["fake"])
        self.assertEqual(order["orderId"], 101)

    # Глобальный старый флаг ASAT не должен случайно включать fake-заказы другого магазина.
    def test_test_store_does_not_inherit_legacy_fake_orders_flag(self):
        settings = {
            "YANDEX_MARKET_INCLUDE_FAKE_ORDERS": "true",
            "YANDEX_MARKET_TEST_TOKEN": "test-token",
            "YANDEX_MARKET_TEST_BUSINESS_ID": "216926720",
            "YANDEX_MARKET_TEST_CAMPAIGN_ID": "149196813",
        }
        response = {"orders": [{"orderId": 101, "campaignId": 149196813, "items": []}], "paging": {}}
        with (
            patch.dict(os.environ, settings, clear=True),
            patch.object(yandex_market_catalog_service, "_request_json", return_value=response) as request_json,
        ):
            yandex_market_catalog_service.fetch_yandex_market_order(101, store_code="test")

        self.assertFalse(request_json.call_args.kwargs["payload"]["fake"])

    # CampaignId из уведомления должен возвращать код нужного локально настроенного магазина.
    def test_find_store_code_by_campaign_id_uses_scoped_environment(self):
        settings = {
            "YANDEX_MARKET_ASAT_CAMPAIGN_ID": "70940298",
            "YANDEX_MARKET_SPS_CAMPAIGN_ID": "12345678",
        }
        with patch.dict(os.environ, settings, clear=True):
            self.assertEqual(yandex_market_catalog_service.find_yandex_market_store_code_by_campaign_id(12345678), "sps")
            self.assertIsNone(yandex_market_catalog_service.find_yandex_market_store_code_by_campaign_id(1))
