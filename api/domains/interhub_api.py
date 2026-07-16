from fastapi import Body, Depends


def mount_interhub_routes(
    app,
    *,
    get_current_user,
    UserOut,
    InterHubServiceListOut,
    InterHubBalanceOut,
    InterHubPaymentRequestIn,
    InterHubPaymentCheckOut,
    interhub_get_services,
    interhub_get_balance,
    interhub_calculate,
    interhub_check,
):
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
        # Рассчитываем номинал без pay, чтобы оператор видел результат до подтверждения.
        _ = user
        return InterHubPaymentCheckOut(**interhub_calculate(payload.model_dump(exclude_none=True)))

    @app.post("/integrations/interhub/check", response_model=InterHubPaymentCheckOut)
    def check_interhub_payment(payload: InterHubPaymentRequestIn = Body(...), user: UserOut = Depends(get_current_user)):
        # Проверяем реквизиты отдельным шагом, не создавая финансовую операцию.
        _ = user
        return InterHubPaymentCheckOut(**interhub_check(payload.model_dump(exclude_none=True)))
