"""HTTP-интерфейс собственного каталога; внешние ответы не задают права доступа."""

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field


class VoucherBindingIn(BaseModel):
    supplier_code: str = Field(default='interhub', min_length=1, max_length=80)
    service_id: str = Field(min_length=1, max_length=100)
    nominal_id: str = Field(min_length=1, max_length=100)


class VoucherItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=250)
    binding: VoucherBindingIn | None = None
    nominals: list['VoucherNominalIn'] = Field(default_factory=list, max_length=100)


class VoucherOfferRoutingIn(BaseModel):
    offer_id: int = Field(gt=0)
    enabled: bool = Field(strict=True)


class VoucherRoutingIn(BaseModel):
    revision: int = Field(ge=0)
    offers: list[VoucherOfferRoutingIn] = Field(max_length=1000)


class VoucherNominalIn(BaseModel):
    name: str = Field(min_length=1, max_length=250)
    catalog_nominal_id: int | None = Field(default=None, gt=0)
    routing: VoucherRoutingIn | None = None
    binding: VoucherBindingIn | None = None


class VoucherNominalsIn(BaseModel):
    nominals: list[VoucherNominalIn] = Field(min_length=1, max_length=100)


VoucherItemIn.model_rebuild()


def mount_voucher_catalog_routes(app, *, service, get_current_user):
    # Чтение доступно по правам раздела, изменение — администраторам и владельцам с этим доступом.
    def viewer(user=Depends(get_current_user)):
        # Проверяем права на сервере, в том числе при прямом вызове endpoint.
        if not service.can_view(user.role):
            raise HTTPException(403, 'Нет доступа к каталогу')
        return user

    def editor(user=Depends(viewer)):
        # Право просмотра само по себе не разрешает изменять связки поставщиков.
        if user.role not in {'admin', 'owner'}:
            raise HTTPException(403, 'Изменять каталог может администратор или владелец')
        return user

    @app.get('/voucher-catalog')
    def list_items(user=Depends(viewer)):
        # Возвращаем сохранённые снимки вместе с доступными действиями интерфейса.
        return {**service.list_items(), 'can_edit': user.role in {'admin', 'owner'}}

    @app.get('/voucher-catalog/suppliers/{supplier_code}/nominals')
    def options(supplier_code: str, user=Depends(editor)):
        # Живой список нужен только в форме создания соответствия.
        return service.options(supplier_code)

    @app.get('/voucher-catalog/nominals/{catalog_nominal_id}/warehouse')
    def warehouse_snapshot(catalog_nominal_id: int, user=Depends(editor)):
        # Предпросмотр склада доступен редакторам каталога без доступа к полным кодам.
        return service.warehouse_snapshot(catalog_nominal_id)

    @app.post('/voucher-catalog/items')
    def create_item(payload: VoucherItemIn, user=Depends(editor)):
        # Позицию можно завести без связки и дополнить её позднее.
        return service.save_item(payload.name, user.username, binding=payload.binding, nominals=payload.nominals)

    @app.put('/voucher-catalog/items/{item_id}')
    def update_item(item_id: int, payload: VoucherItemIn, user=Depends(editor)):
        # Одна форма позволяет переименовать позицию или добавить предложение поставщика.
        return service.save_item(payload.name, user.username, item_id=item_id, binding=payload.binding,
                                 nominals=payload.nominals)

    @app.post('/voucher-catalog/items/{item_id}/nominals')
    def save_nominals(item_id: int, payload: VoucherNominalsIn, user=Depends(editor)):
        # Добавляем выбранные номиналы или изменяем одну карточку, не перезаписывая имя услуги.
        return service.save_item(None, user.username, item_id=item_id, nominals=payload.nominals)

    @app.delete('/voucher-catalog/items/{item_id}')
    def delete_item(item_id: int, user=Depends(editor)):
        # Удаляем услугу со всеми собственными номиналами и соответствиями поставщиков.
        service.delete_item(item_id)
        return {'ok': True}

    @app.delete('/voucher-catalog/items/{item_id}/offers/{offer_id}')
    def unlink(item_id: int, offer_id: int, user=Depends(editor)):
        # Удаляем только соответствие, само наименование и история сохраняются.
        service.unlink(item_id, offer_id)
        return {'ok': True}

    @app.delete('/voucher-catalog/items/{item_id}/nominals/{catalog_nominal_id}')
    def delete_nominal(item_id: int, catalog_nominal_id: int, user=Depends(editor)):
        # Удаление собственного номинала отличается от отвязки одного поставщика.
        service.delete_nominal(item_id, catalog_nominal_id)
        return {'ok': True}
