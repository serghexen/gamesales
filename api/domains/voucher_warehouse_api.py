"""HTTP склада: права раздела для сводки, права владельца для ключей и изменения цены."""
from datetime import date, datetime
from decimal import Decimal
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field


class WarehousePriceIn(BaseModel):
    price: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=6, allow_inf_nan=False)
    expected_updated_at: datetime | None


class WarehouseKeysIn(BaseModel):
    codes: list[str] = Field(min_length=1, max_length=1000)
    expires_at: date | None = None


def mount_voucher_warehouse_routes(app, *, service, get_current_user):
    # Склад отделён от маршрутов маркетплейсов и не запускает выдачу заказов.
    def viewer(user=Depends(get_current_user)):
        # Учитываем отдельное право на вкладку даже при прямом запросе API.
        if not service.can_view(user.role):
            raise HTTPException(403, 'Нет доступа к складу')
        return user

    def owner(user=Depends(viewer)):
        # Полные ключи и их изменение доступны владельцу, как в существующих пулах селлера.
        if user.role != 'owner':
            raise HTTPException(403, 'Управлять ключами и ценами склада может владелец')
        return user

    @app.get('/voucher-warehouse')
    def positions(user=Depends(viewer)):
        # Сводка не содержит ключей и включает пустые позиции каталога.
        return {'items': service.list_positions(), 'can_manage': user.role == 'owner'}

    @app.put('/voucher-warehouse/nominals/{nominal_id}/price')
    def price(nominal_id: int, payload: WarehousePriceIn, user=Depends(owner)):
        # Сохраняем цену всего пула, а не цену загружаемой партии.
        return service.set_price(nominal_id, payload.price, user.username, expected_updated_at=payload.expected_updated_at)

    @app.get('/voucher-warehouse/nominals/{nominal_id}/keys')
    def keys(nominal_id: int, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user=Depends(owner)):
        # Пагинация не даёт большим запасам перегружать интерфейс.
        return service.list_keys(nominal_id, page, page_size)

    @app.post('/voucher-warehouse/nominals/{nominal_id}/keys')
    def add(nominal_id: int, payload: WarehouseKeysIn, user=Depends(owner)):
        # Одна загрузка добавляет ключи к существующему SKU.
        return service.add_keys(nominal_id, payload.codes, payload.expires_at, user.username)

    @app.post('/voucher-warehouse/nominals/{nominal_id}/keys/{key_id}/reveal')
    def reveal(nominal_id: int, key_id: int, user=Depends(owner)):
        # Полный код отдаётся только по явному запросу владельца.
        return service.reveal(nominal_id, key_id)

    @app.delete('/voucher-warehouse/nominals/{nominal_id}/keys/{key_id}')
    def delete(nominal_id: int, key_id: int, user=Depends(owner)):
        # Сохраняем защиту выданных и зарезервированных ключей.
        return service.delete_keys(nominal_id, key_id)

    @app.delete('/voucher-warehouse/nominals/{nominal_id}/keys')
    def clear(nominal_id: int, through_key_id: int = Query(..., gt=0), user=Depends(owner)):
        # Очищаем свободные ключи только из снимка, который видел пользователь.
        return service.delete_keys(nominal_id, through_key_id=through_key_id)
