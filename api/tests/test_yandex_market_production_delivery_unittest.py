import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

try:
    from api.domains import yandex_market_production_delivery
except ModuleNotFoundError:  # Запуск из папки api использует локальный пакет domains.
    from domains import yandex_market_production_delivery


class _NoDatabasePsycopg:
    def connect(self, _dsn):
        raise AssertionError("При выключенном боевом флаге обращение к БД не требуется")


class _FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        return False

    def commit(self):
        return None


class _FakePsycopg:
    def connect(self, _dsn):
        return _FakeConn()


class YandexMarketProductionDeliveryTests(unittest.TestCase):
    # Выключенный флаг останавливает webhook до резервирования ключей, оплаты Interhub и даже чтения очереди.
    def test_disabled_flag_makes_webhook_delivery_a_noop(self):
        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_NoDatabasePsycopg(),
            q1=lambda *_args: None,
            qall=lambda *_args: [],
            exec1=lambda *_args: None,
            interhub_calculate=lambda *_args: (_ for _ in ()).throw(AssertionError("Interhub calculate must not run")),
            interhub_check=lambda *_args: (_ for _ in ()).throw(AssertionError("Interhub check must not run")),
            interhub_pay=lambda *_args: (_ for _ in ()).throw(AssertionError("Interhub pay must not run")),
        )
        with patch.dict(os.environ, {"YANDEX_MARKET_ASAT_AUTO_DELIVERY_ENABLED": "false"}, clear=False):
            processor("asat", 501, 99)

    # Опрос незавершенных оплат не делает внешний запрос, пока боевой флаг выключен.
    def test_disabled_flag_makes_supplier_poll_a_noop(self):
        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_NoDatabasePsycopg(),
            q1=lambda *_args: None,
            qall=lambda *_args: [],
            exec1=lambda *_args: None,
            interhub_check_status=lambda *_args: (_ for _ in ()).throw(AssertionError("Interhub status must not run")),
        )
        with patch.dict(os.environ, {"YANDEX_MARKET_ASAT_AUTO_DELIVERY_ENABLED": "false"}, clear=False):
            processor.refresh_supplier_attempts()

    # Ошибка сети после pay сохраняет неопределенную попытку, а повторное уведомление не запускает второй pay.
    def test_pay_timeout_waits_for_check_status_without_second_payment(self):
        writes = []
        pay_calls = []

        def fake_q1(_conn, sql, _params=None):
            if "SELECT orders.offer_id" in sql:
                return ("PSN-500", 1, "PROCESSING", False, True, False)
            if "INSERT INTO app.marketplace_yandex_digital_deliveries" in sql:
                return (10,)
            if "SELECT required_qty, delivered_codes" in sql:
                return (1, [], "supplier_processing", "asat", "PSN-500")
            if "SELECT 1 FROM app.marketplace_yandex_digital_suppliers" in sql:
                return (1,)
            if "SELECT auto_issue_enabled" in sql:
                return (True, False)
            if "SELECT delivery.store_code" in sql:
                return ("asat", "PSN-500", 1, [], "supplier_processing", 2, 5, "", {})
            if "state='processing'" in sql:
                return (1,) if pay_calls else None
            if "state IN ('failed', 'manual_required')" in sql:
                return None
            return None

        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=fake_q1,
            qall=lambda *_args: [],
            exec1=lambda _conn, sql, params=None: writes.append((sql, params)),
            interhub_calculate=lambda _payload: {"success": True, "fixed_amount": "100"},
            interhub_check=lambda _payload: {"success": True},
            interhub_pay=lambda _payload: (pay_calls.append(_payload), (_ for _ in ()).throw(TimeoutError("network timeout")))[1],
        )
        env = {
            "YANDEX_MARKET_ASAT_AUTO_DELIVERY_ENABLED": "true",
            "YANDEX_MARKET_ASAT_AUTO_DELIVERY_NOT_BEFORE": "2026-01-01T00:00:00+00:00",
        }
        with patch.dict(os.environ, env, clear=False):
            processor("asat", 501, 99, datetime(2026, 7, 29, tzinfo=timezone.utc))
            processor("asat", 501, 99, datetime(2026, 7, 29, tzinfo=timezone.utc))

        self.assertEqual(len(pay_calls), 1)
        self.assertTrue(any("SET state='processing'" in sql and "next_status_check_at" in sql for sql, _params in writes))

    # После принятия ключа Маркетом повторно публикуется сохраненный лимит, а не вычисленный остаток поставщика.
    def test_successful_delivery_republishes_saved_target_stock(self):
        writes = []

        def fake_q1(_conn, sql, _params=None):
            if "SELECT orders.offer_id" in sql:
                return ("PSN-500", 1, "PROCESSING", False, True, False)
            if "INSERT INTO app.marketplace_yandex_digital_deliveries" in sql:
                return (10,)
            if "SELECT required_qty, delivered_codes" in sql:
                return (1, ["CODE-ONE"], "supplier_processing", "asat", "PSN-500")
            if "SELECT delivery.store_code" in sql:
                return ("asat", 501, 99, ["CODE-ONE"], "PSN-500", "Инструкция", "supplier_processing")
            if "SELECT manual_stock_limit" in sql:
                return (7,)
            return None

        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=fake_q1,
            qall=lambda *_args: [],
            exec1=lambda _conn, sql, params=None: writes.append((sql, params)),
            stock_republish_delay_sec=0,
        )
        env = {
            "YANDEX_MARKET_ASAT_AUTO_DELIVERY_ENABLED": "true",
            "YANDEX_MARKET_ASAT_AUTO_DELIVERY_NOT_BEFORE": "2026-01-01T00:00:00+00:00",
        }
        with (
            patch.dict(os.environ, env, clear=False),
            patch.object(yandex_market_production_delivery, "deliver_yandex_market_digital_goods", return_value={}) as deliver,
            patch.object(yandex_market_production_delivery, "update_yandex_market_stock", return_value={}) as update_stock,
        ):
            processor("asat", 501, 99, datetime(2026, 7, 29, tzinfo=timezone.utc))

        deliver.assert_called_once_with(501, item_id=99, codes=["CODE-ONE"], slip="Инструкция", store_code="asat")
        update_stock.assert_called_once_with("PSN-500", 7, store_code="asat")
        self.assertTrue(any("last_stock_sync_error=''" in sql for sql, _params in writes))
