from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from threading import Timer
import uuid
from typing import Any, Callable

from fastapi import Depends, HTTPException, Query
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
    codes: list[str] = Field(default_factory=list, max_length=100)


class YandexMarketDigitalOrderCodesOut(BaseModel):
    order_id: int
    item_id: int
    codes: list[str] = Field(default_factory=list)


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
    outbound_delivery_recovery_grace_sec: int = 600,
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

    def save_auto_interhub_check(delivery_id: int, request: dict[str, Any], amount: float, result: dict[str, Any]) -> None:
        # Дублирует успешную проверку в общий журнал Interhub, чтобы история поставщика включала Яндекс и Ozon.
        state = "checked" if bool(result.get("success")) else "failed"
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                INSERT INTO app.interhub_transactions(
                  agent_transaction_id, service_id, account, amount, request_params, state,
                  provider_status, provider_message, provider_transaction_id, provider_response,
                  created_by, yandex_market_delivery_id, updated_at
                )
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s::jsonb, 'yandex-auto', %s, now())
                ON CONFLICT (agent_transaction_id) DO UPDATE
                SET state=excluded.state,
                    amount=excluded.amount,
                    request_params=excluded.request_params,
                    provider_status=excluded.provider_status,
                    provider_message=excluded.provider_message,
                    provider_transaction_id=excluded.provider_transaction_id,
                    provider_response=excluded.provider_response,
                    yandex_market_delivery_id=excluded.yandex_market_delivery_id,
                    updated_at=now()
                """,
                (
                    str(request["agent_transaction_id"]), int(request["service_id"]), str(request.get("account") or ""), amount,
                    json.dumps(request.get("params") or {}), state, int(result.get("status") or 0), str(result.get("message") or "")[:2000],
                    str(result.get("transaction_id") or ""), json.dumps(result.get("raw") or {}), int(delivery_id),
                ),
            )
            conn.commit()

    def save_auto_interhub_result(agent_transaction_id: str, result: dict[str, Any]) -> None:
        # Обновляет общий журнал финальным ответом поставщика и сохраняет код там же, где его ожидает история Interhub.
        state = provider_state(result)
        params = result.get("params") if isinstance(result.get("params"), dict) else {}
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                UPDATE app.interhub_transactions
                SET state=%s, provider_status=%s, provider_message=%s,
                    provider_transaction_id=COALESCE(NULLIF(%s, ''), provider_transaction_id),
                    gift_code=COALESCE(NULLIF(%s, ''), gift_code), provider_response=%s::jsonb,
                    updated_at=now()
                WHERE agent_transaction_id=%s
                """,
                (
                    state, int(result.get("status") or 0), str(result.get("message") or "")[:2000],
                    str(result.get("transaction_id") or ""), str(params.get("gift_code") or ""),
                    json.dumps(result.get("raw") or {}), str(agent_transaction_id),
                ),
            )
            conn.commit()

    def mark_manual(delivery_id: int, message: str = "") -> None:
        # Открывает ручную выдачу только после завершения всех неопределенных попыток поставщика.
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                UPDATE app.marketplace_yandex_digital_deliveries AS delivery
                SET status='manual_required',
                    last_error=COALESCE(
                      NULLIF(%s, ''),
                      (
                        SELECT NULLIF(attempt.provider_message, '')
                        FROM app.marketplace_yandex_digital_supplier_attempts AS attempt
                        WHERE attempt.delivery_id=delivery.id
                          AND attempt.state IN ('failed', 'manual_required')
                        ORDER BY attempt.updated_at DESC, attempt.id DESC
                        LIMIT 1
                      ),
                      NULLIF(delivery.last_error, ''),
                      'Поставщик не выдал код'
                    ),
                    updated_at=now()
                WHERE delivery.id=%s
                  AND delivery.status='supplier_processing'
                  AND NOT EXISTS (
                    SELECT 1 FROM app.marketplace_yandex_digital_supplier_attempts AS attempt
                    WHERE attempt.delivery_id=delivery.id AND attempt.state='processing'
                  )
                  AND NOT EXISTS (
                    SELECT 1 FROM app.marketplace_yandex_digital_supplier_attempts AS attempt
                    WHERE attempt.delivery_id=delivery.id
                      AND attempt.state='paid' AND attempt.code_applied_at IS NULL
                  )
                """,
                (str(message)[:2000], delivery_id),
            )
            conn.commit()

    def finalize_paid_supplier_attempt(attempt_id: int) -> tuple[bool, int]:
        # Одним коммитом переносит оплаченный ключ InterHub в выдачу и отмечает попытку полностью примененной.
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                """
                SELECT attempt.delivery_id,
                       COALESCE(NULLIF(attempt.gift_code, ''), NULLIF(transaction.gift_code, '')),
                       attempt.state, attempt.code_applied_at,
                       delivery.required_qty, delivery.delivered_codes, delivery.status
                FROM app.marketplace_yandex_digital_supplier_attempts AS attempt
                JOIN app.marketplace_yandex_digital_deliveries AS delivery ON delivery.id=attempt.delivery_id
                LEFT JOIN app.interhub_transactions AS transaction
                  ON transaction.agent_transaction_id=attempt.agent_transaction_id
                WHERE attempt.id=%s
                FOR UPDATE OF attempt, delivery
                """,
                (attempt_id,),
            )
            if not row:
                return False, 0
            delivery_id = int(row[0])
            normalized = str(row[1] or "").strip()
            attempt_state = str(row[2] or "")
            if row[3] is not None:
                conn.commit()
                return True, delivery_id
            required_qty = int(row[4] or 1)
            codes = texts(row[5])
            delivery_status = str(row[6] or "")
            if attempt_state != "paid":
                conn.commit()
                return False, delivery_id
            if not normalized:
                message = "InterHub подтвердил оплату, но ключ пока не найден в сохраненном результате. Повторная покупка заблокирована."
                exec1(conn, "UPDATE app.marketplace_yandex_digital_supplier_attempts SET finalization_error=%s, next_status_check_at=COALESCE(next_status_check_at, now() + interval '5 minutes'), updated_at=now() WHERE id=%s", (message, attempt_id))
                exec1(
                    conn,
                    "UPDATE app.marketplace_yandex_digital_deliveries SET status=CASE WHEN status IN ('cancelled', 'market_sending', 'market_submitted', 'market_unknown', 'market_delivered') THEN status ELSE 'supplier_processing' END, last_error=%s, updated_at=now() WHERE id=%s",
                    (message, delivery_id),
                )
                conn.commit()
                return False, delivery_id
            if normalized in codes:
                exec1(
                    conn,
                    "UPDATE app.marketplace_yandex_digital_supplier_attempts SET gift_code=%s, code_applied_at=now(), finalization_error='', updated_at=now() WHERE id=%s",
                    (normalized, attempt_id),
                )
                conn.commit()
                return True, delivery_id
            if delivery_status in {"market_sending", "market_submitted", "market_unknown", "market_delivered"}:
                message = f"Оплаченный ключ InterHub не совпал с уже отправленным комплектом выдачи со статусом {delivery_status}"
                exec1(conn, "UPDATE app.marketplace_yandex_digital_supplier_attempts SET gift_code=%s, finalization_error=%s, updated_at=now() WHERE id=%s", (normalized, message[:2000], attempt_id))
                exec1(conn, "UPDATE app.marketplace_yandex_digital_deliveries SET last_error=%s, updated_at=now() WHERE id=%s", (message[:2000], delivery_id))
                conn.commit()
                return False, delivery_id
            if len(codes) >= required_qty:
                message = "Оплаченный ключ InterHub не помещается в уже собранный комплект выдачи"
                exec1(conn, "UPDATE app.marketplace_yandex_digital_supplier_attempts SET gift_code=%s, finalization_error=%s, updated_at=now() WHERE id=%s", (normalized, message, attempt_id))
                exec1(conn, "UPDATE app.marketplace_yandex_digital_deliveries SET last_error=%s, updated_at=now() WHERE id=%s", (message, delivery_id))
                conn.commit()
                return False, delivery_id
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
                existing_owner = q1(
                    conn,
                    "SELECT delivery_id FROM app.marketplace_yandex_digital_code_registry WHERE code_hash=%s",
                    (code_hash(normalized),),
                )
                if not existing_owner or int(existing_owner[0]) != delivery_id:
                    message = "InterHub вернул ключ, уже закрепленный за другим заказом"
                    exec1(conn, "UPDATE app.marketplace_yandex_digital_supplier_attempts SET gift_code=%s, finalization_error=%s, updated_at=now() WHERE id=%s", (normalized, message, attempt_id))
                    exec1(conn, "UPDATE app.marketplace_yandex_digital_deliveries SET status=CASE WHEN status='cancelled' THEN status ELSE 'manual_required' END, last_error=%s, updated_at=now() WHERE id=%s", (message, delivery_id))
                    conn.commit()
                    return False, delivery_id
            codes.append(normalized)
            exec1(
                conn,
                """
                UPDATE app.marketplace_yandex_digital_deliveries
                SET delivered_codes=%s::jsonb, delivery_source='interhub',
                    status=CASE WHEN status='cancelled' THEN status ELSE 'supplier_processing' END,
                    last_error='', updated_at=now()
                WHERE id=%s
                """,
                (json.dumps(codes, ensure_ascii=False), delivery_id),
            )
            exec1(
                conn,
                "UPDATE app.marketplace_yandex_digital_supplier_attempts SET gift_code=%s, code_applied_at=now(), finalization_error='', updated_at=now() WHERE id=%s",
                (normalized, attempt_id),
            )
            exec1(
                conn,
                "UPDATE app.interhub_transactions SET gift_code=COALESCE(NULLIF(gift_code, ''), %s), updated_at=now() WHERE agent_transaction_id=(SELECT agent_transaction_id FROM app.marketplace_yandex_digital_supplier_attempts WHERE id=%s)",
                (normalized, attempt_id),
            )
            conn.commit()
        return True, delivery_id

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
                "UPDATE app.marketplace_yandex_digital_deliveries SET status='market_sending', market_send_started_at=now(), last_error='', updated_at=now() WHERE id=%s",
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
                    "UPDATE app.marketplace_yandex_digital_deliveries SET status=%s, last_error=%s, updated_at=now() WHERE id=%s AND status='market_sending'",
                    ("manual_required" if definite else "market_unknown", str(error.detail)[:2000], delivery_id),
                )
                conn.commit()
            return
        with psycopg.connect(DB_DSN) as conn:
            submitted_at = datetime.now(timezone.utc)
            exec1(
                conn,
                "UPDATE app.marketplace_yandex_digital_deliveries SET status='market_submitted', market_submitted_at=%s, updated_at=now() WHERE id=%s AND status='market_sending'",
                (submitted_at, delivery_id),
            )
            # Подтвержденная отправка завершает тот же резерв пула, не освобождая и не меняя закрепленный ключ.
            exec1(
                conn,
                """
                UPDATE app.marketplace_manual_keys AS key
                SET status='delivered', issued_at=%s, updated_at=now()
                FROM app.marketplace_manual_key_pools AS pool
                WHERE key.pool_id=pool.id
                  AND pool.marketplace='yandex_market'
                  AND pool.store_code=%s
                  AND pool.product_key=%s
                  AND key.issued_order_ref=%s
                  AND key.status IN ('reserved', 'sending')
                """,
                (submitted_at, str(row[0]), str(row[4]), f"yandex:{row[0]}:{row[1]}:{row[2]}"),
            )
            conn.commit()
        schedule_yandex_target_stock_republish(str(row[0]), str(row[4]))

    def recover_stale_market_sendings(enabled_store_codes: set[str]) -> None:
        # Помечает прерванную отправку как неоднозначную, чтобы повторный цикл не отправил тот же ключ в Маркет автоматически.
        if not enabled_store_codes:
            return
        grace_seconds = max(60, int(outbound_delivery_recovery_grace_sec or 600))
        recovery_error = (
            "Процесс остановился во время отправки закрепленного ключа. "
            "Автоматический повтор запрещен; дождитесь статуса DELIVERED или проверьте заказ в Яндекс Маркете."
        )
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                UPDATE app.marketplace_yandex_digital_deliveries
                SET status='market_unknown', last_error=%s, updated_at=now()
                WHERE status='market_sending'
                  AND store_code = ANY(%s)
                  AND market_send_started_at IS NOT NULL
                  AND market_send_started_at <= now() - (%s * interval '1 second')
                """,
                (recovery_error, sorted(enabled_store_codes), grace_seconds),
            )
            conn.commit()

    def take_from_pool(delivery_id: int, allowed_statuses: set[str] | None = None) -> bool:
        # Резервирует полный комплект из пула транзакционно: частичный заказ автоматически не отправляется.
        secret = pool_secret()
        with psycopg.connect(DB_DSN) as conn:
            delivery = q1(
                conn,
                """
                SELECT store_code, order_id, item_id, offer_id, required_qty, delivered_codes, status, delivery_source
                FROM app.marketplace_yandex_digital_deliveries WHERE id=%s FOR UPDATE
                """,
                (delivery_id,),
            )
            allowed = allowed_statuses or {"manual_required", "supplier_processing"}
            if not delivery or str(delivery[6] or "") not in allowed:
                conn.commit()
                return False
            # После неуспешной заглушки оператор может взять настоящий комплект из пула вручную.
            current = [] if str(delivery[7] or "") == "support_message" else texts(delivery[5])
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
                "UPDATE app.marketplace_yandex_digital_deliveries SET delivered_codes=%s::jsonb, delivery_source='pool', status='supplier_processing', last_error='', updated_at=now() WHERE id=%s",
                (json.dumps(current + codes, ensure_ascii=False), delivery_id),
            )
            conn.commit()
        send_delivery(delivery_id)
        return True

    def send_support_message(delivery_id: int) -> bool:
        # Намеренно завершает выдачу текстом поддержки только после недоступных Interhub и пула.
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                """
                SELECT delivery.store_code, delivery.required_qty, delivery.delivered_codes, delivery.status,
                       delivery.delivery_source, settings.support_error_message,
                       settings.support_message_delivery_enabled
                FROM app.marketplace_yandex_digital_deliveries AS delivery
                JOIN app.marketplace_yandex_stock_settings AS settings
                  ON settings.store_code=delivery.store_code AND settings.offer_id=delivery.offer_id
                WHERE delivery.id=%s FOR UPDATE
                """,
                (delivery_id,),
            )
            if not row or str(row[3] or "") not in {"manual_required", "supplier_processing"}:
                conn.commit()
                return False
            message = str(row[5] or "").strip()
            if not bool(row[6]) or not message or texts(row[2]):
                conn.commit()
                return False
            # Это не лицензионный ключ: одинаковый текст можно отправлять разным покупателям без реестра кодов.
            codes = [message] * max(1, int(row[1] or 1))
            exec1(
                conn,
                "UPDATE app.marketplace_yandex_digital_deliveries SET delivered_codes=%s::jsonb, delivery_source='support_message', status='supplier_processing', last_error='', updated_at=now() WHERE id=%s",
                (json.dumps(codes, ensure_ascii=False), delivery_id),
            )
            conn.commit()
        send_delivery(delivery_id)
        return True

    def buy_from_interhub(delivery_id: int) -> str:
        # Возвращает итог попытки, чтобы ожидание оплаты не перешло к следующему источнику выдачи.
        if not interhub_calculate or not interhub_check or not interhub_pay:
            return "failed"
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
                return "failed"
            if len(texts(row[3])) >= int(row[2] or 1):
                conn.commit()
                send_delivery(delivery_id)
                return "completed"
            active = q1(
                conn,
                "SELECT id FROM app.marketplace_yandex_digital_supplier_attempts WHERE delivery_id=%s AND state='processing' LIMIT 1",
                (delivery_id,),
            )
            if active:
                conn.commit()
                return "pending"
            paid_unapplied = q1(
                conn,
                """
                SELECT id FROM app.marketplace_yandex_digital_supplier_attempts
                WHERE delivery_id=%s AND state='paid' AND code_applied_at IS NULL
                ORDER BY updated_at, id
                LIMIT 1
                """,
                (delivery_id,),
            )
            if paid_unapplied:
                # Уже оплаченный ключ сначала восстановит фоновый финализатор; новый pay здесь запрещен.
                conn.commit()
                return "pending"
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
                return "failed"
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
            save_auto_interhub_check(delivery_id, request, amount, checked)
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
            return "pending" if pay_started else "failed"
        state = provider_state(paid)
        paid_gift_code = str((paid.get("params") or {}).get("gift_code") or "").strip()
        needs_status_retry = state == "processing" or (state == "paid" and not paid_gift_code)
        with psycopg.connect(DB_DSN) as conn:
            exec1(
                conn,
                """
                UPDATE app.marketplace_yandex_digital_supplier_attempts
                SET state=%s, provider_status=%s, provider_message=%s, provider_response=%s::jsonb,
                    next_status_check_at=CASE WHEN %s THEN now() + interval '1 minute' ELSE NULL END,
                    gift_code=CASE WHEN %s='paid' AND %s<>'' THEN %s ELSE gift_code END,
                    finalization_error=CASE WHEN %s='paid' THEN '' ELSE finalization_error END,
                    updated_at=now()
                WHERE agent_transaction_id=%s
                """,
                (
                    state,
                    int(paid.get("status") or 0),
                    str(paid.get("message") or "")[:2000],
                    json.dumps(paid.get("raw") or {}),
                    needs_status_retry,
                    state,
                    paid_gift_code,
                    paid_gift_code,
                    state,
                    transaction_id,
                ),
            )
            conn.commit()
        try:
            # Журнал сверки не должен отменить уже полученный ключ, если служебная запись временно недоступна.
            save_auto_interhub_result(transaction_id, paid)
        except Exception:
            pass
        if state == "paid":
            with psycopg.connect(DB_DSN) as conn:
                attempt = q1(
                    conn,
                    "SELECT id FROM app.marketplace_yandex_digital_supplier_attempts WHERE agent_transaction_id=%s",
                    (transaction_id,),
                )
                conn.commit()
            applied, _applied_delivery_id = finalize_paid_supplier_attempt(int(attempt[0])) if attempt else (False, delivery_id)
            return "completed" if applied else "pending"
        return "pending" if state == "processing" else "failed"

    def process_delivery_steps(delivery_id: int) -> None:
        # Собирает недостающие коды без рекурсии и останавливается на ожидании неопределенной оплаты.
        while True:
            with psycopg.connect(DB_DSN) as conn:
                row = q1(
                    conn,
                    "SELECT required_qty, delivered_codes, status, store_code, offer_id, delivery_source FROM app.marketplace_yandex_digital_deliveries WHERE id=%s",
                    (delivery_id,),
                )
                conn.commit()
            if not row or str(row[2] or "") not in {"manual_required", "supplier_processing"}:
                return
            if len(texts(row[1])) >= int(row[0] or 1):
                # Не пытается автоматически повторить заглушку после отказа Маркета: дальше только ручной оператор.
                if len(row) > 5 and str(row[5] or "") == "support_message":
                    return
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
                    "SELECT auto_issue_enabled, pool_issue_enabled, support_message_delivery_enabled FROM app.marketplace_yandex_stock_settings WHERE store_code=%s AND offer_id=%s",
                    (str(row[3]), str(row[4])),
                )
                conn.commit()
            if settings and bool(settings[0]) and supplier:
                interhub_result = buy_from_interhub(delivery_id)
                if interhub_result == "pending":
                    return
                if interhub_result == "completed":
                    # Продолжает цикл: следующая итерация либо докупит недостающий ключ, либо отправит комплект в Маркет.
                    continue
            if settings and bool(settings[1]) and take_from_pool(delivery_id):
                return
            if settings and len(settings) > 2 and bool(settings[2]):
                send_support_message(delivery_id)
                return
            # Финальный отказ без рабочего резерва не должен оставлять карточку в бесконечном ожидании поставщика.
            mark_manual(delivery_id)
            return

    def recover_paid_supplier_attempts(enabled_store_codes: set[str]) -> None:
        # После рестарта применяет уже оплаченные ключи и продолжает выдачи, остановленные между коммитами.
        with psycopg.connect(DB_DSN) as conn:
            paid_attempts = qall(
                conn,
                """
                SELECT attempt.id
                FROM app.marketplace_yandex_digital_supplier_attempts AS attempt
                JOIN app.marketplace_yandex_digital_deliveries AS delivery ON delivery.id=attempt.delivery_id
                WHERE attempt.state='paid' AND attempt.code_applied_at IS NULL
                  AND delivery.store_code = ANY(%s)
                ORDER BY attempt.updated_at, attempt.id
                LIMIT 100
                """,
                (sorted(enabled_store_codes),),
            )
            conn.commit()
        delivery_ids: set[int] = set()
        for paid_attempt in paid_attempts:
            applied, delivery_id = finalize_paid_supplier_attempt(int(paid_attempt[0]))
            if applied and delivery_id:
                delivery_ids.add(delivery_id)
        with psycopg.connect(DB_DSN) as conn:
            stranded_deliveries = qall(
                conn,
                """
                SELECT delivery.id
                FROM app.marketplace_yandex_digital_deliveries AS delivery
                WHERE delivery.status='supplier_processing'
                  AND delivery.store_code = ANY(%s)
                  AND NOT EXISTS (
                    SELECT 1 FROM app.marketplace_yandex_digital_supplier_attempts AS attempt
                    WHERE attempt.delivery_id=delivery.id AND attempt.state='processing'
                  )
                  AND NOT EXISTS (
                    SELECT 1 FROM app.marketplace_yandex_digital_supplier_attempts AS attempt
                    WHERE attempt.delivery_id=delivery.id AND attempt.state='paid' AND attempt.code_applied_at IS NULL
                  )
                ORDER BY delivery.updated_at, delivery.id
                LIMIT 100
                """,
                (sorted(enabled_store_codes),),
            )
            conn.commit()
        delivery_ids.update(int(row[0]) for row in stranded_deliveries)
        for delivery_id in sorted(delivery_ids):
            try:
                process_delivery_steps(delivery_id)
            except Exception:
                # Следующий цикл повторит локальное продолжение, не создавая pay поверх незавершенной попытки.
                continue

    def refresh_supplier_attempts() -> None:
        # Дозапрашивает только оплаты включенных кабинетов и никогда не создает новый заказ, ключ или повторный pay.
        enabled_store_codes = yandex_market_production_auto_delivery_enabled_store_codes()
        if not enabled_store_codes:
            return
        recover_stale_market_sendings(enabled_store_codes)
        recover_paid_supplier_attempts(enabled_store_codes)
        if not interhub_check_status:
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
                  WHERE (
                      attempt.state='processing'
                      OR (attempt.state='paid' AND attempt.code_applied_at IS NULL AND attempt.gift_code='')
                    )
                    AND attempt.next_status_check_at <= now()
                    AND delivery.store_code = ANY(%s)
                    AND (attempt.status_check_locked_until IS NULL OR attempt.status_check_locked_until <= now())
                  ORDER BY attempt.next_status_check_at, attempt.id
                  FOR UPDATE SKIP LOCKED LIMIT 50
                )
                UPDATE app.marketplace_yandex_digital_supplier_attempts AS attempt
                SET status_check_lock_token=%s::uuid, status_check_locked_until=now() + interval '5 minutes', updated_at=now()
                FROM due WHERE attempt.id=due.id
                RETURNING attempt.id, attempt.delivery_id, attempt.agent_transaction_id, attempt.state
                """,
                (sorted(enabled_store_codes), lock_token),
            )
            conn.commit()
        for attempt_id, delivery_id, transaction_id, saved_attempt_state in attempts:
            try:
                result = interhub_check_status({"agent_transaction_id": str(transaction_id)})
                result_state = provider_state(result)
            except Exception as error:
                result = {"success": False, "status": 0, "message": str(getattr(error, "detail", error)), "raw": {}}
                result_state = "processing"
            # После paid продолжаем искать ключ, но не считаем оплату отмененной из-за временной сверки.
            state = "paid" if str(saved_attempt_state or "") == "paid" else result_state
            result_gift_code = str((result.get("params") or {}).get("gift_code") or "").strip()
            confirmed_gift_code = result_state == "paid" and bool(result_gift_code)
            needs_status_retry = state == "processing" or (state == "paid" and not confirmed_gift_code)
            with psycopg.connect(DB_DSN) as conn:
                updated = exec1(
                    conn,
                    """
                    UPDATE app.marketplace_yandex_digital_supplier_attempts
                    SET state=%s, provider_status=%s, provider_message=%s, provider_response=%s::jsonb,
                        next_status_check_at=CASE WHEN %s THEN now() + interval '5 minutes' ELSE NULL END,
                        status_check_attempts=CASE WHEN %s THEN status_check_attempts + 1 ELSE status_check_attempts END,
                        gift_code=CASE WHEN %s='paid' AND %s<>'' THEN %s ELSE gift_code END,
                        finalization_error=CASE WHEN %s='paid' THEN '' ELSE finalization_error END,
                        status_check_lock_token=NULL, status_check_locked_until=NULL, updated_at=now()
                    WHERE id=%s AND status_check_lock_token=%s::uuid
                    """,
                    (
                        state,
                        int(result.get("status") or 0),
                        str(result.get("message") or "")[:2000],
                        json.dumps(result.get("raw") or {}),
                        needs_status_retry,
                        needs_status_retry,
                        result_state,
                        result_gift_code,
                        result_gift_code,
                        result_state,
                        int(attempt_id),
                        lock_token,
                    ),
                )
                conn.commit()
            if updated <= 0 or state == "processing":
                if updated > 0 and state == "processing":
                    try:
                        # Фиксирует ожидающий ответ в общей истории без создания новой оплаты.
                        save_auto_interhub_result(str(transaction_id), result)
                    except Exception:
                        pass
                continue
            if str(saved_attempt_state or "") != "paid" or result_state == "paid":
                try:
                    # Переносит финальный результат фоновой сверки в тот же общий журнал, что и Ozon.
                    save_auto_interhub_result(str(transaction_id), result)
                except Exception:
                    pass
            if state == "paid":
                applied, finalized_delivery_id = finalize_paid_supplier_attempt(int(attempt_id))
                if applied:
                    process_delivery_steps(finalized_delivery_id)
            else:
                # Финальный отказ может перейти к пулу, но никогда не повторяет исходный Interhub pay.
                process_delivery_steps(int(delivery_id))

    def delivery_out(row: tuple[Any, ...]) -> dict[str, Any]:
        # Отдает оператору только сведения для ручной выдачи, не раскрывая уже закрепленные коды.
        delivery_source = str(row[12] or "") if len(row) > 12 else ""
        collected_qty = 0 if delivery_source == "support_message" and str(row[6] or "") == "manual_required" else len(texts(row[5]))
        return {
            "id": int(row[0]),
            "order_id": int(row[1]),
            "item_id": int(row[2]),
            "offer_id": str(row[3]),
            "required_qty": int(row[4] or 1),
            "collected_qty": collected_qty,
            "delivery_source": delivery_source,
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
                   delivery.created_at, delivery.updated_at, delivery.delivery_source
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
                       delivery.created_at, delivery.updated_at, delivery.delivery_source
                FROM app.marketplace_yandex_digital_deliveries AS delivery
                JOIN app.marketplace_yandex_order_items AS orders
                  ON orders.store_code=delivery.store_code AND orders.order_id=delivery.order_id AND orders.item_id=delivery.item_id
                WHERE delivery.store_code=%s
                  AND delivery.offer_id=%s
                  AND delivery.status IN ('manual_required', 'market_unknown')
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
                "SELECT required_qty, delivered_codes, status, delivery_source FROM app.marketplace_yandex_digital_deliveries WHERE id=%s FOR UPDATE",
                (delivery_id,),
            )
            if not row:
                raise HTTPException(404, "Цифровая выдача Яндекс Маркета не найдена")
            delivery_status = str(row[2] or "")
            if delivery_status not in {"manual_required", "market_unknown"}:
                raise HTTPException(409, "Ручной ключ можно выдать только заказу, ожидающему ручной обработки")
            # Заменяет неотправленную заглушку настоящим ключом по явному действию оператора.
            existing = [] if str(row[3] or "") == "support_message" and delivery_status == "manual_required" else texts(row[1])
            required_qty = int(row[0] or 1)
            if delivery_status == "market_unknown":
                # Не дает заменить секрет после неоднозначного ответа: оператор может повторить только уже закрепленный комплект.
                if prepared:
                    raise HTTPException(400, "Для этой выдачи повторите уже закрепленные ключи без ввода новых")
                if len(existing) != required_qty:
                    raise HTTPException(409, "Для безопасного повтора не найден полный закрепленный комплект ключей")
            new_codes = [code for code in prepared if code not in existing]
            all_codes = existing + new_codes
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
                "UPDATE app.marketplace_yandex_digital_deliveries SET delivered_codes=%s::jsonb, delivery_source='manual', status='supplier_processing', last_error='', updated_at=now() WHERE id=%s",
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
                       settings.auto_issue_enabled, settings.pool_issue_enabled, settings.support_message_delivery_enabled
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
                    "UPDATE app.marketplace_yandex_digital_deliveries SET status='market_delivered', delivered_at=now(), last_error='', updated_at=now() WHERE store_code=%s AND order_id=%s AND item_id=%s AND status IN ('market_sending', 'market_submitted', 'market_unknown')",
                    (store_code, order_id, item_id),
                )
                exec1(
                    conn,
                    """
                    UPDATE app.marketplace_manual_keys AS key
                    SET status='delivered', issued_at=COALESCE(key.issued_at, now()), updated_at=now()
                    FROM app.marketplace_manual_key_pools AS pool
                    WHERE key.pool_id=pool.id
                      AND pool.marketplace='yandex_market'
                      AND pool.store_code=%s
                      AND pool.product_key=%s
                      AND key.issued_order_ref=%s
                      AND key.status IN ('reserved', 'sending')
                    """,
                    (store_code, str(order[0]), f"yandex:{store_code}:{order_id}:{item_id}"),
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
            if market_status != "PROCESSING" or (not allow_manual and not (bool(order[4]) or bool(order[5]) or (len(order) > 6 and bool(order[6])))):
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

    def reveal_delivered_codes(store_code: str, order_id: int, item_id: int) -> dict[str, Any]:
        # Отдает уже отправленный ключ только владельцу по точной позиции заказа, не раскрывая его в общей истории.
        with psycopg.connect(DB_DSN) as conn:
            row = q1(
                conn,
                """
                SELECT delivered_codes
                FROM app.marketplace_yandex_digital_deliveries
                WHERE store_code=%s AND order_id=%s AND item_id=%s
                """,
                (store_code, int(order_id), int(item_id)),
            )
            conn.commit()
        if not row:
            raise HTTPException(404, "Выдача по этой позиции заказа не найдена")
        codes = texts(row[0])
        if not codes:
            raise HTTPException(409, "Ключ для этой позиции еще не был отправлен")
        return {"order_id": int(order_id), "item_id": int(item_id), "codes": codes}

    # Публикует узкие ручные операции отдельно от webhook-процессора, чтобы UI не мог запустить автопокупку.
    process.refresh_supplier_attempts = refresh_supplier_attempts  # type: ignore[attr-defined]
    process.list_manual_deliveries = list_manual_deliveries  # type: ignore[attr-defined]
    process.deliver_manually = deliver_manually  # type: ignore[attr-defined]
    process.issue_from_pool_manually = issue_from_pool_manually  # type: ignore[attr-defined]
    process.start_existing_order_manually = start_existing_order_manually  # type: ignore[attr-defined]
    process.reveal_delivered_codes = reveal_delivered_codes  # type: ignore[attr-defined]
    process.finalize_paid_supplier_attempt = finalize_paid_supplier_attempt  # type: ignore[attr-defined]
    process.recover_paid_supplier_attempts = recover_paid_supplier_attempts  # type: ignore[attr-defined]
    process.recover_stale_market_sendings = recover_stale_market_sendings  # type: ignore[attr-defined]
    process.buy_from_interhub = buy_from_interhub  # type: ignore[attr-defined]
    return process


def mount_yandex_market_production_delivery_routes(app, *, delivery_processor, require_role) -> None:
    @app.get("/marketplaces/yandex/catalog/{offer_id}/manual-deliveries")
    def list_yandex_market_manual_deliveries(
        offer_id: str,
        store_code: str = Query(..., min_length=1, max_length=64),
        user=Depends(require_role("owner")),
    ):
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

    @app.get("/marketplaces/yandex/orders/{order_id}/items/{item_id}/codes", response_model=YandexMarketDigitalOrderCodesOut)
    def get_yandex_market_order_codes(
        order_id: int,
        item_id: int,
        store_code: str = Query(..., min_length=1, max_length=64),
        user=Depends(require_role("owner")),
    ):
        # Раскрывает ключ владельцу лишь после явного клика по уже доставленной позиции Маркета.
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        result = delivery_processor.reveal_delivered_codes(normalized_store_code, int(order_id), int(item_id))
        return YandexMarketDigitalOrderCodesOut(**result)

    @app.post("/marketplaces/yandex/orders/{order_id}/items/{item_id}/start-delivery")
    def start_yandex_market_existing_order(
        order_id: int,
        item_id: int,
        store_code: str = Query(..., min_length=1, max_length=64),
        user=Depends(require_role("owner")),
    ):
        # Позволяет владельцу один раз явно запустить выдачу по уже сохраненному заказу до порога автоматики.
        normalized_store_code = normalize_yandex_market_store_code(store_code)
        delivery_processor.start_existing_order_manually(normalized_store_code, int(order_id), int(item_id))
        return {"order_id": int(order_id), "item_id": int(item_id), "started": True}
