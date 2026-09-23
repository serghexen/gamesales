import json
import threading
import uuid
from datetime import date
from typing import Literal

from fastapi import Body, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from domains.interhub_price_cache import build_interhub_prices_xlsx
from domains.interhub_stock_cache import fetch_nominal_stock
from domains.purchase_history_export import build_purchase_history_xlsx
from domains.crm_purchase_export import iter_crm_purchase_export


PENDING_STATUS = 1
INTERHUB_HISTORY_TIMEZONE = "Europe/Moscow"
DEAL_INTERHUB_SERVICE_IDS = {"TR": 11125, "PL": 9811}


def interhub_status_check_interval(check_attempts: int) -> str:
    # Возвращаем следующий интервал проверки строго по рекомендации InterHub.
    if check_attempts == 0:
        return "1 minute"
    if check_attempts < 4:
        return "5 minutes"
    return "30 minutes"


def mount_interhub_routes(
    app,
    *,
    DB_DSN,
    psycopg,
    get_current_user,
    require_role,
    UserOut,
    InterHubServiceListOut,
    InterHubBalanceOut,
    InterHubPaymentRequestIn,
    InterHubPaymentCheckOut,
    InterHubPayRequestIn,
    InterHubVoucherBatchPayRequestIn,
    interhub_get_services,
    interhub_get_balance,
    interhub_calculate,
    interhub_check,
    interhub_pay,
    interhub_check_status,
    price_calculate_delay_ms=700,
    publish_deal_event=None,
    supplier_hub_client=None,
    interhub_get_service_detail=None,
    shared_catalog=None,
):
    price_jobs: dict[str, dict] = {}
    price_jobs_lock = threading.Lock()

    def response_state(result: dict) -> str:
        # Приводим ответы провайдера к коротким внутренним состояниям операции.
        if int(result.get("status") or 0) == PENDING_STATUS and bool(result.get("success")):
            return "processing"
        if bool(result.get("success")) and int(result.get("status") or 0) == 0:
            return "paid"
        return "failed"

    def write_checked_transaction(conn, payload: dict, result: dict, username: str, *, deal_id: int | None = None) -> None:
        # Пишем успешный check в переданную транзакцию, чтобы deal-lock охватывал подготовку целиком.
        if not bool(result.get("success")):
            return
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app.interhub_transactions(
                  agent_transaction_id, service_id, account, amount, request_params,
                  state, provider_status, provider_message, provider_transaction_id,
                  provider_response, created_by, deal_id, updated_at
                ) VALUES (%s, %s, %s, %s, %s::jsonb, 'checked', %s, %s, %s, %s::jsonb, %s, %s, now())
                ON CONFLICT (agent_transaction_id) DO UPDATE SET
                  service_id=EXCLUDED.service_id,
                  account=EXCLUDED.account,
                  amount=EXCLUDED.amount,
                  request_params=EXCLUDED.request_params,
                  provider_status=EXCLUDED.provider_status,
                  provider_message=EXCLUDED.provider_message,
                  provider_transaction_id=EXCLUDED.provider_transaction_id,
                  provider_response=EXCLUDED.provider_response,
                  deal_id=COALESCE(EXCLUDED.deal_id, app.interhub_transactions.deal_id),
                  updated_at=now()
                WHERE app.interhub_transactions.state='checked'
                """,
                (
                    str(payload["agent_transaction_id"]), int(payload["service_id"]), str(payload.get("account") or ""),
                    float(payload.get("amount") or 0), json.dumps(payload.get("params") or {}), int(result.get("status") or 0),
                    str(result.get("message") or ""), str(result.get("transaction_id") or ""), json.dumps(result.get("raw") or {}), username,
                    deal_id,
                ),
            )

    def save_checked_transaction(payload: dict, result: dict, username: str, *, deal_id: int | None = None) -> None:
        # Фиксируем успешный check до pay, чтобы повторный клик не стал новой оплатой.
        if not bool(result.get("success")):
            return
        with psycopg.connect(DB_DSN) as conn:
            write_checked_transaction(conn, payload, result, username, deal_id=deal_id)
            conn.commit()

    def ensure_checked_transaction(agent_transaction_id: str) -> None:
        # Не разрешаем pay без ранее сохранённой успешной проверки.
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT state FROM app.interhub_transactions WHERE agent_transaction_id=%s", (agent_transaction_id,))
                row = cur.fetchone()
        if not row:
            raise HTTPException(409, "InterHub payment must be checked before pay")
        if str(row[0]) != "checked":
            raise HTTPException(409, "InterHub payment cannot be paid in its current state")

    def require_standalone_transaction(agent_transaction_id: str) -> None:
        # Общие платежи не должны обходить проверки черновика, региона и версии покупки в сделке.
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT deal_id FROM app.interhub_transactions WHERE agent_transaction_id=%s", (agent_transaction_id,))
                row = cur.fetchone()
        if row and row[0] is not None:
            raise HTTPException(409, "Покупку, связанную со сделкой, выполняйте только из карточки сделки.")

    def start_provider_payment(agent_transaction_id: str) -> None:
        # Помечаем оплату начатой до сетевого вызова, чтобы после обрыва не отправить pay второй раз.
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE app.interhub_transactions
                    SET state='processing', provider_message='Оплата отправлена в InterHub; ожидается ответ',
                        next_status_check_at=now() + interval '1 minute', updated_at=now()
                    WHERE agent_transaction_id=%s AND state='checked'
                    RETURNING agent_transaction_id
                    """,
                    (agent_transaction_id,),
                )
                started = cur.fetchone()
            conn.commit()
        if not started:
            ensure_checked_transaction(agent_transaction_id)

    def mark_payment_uncertain(agent_transaction_id: str, message: str) -> None:
        # Оставляем неопределённую оплату на сверку статуса и никогда не пытаемся оплатить её повторно.
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE app.interhub_transactions
                    SET state='processing', provider_message=%s, next_status_check_at=now() + interval '1 minute', updated_at=now()
                    WHERE agent_transaction_id=%s AND state='processing'
                    """,
                    (message[:2000], agent_transaction_id),
                )
            conn.commit()

    def save_provider_result(agent_transaction_id: str, result: dict, *, is_status_check: bool = False) -> None:
        # Сохраняем финальный ответ и ключ сразу, потому что check_status может не повторить gift_code.
        state = response_state(result)
        params = result.get("params") if isinstance(result.get("params"), dict) else {}
        gift_code = str(params.get("gift_code") or "")
        changed_deal_id = None
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT state, status_check_attempts, deal_id FROM app.interhub_transactions WHERE agent_transaction_id=%s", (agent_transaction_id,))
                row = cur.fetchone()
                if row and row[2] is not None:
                    # Порядок блокировок совпадает с сохранением/удалением сделки: сначала сделка, затем покупка.
                    cur.execute("SELECT deal_id FROM app.deals WHERE deal_id=%s FOR UPDATE", (int(row[2]),))
                cur.execute("SELECT state, status_check_attempts, deal_id FROM app.interhub_transactions WHERE agent_transaction_id=%s FOR UPDATE", (agent_transaction_id,))
                row = cur.fetchone()
                # Не даём запоздалой сверке по сети откатить уже подтверждённую оплату в processing или failed.
                if row and str(row[0] or "") == "paid" and state != "paid":
                    conn.commit()
                    return
                current_attempts = int(row[1] or 0) if row else 0
                check_attempts = current_attempts + 1 if state == "processing" and is_status_check else current_attempts
                interval = interhub_status_check_interval(check_attempts)
                cur.execute(
                    """
                    UPDATE app.interhub_transactions
                    SET state=%s, provider_status=%s, provider_message=%s,
                        provider_transaction_id=COALESCE(NULLIF(%s, ''), provider_transaction_id),
                        gift_code=COALESCE(NULLIF(%s, ''), gift_code), provider_response=%s::jsonb,
                        updated_at=now(),
                        status_check_attempts=CASE WHEN %s='processing' THEN %s ELSE status_check_attempts END,
                        next_status_check_at=CASE WHEN %s='processing' THEN now() + CAST(%s AS interval) ELSE NULL END
                    WHERE agent_transaction_id=%s
                    """,
                    (
                        state, int(result.get("status") or 0), str(result.get("message") or ""),
                        str(result.get("transaction_id") or ""), gift_code, json.dumps(result.get("raw") or {}),
                        state, check_attempts, state, interval, agent_transaction_id,
                    ),
                )
                if state == "paid" and row and row[2] is not None and str(row[0] or "") != "paid":
                    # Суммируем все оплаченные ваучеры сделки, чтобы отчёты учитывали повторные покупки.
                    cur.execute(
                        """
                        UPDATE app.deal_items
                        SET purchase_cost=(
                              SELECT COALESCE(SUM(amount), 0)
                              FROM app.interhub_transactions
                              WHERE deal_id=%s AND state='paid'
                            ),
                            purchase_at=COALESCE(purchase_at, now())
                        WHERE deal_id=%s
                        """,
                        (int(row[2]), int(row[2])),
                    )
                    changed_deal_id = int(row[2])
                    cur.execute("UPDATE app.deals SET lock_version=lock_version + 1 WHERE deal_id=%s", (changed_deal_id,))
            conn.commit()
        if changed_deal_id and publish_deal_event:
            # Фоновое подтверждение оплаты тоже обновляет таблицу сделок у открытых клиентов.
            try:
                publish_deal_event("deal_updated", changed_deal_id, "supplier")
            except Exception:
                pass

    def voucher_batch_response(batch_id: str) -> dict:
        # Собираем итог из операций, чтобы число ключей всегда совпадало с фактически сохранёнными ответами.
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT requested_quantity, state, message, active_agent_transaction_id
                    FROM app.interhub_voucher_purchase_batches
                    WHERE batch_id=%s::uuid
                    """,
                    (batch_id,),
                )
                batch = cur.fetchone()
                if not batch:
                    raise HTTPException(404, "InterHub voucher batch not found")
                cur.execute(
                    """
                    SELECT
                      COUNT(*) FILTER (WHERE state='paid'),
                      COUNT(*) FILTER (WHERE state='paid' AND gift_code<>''),
                      COALESCE(array_agg(gift_code ORDER BY voucher_batch_position) FILTER (WHERE state='paid' AND gift_code<>''), ARRAY[]::text[])
                    FROM app.interhub_transactions
                    WHERE voucher_batch_id=%s::uuid
                    """,
                    (batch_id,),
                )
                paid_quantity, received_quantity, gift_codes = cur.fetchone()
            conn.commit()
        state = str(batch[1] or "")
        return {
            "success": state == "completed",
            "status": 0 if state == "completed" else (1 if state in {"ready", "running", "awaiting_status"} else 2),
            "batch_id": batch_id,
            "state": state,
            "message": str(batch[2] or ""),
            "requested_quantity": int(batch[0] or 0),
            "paid_quantity": int(paid_quantity or 0),
            "received_quantity": int(received_quantity or 0),
            "gift_codes": [str(code) for code in (gift_codes or [])],
            "active_agent_transaction_id": str(batch[3] or ""),
        }

    def set_voucher_batch_state(batch_id: str, state: str, message: str, active_agent_transaction_id: str = "") -> None:
        # Фиксируем этап пачки после каждого внешнего действия, чтобы её можно было безопасно продолжить позже.
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE app.interhub_voucher_purchase_batches
                    SET state=%s, message=%s, active_agent_transaction_id=%s, updated_at=now()
                    WHERE batch_id=%s::uuid
                    """,
                    (state, message[:2000], active_agent_transaction_id, batch_id),
                )
            conn.commit()

    def release_voucher_batch(batch_id: str, lease_token: str) -> None:
        # Освобождаем аренду после ответа, чтобы следующий безопасный шаг не ждал её полного срока.
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE app.interhub_voucher_purchase_batches
                    SET lease_token=NULL, lease_expires_at=NULL, updated_at=now()
                    WHERE batch_id=%s::uuid AND lease_token=%s::uuid
                    """,
                    (batch_id, lease_token),
                )
            conn.commit()

    def claim_voucher_batch(batch_id: str) -> str | None:
        # Берём пачку в работу атомарно, чтобы два клика или повтор HTTP-запроса не купили один ключ дважды.
        lease_token = str(uuid.uuid4())
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE app.interhub_voucher_purchase_batches
                    SET lease_token=%s::uuid, lease_expires_at=now() + interval '30 minutes',
                        state=CASE WHEN state='awaiting_status' THEN state ELSE 'running' END,
                        updated_at=now()
                    WHERE batch_id=%s::uuid
                      AND (lease_expires_at IS NULL OR lease_expires_at < now())
                      AND state NOT IN ('completed', 'stopped')
                    RETURNING batch_id
                    """,
                    (lease_token, batch_id),
                )
                claimed = cur.fetchone()
            conn.commit()
        return lease_token if claimed else None

    def prepare_voucher_batch(batch_id: str, first_agent_transaction_id: str, quantity: int, username: str) -> tuple[str, int]:
        # Создаём одну долговечную пачку из уже проверенной операции и привязываем к ней первый ключ.
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                # Сериализуем два одновременных старта по одной проверке ещё до появления строки пачки.
                cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (first_agent_transaction_id,))
                cur.execute(
                    """
                    SELECT batch_id::text, requested_quantity
                    FROM app.interhub_voucher_purchase_batches
                    WHERE first_agent_transaction_id=%s
                    FOR UPDATE
                    """,
                    (first_agent_transaction_id,),
                )
                existing = cur.fetchone()
                if existing:
                    conn.commit()
                    if int(existing[1]) != quantity:
                        raise HTTPException(409, "InterHub voucher batch quantity does not match the first request")
                    return str(existing[0]), int(existing[1])
                cur.execute(
                    """
                    SELECT service_id, account, amount, request_params, state
                    FROM app.interhub_transactions
                    WHERE agent_transaction_id=%s
                    FOR UPDATE
                    """,
                    (first_agent_transaction_id,),
                )
                transaction = cur.fetchone()
                if not transaction or str(transaction[4] or "") != "checked":
                    conn.commit()
                    raise HTTPException(409, "InterHub voucher payment must be checked before batch pay")
                cur.execute(
                    """
                    INSERT INTO app.interhub_voucher_purchase_batches(
                      batch_id, first_agent_transaction_id, service_id, account, amount, request_params,
                      requested_quantity, state, created_by
                    ) VALUES (%s::uuid, %s, %s, %s, %s, %s::jsonb, %s, 'ready', %s)
                    """,
                    (
                        batch_id, first_agent_transaction_id, int(transaction[0]), str(transaction[1] or ""),
                        float(transaction[2] or 0), json.dumps(transaction[3] or {}), quantity, username,
                    ),
                )
                cur.execute(
                    """
                    UPDATE app.interhub_transactions
                    SET voucher_batch_id=%s::uuid, voucher_batch_position=1, updated_at=now()
                    WHERE agent_transaction_id=%s AND state='checked'
                    """,
                    (batch_id, first_agent_transaction_id),
                )
            conn.commit()
        return batch_id, quantity

    def read_voucher_batch(batch_id: str) -> dict:
        # Читаем исходные реквизиты пачки только из БД, чтобы повтор не зависел от состояния формы в браузере.
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT service_id, account, amount, request_params, requested_quantity, first_agent_transaction_id
                    FROM app.interhub_voucher_purchase_batches
                    WHERE batch_id=%s::uuid
                    """,
                    (batch_id,),
                )
                row = cur.fetchone()
            conn.commit()
        if not row:
            raise HTTPException(404, "InterHub voucher batch not found")
        params = row[3] if isinstance(row[3], dict) else json.loads(row[3] or "{}")
        return {
            "service_id": int(row[0]), "account": str(row[1] or ""), "amount": float(row[2] or 0),
            "params": params, "quantity": int(row[4]), "first_agent_transaction_id": str(row[5]),
        }

    def read_voucher_transaction(batch_id: str, position: int) -> tuple[str, str, str] | None:
        # Находим ровно одну операцию позиции, потому что уникальный индекс не допускает дубля ключа.
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT agent_transaction_id, state, gift_code
                    FROM app.interhub_transactions
                    WHERE voucher_batch_id=%s::uuid AND voucher_batch_position=%s
                    """,
                    (batch_id, position),
                )
                row = cur.fetchone()
            conn.commit()
        return (str(row[0]), str(row[1]), str(row[2] or "")) if row else None

    def attach_voucher_transaction(batch_id: str, position: int, agent_transaction_id: str) -> None:
        # Привязываем успешный check к позиции до pay, чтобы повторный запуск увидел уже созданную операцию.
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE app.interhub_transactions
                    SET voucher_batch_id=%s::uuid, voucher_batch_position=%s, updated_at=now()
                    WHERE agent_transaction_id=%s AND state='checked'
                    """,
                    (batch_id, position, agent_transaction_id),
                )
                if cur.rowcount != 1:
                    conn.commit()
                    raise HTTPException(409, "InterHub voucher check cannot be attached to batch")
            conn.commit()

    def check_voucher_service(service_id: int) -> None:
        # Не доверяем типу из браузера: массовая покупка доступна только реальному типу VOUCHER у поставщика.
        services = interhub_get_services()
        service = next((item for item in services if int(item.get("service_id") or 0) == service_id), None)
        if not service or str(service.get("type") or "").upper() != "VOUCHER":
            raise HTTPException(422, "InterHub batch payment is available only for VOUCHER services")

    def resolve_uncertain_voucher_payment(agent_transaction_id: str) -> tuple[str, str]:
        # Сверяем начатую оплату по её прежнему идентификатору и не создаём вместо неё новую.
        try:
            result = interhub_check_status({"agent_transaction_id": agent_transaction_id})
        except Exception as exc:
            message = str(getattr(exc, "detail", exc))
            mark_payment_uncertain(agent_transaction_id, message)
            return "processing", message
        save_provider_result(agent_transaction_id, result, is_status_check=True)
        return response_state(result), str(result.get("message") or "")

    def pay_voucher_transaction(batch_id: str, agent_transaction_id: str) -> tuple[str, str]:
        # Выполняем только один pay для позиции; исключение сети переводит её в безопасное ожидание статуса.
        set_voucher_batch_state(batch_id, "running", "Отправляем запрос на получение ключа", agent_transaction_id)
        try:
            start_provider_payment(agent_transaction_id)
        except HTTPException as exc:
            # Второй поток не имеет права повторять pay: вместо этого он ждёт и сверяет уже начатую операцию.
            return "processing", str(exc.detail)
        try:
            result = interhub_pay({"agent_transaction_id": agent_transaction_id})
        except Exception as exc:
            message = str(getattr(exc, "detail", exc))
            mark_payment_uncertain(agent_transaction_id, message)
            return "processing", message
        save_provider_result(agent_transaction_id, result)
        return response_state(result), str(result.get("message") or "")

    def create_checked_voucher_transaction(batch_id: str, position: int, batch: dict, username: str) -> tuple[str | None, str]:
        # Создаём следующие ключи отдельными check-операциями, чтобы у каждого был свой устойчивый идентификатор.
        agent_transaction_id = f"gamesales-voucher-{batch_id[:8]}-{position}-{uuid.uuid4().hex[:12]}"
        request = {
            "service_id": batch["service_id"], "account": batch["account"], "params": batch["params"],
            "agent_transaction_id": agent_transaction_id,
        }
        try:
            calculated = interhub_calculate({**request, "agent_transaction_id": f"{agent_transaction_id}-calculate"})
            amount = float(calculated.get("fixed_amount") or 0)
            if not bool(calculated.get("success")) or amount <= 0:
                return None, str(calculated.get("message") or "InterHub не вернул цену ваучера")
            checked = interhub_check({**request, "amount": amount})
        except Exception as exc:
            return None, str(getattr(exc, "detail", exc))
        save_checked_transaction({**request, "amount": amount}, checked, username)
        if not bool(checked.get("success")):
            return None, str(checked.get("message") or "InterHub не подтвердил выдачу ваучера")
        attach_voucher_transaction(batch_id, position, agent_transaction_id)
        return agent_transaction_id, ""

    def run_voucher_batch(batch_id: str, username: str) -> dict:
        # Идём по ограниченному циклу позиций и завершаем пачку при первом неясном или неуспешном ответе.
        lease_token = claim_voucher_batch(batch_id)
        if not lease_token:
            return voucher_batch_response(batch_id)
        try:
            batch = read_voucher_batch(batch_id)
            # Проверяем тип уже в фоне, чтобы запуск пачки не ждал внешний каталог InterHub.
            check_voucher_service(batch["service_id"])
            for position in range(1, batch["quantity"] + 1):
                transaction = read_voucher_transaction(batch_id, position)
                if transaction:
                    agent_transaction_id, state, gift_code = transaction
                    if state == "paid":
                        if not gift_code:
                            set_voucher_batch_state(batch_id, "stopped", "InterHub подтвердил оплату, но не вернул ключ", agent_transaction_id)
                            return voucher_batch_response(batch_id)
                        continue
                    if state == "failed":
                        set_voucher_batch_state(batch_id, "stopped", "InterHub не выдал следующий ваучер", agent_transaction_id)
                        return voucher_batch_response(batch_id)
                    if state == "processing":
                        state, message = resolve_uncertain_voucher_payment(agent_transaction_id)
                        if state == "processing":
                            set_voucher_batch_state(batch_id, "awaiting_status", f"Ожидаем статус уже отправленной оплаты: {message}", agent_transaction_id)
                            return voucher_batch_response(batch_id)
                        if state != "paid":
                            set_voucher_batch_state(batch_id, "stopped", f"InterHub не подтвердил оплату: {message}", agent_transaction_id)
                            return voucher_batch_response(batch_id)
                        transaction = read_voucher_transaction(batch_id, position)
                        if not transaction or not transaction[2]:
                            set_voucher_batch_state(batch_id, "stopped", "InterHub подтвердил оплату, но не вернул ключ", agent_transaction_id)
                            return voucher_batch_response(batch_id)
                        continue
                    if state != "checked":
                        set_voucher_batch_state(batch_id, "awaiting_status", "Операция ожидает безопасной сверки статуса", agent_transaction_id)
                        return voucher_batch_response(batch_id)
                else:
                    agent_transaction_id, message = create_checked_voucher_transaction(batch_id, position, batch, username)
                    if not agent_transaction_id:
                        set_voucher_batch_state(batch_id, "stopped", f"Получено ключей: {voucher_batch_response(batch_id)['received_quantity']}. {message}")
                        return voucher_batch_response(batch_id)
                state, message = pay_voucher_transaction(batch_id, agent_transaction_id)
                if state == "processing":
                    set_voucher_batch_state(batch_id, "awaiting_status", f"Оплата отправлена, ждём статус: {message}", agent_transaction_id)
                    return voucher_batch_response(batch_id)
                if state != "paid":
                    set_voucher_batch_state(batch_id, "stopped", f"Получено ключей: {voucher_batch_response(batch_id)['received_quantity']}. {message}", agent_transaction_id)
                    return voucher_batch_response(batch_id)
                transaction = read_voucher_transaction(batch_id, position)
                if not transaction or not transaction[2]:
                    set_voucher_batch_state(batch_id, "stopped", "InterHub подтвердил оплату, но не вернул ключ", agent_transaction_id)
                    return voucher_batch_response(batch_id)
            set_voucher_batch_state(batch_id, "completed", f"Успешно получено ключей: {batch['quantity']}")
            return voucher_batch_response(batch_id)
        finally:
            release_voucher_batch(batch_id, lease_token)

    def run_voucher_batch_worker(batch_id: str, username: str) -> None:
        # Выполняем длительную покупку вне HTTP-ответа, чтобы тайм-аут браузера не прерывал выдачу ключей.
        try:
            run_voucher_batch(batch_id, username)
        except Exception as exc:
            set_voucher_batch_state(batch_id, "stopped", f"Не удалось продолжить выдачу ключей: {exc}")

    def start_voucher_batch_worker(batch_id: str, username: str) -> None:
        # Запускаем отдельный поток; аренда пачки внутри не даст параллельным кликам списать деньги повторно.
        threading.Thread(
            target=run_voucher_batch_worker,
            args=(batch_id, username),
            daemon=True,
            name=f"interhub-voucher-{batch_id[:8]}",
        ).start()

    def resume_pending_voucher_batches() -> None:
        # После перезапуска возвращаем в работу незавершённые пачки, когда их прежняя аренда уже истекла.
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT batch_id::text, created_by
                    FROM app.interhub_voucher_purchase_batches
                    WHERE state IN ('ready', 'running', 'awaiting_status')
                      AND (lease_expires_at IS NULL OR lease_expires_at < now())
                    ORDER BY updated_at
                    LIMIT 20
                    """
                )
                batches = [(str(row[0]), str(row[1] or "")) for row in cur.fetchall()]
            conn.commit()
        for batch_id, username in batches:
            start_voucher_batch_worker(batch_id, username)

    def refresh_pending_transactions() -> None:
        # Выбираем просроченные processing-операции и опрашиваем InterHub не чаще раза в пять минут.
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH due AS (
                      SELECT agent_transaction_id FROM app.interhub_transactions
                      WHERE state='processing'
                        AND next_status_check_at <= now()
                        AND COALESCE(created_by, '') <> 'ozon-auto'
                      ORDER BY next_status_check_at
                      FOR UPDATE SKIP LOCKED
                      LIMIT 50
                    )
                    UPDATE app.interhub_transactions target
                    SET next_status_check_at=now() + interval '5 minutes', updated_at=now()
                    FROM due
                    WHERE target.agent_transaction_id=due.agent_transaction_id
                    RETURNING target.agent_transaction_id
                    """
                )
                identifiers = [str(row[0]) for row in cur.fetchall()]
            conn.commit()
        for agent_transaction_id in identifiers:
            try:
                # Отдельная ошибка одного поставщика не останавливает проверку остальных операций.
                save_provider_result(agent_transaction_id, interhub_check_status({"agent_transaction_id": agent_transaction_id}), is_status_check=True)
            except Exception:
                continue
        # Возобновляем пачки отдельно: их обработчик сам проверит аренду и не создаст дубли оплат.
        resume_pending_voucher_batches()

    def serialize_price_job(job: dict) -> dict:
        # Возвращаем только данные прогресса, чтобы UI мог безопасно показывать выполнение запуска.
        return {
            "job_id": job["job_id"], "batch_id": job["batch_id"], "state": job["state"],
            "total": job["total"], "processed": job["processed"], "successes": job["successes"],
            "errors": job["errors"], "message": job["message"],
            "stock_total": job["stock_total"], "stock_processed": job["stock_processed"],
            "stock_successes": job["stock_successes"], "stock_errors": job["stock_errors"],
        }

    def run_price_refresh(job_id: str, username: str) -> None:
        # Ручной запуск использует тот же движок и блокировку, что и расписание.
        def progress(counts):
            # Обновляем привычный индикатор без вмешательства в открытую форму покупки.
            with price_jobs_lock:
                price_jobs[job_id].update(counts)
        try:
            shared_catalog.refresh(progress=progress)
            with price_jobs_lock:
                price_jobs[job_id].update(state='completed', message='Цены и остатки обновлены')
        except Exception as exc:
            with price_jobs_lock:
                price_jobs[job_id].update(state='failed', message=str(getattr(exc, 'detail', exc)))

    def read_deal_context(conn, deal_id: int, *, lock: bool = False) -> dict:
        # Читаем тип и регион из самой сделки, чтобы браузер не мог подменить разрешённый сервис поставщика.
        if int(deal_id or 0) <= 0:
            raise HTTPException(422, "deal_id must be positive")
        lock_sql = " FOR UPDATE OF d" if lock else ""
        with conn.cursor() as cur:
            if lock:
                # После ожидания блокировки читаем и сделку, и её позиции из свежего снимка.
                cur.execute("SELECT deal_id FROM app.deals WHERE deal_id=%s FOR UPDATE", (deal_id,))
            cur.execute(
                f"""
                SELECT d.deal_type_code, COALESCE(rd.code, ra.code), d.status_code,
                       di.returned_at, d.order_number, COALESCE(c.nickname, ''),
                       d.flow_status_code, d.lock_version
                FROM app.deals d
                JOIN app.deal_items di ON di.deal_id=d.deal_id
                LEFT JOIN app.regions rd ON rd.region_id=d.region_id
                LEFT JOIN app.accounts a ON a.account_id=di.account_id
                LEFT JOIN app.regions ra ON ra.region_id=a.region_id
                LEFT JOIN app.customers c ON c.customer_id=d.customer_id
                WHERE d.deal_id=%s
                ORDER BY di.deal_item_id
                LIMIT 1{lock_sql}
                """,
                (deal_id,),
            )
            row = cur.fetchone()
        if not row or str(row[2] or "") == "cancelled":
            raise HTTPException(404, "deal not found")
        if str(row[0] or "").strip().lower() != "sale":
            raise HTTPException(422, "Supplier nominals are available only for service deals")
        region_code = str(row[1] or "").strip().upper()
        if region_code not in DEAL_INTERHUB_SERVICE_IDS:
            raise HTTPException(422, "Supplier nominals are available only for Turkey and Poland")
        return {
            "deal_id": int(deal_id), "region_code": region_code,
            "order_number": str(row[4] or ""), "customer_nickname": str(row[5] or ""),
            "flow_status_code": str(row[6] or ""), "lock_version": int(row[7]),
            # Завершённые сделки сохраняют историю кодов, но не допускают новых списаний.
            "purchase_allowed": str(row[6] or "") not in {"draft", "completed"} and row[3] is None,
        }

    def require_deal_purchase_allowed(deal: dict, payload: dict) -> None:
        # Проверяем сохранённый статус и версию, а не редактируемые поля браузера.
        if deal["flow_status_code"] == "draft":
            raise HTTPException(409, "Покупка в черновике запрещена. Сначала сохраните рабочую сделку.")
        if deal["flow_status_code"] == "completed":
            raise HTTPException(409, "Покупка ваучеров в завершённой сделке запрещена.")
        if not deal["purchase_allowed"]:
            raise HTTPException(409, "Нельзя покупать ваучеры для возвращённой сделки.")
        version = payload.get("lock_version")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise HTTPException(422, "Для покупки требуется lock_version сохранённой сделки.")
        if version != deal["lock_version"]:
            raise HTTPException(409, "Сделка изменилась. Обновите карточку и заново получите цену поставщика.")

    def provider_service_for_region(region_code: str) -> dict:
        # Находим только заранее разрешённый PlayStation-сервис региона и дополнительно проверяем его название.
        normalized_region = str(region_code or "").strip().upper()
        service_id = DEAL_INTERHUB_SERVICE_IDS.get(normalized_region)
        expected_region = {"TR": "turkey", "PL": "poland"}.get(normalized_region, "")
        services = interhub_get_services()
        service = next((item for item in services if int(item.get("service_id") or 0) == int(service_id or 0)), None)
        title = str(service.get("title") or "") if service else ""
        normalized_title = title.casefold()
        if not service or "playstation" not in normalized_title or expected_region not in normalized_title:
            raise HTTPException(503, f"InterHub PlayStation service for {normalized_region} is unavailable")
        if str(service.get("type") or "").strip().upper() != "VOUCHER":
            raise HTTPException(503, "Configured InterHub PlayStation service is not a voucher service")
        return service

    def fallback_provider_service(region_code: str) -> dict:
        # Восстанавливаем подпись уже купленного кода без обращения к каталогу, если Interhub временно недоступен.
        normalized_region = str(region_code or "").strip().upper()
        region_title = {"TR": "Turkey", "PL": "Poland"}.get(normalized_region, normalized_region)
        return {
            "service_id": int(DEAL_INTERHUB_SERVICE_IDS.get(normalized_region) or 0),
            "title": f"PlayStation - {region_title}", "type": "VOUCHER", "fields": [],
        }

    def supplier_nominals(service: dict) -> list[dict]:
        # Возвращаем только активные значения поля nominal и сортируем их по числовому номиналу.
        field = next(
            (item for item in service.get("fields") or [] if str(item.get("name") or "").strip().casefold() == "nominal"),
            None,
        )
        items: list[dict] = []
        for option in (field or {}).get("value_list") or []:
            if not isinstance(option, dict) or option.get("active") is False:
                continue
            nominal_id = str(option.get("id") or "").strip()
            title = str(option.get("title") or nominal_id).strip()
            if not nominal_id or not title:
                continue
            numeric = "".join(char if char.isdigit() or char in ".," else " " for char in title).split()
            try:
                sort_amount = float(str(numeric[0]).replace(",", ".")) if numeric else 0.0
            except (TypeError, ValueError):
                sort_amount = 0.0
            items.append({"id": nominal_id, "title": title, "sort_amount": sort_amount})
        items.sort(key=lambda item: (float(item["sort_amount"]), item["title"].casefold()))
        return [{"id": item["id"], "title": item["title"]} for item in items]

    def read_deal_transactions(deal_id: int, *, conn=None) -> list[tuple]:
        # Возвращаем все операции сделки, чтобы каждый номинал и выданный код оставались в её истории.
        if conn is None:
            with psycopg.connect(DB_DSN) as connection:
                return read_deal_transactions(deal_id, conn=connection)
        else:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT agent_transaction_id, state, provider_status, provider_message, service_id,
                           COALESCE(request_params->>'nominal', ''), amount, gift_code,
                           created_by, created_at, updated_at,
                           COALESCE(request_params->>'nominal_title', '')
                    FROM app.interhub_transactions
                    WHERE deal_id=%s AND state<>'cancelled'
                    ORDER BY created_at DESC, agent_transaction_id DESC
                    """,
                    (deal_id,),
                )
                return cur.fetchall()

    def read_deal_transaction(deal_id: int) -> tuple | None:
        # Находим последнюю операцию для совместимости с одиночным статусом текущей покупки.
        transactions = read_deal_transactions(deal_id)
        return transactions[0] if transactions else None

    def serialize_deal_transaction(row: tuple | None, *, service: dict | None = None) -> dict | None:
        # Отдаём статус и код только из строки, уже связанной с нужной сделкой.
        if not row:
            return None
        state = str(row[1] or "")
        nominal_id = str(row[5] or "")
        nominal_title = str(row[11] or "") if len(row) > 11 else ""
        service_title = str((service or {}).get("title") or "")
        if service:
            nominal = next((item for item in supplier_nominals(service) if item["id"] == nominal_id), None)
            nominal_title = str((nominal or {}).get("title") or nominal_title or nominal_id)
        return {
            "agent_transaction_id": str(row[0] or ""), "state": state,
            "success": state in {"checked", "processing", "paid"},
            "status": 1 if state == "processing" else (0 if state in {"checked", "paid"} else 2),
            "message": str(row[3] or ""), "provider_status": int(row[2] or 0),
            "service_id": int(row[4] or 0), "service_title": service_title,
            "nominal_id": nominal_id, "nominal_title": nominal_title,
            "amount": float(row[6] or 0), "gift_code": str(row[7] or ""),
            "created_by": str(row[8] or ""), "created_at": row[9], "updated_at": row[10],
        }

    def deal_supplier_payload(deal_id: int) -> dict:
        # Собираем каталог региона и сохранённую операцию одним ответом для восстановления формы после открытия.
        with psycopg.connect(DB_DSN) as conn:
            deal = read_deal_context(conn, deal_id, lock=True)
            transactions = read_deal_transactions(deal_id, conn=conn)
            conn.commit()
        transaction = transactions[0] if transactions else None
        try:
            service = provider_service_for_region(deal["region_code"]) if deal["purchase_allowed"] else fallback_provider_service(deal["region_code"])
        except Exception:
            # Сохранённый код важнее временной ошибки каталога; новую покупку без живой проверки всё равно не начинаем.
            if not transaction:
                raise
            service = fallback_provider_service(deal["region_code"])
        return {
            **deal,
            "service_id": int(service["service_id"]),
            "service_title": str(service.get("title") or ""),
            "nominals": supplier_nominals(service),
            "purchase": serialize_deal_transaction(transaction, service=service),
            "purchases": [serialize_deal_transaction(row, service=service) for row in transactions],
        }

    def read_locked_deal_transaction(conn, deal_id: int) -> tuple | None:
        # Блокируем только активную строку выбранной сделки перед сменой состояния оплаты.
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT agent_transaction_id, state, provider_status, provider_message, service_id,
                       COALESCE(request_params->>'nominal', ''), amount, gift_code,
                       created_by, created_at, updated_at,
                       COALESCE(request_params->>'nominal_title', '')
                FROM app.interhub_transactions
                WHERE deal_id=%s AND state IN ('checked', 'processing')
                ORDER BY created_at DESC, agent_transaction_id DESC
                LIMIT 1
                FOR UPDATE
                """,
                (deal_id,),
            )
            return cur.fetchone()

    def read_locked_deal_transaction_by_id(conn, deal_id: int, agent_transaction_id: str) -> tuple | None:
        # Блокируем конкретный check, чтобы повтор старой кнопки не смог оплатить более новый ваучер сделки.
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT agent_transaction_id, state, provider_status, provider_message, service_id,
                       COALESCE(request_params->>'nominal', ''), amount, gift_code,
                       created_by, created_at, updated_at,
                       COALESCE(request_params->>'nominal_title', '')
                FROM app.interhub_transactions
                WHERE deal_id=%s AND agent_transaction_id=%s
                  AND state IN ('checked', 'processing', 'paid')
                FOR UPDATE
                """,
                (deal_id, agent_transaction_id),
            )
            return cur.fetchone()

    @app.get("/deals/{deal_id}/interhub")
    def get_deal_supplier_purchase(deal_id: int, user: UserOut = Depends(get_current_user)):
        # Любая авторизованная роль видит только поставщика, разрешённого регионом конкретной сделки.
        _ = user
        return deal_supplier_payload(deal_id)

    @app.post("/deals/{deal_id}/interhub/prepare")
    def prepare_deal_supplier_purchase(
        deal_id: int,
        payload: dict = Body(...),
        user: UserOut = Depends(get_current_user),
    ):
        # Сериализуем подготовку по deal_id, оставляя покупки разных сделок полностью параллельными.
        requested_nominal_id = str(payload.get("nominal_id") or "").strip()
        if not requested_nominal_id:
            raise HTTPException(422, "nominal_id is required")
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(%s)", (deal_id,))
            deal = read_deal_context(conn, deal_id, lock=True)
            require_deal_purchase_allowed(deal, payload)
            service = provider_service_for_region(deal["region_code"])
            nominal = next((item for item in supplier_nominals(service) if item["id"] == requested_nominal_id), None)
            if not nominal:
                raise HTTPException(422, "Selected nominal is not available for the deal region")
            active = read_locked_deal_transaction(conn, deal_id)
            if active:
                active_payload = serialize_deal_transaction(active, service=service)
                if str(active[1] or "") == "processing":
                    conn.commit()
                    return {**active_payload, "lock_version": deal["lock_version"]}
                if int(active[4] or 0) == int(service["service_id"]) and str(active[5] or "") == requested_nominal_id:
                    conn.commit()
                    return {**active_payload, "lock_version": deal["lock_version"]}
                # Новый выбор отменяет только ещё не оплаченную проверку этой же сделки.
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE app.interhub_transactions SET state='cancelled', updated_at=now() WHERE agent_transaction_id=%s AND state='checked'",
                        (str(active[0]),),
                    )
            base_id = f"gamesales-deal-{deal_id}-{uuid.uuid4().hex[:16]}"
            request = {
                "service_id": int(service["service_id"]), "account": "",
                "agent_transaction_id": f"{base_id}-calculate", "params": {"nominal": requested_nominal_id},
            }
            calculation = interhub_calculate(request)
            amount = float(calculation.get("fixed_amount") or 0)
            if not bool(calculation.get("success")) or amount <= 0:
                conn.commit()
                return {
                    "success": False, "status": int(calculation.get("status") or 2), "state": "failed",
                    "message": str(calculation.get("message") or "InterHub не вернул актуальную цену"),
                    "service_id": int(service["service_id"]), "service_title": str(service.get("title") or ""),
                    "nominal_id": requested_nominal_id, "nominal_title": nominal["title"], "amount": amount,
                }
            check_request = {**request, "agent_transaction_id": base_id, "amount": amount}
            checked = interhub_check(check_request)
            # Подпись номинала сохраняем после вызова поставщика, не добавляя лишнее поле в его запрос.
            stored_request = {
                **check_request,
                "params": {**check_request["params"], "nominal_title": nominal["title"]},
            }
            write_checked_transaction(conn, stored_request, checked, str(user.username or ""), deal_id=deal_id)
            conn.commit()
        if not bool(checked.get("success")):
            return {
                "success": False, "status": int(checked.get("status") or 2), "state": "failed",
                "message": str(checked.get("message") or "InterHub не подтвердил доступность"),
                "service_id": int(service["service_id"]), "service_title": str(service.get("title") or ""),
                "nominal_id": requested_nominal_id, "nominal_title": nominal["title"], "amount": amount,
            }
        # Возвращаем именно наш check, а не последнюю строку, которую уже мог создать другой запрос.
        with psycopg.connect(DB_DSN) as conn:
            transaction = read_locked_deal_transaction_by_id(conn, deal_id, base_id)
        if not transaction:
            raise HTTPException(409, "Проверка покупки уже заменена. Получите цену заново.")
        return {**serialize_deal_transaction(transaction, service=service), "lock_version": deal["lock_version"]}

    @app.post("/deals/{deal_id}/interhub/pay")
    def pay_deal_supplier_purchase(
        deal_id: int,
        payload: dict = Body(...),
        user: UserOut = Depends(get_current_user),
    ):
        # Оплачиваем только переданный check; его ID сохраняет идемпотентность при нескольких ваучерах сделки.
        agent_transaction_id = str(payload.get("agent_transaction_id") or "").strip()
        if not agent_transaction_id:
            raise HTTPException(422, "agent_transaction_id is required")
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(%s)", (deal_id,))
            deal = read_deal_context(conn, deal_id, lock=True)
            service = fallback_provider_service(deal["region_code"])
            active = read_locked_deal_transaction_by_id(conn, deal_id, agent_transaction_id)
            if not active:
                raise HTTPException(409, "Supplier purchase must be prepared before pay")
            if int(active[4] or 0) != int(service["service_id"]):
                raise HTTPException(409, "Prepared supplier service does not match the deal region")
            if str(active[1] or "") in {"processing", "paid"}:
                conn.commit()
                return serialize_deal_transaction(active, service=service)
            require_deal_purchase_allowed(deal, payload)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE app.interhub_transactions
                    SET state='processing', provider_message='Оплата отправлена в InterHub; ожидается ответ',
                        next_status_check_at=now() + interval '1 minute', updated_at=now()
                    WHERE agent_transaction_id=%s AND deal_id=%s AND state='checked'
                    RETURNING agent_transaction_id
                    """,
                    (agent_transaction_id, deal_id),
                )
                started = cur.fetchone()
            if not started:
                raise HTTPException(409, "Supplier payment cannot be paid in its current state")
            conn.commit()
        try:
            result = interhub_pay({"agent_transaction_id": agent_transaction_id})
        except Exception as exc:
            # Потеря ответа оставляет именно эту операцию на check_status без повторного списания.
            mark_payment_uncertain(agent_transaction_id, str(getattr(exc, "detail", exc)))
            with psycopg.connect(DB_DSN) as conn:
                return serialize_deal_transaction(
                    read_locked_deal_transaction_by_id(conn, deal_id, agent_transaction_id), service=service,
                )
        save_provider_result(agent_transaction_id, result)
        with psycopg.connect(DB_DSN) as conn:
            return serialize_deal_transaction(
                read_locked_deal_transaction_by_id(conn, deal_id, agent_transaction_id), service=service,
            )

    @app.get("/integrations/interhub/services", response_model=InterHubServiceListOut)
    def list_interhub_services(user: UserOut = Depends(get_current_user)):
        # Список услуг всегда читаем онлайн, в том числе в ограниченном режиме staging.
        _ = user
        items = interhub_get_services()
        return InterHubServiceListOut(total=len(items), items=items)

    @app.get("/integrations/interhub/balance", response_model=InterHubBalanceOut)
    def get_interhub_balance(user: UserOut = Depends(get_current_user)):
        # Баланс всегда запрашиваем у поставщика, не подменяя его нулём на staging.
        _ = user
        return InterHubBalanceOut(**interhub_get_balance())

    @app.get("/integrations/interhub/transactions/paid")
    def list_paid_interhub_transactions(
        date_from: date | None = Query(default=None),
        date_to: date | None = Query(default=None),
        search: str = Query(default="", max_length=200),
        sort_by: Literal["service", "nominal", "price", "giftCode", "createdAt"] = Query(default="createdAt"),
        sort_direction: Literal["asc", "desc"] = Query(default="desc"),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=25, ge=1, le=100),
        user: UserOut = Depends(get_current_user),
    ):
        # Владелец видит весь архив, а остальные роли — только покупки, связанные со сделками.
        user_role = str(getattr(user, "role", "") or "").strip().lower().rsplit(".", 1)[-1]
        is_owner = user_role == "owner"
        if date_from and date_to and date_from > date_to:
            raise HTTPException(422, "Дата «с» не может быть позже даты «по»")
        clauses = ["state='paid'"]
        if not is_owner:
            clauses.append("deal_id IS NOT NULL")
        params: list[object] = []
        if date_from:
            # Привязываем начало дня к МСК, чтобы календарный фильтр совпадал с датой в интерфейсе.
            clauses.append(f"created_at >= (%s::date::timestamp AT TIME ZONE '{INTERHUB_HISTORY_TIMEZONE}')")
            params.append(date_from)
        if date_to:
            # Берём начало следующего дня по МСК, сохраняя включительность даты «по».
            clauses.append(f"created_at < ((%s::date + 1)::timestamp AT TIME ZONE '{INTERHUB_HISTORY_TIMEZONE}')")
            params.append(date_to)
        base_query = f"""
            SELECT history_transaction.agent_transaction_id,
                   history_transaction.service_id,
                   COALESCE(service_calculation.service_title, '') AS service_title,
                   COALESCE(history_transaction.request_params->>'nominal', '') AS nominal,
                   COALESCE(NULLIF(history_transaction.request_params->>'nominal_title', ''), nominal_calculation.nominal_title, '') AS nominal_title,
                   history_transaction.amount,
                   history_transaction.gift_code,
                   history_transaction.created_at,
                   history_transaction.deal_id,
                   COALESCE(history_deal.order_number, '') AS order_number,
                   COALESCE(history_customer.nickname, '') AS customer_nickname,
                   COALESCE(history_deal_region.region_code, '') AS region_code,
                   COALESCE(history_transaction.created_by, '') AS created_by
            FROM app.interhub_transactions AS history_transaction
            LEFT JOIN app.deals AS history_deal ON history_deal.deal_id=history_transaction.deal_id
            LEFT JOIN app.customers AS history_customer ON history_customer.customer_id=history_deal.customer_id
            LEFT JOIN LATERAL (
              SELECT COALESCE(direct_region.code, account_region.code) AS region_code
              FROM app.deal_items AS history_item
              LEFT JOIN app.accounts AS history_account ON history_account.account_id=history_item.account_id
              LEFT JOIN app.regions AS direct_region ON direct_region.region_id=history_deal.region_id
              LEFT JOIN app.regions AS account_region ON account_region.region_id=history_account.region_id
              WHERE history_item.deal_id=history_deal.deal_id
              ORDER BY history_item.deal_item_id
              LIMIT 1
            ) AS history_deal_region ON true
            LEFT JOIN LATERAL (
              SELECT service_title
              FROM app.supplier_catalog_labels
              WHERE success=true AND service_id=history_transaction.service_id
              ORDER BY calculated_at DESC, id DESC
              LIMIT 1
            ) AS service_calculation ON true
            LEFT JOIN LATERAL (
              SELECT nominal_title
              FROM app.supplier_catalog_labels
              WHERE success=true
                AND service_id=history_transaction.service_id
                AND nominal_id::text=COALESCE(history_transaction.request_params->>'nominal', '')
              ORDER BY calculated_at DESC, id DESC
              LIMIT 1
            ) AS nominal_calculation ON true
            WHERE {' AND '.join(f'history_transaction.{clause}' for clause in clauses)}
        """
        filtered_params = list(params)
        search_clause = ""
        if search.strip():
            # Экранируем шаблонные символы LIKE, чтобы поиск совпадал с буквальным текстом пользователя.
            escaped_search = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            search_pattern = f"%{escaped_search}%"
            search_clause = """
                WHERE service_title ILIKE %s ESCAPE '\\'
                   OR nominal ILIKE %s ESCAPE '\\'
                   OR nominal_title ILIKE %s ESCAPE '\\'
                   OR deal_id::text ILIKE %s ESCAPE '\\'
                   OR order_number ILIKE %s ESCAPE '\\'
                   OR customer_nickname ILIKE %s ESCAPE '\\'
                   OR region_code ILIKE %s ESCAPE '\\'
                   OR created_by ILIKE %s ESCAPE '\\'
            """
            filtered_params.extend([search_pattern] * 8)
        sort_columns = {
            "service": "service_title",
            "nominal": "COALESCE(NULLIF(nominal_title, ''), nominal)",
            "price": "amount",
            "giftCode": "gift_code",
            "createdAt": "created_at",
        }
        sort_column = sort_columns[sort_by]
        sort_order = sort_direction.upper()
        offset = (page - 1) * page_size
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    WITH filtered_history AS ({base_query})
                    SELECT COUNT(*), COALESCE(SUM(amount), 0)
                    FROM filtered_history
                    {search_clause}
                    """,
                    filtered_params,
                )
                total_row = cur.fetchone()
                cur.execute(
                    f"""
                    WITH filtered_history AS ({base_query})
                    SELECT service_id, service_title, nominal, nominal_title,
                           amount, gift_code, created_at, deal_id, order_number,
                           customer_nickname, region_code, created_by, agent_transaction_id
                    FROM filtered_history
                    {search_clause}
                    ORDER BY {sort_column} {sort_order}, agent_transaction_id {sort_order}
                    LIMIT %s OFFSET %s
                    """,
                    [*filtered_params, page_size, offset],
                )
                rows = cur.fetchall()
        total = int(total_row[0] or 0) if total_row else 0
        total_amount = float(total_row[1] or 0) if total_row else 0.0
        # Преобразуем сумму в float, чтобы контракт JSON оставался одинаковым для PostgreSQL numeric.
        return {
            "total": total,
            "total_amount": total_amount,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "service_id": int(row[0]),
                    "service_title": str(row[1] or ''),
                    "nominal": str(row[2] or ''),
                    "nominal_title": str(row[3] or ''),
                    "price": float(row[4] or 0),
                    "gift_code": str(row[5] or ''),
                    "created_at": row[6],
                    "deal_id": int(row[7]) if row[7] is not None else None,
                    "order_number": str(row[8] or ''),
                    "customer_nickname": str(row[9] or ''),
                    "region_code": str(row[10] or ''),
                    "created_by": str(row[11] or ''),
                    "agent_transaction_id": str(row[12] or ''),
                }
                for row in rows
            ]
        }

    @app.get("/integrations/interhub/transactions/export")
    def export_purchase_history(
        date_from: date | None = Query(default=None),
        date_to: date | None = Query(default=None),
        user: UserOut = Depends(require_role("owner")),
    ):
        # Владелец получает обе истории за календарные даты окна, независимо от поиска и текущей страницы.
        if date_from and date_to and date_from > date_to:
            raise HTTPException(422, "Дата «с» не может быть позже даты «по»")
        if supplier_hub_client is None:
            raise HTTPException(503, "История селлера недоступна")

        def load_crm_rows():
            # Для выгрузки читаем архив одним запросом с теми же датами и статусом paid.
            return iter_crm_purchase_export(
                psycopg=psycopg, dsn=DB_DSN, date_from=date_from, date_to=date_to,
            )

        try:
            services = interhub_get_services()
        except Exception:
            # Если каталог недоступен, оставляем в файле идентификаторы услуг и сохранённые подписи CRM.
            services = []
        content = build_purchase_history_xlsx(
            load_crm_rows=load_crm_rows, supplier_hub_client=supplier_hub_client,
            services=services, date_from=date_from, date_to=date_to,
        )
        filename = f"purchases-{date_from or 'all'}-{date_to or 'all'}.xlsx"
        return StreamingResponse(
            iter([content]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.post("/integrations/interhub/prices/refresh")
    def refresh_interhub_prices(user: UserOut = Depends(require_role("owner"))):
        # Запускаем один фоновый обход цен, чтобы владелец не мог случайно задвоить запросы.
        if not shared_catalog or shared_catalog.offline:
            raise HTTPException(403, 'На staging опросы отключены')
        with price_jobs_lock:
            if any(job["state"] == "running" for job in price_jobs.values()):
                raise HTTPException(409, "InterHub price refresh is already running")
            job_id = uuid.uuid4().hex
            job = {
                "job_id": job_id, "batch_id": uuid.uuid4().hex, "state": "running", "total": 0,
                "processed": 0, "successes": 0, "errors": 0, "message": "Загружаем каталог InterHub",
                "stock_total": 0, "stock_processed": 0, "stock_successes": 0, "stock_errors": 0,
            }
            price_jobs[job_id] = job
        threading.Thread(target=run_price_refresh, args=(job_id, str(user.username or "")), daemon=True).start()
        return serialize_price_job(job)

    @app.get("/integrations/interhub/prices/refresh/{job_id}")
    def get_interhub_price_refresh_status(job_id: str, user: UserOut = Depends(require_role("owner"))):
        # Отдаём прогресс запущенного в этом процессе расчёта без нового обращения к InterHub.
        _ = user
        with price_jobs_lock:
            job = price_jobs.get(job_id)
            if not job:
                raise HTTPException(404, "InterHub price refresh was not found")
            return serialize_price_job(job)

    @app.get("/integrations/interhub/prices/latest")
    def get_latest_interhub_prices(user: UserOut = Depends(get_current_user)):
        # Отдаём цену и последнюю проверку остатка с независимыми датами из локального кэша.
        _ = user
        prices, stocks = shared_catalog.legacy()
        return {'items': prices, 'stocks': stocks, 'offline': shared_catalog.offline}

    @app.get("/integrations/interhub/prices/export")
    def export_interhub_prices(user: UserOut = Depends(require_role("owner"))):
        # Формируем Excel только из нашей базы, не вызывая поставщика повторно при каждой выгрузке.
        _ = user
        prices, stocks = shared_catalog.legacy()
        errors = [{**r, 'provider_message': r['price_error'], 'calculated_at': r['price_checked_at'],
                   'provider_response': r['price_attempt_response']}
                  for r in prices if r['price_error']]
        if not prices and not errors and not stocks:
            raise HTTPException(404, "InterHub prices have not been calculated yet")
        content = build_interhub_prices_xlsx(prices, errors, stocks)
        filename = "interhub-prices-current.xlsx"
        return StreamingResponse(
            iter([content]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get('/integrations/interhub/catalog/current')
    def supplier_catalog_current(user: UserOut = Depends(get_current_user)):
        # Список изменений читается только из БД, не запускает опрос поставщика.
        return shared_catalog.overview()

    @app.post('/integrations/interhub/catalog/review')
    def review_supplier_catalog(entries: list[dict] = Body(...), user: UserOut = Depends(require_role('owner'))):
        # Явная отметка просмотренных строк общая для команды, с защитой версии.
        if len(entries) > 500 or any(not isinstance(e.get('review_revision'), int)
            or not str(e.get('service_id', '')).isdigit() or not str(e.get('nominal_id', '')).isdigit() for e in entries):
            raise HTTPException(422, 'Некорректный список позиций')
        shared_catalog.review(entries)
        return {'ok': True}

    @app.post("/integrations/interhub/calculate", response_model=InterHubPaymentCheckOut)
    def calculate_interhub_payment(payload: InterHubPaymentRequestIn = Body(...), user: UserOut = Depends(get_current_user)):
        # Рассчитываем фиксированный номинал до обязательной проверки будущей оплаты.
        _ = user
        return InterHubPaymentCheckOut(**interhub_calculate(payload.model_dump(exclude_none=True)))

    @app.post("/integrations/interhub/check", response_model=InterHubPaymentCheckOut)
    def check_interhub_payment(payload: InterHubPaymentRequestIn = Body(...), user: UserOut = Depends(get_current_user)):
        # Сохраняем check и дополняем его живым остатком выбранного номинала без изменения условий оплаты.
        request_data = payload.model_dump(exclude_none=True)
        require_standalone_transaction(str(request_data["agent_transaction_id"]))
        result = interhub_check(request_data)
        save_checked_transaction(request_data, result, str(user.username or ""))
        stock = fetch_nominal_stock(
            request_data['service_id'], (request_data.get('params') or {}).get('nominal'),
            get_services=interhub_get_services, get_detail=interhub_get_service_detail,
        )
        return InterHubPaymentCheckOut(**{**result, 'stock': stock})

    @app.post("/integrations/interhub/pay", response_model=InterHubPaymentCheckOut)
    def pay_interhub_payment(payload: InterHubPayRequestIn = Body(...), user: UserOut = Depends(require_role("owner"))):
        # Атомарно резервируем одиночную оплату до внешнего pay, чтобы два параллельных запроса не списали деньги дважды.
        _ = user
        agent_transaction_id = str(payload.agent_transaction_id or "").strip()
        require_standalone_transaction(agent_transaction_id)
        start_provider_payment(agent_transaction_id)
        try:
            result = interhub_pay({"agent_transaction_id": agent_transaction_id})
        except Exception as exc:
            # После потери ответа сохраняем processing и предлагаем только безопасную сверку прежней операции.
            message = str(getattr(exc, "detail", exc))
            mark_payment_uncertain(agent_transaction_id, message)
            return InterHubPaymentCheckOut(
                success=True,
                status=PENDING_STATUS,
                message="Оплата отправлена, ждём безопасную проверку статуса без повторного списания.",
            )
        save_provider_result(agent_transaction_id, result)
        return InterHubPaymentCheckOut(**result)

    @app.post("/integrations/interhub/vouchers/pay-batch")
    def pay_interhub_voucher_batch(payload: InterHubVoucherBatchPayRequestIn = Body(...), user: UserOut = Depends(require_role("owner"))):
        # Быстро фиксируем и запускаем пачку, а длительное получение ключей продолжаем в фоне.
        try:
            batch_id = str(uuid.UUID(str(payload.batch_id)))
        except (TypeError, ValueError, AttributeError) as exc:
            raise HTTPException(422, "InterHub voucher batch_id must be a UUID") from exc
        first_agent_transaction_id = str(payload.agent_transaction_id or "").strip()
        require_standalone_transaction(first_agent_transaction_id)
        prepared_batch_id, _ = prepare_voucher_batch(batch_id, first_agent_transaction_id, int(payload.quantity), str(user.username or ""))
        start_voucher_batch_worker(prepared_batch_id, str(user.username or ""))
        return voucher_batch_response(prepared_batch_id)

    @app.get("/integrations/interhub/vouchers/batches/{batch_id}")
    def get_interhub_voucher_batch(batch_id: str, user: UserOut = Depends(require_role("owner"))):
        # Возвращаем сохранённый прогресс пачки, чтобы вкладка могла безопасно восстановить результат после обрыва.
        _ = user
        try:
            normalized_batch_id = str(uuid.UUID(str(batch_id)))
        except (TypeError, ValueError, AttributeError) as exc:
            raise HTTPException(422, "InterHub voucher batch_id must be a UUID") from exc
        return voucher_batch_response(normalized_batch_id)

    @app.post("/integrations/interhub/check-status", response_model=InterHubPaymentCheckOut)
    def check_interhub_payment_status(payload: InterHubPayRequestIn = Body(...), user: UserOut = Depends(require_role("owner"))):
        # Даём владельцу вручную обновить статус, не создавая повторный pay.
        _ = user
        agent_transaction_id = str(payload.agent_transaction_id or "").strip()
        result = interhub_check_status({"agent_transaction_id": agent_transaction_id})
        save_provider_result(agent_transaction_id, result, is_status_check=True)
        return InterHubPaymentCheckOut(**result)

    return refresh_pending_transactions
