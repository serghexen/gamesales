from typing import Optional

from fastapi import Body, Depends, HTTPException


def mount_ns_gift_routes(
    app,
    *,
    get_current_user,
    UserOut,
    NsGiftBalanceOut,
    NsGiftServiceListOut,
    NsGiftOrderIn,
    NsGiftOrderOut,
    ns_gift_get_balance,
    ns_gift_get_categories,
    ns_gift_get_services,
    ns_gift_get_steam_currency_rate,
    ns_gift_get_steam_amount,
    ns_gift_create_order_and_pay,
):
    @app.get("/integrations/ns-gift/balance", response_model=NsGiftBalanceOut)
    def get_ns_gift_balance(user: UserOut = Depends(get_current_user)):
        # Отдаем текущий баланс кабинета NS Gift для оперативной проверки оператором.
        payload = ns_gift_get_balance()
        return NsGiftBalanceOut(
            balance=float(payload.get("balance") or 0.0),
            currency=str(payload.get("currency") or "RUB").upper(),
        )

    @app.get("/integrations/ns-gift/services", response_model=NsGiftServiceListOut)
    def list_ns_gift_services(category_id: Optional[int] = None, user: UserOut = Depends(get_current_user)):
        # Возвращаем каталог NS Gift, чтобы можно было показать его в интерфейсе.
        items = ns_gift_get_services(category_id)
        return NsGiftServiceListOut(total=len(items), items=items)

    @app.get("/integrations/ns-gift/categories", response_model=list[dict])
    def list_ns_gift_categories(user: UserOut = Depends(get_current_user)):
        # Возвращаем список категорий NS Gift для фильтрации каталога в UI.
        return ns_gift_get_categories()

    @app.get("/integrations/ns-gift/steam/currency-rate", response_model=dict)
    def get_ns_gift_steam_currency_rate(user: UserOut = Depends(get_current_user)):
        # Возвращаем курсы валют Steam для отдельной формы category_id=68.
        return ns_gift_get_steam_currency_rate()

    @app.get("/integrations/ns-gift/steam/amount", response_model=dict)
    def get_ns_gift_steam_amount(amount: float, user: UserOut = Depends(get_current_user)):
        # Возвращаем расчет суммы Steam по введенному amount.
        return ns_gift_get_steam_amount(amount)

    @app.post("/integrations/ns-gift/orders", response_model=NsGiftOrderOut)
    def create_ns_gift_order(payload: NsGiftOrderIn = Body(...), user: UserOut = Depends(get_current_user)):
        # Создаем заказ и по флагу auto_pay сразу запускаем оплату на стороне NS Gift.
        service_id = int(payload.service_id or 0)
        if service_id <= 0:
            raise HTTPException(400, "service_id is required")
        quantity = float(payload.quantity or 1.0)
        if quantity <= 0:
            raise HTTPException(400, "quantity must be > 0")

        response = ns_gift_create_order_and_pay(service_id, quantity, payload.data or "", bool(payload.auto_pay))
        return NsGiftOrderOut(
            custom_id=str(response.get("custom_id") or ""),
            auto_pay=bool(response.get("auto_pay")),
            created=response.get("created") if isinstance(response, dict) else {},
            paid=response.get("paid") if isinstance(response, dict) else {},
        )
