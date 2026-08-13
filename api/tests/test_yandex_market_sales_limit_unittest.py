import unittest
from datetime import date

try:
    from api.domains.yandex_market_sales_limit import YandexMarketSalesLimitManager
except ModuleNotFoundError:  # Запуск из папки api использует локальный пакет domains.
    from domains.yandex_market_sales_limit import YandexMarketSalesLimitManager


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


class YandexMarketSalesLimitManagerTests(unittest.TestCase):
    # Создает менеджер с управляемыми ответами БД и журналами внешних действий.
    def create_manager(self, q1_handler, qall_handler=None):
        writes = []
        stocks = []
        archives = []
        manager = YandexMarketSalesLimitManager(
            DB_DSN="postgresql://test",
            psycopg=_FakePsycopg(),
            q1=lambda _conn, sql, params=None: q1_handler(sql, params),
            qall=lambda _conn, sql, params=None: qall_handler(sql, params) if qall_handler else [],
            exec1=lambda _conn, sql, params=None: writes.append((sql, params)) or 1,
            update_stock=lambda offer_id, stock, *, store_code: stocks.append((store_code, offer_id, stock)) or {},
            update_archive=lambda offer_id, *, archived, store_code: archives.append((store_code, offer_id, archived)) or {},
        )
        return manager, writes, stocks, archives

    # Оставшаяся квота ограничивает обычный витринный остаток.
    def test_sync_publishes_only_remaining_sales_limit(self):
        def q1_handler(sql, _params):
            if "FROM app.marketplace_yandex_catalog_items AS catalog" in sql:
                return (5, 5, 10, 1, False, None, False, 6, 1)
            return None

        manager, _writes, stocks, archives = self.create_manager(q1_handler)

        state = manager.sync_target_stock("asat", "PSN-500")

        self.assertEqual(state["sales_limit_remaining"], 3)
        self.assertEqual(stocks, [("asat", "PSN-500", 3)])
        self.assertEqual(archives, [])

    # Разовая прибавка увеличивает только сегодняшний общий лимит и сразу расширяет публикуемый остаток.
    def test_add_daily_units_extends_only_current_day(self):
        today = date(2026, 8, 12)

        def q1_handler(sql, _params):
            if "SET sales_limit_daily_extra=sales_limit_daily_extra +" in sql:
                return (10,)
            if "FROM app.marketplace_yandex_catalog_items AS catalog" in sql:
                return (5, 5, 50, 3, False, None, False, 45, 0, 10, today)
            return None

        manager, _writes, stocks, archives = self.create_manager(q1_handler)
        manager.today_provider = lambda: today

        state = manager.add_daily_units("asat", "PSN-500", 10)

        self.assertEqual(state["sales_limit"], 50)
        self.assertEqual(state["sales_limit_daily_extra"], 10)
        self.assertEqual(state["sales_limit_effective"], 60)
        self.assertEqual(state["sales_limit_remaining"], 15)
        self.assertEqual(stocks, [("asat", "PSN-500", 5)])
        self.assertEqual(archives, [])

    # Фоновый переход на новый день создает новую ревизию, обнуляет бонус и повторно публикует карточку.
    def test_rollover_due_limits_starts_new_daily_cycle(self):
        today = date(2026, 8, 13)

        def q1_handler(sql, _params):
            if "FROM app.marketplace_yandex_catalog_items AS catalog" in sql:
                return (5, 0, 50, 4, True, None, True, 0, 0, 0, today)
            return None

        manager, writes, stocks, archives = self.create_manager(
            q1_handler,
            qall_handler=lambda _sql, _params: [("asat", "PSN-500", date(2026, 8, 12))],
        )
        manager.today_provider = lambda: today

        processed = manager.rollover_due_limits()

        self.assertEqual(processed, 1)
        self.assertTrue(any("sales_limit_rollover_pending=true" in sql for sql, _params in writes))
        self.assertTrue(any("reservation.state='reserved'" in sql for sql, _params in writes))
        self.assertEqual(archives, [("asat", "PSN-500", False)])
        self.assertEqual(stocks, [("asat", "PSN-500", 5)])

    # Полностью распределенный лимит сначала публикует ноль, а затем архивирует карточку.
    def test_sync_archives_card_when_limit_is_exhausted(self):
        def q1_handler(sql, _params):
            if "FROM app.marketplace_yandex_catalog_items AS catalog" in sql:
                return (5, 1, 10, 1, False, None, False, 9, 1)
            return None

        manager, writes, stocks, archives = self.create_manager(q1_handler)

        state = manager.sync_target_stock("asat", "PSN-500")

        self.assertEqual(stocks, [("asat", "PSN-500", 0)])
        self.assertEqual(archives, [("asat", "PSN-500", True)])
        self.assertTrue(state["archived_by_sales_limit"])
        self.assertTrue(any("archived_by_sales_limit=true" in sql for sql, _params in writes))

    # Пустой лимит сохраняет прежнее безлимитное восстановление остатка.
    def test_sync_keeps_manual_stock_for_unlimited_card(self):
        def q1_handler(sql, _params):
            if "FROM app.marketplace_yandex_catalog_items AS catalog" in sql:
                return (5, 2, None, 0, False, None, False, 0, 0)
            return None

        manager, _writes, stocks, archives = self.create_manager(q1_handler)

        state = manager.sync_target_stock("joycards", "APEX-1000")

        self.assertIsNone(state["sales_limit_remaining"])
        self.assertEqual(stocks, [("joycards", "APEX-1000", 5)])
        self.assertEqual(archives, [])

    # Резерв создается целиком и сразу уменьшает доступную для новых заказов квоту.
    def test_reserve_delivery_is_atomic_and_syncs_stock(self):
        def q1_handler(sql, _params):
            if "SELECT settings.sales_limit, settings.sales_limit_revision" in sql:
                return (10, 2, "asat", "PSN-500", 2)
            if "SELECT state, limit_revision" in sql:
                return None
            if "SUM(quantity) FILTER" in sql:
                return (5, 1)
            if "INSERT INTO app.marketplace_yandex_sales_limit_reservations" in sql:
                return (41,)
            return None

        manager, _writes, _stocks, _archives = self.create_manager(q1_handler)
        synced = []
        manager.sync_target_stock = lambda store_code, offer_id: synced.append((store_code, offer_id)) or {}

        allowed = manager.reserve_delivery(17)

        self.assertTrue(allowed)
        self.assertEqual(synced, [("asat", "PSN-500")])

    # Заказ больше остатка квоты остается ручным и не получает частичную выдачу.
    def test_reserve_delivery_rejects_quantity_over_remaining_limit(self):
        def q1_handler(sql, _params):
            if "SELECT settings.sales_limit, settings.sales_limit_revision" in sql:
                return (10, 2, "asat", "PSN-500", 3)
            if "SELECT state, limit_revision" in sql:
                return None
            if "SUM(quantity) FILTER" in sql:
                return (8, 1)
            return None

        manager, writes, _stocks, _archives = self.create_manager(q1_handler)
        manager.sync_target_stock = lambda *_args: {}

        allowed = manager.reserve_delivery(18)

        self.assertFalse(allowed)
        errors = [params for sql, params in writes if "Недостаточно лимита" not in sql and "last_error=%s" in sql]
        self.assertEqual(errors[0][1], 18)
        self.assertIn("доступно 1", errors[0][0])

    # Синхронизация удерживает строку настроек до завершения внешнего запроса и защищает от старого остатка.
    def test_sync_locks_settings_before_reading_and_publishing_stock(self):
        reads = []

        def q1_handler(sql, _params):
            reads.append(sql)
            if "FROM app.marketplace_yandex_catalog_items AS catalog" in sql:
                return (5, 5, 10, 1, False, None, False, 3, 1)
            return None

        manager, _writes, stocks, _archives = self.create_manager(q1_handler)

        manager.sync_target_stock("asat", "PSN-500")

        lock_index = next(index for index, sql in enumerate(reads) if "FOR UPDATE" in sql)
        state_index = next(index for index, sql in enumerate(reads) if "FROM app.marketplace_yandex_catalog_items AS catalog" in sql)
        self.assertLess(lock_index, state_index)
        self.assertEqual(stocks, [("asat", "PSN-500", 5)])

    # Неудачная архивация оставляет флаг повтора, чтобы воркер не потерял незавершенное действие.
    def test_sync_keeps_retry_pending_when_archive_fails(self):
        def q1_handler(sql, _params):
            if "FROM app.marketplace_yandex_catalog_items AS catalog" in sql:
                return (5, 1, 10, 1, False, None, False, 10, 0)
            return None

        manager, writes, _stocks, _archives = self.create_manager(q1_handler)
        manager.update_archive = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("archive unavailable"))

        state = manager.sync_target_stock("asat", "PSN-500", raise_errors=False)

        self.assertIsNone(state["sales_limit"])
        self.assertFalse(any("sales_limit_rollover_pending=false" in sql for sql, _params in writes))
        self.assertTrue(any("last_stock_sync_error=%s" in sql for sql, _params in writes))

    # Выдача после полуночи считается в новой дневной ревизии, но повторное событие не переносит уже учтенную продажу.
    def test_consume_moves_unfinished_reservation_to_current_day(self):
        today = date(2026, 8, 13)
        inserts = []

        def q1_handler(sql, params):
            if "SELECT settings.sales_limit, settings.sales_limit_revision" in sql:
                return (50, 7, "asat", "PSN-500", 2)
            if "SET sales_limit_revision=sales_limit_revision + 1" in sql:
                return ("asat", "PSN-500")
            if "INSERT INTO app.marketplace_yandex_sales_limit_reservations" in sql:
                inserts.append((sql, params))
                return (41,)
            return None

        manager, writes, _stocks, _archives = self.create_manager(q1_handler)
        manager.today_provider = lambda: today

        target = manager.consume_delivery(17)

        self.assertEqual(target, ("asat", "PSN-500"))
        self.assertEqual(inserts[0][1][3], 8)
        self.assertIn("ELSE excluded.limit_revision", inserts[0][0])
        self.assertTrue(any("reservation.state='reserved'" in sql for sql, _params in writes))
        self.assertTrue(any("sales_limit_rollover_pending=true" in sql for sql, _params in writes))


if __name__ == "__main__":
    unittest.main()
