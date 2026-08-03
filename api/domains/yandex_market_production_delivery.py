from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
import os
from threading import Timer
import uuid
from typing import Any, Callable

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from .yandex_market_catalog_service import (
    deliver_yandex_market_digital_goods,
    update_yandex_market_stock,
    normalize_yandex_market_store_code,
    yandex_market_production_auto_delivery_enabled,
    yandex_market_production_auto_delivery_enabled_store_codes,
    yandex_market_production_auto_delivery_not_before,
)


class YandexMarketManualDeliveryIn(BaseModel):
    codes: list[str] = Field(min_length=1, max_length=100)


def build_yandex_market_production_delivery_processor(
    *,
    DB_DSN,
    psycopg,
    q1,
    qall,
    exec1,
    interhub_calculate=None,
    interhub_check=None,
    interhub_pay=None,
    interhub_check_status=None,
    stock_republish_delay_sec: float = 3,
) -> Callable[[str, int, int, datetime | None], None]:
    # Создает боевой обработчик отдельно от приема уведомления: выключенный флаг исключает резерв и внешние API.
    def pool_secret() -> str:
        # Использует отдельный секрет пула, чтобы ключи расшифровывались только внутри серверной выдачи.
        value = str(os.getenv("MARKETPLACE_KEY_POOL_SECRET", "")).strip()
        if len(value) < 32:
            raise HTTPException(503, "Не задан секрет ручного пула ключей")
        return value

    def code_hash(code: str) -> str:
        # Создает отпечаток ключа, который не позволяет закрепить его за двумя заказами.
        return sha256(f"yandex-digital-code:v1:{str(code)}".encode("utf-8")).hexdigest()

    def texts(value: Any) -> list[str]:
        # Приводит jsonb со списком ключей к непустым строкам без раскрытия служебных значений.
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = []
        return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []

    def provider_state(result: dict[str, Any]) -> str:
        # Нормализует ответ Interhub к состояниям, которые безопасны для дальнейшего решения по заказу.
        if bool(result.get("success")) and int(result.get("status") or 0) == 1:
            return "processing"
        if bool(result.get("success")) and int(result.get("status") or 0) == 0:
            return "paid"
        return "failed"

    def mark_manual(delivery_id: int, message: str) -> None:
        # Оставляет выдачу оператору и не отменяет уже собранный комплект ключей.
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                UPDATE app.marketplace_yandex_digital_deliveries
                SET status=CASE WHEN status='cancelled' THEN 'cancelled' ELSE 'manual_required' END,
                    last_error=%s, updated_at=now()
                WHERE id=%s
                """,
                (str(message)[:2000], delivery_id),
            )
            conn.commit()

    def save_supplier_code(delivery_id: int, code: str) -> bool:
        # Закрепляет полученный ключ до следующей покупки, чтобы повторный ответ поставщика не ушел другому покупателю.
        normalized = str(code or "").strip()
        if not normalized:
            mark_manual(delivery_id, "Interhub подтвердил оплату, но не вернул ключ. Проверьте операцию у поставщика.")
            return False
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                "SELECT required_qty, delivered_codes, status FROM app.marketplace_yandex_digital_deliveries WHERE id=%s FOR UPDATE",
                (delivery_id,),
            )
            if not row or str(row[2] or "") not in {"manual_required", "supplier_processing"}:
                conn.commit()
                return False
            codes = texts(row[1])
            if normalized in codes:
                conn.commit()
                mark_manual(delivery_id, "Interhub вернул повторный ключ. Добавьте недостающий ключ вручную.")
                return False
            if len(codes) >= int(row[0] or 1):
                conn.commit()
                return False
            owner = q1(
                conn,
                """
                INSERT INTO app.marketplace_yandex_digital_code_registry(code_hash, delivery_id)
                VALUES (%s, %s)
                ON CONFLICT (code_hash) DO NOTHING
                RETURNING delivery_id
                """,
                (code_hash(normalized), delivery_id),
            )
            if not owner:
                conn.commit()
                mark_manual(delivery_id, "Interhub вернул ключ, уже закрепленный за другим заказом.")
                return False
            codes.append(normalized)
            exec1(
                conn,
                """
                UPDATE app.marketplace_yandex_digital_deliveries
                SET delivered_codes=%s::jsonb, status='supplier_processing', last_error='', updated_at=now()
                WHERE id=%s
                """,
                (json.dumps(codes, ensure_ascii=False), delivery_id),
            )
            conn.commit()
        return True

    def republish_yandex_target_stock(store_code: str, offer_id: str) -> None:
        # После принятого ключа повторяет сохраненный оператором остаток и не пытается вычислять запас поставщика.
        try:
            with psycopg.connect(DB_DSN) as conn:
                settings = q1(
                    conn,
                    "SELECT manual_stock_limit FROM app.marketplace_yandex_stock_settings WHERE store_code=%s AND offer_id=%s",
                    (store_code, offer_id),
                )
                conn.commit()
            if not settings:
                return
            target_stock = max(0, int(settings[0] or 0))
            update_yandex_market_stock(offer_id, target_stock, store_code=store_code)
            with psycopg.connect(DB_DSN) as conn:
                exec1(
                    conn,
                    "UPDATE app.marketplace_yandex_stock_settings SET published_stock=%s, last_stock_sync_at=now(), last_stock_sync_error='', updated_at=now() WHERE store_code=%s AND offer_id=%s",
                    (target_stock, store_code, offer_id),
                )
                conn.commit()

        except Exception as error:
            # Выдача уже подтверждена Маркетом, поэтому ошибку остатка сохраняем отдельно и не откатываем ключ.
            with psycopg.connect(DB_DSN) as conn:
                exec1(
                    conn,
                    "UPDATE app.marketplace_yandex_stock_settings SET last_stock_sync_error=%s, updated_at=now() WHERE store_code=%s AND offer_id=%s",
                    (str(getattr(error, "detail", error))[:2000], store_code, offer_id),
                )
                conn.commit()

    def schedule_yandex_target_stock_republish(store_code: str, offer_id: str) -> None:
        # Откладывает публикацию остатка, чтобы Маркет успел принять цифровой код до следующего товарного метода.
        delay = max(0.0, float(stock_republish_delay_sec or 0))
        if delay == 0:
            republish_yandex_target_stock(store_code, offer_id)
            return
        timer = Timer(delay, republish_yandex_target_stock, args=(store_code, offer_id))
        timer.daemon = True
        timer.start()

    def send_delivery(delivery_id: int) -> None:
        # Передает собранный комплект Маркету один раз; неясный сетевой ответ запрещает автоматический повтор.
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                """
                SELECT delivery.store_code, delivery.order_id, delivery.item_id, delivery.delivered_codes,
                       delivery.offer_id, settings.activation_instruction, delivery.status
                FROM app.marketplace_yandex_digital_deliveries AS delivery
                JOIN app.marketplace_yandex_stock_settings AS settings
                  ON settings.store_code=delivery.store_code AND settings.offer_id=delivery.offer_id
                WHERE delivery.id=%s FOR UPDATE
                """,
                (delivery_id,),
            )
            if not row or str(row[6] or "") not in {"manual_required", "supplier_processing"}:
                conn.commit()
                return
            codes = texts(row[3])
            instruction = str(row[5] or "").strip()
            if not codes or not instruction:
                exec1(
                    conn,
                    "UPDATE app.marketplace_yandex_digital_deliveries SET status='manual_required', last_error=%s, updated_at=now() WHERE id=%s",
                    ("Не найден комплект ключей или инструкция покупателю", delivery_id),
                )
                conn.commit()
                return
            exec1(
                conn,
                "UPDATE app.marketplace_yandex_digital_deliveries SET status='market_sending', last_error='', updated_at=now() WHERE id=%s",
                (delivery_id,),
            )
            conn.commit()
        try:
            deliver_yandex_market_digital_goods(
                int(row[1]), item_id=int(row[2]), codes=codes, slip=instruction, store_code=str(row[0])
            )
        except HTTPException as error:
            definite = 400 <= int(error.status_code) < 500
            with psycopg.connect(DB_DSN) as conn:
                exec1(
                    conn,
                    "UPDATE app.marketplace_yandex_digital_deliveries SET status=%s, last_error=%s, updated_at=now() WHERE id=%s",
                    ("manual_required" if definite else "market_unknown", str(error.detail)[:2000], delivery_id),
                )
                conn.commit()
            return
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                "UPDATE app.marketplace_yandex_digital_deliveries SET status='market_submitted', market_submitted_at=now(), updated_at=now() WHERE id=%s",
                (delivery_id,),
            )
            conn.commit()
        schedule_yandex_target_stock_republish(str(row[0]), str(row[4]))

    def take_from_pool(delivery_id: int, allowed_statuses: set[str] | None = None) -> bool:
        # Резервирует полный комплект из пула транзакционно: частичный заказ автоматически не отправляется.
        secret = pool_secret()
        with psycopg.connect(DB_DSN) as conn:
            delivery = q1(
                conn,
                """
                SELECT store_code, order_id, item_id, offer_id, required_qty, delivered_codes, status
                FROM app.marketplace_yandex_digital_deliveries WHERE id=%s FOR UPDATE
                """,
                (delivery_id,),
            )
            allowed = allowed_statuses or {"manual_required", "supplier_processing"}
            if not delivery or str(delivery[6] or "") not in allowed:
                conn.commit()
                return False
            current = texts(delivery[5])
            missing = int(delivery[4]) - len(current)
            if missing <= 0:
                conn.commit()
                send_delivery(delivery_id)
                return True
            pool = q1(
                conn,
                "SELECT id FROM app.marketplace_manual_key_pools WHERE marketplace='yandex_market' AND store_code=%s AND product_key=%s",
                (str(delivery[0]), str(delivery[3])),
            )
            if not pool:
                conn.commit()
                return False
            rows = qall(
                conn,
                """
                SELECT id, pgp_sym_decrypt(code_ciphertext, %s) FROM app.marketplace_manual_keys
                WHERE pool_id=%s AND status='free' AND (expires_at IS NULL OR expires_at >= current_date)
                ORDER BY created_at, id FOR UPDATE SKIP LOCKED LIMIT %s
                """,
                (secret, int(pool[0]), missing),
            )
            if len(rows) != missing:
                conn.commit()
                return False
            codes = [str(item[1] or "").strip() for item in rows]
            if any(not code for code in codes):
                raise HTTPException(409, "В ручном пуле найден пустой ключ")
            for code in codes:
                owner = q1(
                    conn,
                    "INSERT INTO app.marketplace_yandex_digital_code_registry(code_hash, delivery_id) VALUES (%s, %s) ON CONFLICT (code_hash) DO NOTHING RETURNING delivery_id",
                    (code_hash(code), delivery_id),
                )
                if not owner:
                    raise HTTPException(409, "Ключ из ручного пула уже закреплен за другой выдачей")
            order_ref = f"yandex:{delivery[0]}:{delivery[1]}:{delivery[2]}"
            exec1(
                conn,
                "UPDATE app.marketplace_manual_keys SET status='reserved', issued_order_ref=%s, reserved_at=now(), updated_at=now() WHERE id=ANY(%s) AND status='free'",
                (order_ref, [int(item[0]) for item in rows]),
            )
            exec1(
                conn,
                "UPDATE app.marketplace_yandex_digital_deliveries SET delivered_codes=%s::jsonb, status='supplier_processing', last_error='', updated_at=now() WHERE id=%s",
                (json.dumps(current + codes, ensure_ascii=False), delivery_id),
            )
            conn.commit()
        send_delivery(delivery_id)
        return True

    def buy_from_interhub(delivery_id: int) -> bool:
        # Покупает один недостающий ключ и создает попытку до pay, чтобы новый webhook не списал деньги повторно.
        if not interhub_calculate or not interhub_check or not interhub_pay:
            return False
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                """
                SELECT delivery.store_code, delivery.offer_id, delivery.required_qty, delivery.delivered_codes, delivery.status,
                       supplier.id, supplier.service_id, supplier.nominal_id, supplier.params
                FROM app.marketplace_yandex_digital_deliveries AS delivery
                JOIN app.marketplace_yandex_digital_suppliers AS supplier
                  ON supplier.store_code=delivery.store_code AND supplier.offer_id=delivery.offer_id
                WHERE delivery.id=%s AND supplier.enabled=true AND supplier.provider_code='interhub'
                ORDER BY supplier.priority, supplier.id LIMIT 1 FOR UPDATE
                """,
                (delivery_id,),
            )
            if not row or str(row[4] or "") not in {"manual_required", "supplier_processing"}:
                conn.commit()
                return False
            if len(texts(row[3])) >= int(row[2] or 1):
                conn.commit()
                send_delivery(delivery_id)
                return True
            active = q1(
                conn,
                "SELECT id FROM app.marketplace_yandex_digital_supplier_attempts WHERE delivery_id=%s AND state='processing' LIMIT 1",
                (delivery_id,),
            )
            if active:
                conn.commit()
                return False
            failed = q1(
                conn,
                """
                SELECT id FROM app.marketplace_yandex_digital_supplier_attempts
                WHERE delivery_id=%s AND supplier_id=%s AND state IN ('failed', 'manual_required')
                LIMIT 1
                """,
                (delivery_id, int(row[5])),
            )
            if failed:
                # После окончательного отказа не повторяем оплату тем же поставщиком: дальше возможен только пул или оператор.
                conn.commit()
                return False
            transaction_id = f"gamesales-yandex-{uuid.uuid4().hex}"
            exec1(
                conn,
                "UPDATE app.marketplace_yandex_digital_deliveries SET status='supplier_processing', last_error='', updated_at=now() WHERE id=%s",
                (delivery_id,),
            )
            exec1(
                conn,
                """
                INSERT INTO app.marketplace_yandex_digital_supplier_attempts(
                  delivery_id, supplier_id, agent_transaction_id, state, next_status_check_at
                ) VALUES (%s, %s, %s, 'processing', now() + interval '1 minute')
                """,
                (delivery_id, int(row[5]), transaction_id),
            )
            conn.commit()
        try:
            params = row[8] if isinstance(row[8], dict) else json.loads(row[8] or "{}")
        except (TypeError, json.JSONDecodeError):
            params = {}
        if str(row[7] or "").strip():
            params["nominal"] = str(row[7]).strip()
        request = {"service_id": int(row[6]), "account": "", "agent_transaction_id": transaction_id, "params": params}
        pay_started = False
        try:
            calculated = interhub_calculate({**request, "agent_transaction_id": f"{transaction_id}-calculate"})
            amount = float(calculated.get("fixed_amount") or 0)
            if not bool(calculated.get("success")) or amount <= 0:
                raise HTTPException(502, str(calculated.get("message") or "Interhub не вернул цену"))
            checked = interhub_check({**request, "amount": amount})
            if not bool(checked.get("success")):
                raise HTTPException(502, str(checked.get("message") or "Interhub не подтвердил выдачу"))
            # После отправки pay сетевая ошибка означает неизвестный результат, а не безопасный отказ.
            pay_started = True
            paid = interhub_pay({"agent_transaction_id": transaction_id})
        except Exception as error:
            message = str(getattr(error, "detail", error))[:2000]
            with psycopg.connect(DB_DSN) as conn:
                if pay_started:
                    exec1(
                        conn,
                        """
                        UPDATE app.marketplace_yandex_digital_supplier_attempts
                        SET state='processing', provider_message=%s, next_status_check_at=now() + interval '1 minute', updated_at=now()
                        WHERE agent_transaction_id=%s
                        """,
                        (message, transaction_id),
                    )
                else:
                    exec1(
                        conn,
                        "UPDATE app.marketplace_yandex_digital_supplier_attempts SET state='failed', provider_message=%s, updated_at=now() WHERE agent_transaction_id=%s",
                        (message, transaction_id),
                    )
                conn.commit()
            return False
        state = provider_state(paid)
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                UPDATE app.marketplace_yandex_digital_supplier_attempts
                SET state=%s, provider_status=%s, provider_message=%s, provider_response=%s::jsonb,
                    next_status_check_at=CASE WHEN %s='processing' THEN now() + interval '1 minute' ELSE NULL END,
                    updated_at=now()
                WHERE agent_transaction_id=%s
                """,
                (
                    state,
                    int(paid.get("status") or 0),
                    str(paid.get("message") or "")[:2000],
                    json.dumps(paid.get("raw") or {}),
                    state,
                    transaction_id,
                ),
            )
            conn.commit()
        if state == "paid":
            return save_supplier_code(delivery_id, str((paid.get("params") or {}).get("gift_code") or ""))
        return False

    def process_delivery_steps(delivery_id: int) -> None:
        # Собирает недостающие коды без рекурсии и останавливается на ожидании неопределенной оплаты.
        while True:
            with psycopg.connect(DB_DSN) as conn:
                row = q1(
                    conn,
                    "SELECT required_qty, delivered_codes, status, store_code, offer_id FROM app.marketplace_yandex_digital_deliveries WHERE id=%s",
                    (delivery_id,),
                )
                conn.commit()
            if not row or str(row[2] or "") not in {"manual_required", "supplier_processing"}:
                return
            if len(texts(row[1])) >= int(row[0] or 1):
                send_delivery(delivery_id)
                return
            with psycopg.connect(DB_DSN) as conn:
                supplier = q1(
                    conn,
                    "SELECT 1 FROM app.marketplace_yandex_digital_suppliers WHERE store_code=%s AND offer_id=%s AND enabled=true LIMIT 1",
                    (str(row[3]), str(row[4])),
                )
                settings = q1(
                    conn,
                    "SELECT auto_issue_enabled, pool_issue_enabled FROM app.marketplace_yandex_stock_settings WHERE store_code=%s AND offer_id=%s",
                    (str(row[3]), str(row[4])),
                )
                conn.commit()
            if settings and bool(settings[0]) and supplier and buy_from_interhub(delivery_id):
                continue
            if settings and bool(settings[1]):
                take_from_pool(delivery_id)
            return

    def refresh_supplier_attempts() -> None:
        # Дозапрашивает только оплаты включенных кабинетов и никогда не создает новый заказ, ключ или повторный pay.
        enabled_store_codes = yandex_market_production_auto_delivery_enabled_store_codes()
        if not interhub_check_status or not enabled_store_codes:
            return
        lock_token = str(uuid.uuid4())
        with psycopg.connect(DB_DSN) as conn:
            attempts = qall(
                conn,
                """
                WITH due AS (
                  SELECT attempt.id
                  FROM app.marketplace_yandex_digital_supplier_attempts AS attempt
                  JOIN app.marketplace_yandex_digital_deliveries AS delivery ON delivery.id=attempt.delivery_id
                  WHERE attempt.state='processing' AND attempt.next_status_check_at <= now()
                    AND delivery.store_code = ANY(%s)
                    AND (attempt.status_check_locked_until IS NULL OR attempt.status_check_locked_until <= now())
                  ORDER BY attempt.next_status_check_at, attempt.id
                  FOR UPDATE SKIP LOCKED LIMIT 50
                )
                UPDATE app.marketplace_yandex_digital_supplier_attempts AS attempt
                SET status_check_lock_token=%s::uuid, status_check_locked_until=now() + interval '5 minutes', updated_at=now()
                FROM due WHERE attempt.id=due.id
                RETURNING attempt.id, attempt.delivery_id, attempt.agent_transaction_id
                """,
                (sorted(enabled_store_codes), lock_token),
            )
            conn.commit()
        for attempt_id, delivery_id, transaction_id in attempts:
            try:
                result = interhub_check_status({"agent_transaction_id": str(transaction_id)})
                state = provider_state(result)
            except Exception as error:
                result = {"success": False, "status": 0, "message": str(getattr(error, "detail", error)), "raw": {}}
                state = "processing"
            with psycopg.connect(DB_DSN) as conn:
                updated = exec1(
                    conn,
                    """
                    UPDATE app.marketplace_yandex_digital_supplier_attempts
                    SET state=%s, provider_status=%s, provider_message=%s, provider_response=%s::jsonb,
                        next_status_check_at=CASE WHEN %s='processing' THEN now() + interval '5 minutes' ELSE NULL END,
                        status_check_attempts=CASE WHEN %s='processing' THEN status_check_attempts + 1 ELSE status_check_attempts END,
                        status_check_lock_token=NULL, status_check_locked_until=NULL, updated_at=now()
                    WHERE id=%s AND status_check_lock_token=%s::uuid
                    """,
                    (
                        state,
                        int(result.get("status") or 0),
                        str(result.get("message") or "")[:2000],
                        json.dumps(result.get("raw") or {}),
                        state,
                        state,
                        int(attempt_id),
                        lock_token,
                    ),
                )
                conn.commit()
            if updated <= 0 or state == "processing":
                continue
            if state == "paid":
                if save_supplier_code(int(delivery_id), str((result.get("params") or {}).get("gift_code") or "")):
                    process_delivery_steps(int(delivery_id))
            else:
                # Финальный отказ может перейти к пулу, но никогда не повторяет исходный Interhub pay.
                process_delivery_steps(int(delivery_id))

    def delivery_out(row: tuple[Any, ...]) -> dict[str, Any]:
        # Отдает оператору только сведения для ручной выдачи, не раскрывая уже закрепленные коды.
        return {
            "id": int(row[0]),
            "order_id": int(row[1]),
            "item_id": int(row[2]),
            "offer_id": str(row[3]),
            "required_qty": int(row[4] or 1),
            "collected_qty": len(texts(row[5])),
            "status": str(row[6] or "manual_required"),
            "last_error": str(row[7] or ""),
            "item_name": str(row[8] or ""),
            "market_status": str(row[9] or ""),
            "created_at": row[10],
            "updated_at": row[11],
        }

    def read_manual_delivery(conn, delivery_id: int) -> dict[str, Any]:
        # Читает один заказ после явной выдачи, чтобы интерфейс получил финальное локальное состояние.
        row = q1(
            conn,
            """
            SELECT delivery.id, delivery.order_id, delivery.item_id, delivery.offer_id, delivery.required_qty,
                   delivery.delivered_codes, delivery.status, delivery.last_error, orders.item_name, orders.status,
                   delivery.created_at, delivery.updated_at
            FROM app.marketplace_yandex_digital_deliveries AS delivery
            JOIN app.marketplace_yandex_order_items AS orders
              ON orders.store_code=delivery.store_code AND orders.order_id=delivery.order_id AND orders.item_id=delivery.item_id
            WHERE delivery.id=%s
            """,
            (delivery_id,),
        )
        if not row:
            raise HTTPException(404, "Цифровая выдача Яндекс Маркета не найдена")
        return delivery_out(row)

    def list_manual_deliveries(store_code: str, offer_id: str) -> list[dict[str, Any]]:
        # Показывает только остановленные выдачи: список не запускает Interhub и не отправляет ключи в Маркет.
        with psycopg.connect(DB_DSN) as conn:
            rows = qall(
                conn,
                """
                SELECT delivery.id, delivery.order_id, delivery.item_id, delivery.offer_id, delivery.required_qty,
                       delivery.delivered_codes, delivery.status, delivery.last_error, orders.item_name, orders.status,
                       delivery.created_at, delivery.updated_at
                FROM app.marketplace_yandex_digital_deliveries AS delivery
                JOIN app.marketplace_yandex_order_items AS orders
                  ON orders.store_code=delivery.store_code AND orders.order_id=delivery.order_id AND orders.item_id=delivery.item_id
                WHERE delivery.store_code=%s AND delivery.offer_id=%s AND delivery.status='manual_required'
                ORDER BY delivery.created_at DESC, delivery.id DESC
                """,
                (store_code, offer_id),
            )
            conn.commit()
        return [delivery_out(row) for row in rows]

    def deliver_manually(delivery_id: int, raw_codes: list[str]) -> dict[str, Any]:
        # Закрепляет ручные коды за одной остановленной выдачей и только затем однократно отправляет их в Маркет.
        prepared: list[str] = []
        seen: set[str] = set()
        for raw_code in raw_codes:
            code = str(raw_code or "").strip()
            if not code or len(code) > 1024:
                raise HTTPException(400, "Каждый ручной ключ должен быть непустым и короче 1025 символов")
            if code in seen:
                raise HTTPException(400, "Один и тот же ручной ключ нельзя указать дважды")
            seen.add(code)
            prepared.append(code)
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                "SELECT required_qty, delivered_codes, status FROM app.marketplace_yandex_digital_deliveries WHERE id=%s FOR UPDATE",
                (delivery_id,),
            )
            if not row:
                raise HTTPException(404, "Цифровая выдача Яндекс Маркета не найдена")
            if str(row[2] or "") != "manual_required":
                raise HTTPException(409, "Ручной ключ можно выдать только заказу, ожидающему ручной обработки")
            existing = texts(row[1])
            new_codes = [code for code in prepared if code not in existing]
            all_codes = existing + new_codes
            required_qty = int(row[0] or 1)
            if len(all_codes) != required_qty:
                raise HTTPException(400, f"Для этой позиции нужно ключей: {required_qty - len(existing)}")
            for code in new_codes:
                owner = q1(
                    conn,
                    "INSERT INTO app.marketplace_yandex_digital_code_registry(code_hash, delivery_id) VALUES (%s, %s) ON CONFLICT (code_hash) DO NOTHING RETURNING delivery_id",
                    (code_hash(code), delivery_id),
                )
                if owner:
                    continue
                existing_owner = q1(
                    conn,
                    "SELECT delivery_id FROM app.marketplace_yandex_digital_code_registry WHERE code_hash=%s",
                    (code_hash(code),),
                )
                if not existing_owner or int(existing_owner[0]) != delivery_id:
                    raise HTTPException(409, "Этот ключ уже закреплен за другим заказом")
            exec1(
                conn,
                "UPDATE app.marketplace_yandex_digital_deliveries SET delivered_codes=%s::jsonb, status='supplier_processing', last_error='', updated_at=now() WHERE id=%s",
                (json.dumps(all_codes, ensure_ascii=False), delivery_id),
            )
            conn.commit()
        send_delivery(delivery_id)
        with psycopg.connect(DB_DSN) as conn:
            result = read_manual_delivery(conn, delivery_id)
            conn.commit()
        return result

    def issue_from_pool_manually(delivery_id: int) -> dict[str, Any]:
        # Берет ключи только для остановленной выдачи, не вмешиваясь в активную покупку у Interhub.
        if not take_from_pool(delivery_id, {"manual_required"}):
            raise HTTPException(409, "В ручном пуле нет полного комплекта ключей для этого заказа")
        with psycopg.connect(DB_DSN) as conn:
            result = read_manual_delivery(conn, delivery_id)
            conn.commit()
        return result

    def process_saved_order(store_code: str, order_id: int, item_id: int, *, allow_manual: bool = False) -> None:
        # Создает или продолжает одну выдачу из сохраненного заказа, оставляя ее ручной по явной команде без источника.
        with psycopg.connect(DB_DSN) as conn:
            order = q1(
                conn,
                """
                SELECT orders.offer_id, orders.quantity, orders.status, orders.is_sandbox,
                       settings.auto_issue_enabled, settings.pool_issue_enabled
                FROM app.marketplace_yandex_order_items AS orders
                LEFT JOIN app.marketplace_yandex_stock_settings AS settings
                  ON settings.store_code=orders.store_code AND settings.offer_id=orders.offer_id
                WHERE orders.store_code=%s AND orders.order_id=%s AND orders.item_id=%s FOR UPDATE OF orders
                """,
                (store_code, order_id, item_id),
            )
            if not order or bool(order[3]):
                conn.commit()
                return
            market_status = str(order[2] or "").upper()
            if market_status == "DELIVERED":
                # Закрывает локальную историю по подтвержденному уведомлению Маркета и не выполняет никаких внешних действий.
                exec1(
                    conn,
                    "UPDATE app.marketplace_yandex_digital_deliveries SET status='market_delivered', delivered_at=now(), updated_at=now() WHERE store_code=%s AND order_id=%s AND item_id=%s AND status IN ('market_submitted', 'market_unknown')",
                    (store_code, order_id, item_id),
                )
                conn.commit()
                return
            if market_status == "CANCELLED":
                # Не возобновляет отмененную позицию: закрепленные ключи остаются в истории для ручной сверки.
                exec1(
                    conn,
                    "UPDATE app.marketplace_yandex_digital_deliveries SET status='cancelled', updated_at=now() WHERE store_code=%s AND order_id=%s AND item_id=%s AND status NOT IN ('market_delivered')",
                    (store_code, order_id, item_id),
                )
                conn.commit()
                return
            if market_status != "PROCESSING" or (not allow_manual and not (bool(order[4]) or bool(order[5]))):
                conn.commit()
                return
            delivery = q1(
                conn,
                """
                INSERT INTO app.marketplace_yandex_digital_deliveries(store_code, order_id, item_id, offer_id, required_qty)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (store_code, order_id, item_id) DO UPDATE
                SET updated_at=app.marketplace_yandex_digital_deliveries.updated_at
                RETURNING id
                """,
                (store_code, order_id, item_id, str(order[0]), max(1, int(order[1] or 1))),
            )
            conn.commit()
        if delivery:
            process_delivery_steps(int(delivery[0]))

    def process(store_code: str, order_id: int, item_id: int, event_time: datetime | None = None) -> None:
        # Запускается только после двух глобальных предохранителей, чтобы выключенная автоматика не читала и не меняла очередь.
        not_before = yandex_market_production_auto_delivery_not_before(store_code)
        if not yandex_market_production_auto_delivery_enabled(store_code) or not_before is None or (event_time and event_time < not_before):
            return
        process_saved_order(store_code, order_id, item_id)

    def start_existing_order_manually(store_code: str, order_id: int, item_id: int) -> None:
        # Запускает старый сохраненный заказ только по явной команде владельца, не меняя порог webhook-автоматики.
        if not yandex_market_production_auto_delivery_enabled(store_code):
            raise HTTPException(409, "Автовыдача Яндекс Маркета выключена для этого кабинета")
        process_saved_order(store_code, order_id, item_id, allow_manual=True)

    # Публикует узкие ручные операции отдельно от webhook-процессора, чтобы UI не мог запустить автопокупку.
    process.refresh_supplier_attempts = refresh_supplier_attempts  # type: ignore[attr-defined]
    process.list_manual_deliveries = list_manual_deliveries  # type: ignore[attr-defined]
    process.deliver_manually = deliver_manually  # type: ignore[attr-defined]
    process.issue_from_pool_manually = issue_from_pool_manually  # type: ignore[attr-defined]
    process.start_existing_order_manually = start_existing_order_manually  # type: ignore[attr-defined]
    return process


def mount_yandex_market_production_delivery_routes(app, *, delivery_processor, require_role) -> None:
    @app.get("/marketplaces/yandex/catalog/{offer_id}/manual-deliveries")
    def list_yandex_market_manual_deliveries(offer_id: str, store_code: str = "asat", user=Depends(require_role("owner"))):
        # Возвращает локальную очередь ручной выдачи без обращения к Interhub или Яндекс Маркету.
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        items = delivery_processor.list_manual_deliveries(normalized_store_code, str(offer_id))
        return {"offer_id": str(offer_id), "items": items}

    @app.post("/marketplaces/yandex/digital-deliveries/{delivery_id}/deliver")
    def deliver_yandex_market_order_manually(delivery_id: int, payload: YandexMarketManualDeliveryIn, user=Depends(require_role("owner"))):
        # Передает операторские коды только для выбранной остановленной выдачи.
        return delivery_processor.deliver_manually(int(delivery_id), payload.codes)

    @app.post("/marketplaces/yandex/digital-deliveries/{delivery_id}/issue-from-pool")
    def issue_yandex_market_order_from_pool(delivery_id: int, user=Depends(require_role("owner"))):
        # Берет полный комплект из ручного пула только по явной команде оператора.
        return delivery_processor.issue_from_pool_manually(int(delivery_id))

    @app.post("/marketplaces/yandex/orders/{order_id}/items/{item_id}/start-delivery")
    def start_yandex_market_existing_order(order_id: int, item_id: int, store_code: str = "asat", user=Depends(require_role("owner"))):
        # Позволяет владельцу один раз явно запустить выдачу по уже сохраненному заказу до порога автоматики.
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        delivery_processor.start_existing_order_manually(normalized_store_code, int(order_id), int(item_id))
        return {"order_id": int(order_id), "item_id": int(item_id), "started": True}
