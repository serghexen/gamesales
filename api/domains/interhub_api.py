import json
import threading
import time
import uuid
from datetime import date

from fastapi import Body, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from domains.interhub_price_cache import build_interhub_prices_xlsx, collect_price_targets


PENDING_STATUS = 1


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

    def save_checked_transaction(payload: dict, result: dict, username: str) -> None:
        # Фиксируем успешный check до pay, чтобы повторный клик не стал новой оплатой.
        if not bool(result.get("success")):
            return
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO app.interhub_transactions(
                      agent_transaction_id, service_id, account, amount, request_params,
                      state, provider_status, provider_message, provider_transaction_id,
                      provider_response, created_by, updated_at
                    ) VALUES (%s, %s, %s, %s, %s::jsonb, 'checked', %s, %s, %s, %s::jsonb, %s, now())
                    ON CONFLICT (agent_transaction_id) DO UPDATE SET
                      service_id=EXCLUDED.service_id,
                      account=EXCLUDED.account,
                      amount=EXCLUDED.amount,
                      request_params=EXCLUDED.request_params,
                      provider_status=EXCLUDED.provider_status,
                      provider_message=EXCLUDED.provider_message,
                      provider_transaction_id=EXCLUDED.provider_transaction_id,
                      provider_response=EXCLUDED.provider_response,
                      updated_at=now()
                    WHERE app.interhub_transactions.state='checked'
                    """,
                    (
                        str(payload["agent_transaction_id"]), int(payload["service_id"]), str(payload.get("account") or ""),
                        float(payload.get("amount") or 0), json.dumps(payload.get("params") or {}), int(result.get("status") or 0),
                        str(result.get("message") or ""), str(result.get("transaction_id") or ""), json.dumps(result.get("raw") or {}), username,
                    ),
                )
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
                    WHERE agent_transaction_id=%s
                    """,
                    (message[:2000], agent_transaction_id),
                )
            conn.commit()

    def save_provider_result(agent_transaction_id: str, result: dict, *, is_status_check: bool = False) -> None:
        # Сохраняем финальный ответ и ключ сразу, потому что check_status может не повторить gift_code.
        state = response_state(result)
        params = result.get("params") if isinstance(result.get("params"), dict) else {}
        gift_code = str(params.get("gift_code") or "")
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT state, status_check_attempts FROM app.interhub_transactions WHERE agent_transaction_id=%s", (agent_transaction_id,))
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
            conn.commit()

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
        }

    def save_price_calculation(batch_id: str, target: dict, result: dict, username: str) -> None:
        # Сохраняем каждый calculate, чтобы ошибки поставщика не терялись после закрытия страницы.
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO app.interhub_price_calculations(
                      batch_id, service_id, service_title, category, service_type, nominal_id, nominal_title,
                      success, provider_status, provider_message, fixed_amount, provider_response, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        batch_id, target["service_id"], target["service_title"], target["category"], target["service_type"],
                        target["nominal_id"], target["nominal_title"], bool(result.get("success")),
                        int(result.get("status") or 0), str(result.get("message") or ""),
                        float(result.get("fixed_amount") or 0), json.dumps(result.get("raw") or {}), username,
                    ),
                )
            conn.commit()

    def run_price_refresh(job_id: str, username: str) -> None:
        # Запускаем calculate последовательно с паузой, чтобы не создавать всплеск нагрузки у поставщика.
        try:
            targets = collect_price_targets(interhub_get_services())
            with price_jobs_lock:
                job = price_jobs[job_id]
                job["total"] = len(targets)
                if not targets:
                    job["state"] = "completed"
                    job["message"] = "В каталоге нет активных номиналов Voucher и Top-up-fixed"
                    return
            for index, target in enumerate(targets):
                if index:
                    time.sleep(max(0, int(price_calculate_delay_ms)) / 1000)
                try:
                    result = interhub_calculate({
                        "service_id": target["service_id"],
                        "account": "",
                        "agent_transaction_id": f"gamesales-price-{job_id[:8]}-{index + 1}",
                        "params": {"nominal": target["nominal_id"]},
                    })
                except Exception as exc:
                    # Фиксируем сетевую или контрактную ошибку отдельно от корректного ответа InterHub.
                    result = {"success": False, "status": -1, "message": str(getattr(exc, "detail", exc)), "raw": {}}
                save_price_calculation(job["batch_id"], target, result, username)
                with price_jobs_lock:
                    job["processed"] += 1
                    if result.get("success"):
                        job["successes"] += 1
                    else:
                        job["errors"] += 1
            with price_jobs_lock:
                job["state"] = "completed"
                job["message"] = "Расчёт цен завершён"
        except Exception as exc:
            with price_jobs_lock:
                job = price_jobs[job_id]
                job["state"] = "failed"
                job["message"] = f"Не удалось запустить расчёт: {getattr(exc, 'detail', exc)}"

    def read_latest_prices() -> list[dict]:
        # Берём последнюю успешную цену по номиналу, не затирая её временной ошибкой calculate.
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT ON (service_id, nominal_id)
                      service_id, service_title, category, service_type, nominal_id, nominal_title,
                      fixed_amount, calculated_at, provider_response
                    FROM app.interhub_price_calculations
                    WHERE success=true
                    ORDER BY service_id, nominal_id, calculated_at DESC, id DESC
                    """
                )
                rows = cur.fetchall()
        keys = ["service_id", "service_title", "category", "service_type", "nominal_id", "nominal_title", "fixed_amount", "calculated_at", "provider_response"]
        return [dict(zip(keys, row)) for row in rows]

    def read_latest_batch_errors() -> tuple[str, list[dict]]:
        # Выгружаем ошибки именно последнего запуска, чтобы их можно было сразу отправить InterHub.
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT batch_id FROM app.interhub_price_calculations ORDER BY calculated_at DESC, id DESC LIMIT 1")
                batch_row = cur.fetchone()
                if not batch_row:
                    return "", []
                batch_id = str(batch_row[0])
                cur.execute(
                    """
                    SELECT service_id, service_title, service_type, nominal_id, nominal_title,
                           provider_status, provider_message, calculated_at, provider_response
                    FROM app.interhub_price_calculations
                    WHERE batch_id=%s AND success=false
                    ORDER BY service_title, nominal_title
                    """,
                    (batch_id,),
                )
                rows = cur.fetchall()
        keys = ["service_id", "service_title", "service_type", "nominal_id", "nominal_title", "provider_status", "provider_message", "calculated_at", "provider_response"]
        return batch_id, [dict(zip(keys, row)) for row in rows]

    @app.get("/integrations/interhub/services", response_model=InterHubServiceListOut)
    def list_interhub_services(user: UserOut = Depends(get_current_user)):
        # Отдаём нормализованный каталог только авторизованным пользователям приложения.
        _ = user
        items = interhub_get_services()
        return InterHubServiceListOut(total=len(items), items=items)

    @app.get("/integrations/interhub/balance", response_model=InterHubBalanceOut)
    def get_interhub_balance(user: UserOut = Depends(get_current_user)):
        # Отдаём баланс агентского счёта без раскрытия токена внешнего провайдера.
        _ = user
        return InterHubBalanceOut(**interhub_get_balance())

    @app.get("/integrations/interhub/transactions/paid")
    def list_paid_interhub_transactions(
        date_from: date | None = Query(default=None),
        date_to: date | None = Query(default=None),
        user: UserOut = Depends(get_current_user),
    ):
        # Выдаём только завершённые продажи и ограничиваем выборку периодом без передачи SQL из браузера.
        _ = user
        if date_from and date_to and date_from > date_to:
            raise HTTPException(422, "Дата «с» не может быть позже даты «по»")
        clauses = ["state='paid'"]
        params: list[object] = []
        if date_from:
            clauses.append("created_at >= %s")
            params.append(date_from)
        if date_to:
            clauses.append("created_at < %s + interval '1 day'")
            params.append(date_to)
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT history_transaction.service_id,
                           COALESCE(service_calculation.service_title, ''),
                           COALESCE(history_transaction.request_params->>'nominal', ''),
                           COALESCE(nominal_calculation.nominal_title, ''),
                           history_transaction.amount, history_transaction.gift_code, history_transaction.created_at
                    FROM app.interhub_transactions AS history_transaction
                    LEFT JOIN LATERAL (
                      SELECT service_title
                      FROM app.interhub_price_calculations
                      WHERE success=true AND service_id=history_transaction.service_id
                      ORDER BY calculated_at DESC, id DESC
                      LIMIT 1
                    ) AS service_calculation ON true
                    LEFT JOIN LATERAL (
                      SELECT nominal_title
                      FROM app.interhub_price_calculations
                      WHERE success=true
                        AND service_id=history_transaction.service_id
                        AND nominal_id::text=COALESCE(history_transaction.request_params->>'nominal', '')
                      ORDER BY calculated_at DESC, id DESC
                      LIMIT 1
                    ) AS nominal_calculation ON true
                    WHERE {' AND '.join(f'history_transaction.{clause}' for clause in clauses)}
                    ORDER BY history_transaction.created_at DESC, history_transaction.agent_transaction_id DESC
                    LIMIT 5000
                    """,
                    params,
                )
                rows = cur.fetchall()
        # Преобразуем сумму в float, чтобы контракт JSON оставался одинаковым для PostgreSQL numeric.
        return {
            "items": [
                {
                    "service_id": int(row[0]),
                    "service_title": str(row[1] or ''),
                    "nominal": str(row[2] or ''),
                    "nominal_title": str(row[3] or ''),
                    "price": float(row[4] or 0),
                    "gift_code": str(row[5] or ''),
                    "created_at": row[6],
                }
                for row in rows
            ]
        }

    @app.post("/integrations/interhub/prices/refresh")
    def refresh_interhub_prices(user: UserOut = Depends(require_role("owner"))):
        # Запускаем один фоновый обход цен, чтобы владелец не мог случайно задвоить запросы.
        with price_jobs_lock:
            if any(job["state"] == "running" for job in price_jobs.values()):
                raise HTTPException(409, "InterHub price refresh is already running")
            job_id = uuid.uuid4().hex
            job = {
                "job_id": job_id, "batch_id": uuid.uuid4().hex, "state": "running", "total": 0,
                "processed": 0, "successes": 0, "errors": 0, "message": "Загружаем каталог InterHub",
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
        # Показываем оператору ранее сохранённые закупочные цены рядом с номиналом.
        _ = user
        return {"items": read_latest_prices()}

    @app.get("/integrations/interhub/prices/export")
    def export_interhub_prices(user: UserOut = Depends(require_role("owner"))):
        # Формируем Excel только из нашей базы, не вызывая поставщика повторно при каждой выгрузке.
        _ = user
        batch_id, errors = read_latest_batch_errors()
        prices = read_latest_prices()
        if not prices and not errors:
            raise HTTPException(404, "InterHub prices have not been calculated yet")
        content = build_interhub_prices_xlsx(prices, errors)
        filename = f"interhub-prices-{batch_id[:8] or 'cache'}.xlsx"
        return StreamingResponse(
            iter([content]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.post("/integrations/interhub/calculate", response_model=InterHubPaymentCheckOut)
    def calculate_interhub_payment(payload: InterHubPaymentRequestIn = Body(...), user: UserOut = Depends(get_current_user)):
        # Рассчитываем фиксированный номинал до обязательной проверки будущей оплаты.
        _ = user
        return InterHubPaymentCheckOut(**interhub_calculate(payload.model_dump(exclude_none=True)))

    @app.post("/integrations/interhub/check", response_model=InterHubPaymentCheckOut)
    def check_interhub_payment(payload: InterHubPaymentRequestIn = Body(...), user: UserOut = Depends(get_current_user)):
        # Проверяем реквизиты и сохраняем будущую операцию до подтверждения владельцем.
        request_data = payload.model_dump(exclude_none=True)
        result = interhub_check(request_data)
        save_checked_transaction(request_data, result, str(user.username or ""))
        return InterHubPaymentCheckOut(**result)

    @app.post("/integrations/interhub/pay", response_model=InterHubPaymentCheckOut)
    def pay_interhub_payment(payload: InterHubPayRequestIn = Body(...), user: UserOut = Depends(require_role("owner"))):
        # Атомарно резервируем одиночную оплату до внешнего pay, чтобы два параллельных запроса не списали деньги дважды.
        _ = user
        agent_transaction_id = str(payload.agent_transaction_id or "").strip()
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
