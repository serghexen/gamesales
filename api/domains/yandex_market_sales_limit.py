from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo


YANDEX_MARKET_SALES_LIMIT_TIMEZONE = ZoneInfo("Europe/Moscow")


class YandexMarketSalesLimitManager:
    def __init__(
        self,
        *,
        DB_DSN,
        psycopg,
        q1,
        qall,
        exec1,
        update_stock: Callable[..., dict[str, Any]],
        update_archive: Callable[..., dict[str, Any]],
        today_provider: Callable[[], date] | None = None,
    ) -> None:
        # Собирает операции лимита в одном месте, чтобы ручная публикация и webhook считали одинаково.
        self.DB_DSN = DB_DSN
        self.psycopg = psycopg
        self.q1 = q1
        self.qall = qall
        self.exec1 = exec1
        self.update_stock = update_stock
        self.update_archive = update_archive
        self.today_provider = today_provider or (lambda: datetime.now(YANDEX_MARKET_SALES_LIMIT_TIMEZONE).date())

    def current_day(self) -> date:
        # Возвращает торговый день по Москве, чтобы все процессы переключали лимит одновременно.
        return self.today_provider()

    def empty_state(self) -> dict[str, Any]:
        # Возвращает безлимитное состояние для карточки, у которой настройки еще не создавались.
        return {
            "sales_limit": None,
            "sales_limit_daily_extra": 0,
            "sales_limit_effective": None,
            "sales_limit_day": self.current_day(),
            "sales_limit_revision": 0,
            "sales_limit_used": 0,
            "sales_limit_reserved": 0,
            "sales_limit_remaining": None,
            "archived_by_sales_limit": False,
            "sales_limit_exhausted_at": None,
            "catalog_archived": False,
            "manual_stock_limit": 0,
            "published_stock": 0,
        }

    def rollover_locked(self, conn, store_code: str, offer_id: str) -> bool:
        # Под блокировкой начинает новый день и переносит незавершенные резервы в новую дневную квоту.
        current_day = self.current_day()
        row = self.q1(
            conn,
            """
            UPDATE app.marketplace_yandex_stock_settings
            SET sales_limit_revision=sales_limit_revision + 1,
                sales_limit_daily_extra=0,
                sales_limit_day=%s,
                sales_limit_rollover_pending=true,
                sales_limit_exhausted_at=NULL,
                updated_at=now()
            WHERE store_code=%s AND offer_id=%s
              AND sales_limit IS NOT NULL AND sales_limit_day < %s
            RETURNING store_code, offer_id
            """,
            (current_day, store_code, offer_id, current_day),
        )
        if row:
            self.exec1(
                conn,
                """
                UPDATE app.marketplace_yandex_sales_limit_reservations AS reservation
                SET limit_revision=settings.sales_limit_revision, updated_at=now()
                FROM app.marketplace_yandex_stock_settings AS settings
                WHERE reservation.store_code=settings.store_code
                  AND reservation.offer_id=settings.offer_id
                  AND reservation.store_code=%s AND reservation.offer_id=%s
                  AND reservation.state='reserved'
                  AND reservation.limit_revision<>settings.sales_limit_revision
                """,
                (store_code, offer_id),
            )
        return bool(row)

    def read_state(self, conn, store_code: str, offer_id: str) -> dict[str, Any]:
        # Считает проданные и зарезервированные единицы только для текущего цикла лимита.
        self.rollover_locked(conn, store_code, offer_id)
        row = self.q1(
            conn,
            """
            SELECT settings.manual_stock_limit, settings.published_stock, settings.sales_limit,
                   settings.sales_limit_revision, settings.archived_by_sales_limit,
                   settings.sales_limit_exhausted_at, catalog.archived,
                   COALESCE(SUM(reservation.quantity) FILTER (
                     WHERE reservation.limit_revision=settings.sales_limit_revision
                       AND reservation.state='consumed'
                   ), 0),
                   COALESCE(SUM(reservation.quantity) FILTER (
                     WHERE reservation.limit_revision=settings.sales_limit_revision
                       AND reservation.state='reserved'
                   ), 0), settings.sales_limit_daily_extra, settings.sales_limit_day
            FROM app.marketplace_yandex_catalog_items AS catalog
            JOIN app.marketplace_yandex_stock_settings AS settings
              ON settings.store_code=catalog.store_code AND settings.offer_id=catalog.offer_id
            LEFT JOIN app.marketplace_yandex_sales_limit_reservations AS reservation
              ON reservation.store_code=settings.store_code AND reservation.offer_id=settings.offer_id
            WHERE settings.store_code=%s AND settings.offer_id=%s
            GROUP BY settings.store_code, settings.offer_id, settings.manual_stock_limit,
                     settings.published_stock, settings.sales_limit, settings.sales_limit_revision,
                     settings.archived_by_sales_limit, settings.sales_limit_exhausted_at, catalog.archived,
                     settings.sales_limit_daily_extra, settings.sales_limit_day
            """,
            (store_code, offer_id),
        )
        if not row:
            return self.empty_state()
        sales_limit = int(row[2]) if row[2] is not None else None
        daily_extra = max(0, int(row[9] or 0)) if len(row) > 9 else 0
        effective_limit = None if sales_limit is None else sales_limit + daily_extra
        used = max(0, int(row[7] or 0))
        reserved = max(0, int(row[8] or 0))
        remaining = None if effective_limit is None else max(0, effective_limit - used - reserved)
        return {
            "manual_stock_limit": max(0, int(row[0] or 0)),
            "published_stock": max(0, int(row[1] or 0)),
            "sales_limit": sales_limit,
            "sales_limit_daily_extra": daily_extra,
            "sales_limit_effective": effective_limit,
            "sales_limit_day": row[10] if len(row) > 10 and row[10] else self.current_day(),
            "sales_limit_revision": max(0, int(row[3] or 0)),
            "archived_by_sales_limit": bool(row[4]),
            "sales_limit_exhausted_at": row[5],
            "catalog_archived": bool(row[6]),
            "sales_limit_used": used,
            "sales_limit_reserved": reserved,
            "sales_limit_remaining": remaining,
        }

    def add_daily_units(self, store_code: str, offer_id: str, units: int) -> dict[str, Any]:
        # Прибавляет квоту только текущему московскому дню и сразу восстанавливает доступный остаток на Маркете.
        normalized_units = max(1, int(units or 0))
        with self.psycopg.connect(self.DB_DSN) as conn:
            self.rollover_locked(conn, store_code, offer_id)
            row = self.q1(
                conn,
                """
                UPDATE app.marketplace_yandex_stock_settings
                SET sales_limit_daily_extra=sales_limit_daily_extra + %s,
                    sales_limit_exhausted_at=NULL,
                    sales_limit_rollover_pending=true,
                    updated_at=now()
                WHERE store_code=%s AND offer_id=%s AND sales_limit IS NOT NULL
                RETURNING sales_limit_daily_extra
                """,
                (normalized_units, store_code, offer_id),
            )
            conn.commit()
        if not row:
            raise ValueError("Сначала задайте дневной лимит")
        return self.sync_target_stock(store_code, offer_id)

    def rollover_due_limits(self, *, batch_size: int = 100) -> int:
        # Находит просроченные дневные циклы малыми блоками и синхронизирует каждую карточку после фиксации БД.
        current_day = self.current_day()
        with self.psycopg.connect(self.DB_DSN) as conn:
            rows = self.qall(
                conn,
                """
                SELECT store_code, offer_id, sales_limit_day
                FROM app.marketplace_yandex_stock_settings
                WHERE sales_limit IS NOT NULL
                  AND (sales_limit_day < %s OR sales_limit_rollover_pending=true)
                ORDER BY sales_limit_day, store_code, offer_id
                FOR UPDATE SKIP LOCKED
                LIMIT %s
                """,
                (current_day, max(1, int(batch_size or 1))),
            )
            for store_code, offer_id, sales_limit_day in rows:
                if sales_limit_day < current_day:
                    self.exec1(
                        conn,
                        """
                        UPDATE app.marketplace_yandex_stock_settings
                        SET sales_limit_revision=sales_limit_revision + 1,
                            sales_limit_daily_extra=0,
                            sales_limit_day=%s,
                            sales_limit_rollover_pending=true,
                            sales_limit_exhausted_at=NULL,
                            updated_at=now()
                        WHERE store_code=%s AND offer_id=%s AND sales_limit_day < %s
                        """,
                        (current_day, str(store_code), str(offer_id), current_day),
                    )
                    self.exec1(
                        conn,
                        """
                        UPDATE app.marketplace_yandex_sales_limit_reservations AS reservation
                        SET limit_revision=settings.sales_limit_revision, updated_at=now()
                        FROM app.marketplace_yandex_stock_settings AS settings
                        WHERE reservation.store_code=settings.store_code
                          AND reservation.offer_id=settings.offer_id
                          AND reservation.store_code=%s AND reservation.offer_id=%s
                          AND reservation.state='reserved'
                          AND reservation.limit_revision<>settings.sales_limit_revision
                        """,
                        (str(store_code), str(offer_id)),
                    )
            conn.commit()
        for store_code, offer_id, _sales_limit_day in rows:
            self.sync_target_stock(str(store_code), str(offer_id), raise_errors=False)
        return len(rows)

    def effective_stock(self, state: dict[str, Any]) -> int:
        # Ограничивает витринный остаток нераспределенной частью общего лимита.
        manual_stock = max(0, int(state.get("manual_stock_limit") or 0))
        remaining = state.get("sales_limit_remaining")
        return manual_stock if remaining is None else min(manual_stock, max(0, int(remaining)))

    def sync_target_stock(self, store_code: str, offer_id: str, *, raise_errors: bool = True) -> dict[str, Any]:
        # Под блокировкой публикует свежий остаток и не дает параллельному заказу вернуть устаревшее значение.
        try:
            with self.psycopg.connect(self.DB_DSN) as conn:
                self.q1(
                    conn,
                    "SELECT 1 FROM app.marketplace_yandex_stock_settings WHERE store_code=%s AND offer_id=%s FOR UPDATE",
                    (store_code, offer_id),
                )
                state = self.read_state(conn, store_code, offer_id)
                target_stock = self.effective_stock(state)
                should_restore = bool(state["archived_by_sales_limit"]) and state["sales_limit_remaining"] != 0
                if should_restore:
                    self.update_archive(offer_id, archived=False, store_code=store_code)
                    self.exec1(
                        conn,
                        "UPDATE app.marketplace_yandex_catalog_items SET archived=false, synced_at=now() WHERE store_code=%s AND offer_id=%s",
                        (store_code, offer_id),
                    )
                    self.exec1(
                        conn,
                        "UPDATE app.marketplace_yandex_stock_settings SET archived_by_sales_limit=false, sales_limit_exhausted_at=NULL, updated_at=now() WHERE store_code=%s AND offer_id=%s",
                        (store_code, offer_id),
                    )
                    state["catalog_archived"] = False
                    state["archived_by_sales_limit"] = False

                self.update_stock(offer_id, target_stock, store_code=store_code)

                exhausted = state["sales_limit_remaining"] == 0
                if exhausted and not state["catalog_archived"]:
                    self.update_archive(offer_id, archived=True, store_code=store_code)
                    self.exec1(
                        conn,
                        "UPDATE app.marketplace_yandex_catalog_items SET archived=true, synced_at=now() WHERE store_code=%s AND offer_id=%s",
                        (store_code, offer_id),
                    )
                    self.exec1(
                        conn,
                        "UPDATE app.marketplace_yandex_stock_settings SET archived_by_sales_limit=true, sales_limit_exhausted_at=COALESCE(sales_limit_exhausted_at, now()), updated_at=now() WHERE store_code=%s AND offer_id=%s",
                        (store_code, offer_id),
                    )
                    state["catalog_archived"] = True
                    state["archived_by_sales_limit"] = True

                # Снимает флаг повтора только после успешного завершения всех внешних действий.
                self.exec1(
                    conn,
                    "UPDATE app.marketplace_yandex_stock_settings SET published_stock=%s, sales_limit_rollover_pending=false, last_stock_sync_at=now(), last_stock_sync_error='', updated_at=now() WHERE store_code=%s AND offer_id=%s",
                    (target_stock, store_code, offer_id),
                )
                conn.commit()
            state["published_stock"] = target_stock
            return state
        except Exception as error:
            # Сохраняет сбой внешнего действия отдельно, чтобы уже выданный ключ и счетчик лимита не откатывались.
            with self.psycopg.connect(self.DB_DSN) as conn:
                self.exec1(
                    conn,
                    "UPDATE app.marketplace_yandex_stock_settings SET last_stock_sync_error=%s, updated_at=now() WHERE store_code=%s AND offer_id=%s",
                    (str(getattr(error, "detail", error))[:2000], store_code, offer_id),
                )
                conn.commit()
            if raise_errors:
                raise
            return self.empty_state()

    def reserve_delivery(self, delivery_id: int) -> bool:
        # Резервирует весь заказ под блокировкой карточки и не допускает частичного превышения лимита.
        sync_target: tuple[str, str] | None = None
        with self.psycopg.connect(self.DB_DSN) as conn:
            row = self.q1(
                conn,
                """
                SELECT settings.sales_limit, settings.sales_limit_revision,
                       delivery.store_code, delivery.offer_id, delivery.required_qty,
                       settings.sales_limit_daily_extra
                FROM app.marketplace_yandex_digital_deliveries AS delivery
                JOIN app.marketplace_yandex_stock_settings AS settings
                  ON settings.store_code=delivery.store_code AND settings.offer_id=delivery.offer_id
                WHERE delivery.id=%s
                FOR UPDATE OF delivery, settings
                """,
                (delivery_id,),
            )
            if not row or row[0] is None:
                conn.commit()
                return True
            store_code, offer_id, required_qty = str(row[2]), str(row[3]), max(1, int(row[4] or 1))
            rolled_over = self.rollover_locked(conn, store_code, offer_id)
            revision = max(0, int(row[1] or 0)) + (1 if rolled_over else 0)
            daily_extra = max(0, int(row[5] or 0)) if len(row) > 5 else 0
            effective_limit = int(row[0]) + (0 if rolled_over else daily_extra)
            existing = self.q1(
                conn,
                "SELECT state, limit_revision FROM app.marketplace_yandex_sales_limit_reservations WHERE delivery_id=%s",
                (delivery_id,),
            )
            existing_state = str(existing[0] or "") if existing else ""
            existing_revision = int(existing[1] or 0) if existing else 0
            if existing_state == "consumed" or (existing_state == "reserved" and existing_revision == revision):
                sync_target = (store_code, offer_id)
                allowed = True
            else:
                totals = self.q1(
                    conn,
                    """
                    SELECT COALESCE(SUM(quantity) FILTER (WHERE state='consumed'), 0),
                           COALESCE(SUM(quantity) FILTER (WHERE state='reserved'), 0)
                    FROM app.marketplace_yandex_sales_limit_reservations
                    WHERE store_code=%s AND offer_id=%s AND limit_revision=%s
                    """,
                    (store_code, offer_id, revision),
                ) or (0, 0)
                remaining = max(0, effective_limit - int(totals[0] or 0) - int(totals[1] or 0))
                if required_qty > remaining:
                    self.exec1(
                        conn,
                        "UPDATE app.marketplace_yandex_digital_deliveries SET status='manual_required', last_error=%s, updated_at=now() WHERE id=%s",
                        (f"Недостаточно лимита продаж: доступно {remaining}, требуется {required_qty}", delivery_id),
                    )
                    sync_target = (store_code, offer_id)
                    allowed = False
                else:
                    self.q1(
                        conn,
                        """
                        INSERT INTO app.marketplace_yandex_sales_limit_reservations(
                          delivery_id, store_code, offer_id, limit_revision, quantity, state
                        )
                        VALUES (%s, %s, %s, %s, %s, 'reserved')
                        ON CONFLICT (delivery_id) DO UPDATE
                        SET limit_revision=excluded.limit_revision, quantity=excluded.quantity,
                            state=CASE
                              WHEN app.marketplace_yandex_sales_limit_reservations.state='consumed' THEN 'consumed'
                              ELSE 'reserved'
                            END,
                            released_at=NULL, updated_at=now()
                        RETURNING id
                        """,
                        (delivery_id, store_code, offer_id, revision, required_qty),
                    )
                    sync_target = (store_code, offer_id)
                    allowed = True
            # Оставляет флаг повтора до подтвержденной публикации рассчитанного остатка.
            self.exec1(
                conn,
                "UPDATE app.marketplace_yandex_stock_settings SET sales_limit_rollover_pending=true, updated_at=now() WHERE store_code=%s AND offer_id=%s",
                (store_code, offer_id),
            )
            conn.commit()
        if sync_target:
            self.sync_target_stock(*sync_target)
        return allowed

    def consume_delivery(self, delivery_id: int) -> tuple[str, str] | None:
        # Переводит резерв в продажу один раз после подтвержденной отправки цифрового товара Маркету.
        with self.psycopg.connect(self.DB_DSN) as conn:
            row = self.q1(
                conn,
                """
                SELECT settings.sales_limit, settings.sales_limit_revision,
                       delivery.store_code, delivery.offer_id, delivery.required_qty
                FROM app.marketplace_yandex_digital_deliveries AS delivery
                JOIN app.marketplace_yandex_stock_settings AS settings
                  ON settings.store_code=delivery.store_code AND settings.offer_id=delivery.offer_id
                WHERE delivery.id=%s
                FOR UPDATE OF delivery, settings
                """,
                (delivery_id,),
            )
            if not row:
                conn.commit()
                return None
            store_code, offer_id = str(row[2]), str(row[3])
            rolled_over = self.rollover_locked(conn, store_code, offer_id)
            if row[0] is not None:
                self.q1(
                    conn,
                    """
                    INSERT INTO app.marketplace_yandex_sales_limit_reservations(
                      delivery_id, store_code, offer_id, limit_revision, quantity, state, consumed_at
                    )
                    VALUES (%s, %s, %s, %s, %s, 'consumed', now())
                    ON CONFLICT (delivery_id) DO UPDATE
                    SET limit_revision=CASE
                          WHEN app.marketplace_yandex_sales_limit_reservations.state='consumed'
                          THEN app.marketplace_yandex_sales_limit_reservations.limit_revision
                          ELSE excluded.limit_revision
                        END,
                        quantity=CASE
                          WHEN app.marketplace_yandex_sales_limit_reservations.state='consumed'
                          THEN app.marketplace_yandex_sales_limit_reservations.quantity
                          ELSE excluded.quantity
                        END,
                        state='consumed',
                        consumed_at=COALESCE(app.marketplace_yandex_sales_limit_reservations.consumed_at, now()),
                        updated_at=now()
                    RETURNING id
                    """,
                    (
                        delivery_id,
                        store_code,
                        offer_id,
                        int(row[1] or 0) + (1 if rolled_over else 0),
                        max(1, int(row[4] or 1)),
                    ),
                )
                self.exec1(
                    conn,
                    "UPDATE app.marketplace_yandex_stock_settings SET sales_limit_rollover_pending=true, updated_at=now() WHERE store_code=%s AND offer_id=%s",
                    (store_code, offer_id),
                )
            conn.commit()
        return (store_code, offer_id)

    def consume_order(self, store_code: str, order_id: int, item_id: int) -> tuple[str, str] | None:
        # Находит локальную выдачу по позиции, чтобы поздний DELIVERED восстановил незавершенный учет продажи.
        with self.psycopg.connect(self.DB_DSN) as conn:
            row = self.q1(
                conn,
                "SELECT id FROM app.marketplace_yandex_digital_deliveries WHERE store_code=%s AND order_id=%s AND item_id=%s",
                (store_code, order_id, item_id),
            )
            conn.commit()
        return self.consume_delivery(int(row[0])) if row else None

    def release_delivery(self, store_code: str, order_id: int, item_id: int) -> tuple[str, str] | None:
        # Освобождает только неиспользованный резерв отмененного заказа и оставляет проданные ключи учтенными.
        with self.psycopg.connect(self.DB_DSN) as conn:
            row = self.q1(
                conn,
                """
                SELECT delivery.id, delivery.offer_id
                FROM app.marketplace_yandex_digital_deliveries AS delivery
                WHERE delivery.store_code=%s AND delivery.order_id=%s AND delivery.item_id=%s
                FOR UPDATE OF delivery
                """,
                (store_code, order_id, item_id),
            )
            if not row:
                conn.commit()
                return None
            reservation = self.q1(
                conn,
                "SELECT state FROM app.marketplace_yandex_sales_limit_reservations WHERE delivery_id=%s FOR UPDATE",
                (int(row[0]),),
            )
            if reservation and str(reservation[0] or "") == "released":
                conn.commit()
                return (store_code, str(row[1]))
            if not reservation or str(reservation[0] or "") != "reserved":
                conn.commit()
                return None
            self.exec1(
                conn,
                "UPDATE app.marketplace_yandex_sales_limit_reservations SET state='released', released_at=now(), updated_at=now() WHERE delivery_id=%s AND state='reserved'",
                (int(row[0]),),
            )
            self.exec1(
                conn,
                "UPDATE app.marketplace_yandex_stock_settings SET sales_limit_rollover_pending=true, updated_at=now() WHERE store_code=%s AND offer_id=%s",
                (store_code, str(row[1])),
            )
            conn.commit()
        return (store_code, str(row[1]))
