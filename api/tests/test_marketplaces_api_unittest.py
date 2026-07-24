import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

from api.domains.marketplaces_api import mount_marketplaces_routes


class _FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def commit(self):
        return None


class _FakePsycopg:
    def connect(self, _dsn):
        return _FakeConn()


@unittest.skipIf(TestClient is None, "fastapi.testclient requires httpx")
class MarketplacesApiTests(unittest.TestCase):
    # Поднимает маршрут с памятью вместо БД, чтобы проверять контракт без доступа к Ozon.
    def create_client(self, rows=None, writes=None, detail_row=None, q1_handler=None, qall_handler=None):
        app = FastAPI()
        stored_rows = list(rows or [])
        write_log = writes if writes is not None else []

        def fake_qall(_conn, _sql, _params=None):
            if qall_handler:
                return qall_handler(_sql, _params)
            return stored_rows

        def fake_q1(_conn, _sql, _params=None):
            if q1_handler:
                return q1_handler(_sql, _params)
            return detail_row

        def fake_exec1(_conn, sql, params=None):
            write_log.append((sql, params))

        refresh_orders = mount_marketplaces_routes(
            app,
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=fake_q1,
            qall=fake_qall,
            exec1=fake_exec1,
            get_current_user=lambda: SimpleNamespace(username="owner", role="owner"),
            require_role=lambda *_roles: (lambda: SimpleNamespace(username="owner", role="owner")),
        )
        self._refresh_orders = refresh_orders
        return TestClient(app), write_log

    # Чтение снимка не должно выполнять запрос к внешнему кабинету Ozon.
    def test_list_catalog_returns_local_snapshot(self):
        client, writes = self.create_client(
            rows=[(101, "steam-1000", "Steam 1000", "VISIBLE", "sale", {"sku": 5510101, "fbs_sku": 4410101}, datetime(2026, 7, 21, tzinfo=timezone.utc))]
        )
        with client:
            response = client.get("/marketplaces/ozon/catalog")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["external_product_id"], 101)
        self.assertEqual(response.json()["items"][0]["offer_id"], "steam-1000")
        self.assertEqual(response.json()["items"][0]["sku"], "5510101")
        self.assertFalse(writes, "catalog read must not run schema migration")

    # Миграция запускается явно при старте, а не скрыто в каждом обработчике Ozon.
    def test_marketplaces_schema_is_prepared_by_startup_function(self):
        _client, writes = self.create_client()

        self._refresh_orders.prepare_schema()

        self.assertTrue(any("ALTER TABLE app.marketplace_ozon_digital_orders" in sql for sql, _params in writes))
        # Экранирование нужно psycopg, иначе PostgreSQL-формат %I ошибочно читается как параметр запроса.
        migration_sql = next(sql for sql, _params in writes if "DROP CONSTRAINT %%I" in sql)
        self.assertIn("DROP CONSTRAINT %%I", migration_sql)

    # История показывает источник и только маску ключа, а полный код остается отдельным защищенным запросом.
    def test_digital_orders_list_masks_codes_and_returns_supplier_source(self):
        client, _writes = self.create_client(
            rows=[(
                41, "04259716-0124-1", "04259716-0124", "PUBG", 5196324554, 1,
                "delivered", "done", None, datetime(2026, 7, 24, tzinfo=timezone.utc),
                datetime(2026, 7, 24, tzinfo=timezone.utc), "", "interhub", ["ABCD-EFGH-IJKL"],
            )]
        )
        with client:
            response = client.get("/marketplaces/ozon/catalog/103/digital-orders")

        self.assertEqual(response.status_code, 200)
        item = response.json()["items"][0]
        self.assertEqual(item["delivery_source"], "interhub")
        self.assertEqual(item["delivered_codes_masked"], ["••••IJKL"])
        self.assertEqual(item["collected_qty"], 1)
        self.assertEqual(item["remaining_qty"], 0)
        self.assertNotIn("delivered_codes", item)

    # Частично полученные ключи должны показывать оператору только оставшееся количество для ручной выдачи.
    def test_digital_orders_list_returns_remaining_quantity_after_partial_supplier_issue(self):
        client, _writes = self.create_client(
            rows=[(
                42, "04259716-0125-1", "04259716-0125", "PUBG", 5196324554, 3,
                "manual_required", "awaiting_packaging", None, datetime(2026, 7, 24, tzinfo=timezone.utc),
                None, "Поставщик не выдал следующий ключ", "interhub", ["CODE-ONE", "CODE-TWO"],
            )]
        )
        with client:
            response = client.get("/marketplaces/ozon/catalog/103/digital-orders")

        self.assertEqual(response.status_code, 200)
        item = response.json()["items"][0]
        self.assertEqual(item["collected_qty"], 2)
        self.assertEqual(item["remaining_qty"], 1)

    # Полный ключ выдается только отдельным маршрутом, чтобы не попадать в общий список заказов.
    def test_digital_order_codes_returns_full_codes_for_privileged_request(self):
        def q1_handler(sql, _params):
            if "SELECT id, delivered_codes" in sql:
                return (41, ["ABCD-EFGH-IJKL"])
            return None

        client, _writes = self.create_client(q1_handler=q1_handler)
        with client:
            response = client.get("/marketplaces/ozon/digital-orders/41/codes")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"id": 41, "codes": ["ABCD-EFGH-IJKL"]})

    # Карточка операции должна брать именно успешную попытку поставщика, связанную с заказом Ozon.
    def test_digital_order_supplier_operation_returns_interhub_transaction(self):
        created_at = datetime(2026, 7, 24, 9, 20, tzinfo=timezone.utc)

        def q1_handler(sql, _params):
            if "FROM app.marketplace_ozon_digital_supplier_attempts AS attempt" in sql:
                return (
                    41, "interhub", "gamesales-check-17848657118956-c99e758d099fd", "interhub-3921",
                    802, "300", 100.0, "paid", 0, "Успешно", created_at, created_at,
                    "PUBG: New State - Global", "300 NC",
                )
            return None

        client, _writes = self.create_client(q1_handler=q1_handler)
        with client:
            response = client.get("/marketplaces/ozon/digital-orders/41/supplier-operation")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["agent_transaction_id"], "gamesales-check-17848657118956-c99e758d099fd")
        self.assertEqual(response.json()["provider_transaction_id"], "interhub-3921")
        self.assertEqual(response.json()["service_title"], "PUBG: New State - Global")
        self.assertEqual(response.json()["nominal_title"], "300 NC")
        self.assertEqual(response.json()["amount"], 100.0)

    # Синхронизация сохраняет данные локально и не отдает клиенту секреты или сырой payload.
    def test_sync_catalog_saves_remote_items_locally(self):
        client, writes = self.create_client()
        with patch(
            "api.domains.marketplaces_api.fetch_ozon_catalog_items",
            return_value=[{"product_id": 202, "offer_id": "psn-500", "name": "PSN 500", "visibility": "VISIBLE"}],
        ):
            with client:
                response = client.post("/marketplaces/ozon/catalog/sync")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["synced_items"], 1)
        insert_calls = [params for sql, params in writes if "INSERT INTO app.marketplace_ozon_catalog_items" in sql]
        self.assertEqual(len(insert_calls), 1)
        self.assertEqual(insert_calls[0][1:4], (202, "psn-500", "PSN 500"))

    # Архивирование должно отправляться в Ozon и сразу менять локальный снимок для списка карточек.
    def test_archive_catalog_item_updates_remote_and_local_snapshot(self):
        client, writes = self.create_client()
        with patch("api.domains.marketplaces_api.update_ozon_catalog_archive", return_value={}) as update_archive:
            with client:
                response = client.post("/marketplaces/ozon/catalog/202/archive")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"external_product_id": 202, "archived": True})
        update_archive.assert_called_once_with(202, archived=True, store_code="asat")
        update_calls = [params for sql, params in writes if "UPDATE app.marketplace_ozon_catalog_items" in sql]
        self.assertEqual(update_calls[0], ("ARCHIVED", "asat", 202))

    # Детали должны браться из локального jsonb и не дублировать неважный сырой ответ Ozon в UI.
    def test_catalog_details_returns_selected_product_fields(self):
        client, _writes = self.create_client(
            detail_row=({
                "name": "Гта 6 PS5",
                "offer_id": "ASAT110",
                "sku": 5196324554,
                "primary_image": "https://example.test/ps5.jpg",
                "barcodes": ["4601234567890"],
                "category_id": 123,
                "fbo_sku": 1001,
                "fbs_sku": 1002,
                "ozon_price": {"price": 999, "currency_code": "RUB"},
                "ozon_stocks": [{"type": "fbs", "present": 4}, {"type": "fbo", "present": 2}],
            }, datetime(2026, 7, 21, tzinfo=timezone.utc)),
        )
        with client:
            response = client.get("/marketplaces/ozon/catalog/101")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["external_product_id"], 101)
        self.assertEqual(body["offer_id"], "ASAT110")
        self.assertEqual(body["sku"], "5196324554")
        self.assertEqual(body["title"], "Гта 6 PS5")
        self.assertEqual(body["barcodes"], ["4601234567890"])
        self.assertEqual(body["fbo_sku"], "1001")
        self.assertEqual(body["category_id"], 123)
        self.assertEqual(body["price"], "999")
        self.assertEqual(body["available_stock"], 6)

    # Снимки, сохраненные до отдельной колонки артикула, должны брать артикул из исходного ответа Ozon.
    def test_digital_settings_reads_offer_id_from_legacy_catalog_payload(self):
        def q1_handler(sql, _params):
            if "FROM app.marketplace_ozon_digital_settings" in sql:
                return None
            if "FROM app.marketplace_ozon_catalog_items" in sql:
                return ("", {"offer_id": "ASAT110"})
            return None

        client, _writes = self.create_client(q1_handler=q1_handler)
        with client:
            response = client.get("/marketplaces/ozon/catalog/103/digital-settings")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["offer_id"], "ASAT110")

    # Если снимок пустой, первая настройка ключей должна восстановить артикул по ID карточки через Ozon.
    def test_digital_settings_recovers_offer_id_from_ozon_when_catalog_snapshot_is_empty(self):
        def q1_handler(sql, _params):
            if "FROM app.marketplace_ozon_digital_settings" in sql:
                return None
            if "FROM app.marketplace_ozon_catalog_items" in sql:
                return ("", {})
            return None

        client, writes = self.create_client(q1_handler=q1_handler)
        with patch("api.domains.marketplaces_api.fetch_ozon_catalog_offer_id", return_value="Joy1"):
            with client:
                response = client.get("/marketplaces/ozon/catalog/103/digital-settings")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["offer_id"], "Joy1")
        self.assertTrue(any("SET offer_id=%s" in sql for sql, _params in writes))

    # Сохранение использует артикул открытой карточки, если снимок и Ozon временно не вернули его повторно.
    def test_digital_settings_saves_with_offer_id_from_opened_card(self):
        def q1_handler(sql, _params):
            if "FROM app.marketplace_ozon_catalog_items" in sql:
                return ("", {})
            if "FROM app.marketplace_ozon_digital_settings" in sql:
                return ("Joy1", 1, False, "", "", 0, None, None)
            return None

        client, _writes = self.create_client(q1_handler=q1_handler)
        with (
            patch("api.domains.marketplaces_api.fetch_ozon_catalog_offer_id", return_value=""),
            patch("api.domains.marketplaces_api.update_ozon_digital_stock", return_value={"status": [{"updated": True}]}),
        ):
            with client:
                response = client.put("/marketplaces/ozon/catalog/103/digital-settings", json={"offer_id": "Joy1", "manual_stock_limit": 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["offer_id"], "Joy1")

    # Связка с поставщиком должна сохраняться отдельно от лимита и не вызывать оплату при нажатии «Сохранить».
    def test_digital_settings_saves_interhub_mapping_without_calling_supplier(self):
        def q1_handler(sql, _params):
            if "COALESCE(SUM" in sql:
                return (0, 0, 0)
            if "FROM app.marketplace_ozon_catalog_items" in sql:
                return ("", {})
            if "FROM app.marketplace_ozon_digital_settings" in sql:
                return ("Joy1", 1, True, "", "", 0, None, None)
            return None

        client, writes = self.create_client(q1_handler=q1_handler, qall_handler=lambda *_args: [])
        with (
            patch("api.domains.marketplaces_api.fetch_ozon_catalog_offer_id", return_value=""),
            patch("api.domains.marketplaces_api.update_ozon_digital_stock", return_value={"status": [{"updated": True}]}),
        ):
            with client:
                response = client.put(
                    "/marketplaces/ozon/catalog/103/digital-settings",
                    json={
                        "offer_id": "Joy1",
                        "manual_stock_limit": 1,
                        "auto_issue_enabled": True,
                        "interhub_service_id": 91,
                        "interhub_nominal_id": "500",
                        "interhub_enabled": True,
                    },
                )

        self.assertEqual(response.status_code, 200)
        supplier_calls = [params for sql, params in writes if "INSERT INTO app.marketplace_ozon_digital_suppliers" in sql]
        self.assertEqual(supplier_calls[-1][2:5], (True, 91, "500"))

    # Заказ другой карточки не должен сбрасывать ID выбранного товара перед публикацией остатка.
    def test_digital_orders_sync_keeps_selected_product_id_when_posting_is_not_matched(self):
        def q1_handler(sql, _params):
            if "COALESCE(SUM" in sql:
                return (0, 0, 0)
            if "FROM app.marketplace_ozon_digital_settings" in sql:
                return ("Joy1", 1, False, "", "", 0, None, None)
            return None

        def qall_handler(sql, _params):
            if "FROM app.marketplace_ozon_digital_settings AS settings" in sql:
                return [(103, "Joy1", {})]
            return []

        client, writes = self.create_client(q1_handler=q1_handler, qall_handler=qall_handler)
        with (
            patch("api.domains.marketplaces_api.fetch_ozon_digital_postings", return_value=[{"posting_number": "100-1", "products": [{"offer_id": "other", "sku": 7}]}]),
            patch("api.domains.marketplaces_api.update_ozon_digital_stock", return_value={"status": [{"updated": True}]}),
        ):
            with client:
                response = client.post("/marketplaces/ozon/catalog/103/digital-orders/sync")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["available_stock"], 1)
        sync_updates = [params for sql, params in writes if "SET last_orders_sync_at=%s" in sql]
        self.assertEqual(sync_updates[-1][2], 103)

    # Старый артикул в заказе должен находить карточку по неизменному SKU из снимка каталога.
    def test_digital_orders_sync_matches_order_by_catalog_sku_when_offer_id_changed(self):
        def q1_handler(sql, _params):
            if "COALESCE(SUM" in sql:
                return (1, 1, 0)
            if "FROM app.marketplace_ozon_digital_settings" in sql:
                return ("Joy1", 1, False, "", "", 0, None, None)
            return None

        def qall_handler(sql, _params):
            if "FROM app.marketplace_ozon_digital_settings AS settings" in sql:
                return [(103, "Joy1", {"sku": 4844194840})]
            return []

        client, writes = self.create_client(q1_handler=q1_handler, qall_handler=qall_handler)
        with (
            patch("api.domains.marketplaces_api.fetch_ozon_digital_postings", return_value=[{"posting_number": "04259716-0122-1", "products": [{"offer_id": "ASAT110", "sku": 4844194840, "quantity": 1}]}]),
            patch("api.domains.marketplaces_api.update_ozon_digital_stock", return_value={"status": [{"updated": True}]}),
        ):
            with client:
                response = client.post("/marketplaces/ozon/catalog/103/digital-orders/sync")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["imported_orders"], 1)
        order_inserts = [params for sql, params in writes if "INSERT INTO app.marketplace_ozon_digital_orders" in sql]
        self.assertEqual(order_inserts[-1][1], 103)

    # Финальный Done от Ozon означает, что цифровой ключ уже доставлен и не должен вернуться в ручную выдачу.
    def test_digital_orders_sync_marks_done_posting_as_delivered(self):
        def q1_handler(sql, _params):
            if "COALESCE(SUM" in sql:
                return (1, 0, 1)
            if "FROM app.marketplace_ozon_digital_settings" in sql:
                return ("Joy1", 1, False, "", "", 0, None, None)
            return None

        def qall_handler(sql, _params):
            if "FROM app.marketplace_ozon_digital_settings AS settings" in sql:
                return [(103, "Joy1", {"sku": 4844194840})]
            return []

        client, writes = self.create_client(q1_handler=q1_handler, qall_handler=qall_handler)
        with (
            patch("api.domains.marketplaces_api.fetch_ozon_digital_postings", return_value=[{"posting_number": "04259716-0123-1", "status": "done", "products": [{"offer_id": "ASAT110", "sku": 4844194840, "quantity": 1}]}]),
            patch("api.domains.marketplaces_api.update_ozon_digital_stock", return_value={"status": [{"updated": True}]}) as update_stock,
        ):
            with client:
                response = client.post("/marketplaces/ozon/catalog/103/digital-orders/sync")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["available_stock"], 1)
        order_inserts = [params for sql, params in writes if "INSERT INTO app.marketplace_ozon_digital_orders" in sql]
        self.assertEqual(order_inserts[-1][7], "delivered")
        self.assertEqual(order_inserts[-1][8], "done")
        update_stock.assert_not_called()

    # Пустой список складов Ozon означает нулевой остаток, а не отсутствие значения в карточке.
    def test_catalog_details_returns_zero_for_empty_stock(self):
        client, _writes = self.create_client(
            detail_row=({"ozon_price": {"price": 6000, "currency_code": "RUB"}, "ozon_stocks": []}, datetime(2026, 7, 21, tzinfo=timezone.utc)),
        )
        with client:
            response = client.get("/marketplaces/ozon/catalog/102")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["available_stock"], 0)

    # Цифровые карточки могут хранить остаток только в поле stocks подробного ответа Ozon.
    def test_catalog_details_reads_stock_from_native_product_info(self):
        client, _writes = self.create_client(
            detail_row=({"stocks": {"stocks": [{"source": "fbo", "present": 4}]}}, datetime(2026, 7, 24, tzinfo=timezone.utc)),
        )
        with client:
            response = client.get("/marketplaces/ozon/catalog/102")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["available_stock"], 4)

    # До первого включения ручного режима карточка должна вернуть нулевой лимит и свой артикул Ozon.
    def test_digital_settings_start_in_manual_mode_without_publishing_stock(self):
        def q1_handler(sql, _params):
            if "FROM app.marketplace_ozon_digital_settings" in sql:
                return None
            if "FROM app.marketplace_ozon_catalog_items" in sql:
                return ("PS5-6",)
            return None

        client, _writes = self.create_client(q1_handler=q1_handler)
        with client:
            response = client.get("/marketplaces/ozon/catalog/103/digital-settings")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["offer_id"], "PS5-6")
        self.assertEqual(body["manual_stock_limit"], 0)
        self.assertEqual(body["published_stock"], 0)


if __name__ == "__main__":
    unittest.main()
