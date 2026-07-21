import json
import threading
import time
import uuid

from fastapi import Body, Depends, HTTPException
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
