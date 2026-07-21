from __future__ import annotations

import json

from fastapi import Body, Depends, HTTPException


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
    interhub_get_services,
    interhub_get_balance,
    interhub_calculate,
    interhub_check,
    interhub_pay,
    interhub_check_status,
):
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

    def save_provider_result(agent_transaction_id: str, result: dict, *, is_status_check: bool = False) -> None:
        # Сохраняем финальный ответ и ключ сразу, потому что check_status может не повторить gift_code.
        state = response_state(result)
        params = result.get("params") if isinstance(result.get("params"), dict) else {}
        gift_code = str(params.get("gift_code") or "")
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT status_check_attempts FROM app.interhub_transactions WHERE agent_transaction_id=%s", (agent_transaction_id,))
                row = cur.fetchone()
                current_attempts = int(row[0] or 0) if row else 0
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

    def refresh_pending_transactions() -> None:
        # Выбираем просроченные processing-операции и опрашиваем InterHub не чаще раза в пять минут.
        with psycopg.connect(DB_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH due AS (
                      SELECT agent_transaction_id FROM app.interhub_transactions
                      WHERE state='processing' AND next_status_check_at <= now()
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
        # Списание доступно только владельцу после успешного check той же операции.
        _ = user
        agent_transaction_id = str(payload.agent_transaction_id or "").strip()
        ensure_checked_transaction(agent_transaction_id)
        result = interhub_pay({"agent_transaction_id": agent_transaction_id})
        save_provider_result(agent_transaction_id, result)
        return InterHubPaymentCheckOut(**result)

    @app.post("/integrations/interhub/check-status", response_model=InterHubPaymentCheckOut)
    def check_interhub_payment_status(payload: InterHubPayRequestIn = Body(...), user: UserOut = Depends(require_role("owner"))):
        # Даём владельцу вручную обновить статус, не создавая повторный pay.
        _ = user
        agent_transaction_id = str(payload.agent_transaction_id or "").strip()
        result = interhub_check_status({"agent_transaction_id": agent_transaction_id})
        save_provider_result(agent_transaction_id, result, is_status_check=True)
        return InterHubPaymentCheckOut(**result)

    return refresh_pending_transactions
