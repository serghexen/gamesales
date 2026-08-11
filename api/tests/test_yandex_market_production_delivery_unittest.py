import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

try:
    from api.domains import yandex_market_production_delivery
    from api.domains.yandex_market_catalog_service import yandex_market_production_auto_delivery_enabled
except ModuleNotFoundError:  # Запуск из папки api использует локальный пакет domains.
    from domains import yandex_market_production_delivery
    from domains.yandex_market_catalog_service import yandex_market_production_auto_delivery_enabled


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
    # Автовыдача изолирована настройкой каждого кабинета, а не зарезервированным именем магазина.
    def test_auto_delivery_flag_is_resolved_for_each_store(self):
        env = {
            "YANDEX_MARKET_ASAT_AUTO_DELIVERY_ENABLED": "false",
            "YANDEX_MARKET_JOYCARDS_AUTO_DELIVERY_ENABLED": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            self.assertFalse(yandex_market_production_auto_delivery_enabled("asat"))
            self.assertTrue(yandex_market_production_auto_delivery_enabled("joycards"))

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
        with patch.dict(os.environ, {
            "YANDEX_MARKET_ASAT_AUTO_DELIVERY_ENABLED": "false",
            "YANDEX_MARKET_JOYCARDS_AUTO_DELIVERY_ENABLED": "false",
        }, clear=False):
            processor.refresh_supplier_attempts()

    # Оплаченный ключ и отметка его применения должны сохраняться одним финальным коммитом выдачи Яндекса.
    def test_paid_yandex_attempt_finalization_applies_code_and_marks_attempt(self):
        writes = []

        def fake_q1(_conn, sql, _params=None):
            if "SELECT attempt.delivery_id" in sql:
                return (31, "PAID-CODE-ONE", "paid", None, 1, [], "supplier_processing")
            if "INSERT INTO app.marketplace_yandex_digital_code_registry" in sql:
                return (31,)
            return None

        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=fake_q1,
            qall=lambda *_args: [],
            exec1=lambda _conn, sql, params=None: writes.append((sql, params)),
        )

        applied, delivery_id = processor.finalize_paid_supplier_attempt(17)

        self.assertTrue(applied)
        self.assertEqual(delivery_id, 31)
        self.assertTrue(any("SET delivered_codes=%s::jsonb" in sql and params[0] == '[\"PAID-CODE-ONE\"]' for sql, params in writes))
        self.assertTrue(any("code_applied_at=now()" in sql and params == ("PAID-CODE-ONE", 17) for sql, params in writes))

    # Ответ paid сначала сохраняет строковое состояние и ключ попытки, а затем запускает атомарный финализатор.
    def test_yandex_paid_response_is_persisted_before_finalization(self):
        writes = []

        def fake_q1(_conn, sql, _params=None):
            if "SELECT delivery.store_code, delivery.offer_id, delivery.required_qty" in sql:
                return ("joycards", "PUBG-300", 1, [], "supplier_processing", 7, 9, "300", {})
            if "state='processing'" in sql or "state='paid' AND code_applied_at IS NULL" in sql:
                return None
            if "state IN ('failed', 'manual_required')" in sql:
                return None
            if "WHERE agent_transaction_id=%s" in sql and sql.lstrip().startswith("SELECT id"):
                return (17,)
            if "SELECT attempt.delivery_id" in sql:
                return (31, "PAID-CODE-ONE", "paid", None, 1, [], "supplier_processing")
            if "INSERT INTO app.marketplace_yandex_digital_code_registry" in sql:
                return (31,)
            return None

        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=fake_q1,
            qall=lambda *_args: [],
            exec1=lambda _conn, sql, params=None: writes.append((sql, params)) or 1,
            interhub_calculate=lambda _payload: {"success": True, "fixed_amount": "100"},
            interhub_check=lambda _payload: {"success": True, "status": 0, "raw": {}},
            interhub_pay=lambda _payload: {
                "success": True,
                "status": 0,
                "message": "paid",
                "params": {"gift_code": "PAID-CODE-ONE"},
                "raw": {},
            },
        )

        result = processor.buy_from_interhub(31)

        self.assertEqual(result, "completed")
        paid_updates = [params for sql, params in writes if "provider_response=%s::jsonb" in sql and "next_status_check_at=CASE WHEN %s THEN" in sql]
        self.assertEqual(paid_updates[0][0], "paid")
        self.assertFalse(paid_updates[0][4])
        self.assertEqual(paid_updates[0][6:8], ("PAID-CODE-ONE", "PAID-CODE-ONE"))

    # Повторный финализатор Яндекса не должен повторно добавлять уже примененный ключ.
    def test_paid_yandex_attempt_finalization_is_idempotent(self):
        writes = []
        applied_at = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)

        def fake_q1(_conn, sql, _params=None):
            if "SELECT attempt.delivery_id" in sql:
                return (31, "PAID-CODE-ONE", "paid", applied_at, 1, ["PAID-CODE-ONE"], "supplier_processing")
            return None

        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=fake_q1,
            qall=lambda *_args: [],
            exec1=lambda _conn, sql, params=None: writes.append((sql, params)),
        )

        applied, delivery_id = processor.finalize_paid_supplier_attempt(17)

        self.assertTrue(applied)
        self.assertEqual(delivery_id, 31)
        self.assertEqual(writes, [])

    # Paid без gift_code блокирует ручную и повторную выдачу, пока фоновая сверка ищет оплаченный ключ.
    def test_paid_yandex_attempt_without_code_stays_unapplied(self):
        writes = []

        def fake_q1(_conn, sql, _params=None):
            if "SELECT attempt.delivery_id" in sql:
                return (31, None, "paid", None, 1, [], "supplier_processing")
            return None

        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=fake_q1,
            qall=lambda *_args: [],
            exec1=lambda _conn, sql, params=None: writes.append((sql, params)),
        )

        applied, delivery_id = processor.finalize_paid_supplier_attempt(17)

        self.assertFalse(applied)
        self.assertEqual(delivery_id, 31)
        self.assertTrue(any("finalization_error=%s" in sql for sql, _params in writes))
        self.assertTrue(any("ELSE 'supplier_processing'" in sql for sql, _params in writes))
        self.assertTrue(any("next_status_check_at=COALESCE" in sql for sql, _params in writes))
        self.assertFalse(any("digital_code_registry" in sql for sql, _params in writes))

    # Ожидающая оплата JoyCards проверяется отдельно, даже когда ASAT оставлен на безопасном выключенном режиме.
    def test_joycards_supplier_poll_runs_while_asat_is_disabled(self):
        status_calls = []
        poll_queries = []

        def fake_qall(_conn, sql, params=None):
            poll_queries.append((sql, params))
            return [(17, 31, "joycards-transaction", "processing")]

        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=lambda *_args: None,
            qall=fake_qall,
            exec1=lambda *_args: 1,
            interhub_check_status=lambda payload: status_calls.append(payload) or {
                "success": False,
                "status": 0,
                "message": "pending",
                "raw": {},
            },
        )
        env = {
            "YANDEX_MARKET_ASAT_AUTO_DELIVERY_ENABLED": "false",
            "YANDEX_MARKET_JOYCARDS_AUTO_DELIVERY_ENABLED": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            processor.refresh_supplier_attempts()

        self.assertEqual(status_calls, [{"agent_transaction_id": "joycards-transaction"}])
        self.assertEqual(poll_queries[0][1][0], ["joycards"])

    # Явный запуск старого заказа без источников создает только локальную ручную очередь, не вызывая внешние API.
    def test_existing_order_can_be_put_into_manual_queue(self):
        queries = []

        def fake_q1(_conn, sql, params=None):
            queries.append((sql, params))
            if "SELECT orders.offer_id" in sql:
                return ("PUBG-300", 1, "PROCESSING", False, False, False)
            if "INSERT INTO app.marketplace_yandex_digital_deliveries" in sql:
                return (17,)
            if "SELECT required_qty, delivered_codes, status" in sql:
                return (1, [], "manual_required", "joycards", "PUBG-300")
            if "SELECT 1 FROM app.marketplace_yandex_digital_suppliers" in sql:
                return None
            if "SELECT auto_issue_enabled" in sql:
                return (False, False)
            return None

        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=fake_q1,
            qall=lambda *_args: [],
            exec1=lambda *_args: 1,
            interhub_calculate=lambda *_args: (_ for _ in ()).throw(AssertionError("Interhub calculate must not run")),
            interhub_check=lambda *_args: (_ for _ in ()).throw(AssertionError("Interhub check must not run")),
            interhub_pay=lambda *_args: (_ for _ in ()).throw(AssertionError("Interhub pay must not run")),
        )
        with patch.dict(os.environ, {"YANDEX_MARKET_JOYCARDS_AUTO_DELIVERY_ENABLED": "true"}, clear=False):
            processor.start_existing_order_manually("joycards", 501, 99)

        self.assertTrue(any("INSERT INTO app.marketplace_yandex_digital_deliveries" in sql for sql, _params in queries))
        self.assertTrue(any("FOR UPDATE OF orders" in sql for sql, _params in queries if "SELECT orders.offer_id" in sql))

    # Просмотр выдачи всегда привязан к item_id, чтобы два товара одного заказа не раскрывали ключи друг друга.
    def test_reveal_delivered_codes_reads_the_exact_yandex_order_item(self):
        queries = []

        def fake_q1(_conn, sql, params=None):
            queries.append((sql, params))
            return (["AAAA-1111"],)

        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=fake_q1,
            qall=lambda *_args: [],
            exec1=lambda *_args: 1,
        )

        self.assertEqual(processor.reveal_delivered_codes("joycards", 501, 99), {"order_id": 501, "item_id": 99, "codes": ["AAAA-1111"]})
        self.assertEqual(queries[0][1], ("joycards", 501, 99))
        self.assertIn("WHERE store_code=%s AND order_id=%s AND item_id=%s", queries[0][0])

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
        self.assertTrue(any("INSERT INTO app.interhub_transactions" in sql and "yandex_market_delivery_id" in sql for sql, _params in writes))
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
        self.assertTrue(any("status='market_sending', market_send_started_at=now()" in sql for sql, _params in writes))
        self.assertTrue(any("status='market_submitted'" in sql and "status='market_sending'" in sql for sql, _params in writes))
        self.assertTrue(any("UPDATE app.marketplace_manual_keys" in sql and "pool.marketplace='yandex_market'" in sql for sql, _params in writes))
        self.assertTrue(any("last_stock_sync_error=''" in sql for sql, _params in writes))

    # После недоступных Interhub и пула третий сценарий передает настроенное сообщение как намеренную заглушку.
    def test_support_message_is_sent_after_interhub_and_pool(self):
        writes = []

        def fake_q1(_conn, sql, _params=None):
            if "SELECT orders.offer_id" in sql:
                return ("PUBG-300", 1, "PROCESSING", False, False, False, True)
            if "INSERT INTO app.marketplace_yandex_digital_deliveries" in sql:
                return (17,)
            if "SELECT required_qty, delivered_codes, status, store_code, offer_id, delivery_source" in sql:
                return (1, [], "manual_required", "joycards", "PUBG-300", "")
            if "SELECT 1 FROM app.marketplace_yandex_digital_suppliers" in sql:
                return None
            if "SELECT auto_issue_enabled, pool_issue_enabled, support_message_delivery_enabled" in sql:
                return (False, False, True)
            if "SELECT delivery.store_code, delivery.required_qty" in sql:
                return ("joycards", 1, [], "manual_required", "", "Заказ принят, код будет отправлен после обработки.", True)
            if "SELECT delivery.store_code, delivery.order_id" in sql:
                return ("joycards", 501, 99, ["Заказ принят, код будет отправлен после обработки."], "PUBG-300", "Инструкция", "supplier_processing")
            if "SELECT manual_stock_limit" in sql:
                return (5,)
            return None

        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=fake_q1,
            qall=lambda *_args: [],
            exec1=lambda _conn, sql, params=None: writes.append((sql, params)),
            stock_republish_delay_sec=0,
        )
        env = {"YANDEX_MARKET_JOYCARDS_AUTO_DELIVERY_ENABLED": "true"}
        with (
            patch.dict(os.environ, env, clear=False),
            patch.object(yandex_market_production_delivery, "deliver_yandex_market_digital_goods", return_value={}) as deliver,
            patch.object(yandex_market_production_delivery, "update_yandex_market_stock", return_value={}),
        ):
            processor.start_existing_order_manually("joycards", 501, 99)

        deliver.assert_called_once_with(
            501,
            item_id=99,
            codes=["Заказ принят, код будет отправлен после обработки."],
            slip="Инструкция",
            store_code="joycards",
        )
        self.assertTrue(any("delivery_source='support_message'" in sql for sql, _params in writes))

    # Ожидающая оплата — не отказ: при всех включенных сценариях пул и сообщение не должны опередить Interhub.
    def test_pending_interhub_stops_fallback_chain_before_pool_and_support_message(self):
        queries = []

        def fake_q1(_conn, sql, _params=None):
            queries.append(sql)
            if "SELECT orders.offer_id" in sql:
                return ("PUBG-300", 1, "PROCESSING", False, True, True, True)
            if "INSERT INTO app.marketplace_yandex_digital_deliveries" in sql:
                return (17,)
            if "SELECT required_qty, delivered_codes, status, store_code, offer_id, delivery_source" in sql:
                return (1, [], "manual_required", "joycards", "PUBG-300", "")
            if "SELECT 1 FROM app.marketplace_yandex_digital_suppliers" in sql:
                return (1,)
            if "SELECT auto_issue_enabled, pool_issue_enabled, support_message_delivery_enabled" in sql:
                return (True, True, True)
            if "SELECT delivery.store_code, delivery.offer_id, delivery.required_qty" in sql:
                return ("joycards", "PUBG-300", 1, [], "manual_required", 7, 9, "300", {})
            if "state='processing'" in sql:
                return (99,)
            return None

        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=fake_q1,
            qall=lambda *_args: [],
            exec1=lambda *_args: 1,
            interhub_calculate=lambda *_args: (_ for _ in ()).throw(AssertionError("Нельзя начинать новую оплату")),
            interhub_check=lambda *_args: (_ for _ in ()).throw(AssertionError("Нельзя начинать новую проверку")),
            interhub_pay=lambda *_args: (_ for _ in ()).throw(AssertionError("Нельзя запускать повторный pay")),
        )
        with patch.dict(os.environ, {"YANDEX_MARKET_JOYCARDS_AUTO_DELIVERY_ENABLED": "true"}, clear=False):
            processor.start_existing_order_manually("joycards", 501, 99)

        self.assertFalse(any("marketplace_manual_key_pools" in sql for sql in queries))
        self.assertFalse(any("settings.support_error_message" in sql for sql in queries))

    # Paid без примененного ключа не должен запускать второй pay, пул или сообщение поддержки.
    def test_paid_unapplied_yandex_attempt_blocks_second_payment_and_fallbacks(self):
        queries = []

        def fake_q1(_conn, sql, _params=None):
            queries.append(sql)
            if "SELECT orders.offer_id" in sql:
                return ("PUBG-300", 1, "PROCESSING", False, True, True, True)
            if "INSERT INTO app.marketplace_yandex_digital_deliveries" in sql:
                return (17,)
            if "SELECT required_qty, delivered_codes, status, store_code, offer_id, delivery_source" in sql:
                return (1, [], "supplier_processing", "joycards", "PUBG-300", "")
            if "SELECT 1 FROM app.marketplace_yandex_digital_suppliers" in sql:
                return (1,)
            if "SELECT auto_issue_enabled, pool_issue_enabled, support_message_delivery_enabled" in sql:
                return (True, True, True)
            if "SELECT delivery.store_code, delivery.offer_id, delivery.required_qty" in sql:
                return ("joycards", "PUBG-300", 1, [], "supplier_processing", 7, 9, "300", {})
            if "state='processing'" in sql:
                return None
            if "state='paid' AND code_applied_at IS NULL" in sql:
                return (99,)
            return None

        forbidden = lambda *_args: (_ for _ in ()).throw(AssertionError("Нельзя запускать повторную оплату"))
        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=fake_q1,
            qall=lambda *_args: [],
            exec1=lambda *_args: 1,
            interhub_calculate=forbidden,
            interhub_check=forbidden,
            interhub_pay=forbidden,
        )
        with patch.dict(os.environ, {"YANDEX_MARKET_JOYCARDS_AUTO_DELIVERY_ENABLED": "true"}, clear=False):
            processor.start_existing_order_manually("joycards", 501, 99)

        self.assertFalse(any("marketplace_manual_key_pools" in sql for sql in queries))
        self.assertFalse(any("settings.support_error_message" in sql for sql in queries))

    # Окончательный отказ Interhub без резервов сразу открывает заказ для ручного ключа.
    def test_terminal_interhub_failure_moves_delivery_to_manual_queue(self):
        writes = []
        pay_calls = []

        def fake_q1(_conn, sql, _params=None):
            if "SELECT orders.offer_id" in sql:
                return ("PUBG-300", 1, "PROCESSING", False, True, False, False)
            if "INSERT INTO app.marketplace_yandex_digital_deliveries" in sql:
                return (31,)
            if "SELECT required_qty, delivered_codes, status, store_code, offer_id, delivery_source" in sql:
                return (1, [], "manual_required", "joycards", "PUBG-300", "")
            if "SELECT 1 FROM app.marketplace_yandex_digital_suppliers" in sql:
                return (1,)
            if "SELECT auto_issue_enabled, pool_issue_enabled, support_message_delivery_enabled" in sql:
                return (True, False, False)
            if "SELECT delivery.store_code, delivery.offer_id, delivery.required_qty" in sql:
                return ("joycards", "PUBG-300", 1, [], "manual_required", 7, 9, "300", {})
            if "state='processing'" in sql or "state='paid' AND code_applied_at IS NULL" in sql:
                return None
            if "state IN ('failed', 'manual_required')" in sql:
                return None
            return None

        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=fake_q1,
            qall=lambda *_args: [],
            exec1=lambda _conn, sql, params=None: writes.append((sql, params)) or 1,
            interhub_calculate=lambda _payload: {"success": True, "fixed_amount": "100"},
            interhub_check=lambda _payload: {"success": False, "status": -136, "message": "not enough gift codes", "raw": {}},
            interhub_pay=lambda payload: pay_calls.append(payload),
        )

        with patch.dict(os.environ, {"YANDEX_MARKET_JOYCARDS_AUTO_DELIVERY_ENABLED": "true"}, clear=False):
            processor.start_existing_order_manually("joycards", 501, 99)

        self.assertEqual(pay_calls, [])
        manual_updates = [sql for sql, _params in writes if "SET status='manual_required'" in sql]
        self.assertEqual(len(manual_updates), 1)
        self.assertIn("attempt.provider_message", manual_updates[0])
        self.assertIn("attempt.state='processing'", manual_updates[0])
        self.assertIn("attempt.state='paid' AND attempt.code_applied_at IS NULL", manual_updates[0])

    # Фоновое восстановление исправляет старую выдачу с уже сохраненным окончательным отказом.
    def test_stranded_failed_attempt_is_recovered_to_manual_queue(self):
        writes = []

        def fake_qall(_conn, sql, _params=None):
            if "SELECT attempt.id" in sql:
                return []
            if "SELECT delivery.id" in sql:
                return [(31,)]
            return []

        def fake_q1(_conn, sql, _params=None):
            if "SELECT required_qty, delivered_codes, status, store_code, offer_id, delivery_source" in sql:
                return (1, [], "supplier_processing", "joycards", "PUBG-300", "")
            if "SELECT 1 FROM app.marketplace_yandex_digital_suppliers" in sql:
                return (1,)
            if "SELECT auto_issue_enabled, pool_issue_enabled, support_message_delivery_enabled" in sql:
                return (True, False, False)
            if "SELECT delivery.store_code, delivery.offer_id, delivery.required_qty" in sql:
                return ("joycards", "PUBG-300", 1, [], "supplier_processing", 7, 9, "300", {})
            if "state='processing'" in sql or "state='paid' AND code_applied_at IS NULL" in sql:
                return None
            if "state IN ('failed', 'manual_required')" in sql:
                return (17,)
            return None

        forbidden = lambda *_args: (_ for _ in ()).throw(AssertionError("Нельзя повторно обращаться к поставщику"))
        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=fake_q1,
            qall=fake_qall,
            exec1=lambda _conn, sql, params=None: writes.append((sql, params)) or 1,
            interhub_calculate=forbidden,
            interhub_check=forbidden,
            interhub_pay=forbidden,
        )

        processor.recover_paid_supplier_attempts({"joycards"})

        manual_updates = [sql for sql, _params in writes if "SET status='manual_required'" in sql]
        self.assertEqual(len(manual_updates), 1)

    # Временный check_status не должен откатить paid или открыть Яндекс-заказ для второго источника.
    def test_paid_yandex_attempt_without_code_keeps_polling_after_status_error(self):
        writes = []

        def fake_qall(_conn, sql, _params=None):
            if "SELECT attempt.id" in sql and "WITH due AS" not in sql:
                return []
            if "SELECT delivery.id" in sql:
                return []
            if "WITH due AS" in sql:
                return [(17, 31, "paid-without-code", "paid")]
            return []

        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=lambda *_args: None,
            qall=fake_qall,
            exec1=lambda _conn, sql, params=None: writes.append((sql, params)) or 1,
            interhub_check_status=lambda *_args: (_ for _ in ()).throw(TimeoutError("temporary")),
        )
        with patch.dict(os.environ, {"YANDEX_MARKET_JOYCARDS_AUTO_DELIVERY_ENABLED": "true"}, clear=False):
            processor.refresh_supplier_attempts()

        status_updates = [
            params
            for sql, params in writes
            if "status_check_lock_token=NULL" in sql and "marketplace_yandex_digital_supplier_attempts" in sql
        ]
        self.assertEqual(status_updates[0][0], "paid")
        self.assertTrue(status_updates[0][4])
        self.assertFalse(any("marketplace_manual_key_pools" in sql for sql, _params in writes))

    # Зависший вызов Маркета переводится в явное неоднозначное состояние без автоматической повторной отправки ключа.
    def test_stale_yandex_market_sending_becomes_unknown_without_resend(self):
        writes = []
        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=lambda *_args: None,
            qall=lambda *_args: [],
            exec1=lambda _conn, sql, params=None: writes.append((sql, params)),
        )

        with patch.object(yandex_market_production_delivery, "deliver_yandex_market_digital_goods") as deliver:
            processor.recover_stale_market_sendings({"asat"})

        deliver.assert_not_called()
        recovery = [(sql, params) for sql, params in writes if "SET status='market_unknown'" in sql]
        self.assertEqual(len(recovery), 1)
        self.assertIn("market_send_started_at", recovery[0][0])
        self.assertEqual(recovery[0][1][1], ["asat"])

    # Поздний подтвержденный статус Маркета закрывает даже процесс, упавший прямо во время внешнего запроса.
    def test_delivered_webhook_reconciles_market_sending(self):
        writes = []

        def fake_q1(_conn, sql, _params=None):
            if "SELECT orders.offer_id" in sql:
                return ("PSN-500", 1, "DELIVERED", False, True, False, False)
            return None

        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=fake_q1,
            qall=lambda *_args: [],
            exec1=lambda _conn, sql, params=None: writes.append((sql, params)),
        )
        env = {
            "YANDEX_MARKET_ASAT_AUTO_DELIVERY_ENABLED": "true",
            "YANDEX_MARKET_ASAT_AUTO_DELIVERY_NOT_BEFORE": "2026-01-01T00:00:00+00:00",
        }
        with patch.dict(os.environ, env, clear=False):
            processor("asat", 501, 99, datetime(2026, 8, 6, tzinfo=timezone.utc))

        terminal_updates = [sql for sql, _params in writes if "status='market_delivered'" in sql]
        self.assertEqual(len(terminal_updates), 1)
        self.assertIn("'market_sending'", terminal_updates[0])
        self.assertIn("last_error=''", terminal_updates[0])
        self.assertTrue(any("UPDATE app.marketplace_manual_keys" in sql for sql, _params in writes))

    # Операторский повтор market_unknown использует сохраненный комплект и не требует раскрывать ключ в браузер.
    def test_manual_retry_of_unknown_delivery_reuses_saved_codes(self):
        writes = []

        def fake_q1(_conn, sql, _params=None):
            if "SELECT required_qty, delivered_codes, status, delivery_source" in sql:
                return (1, ["CODE-ONE"], "market_unknown", "interhub")
            if "SELECT delivery.store_code, delivery.order_id" in sql:
                return ("asat", 501, 99, ["CODE-ONE"], "PSN-500", "Инструкция", "supplier_processing")
            if "SELECT delivery.id, delivery.order_id" in sql:
                return (25, 501, 99, "PSN-500", 1, ["CODE-ONE"], "market_submitted", "", "PSN 500", "PROCESSING", datetime(2026, 8, 6, tzinfo=timezone.utc), datetime(2026, 8, 6, tzinfo=timezone.utc), "interhub")
            return None

        processor = yandex_market_production_delivery.build_yandex_market_production_delivery_processor(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=fake_q1,
            qall=lambda *_args: [],
            exec1=lambda _conn, sql, params=None: writes.append((sql, params)),
            stock_republish_delay_sec=0,
        )
        with (
            patch.object(yandex_market_production_delivery, "deliver_yandex_market_digital_goods", return_value={}) as deliver,
            patch.object(yandex_market_production_delivery, "update_yandex_market_stock", return_value={}),
        ):
            result = processor.deliver_manually(25, [])

        deliver.assert_called_once_with(501, item_id=99, codes=["CODE-ONE"], slip="Инструкция", store_code="asat")
        self.assertEqual(result["status"], "market_submitted")
        self.assertTrue(any("status='supplier_processing'" in sql for sql, _params in writes))


@unittest.skipIf(TestClient is None, "fastapi.testclient requires httpx")
class YandexMarketProductionManualRoutesTests(unittest.TestCase):
    # Проверяет, что ручная выдача вызывается только явными маршрутами и не смешивается с webhook-обработчиком.
    def test_manual_routes_delegate_to_production_processor(self):
        app = FastAPI()
        calls = []
        processor = SimpleNamespace(
            list_manual_deliveries=lambda store_code, offer_id: calls.append(("list", store_code, offer_id)) or [{"id": 7}],
            deliver_manually=lambda delivery_id, codes: calls.append(("deliver", delivery_id, codes)) or {"id": delivery_id, "status": "market_submitted"},
            issue_from_pool_manually=lambda delivery_id: calls.append(("pool", delivery_id)) or {"id": delivery_id, "status": "market_submitted"},
            start_existing_order_manually=lambda store_code, order_id, item_id: calls.append(("start", store_code, order_id, item_id)),
            reveal_delivered_codes=lambda store_code, order_id, item_id: calls.append(("codes", store_code, order_id, item_id)) or {"order_id": order_id, "item_id": item_id, "codes": ["AAAA-1111"]},
        )
        yandex_market_production_delivery.mount_yandex_market_production_delivery_routes(
            app,
            delivery_processor=processor,
            require_role=lambda *_roles: (lambda: SimpleNamespace(username="owner", role="owner")),
        )

        client = TestClient(app)
        # Отсутствующий кабинет должен остановить ручную операцию до запуска выдачи.
        self.assertEqual(client.post("/marketplaces/yandex/orders/501/items/99/start-delivery").status_code, 422)
        self.assertEqual(client.get("/marketplaces/yandex/catalog/PSN-500/manual-deliveries?store_code=asat").json()["items"], [{"id": 7}])
        self.assertEqual(client.post("/marketplaces/yandex/digital-deliveries/7/deliver", json={"codes": ["AAAA-1111"]}).status_code, 200)
        self.assertEqual(client.post("/marketplaces/yandex/digital-deliveries/7/issue-from-pool").status_code, 200)
        self.assertEqual(client.post("/marketplaces/yandex/orders/501/items/99/start-delivery?store_code=joycards").json()["started"], True)
        self.assertEqual(client.get("/marketplaces/yandex/orders/501/items/99/codes?store_code=joycards").json(), {"order_id": 501, "item_id": 99, "codes": ["AAAA-1111"]})
        self.assertEqual(calls, [("list", "asat", "PSN-500"), ("deliver", 7, ["AAAA-1111"]), ("pool", 7), ("start", "joycards", 501, 99), ("codes", "joycards", 501, 99)])
