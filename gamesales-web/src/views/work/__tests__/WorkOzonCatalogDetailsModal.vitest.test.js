import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import WorkOzonCatalogDetailsModal from '../sections/WorkOzonCatalogDetailsModal.vue'

function buildProps() {
  // Передает карточку из снимка Ozon, чтобы проверить отображение артикула рядом с рабочими параметрами.
  return {
    showOzonCatalogDetails: true,
    closeOzonCatalogDetails: vi.fn(),
    openOzonDigitalSettings: vi.fn(),
    ozonCatalogDetails: {
      external_product_id: 5224093734,
      offer_id: 'ASAT110',
      sku: '5196324554',
      title: 'Гта 6 PS5',
      price: '6000',
      price_currency_code: 'RUB',
      available_stock: 0,
      synced_at: '2026-07-23T12:00:00Z',
    },
    ozonCatalogDetailsLoading: false,
    ozonDigitalSettings: {
      manual_stock_limit: 3,
      activation_instruction: 'Активируйте ключ в магазине.',
      support_error_message: 'Напишите в поддержку.',
      published_stock: 3,
      available_stock: 2,
      pending_orders: 1,
      delivered_orders: 4,
    },
    ozonDigitalSettingsLoading: false,
    ozonDigitalSettingsSaving: false,
    ozonDigitalOrdersSyncing: false,
    ozonDigitalOrders: [
      {
        id: 91,
        order_number: '273842',
        posting_number: '04259716-0123-1',
        sku: 5196324554,
        status: 'delivered',
        ozon_status: 'done',
        required_qty: 2,
        created_at: '2026-07-24T10:00:00Z',
        delivered_at: '2026-07-24T10:02:00Z',
        delivery_source: 'interhub',
        delivered_codes_masked: ['••••IJKL'],
      },
      { id: 92, posting_number: '04259716-0124-1', sku: 5196324554, status: 'delivered', ozon_status: 'done', required_qty: 1, delivery_source: 'manual', delivered_codes_masked: ['••••IJKL'] },
      { id: 93, posting_number: '04259716-0125-1', sku: 5196324554, status: 'delivered', ozon_status: '', required_qty: 1 },
    ],
    loadOzonDigitalSettings: vi.fn(),
    saveOzonDigitalSettings: vi.fn(),
    syncOzonDigitalOrders: vi.fn(),
    canRevealOzonDigitalCodes: true,
    revealOzonDigitalOrderCodes: vi.fn().mockResolvedValue({ ok: true, codes: ['ABCD-EFGH-IJKL'], message: '' }),
    loadOzonDigitalSupplierOperation: vi.fn().mockResolvedValue({
      ok: true,
      operation: {
        provider_code: 'interhub',
        agent_transaction_id: 'gamesales-check-123',
        provider_transaction_id: 'interhub-501',
        service_id: 802,
        nominal_id: '300',
        service_title: 'PUBG: New State - Global',
        nominal_title: '300 NC',
        amount: 100,
        state: 'paid',
        provider_message: 'Успешно',
        updated_at: '2026-07-24T10:02:00Z',
      },
      message: '',
    }),
  }
}

describe('WorkOzonCatalogDetailsModal', () => {
  it('shows the hamster while card details are loading', () => {
    const props = buildProps()
    props.ozonCatalogDetailsLoading = true
    const wrapper = mount(WorkOzonCatalogDetailsModal, {
      props,
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.find('.modal__body-overlay .wheel-and-hamster').exists()).toBe(true)
    expect(wrapper.text()).toContain('Загружаем данные карточки…')
    expect(wrapper.get('.modal__body').classes()).toContain('modal__body--loader')
    expect(wrapper.text()).not.toContain('Остаток и сообщения покупателю')
  })

  it('shows the seller offer id from the saved Ozon card', () => {
    const wrapper = mount(WorkOzonCatalogDetailsModal, {
      props: buildProps(),
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.text()).toContain('Артикул продавца')
    expect(wrapper.text()).toContain('ASAT110')
    expect(wrapper.text()).toContain('SKU')
    expect(wrapper.text()).toContain('5196324554')
    expect(wrapper.text()).not.toContain('Данные сохранены при последней синхронизации.')
    expect(wrapper.text()).not.toContain('Остаток и сообщения покупателю')
    expect(wrapper.text()).not.toContain('Все заказы по этой карточке')
    expect(wrapper.find('.ozon-catalog-details-modal__grid').text()).not.toContain('Последняя синхронизация')
    expect(wrapper.findAll('.ozon-catalog-details-modal__sale-settings textarea')).toHaveLength(0)
    expect(wrapper.find('.ozon-catalog-details-modal__stock-submit').exists()).toBe(false)
    expect(wrapper.find('.ozon-catalog-details-modal__overview-info .ozon-catalog-details-modal__grid').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Статусы заказов Ozon')
    expect(wrapper.text()).not.toContain('История заказов')
    expect(wrapper.text()).not.toContain('Заказ 273842')
    expect(wrapper.findAll('.ozon-catalog-details-modal__work-block-toggle')).toHaveLength(2)
    expect(wrapper.findAll('.ozon-catalog-details-modal__work-block-toggle').at(0).text()).toContain('Остаток и инструкции')
    expect(wrapper.findAll('.ozon-catalog-details-modal__work-block-toggle').at(1).text()).toContain('Заказы')
    expect(wrapper.text()).not.toContain('Статус не получен')
    expect(wrapper.get('[title="Ключи"]').classes()).toContain('deal-create-action-btn--save')
    expect(wrapper.find('[title="Ключи"] .ozon-catalog-details-modal__keys-icon').exists()).toBe(true)
    expect(wrapper.get('[title="К каталогу"]').classes()).toContain('deal-create-action-btn--edit')
    expect(wrapper.get('[title="Закрыть"]').classes()).toContain('deal-create-action-btn--close')
  })

  it('synchronizes orders from the opened product card', async () => {
    const props = buildProps()
    const wrapper = mount(WorkOzonCatalogDetailsModal, {
      props,
      global: { stubs: { teleport: true } },
    })

    await wrapper.findAll('.ozon-catalog-details-modal__work-block-toggle').at(1).trigger('click')

    expect(props.syncOzonDigitalOrders).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).not.toContain('История заказов')
    expect(wrapper.get('[aria-label="Синхронизировать заказы"]').classes()).toContain('ozon-catalog-details-modal__sync-orders-btn')
    expect(wrapper.findAll('.ozon-catalog-details-modal__order-history-table th').map((cell) => cell.text())).not.toContain('Выдача')
    expect(wrapper.findAll('.ozon-catalog-details-modal__order-history-table col')).toHaveLength(4)
  })

  it('loads sale settings only after expanding the corresponding block', async () => {
    const props = buildProps()
    const wrapper = mount(WorkOzonCatalogDetailsModal, {
      props,
      global: { stubs: { teleport: true } },
    })

    expect(props.loadOzonDigitalSettings).not.toHaveBeenCalled()
    await wrapper.findAll('.ozon-catalog-details-modal__work-block-toggle').at(0).trigger('click')

    expect(props.loadOzonDigitalSettings).toHaveBeenCalledWith(5224093734, { includeOrders: false })
    expect(wrapper.get('.ozon-catalog-details-modal__stock-submit').text()).toBe('Отправить')
  })

  it('filters order history by order number, SKU and date, then sorts a selected column', async () => {
    const props = buildProps()
    props.ozonDigitalOrders[1] = {
      ...props.ozonDigitalOrders[1],
      order_number: '102030',
      sku: 777,
      created_at: '2026-07-20T10:00:00Z',
    }
    const wrapper = mount(WorkOzonCatalogDetailsModal, {
      props,
      global: { stubs: { teleport: true } },
    })

    await wrapper.findAll('.ozon-catalog-details-modal__work-block-toggle').at(1).trigger('click')
    const search = wrapper.get('input[placeholder="Поиск: заказ, SKU или дата"]')
    await search.setValue('102030')
    expect(wrapper.text()).toContain('Заказ 102030')
    expect(wrapper.text()).not.toContain('Заказ 273842')

    await search.setValue('777')
    expect(wrapper.text()).toContain('Заказ 102030')
    await search.setValue('20.07.2026')
    expect(wrapper.text()).toContain('Заказ 102030')

    await search.setValue('')
    await wrapper.get('[aria-label="Сортировка по заказу"]').trigger('click')
    expect(wrapper.get('[aria-label="Сортировка по заказу"]').classes()).toContain('sort-icon--active')
    expect(wrapper.get('[aria-label="Сортировка по заказу"]').classes()).toContain('sort-icon--asc')
  })

  it('opens a supplier operation card for an Interhub order', async () => {
    const props = buildProps()
    const wrapper = mount(WorkOzonCatalogDetailsModal, {
      props,
      global: { stubs: { teleport: true } },
    })

    await wrapper.findAll('.ozon-catalog-details-modal__work-block-toggle').at(1).trigger('click')
    await wrapper.get('[aria-label="Открыть выдачу для заказа 91"]').trigger('click')
    await Promise.resolve()

    expect(props.loadOzonDigitalSupplierOperation).toHaveBeenCalledWith(props.ozonDigitalOrders[0])
    expect(wrapper.get('[aria-label="Открыть выдачу для заказа 91"]').find('svg').exists()).toBe(true)
    expect(props.revealOzonDigitalOrderCodes).toHaveBeenCalledWith(props.ozonDigitalOrders[0])
    expect(wrapper.text()).toContain('gamesales-check-123')
    expect(wrapper.text()).toContain('interhub-501')
    expect(wrapper.text()).toContain('Услуга')
    expect(wrapper.text()).toContain('PUBG: New State - Global')
    expect(wrapper.text()).toContain('Номинал')
    expect(wrapper.text()).toContain('300 NC')
    expect(wrapper.text()).toContain('ABCD-EFGH-IJKL')
    expect(wrapper.text()).toContain('Оплачено и выдано')
    expect(wrapper.get('[aria-label="Копировать Agent transaction ID"]').find('svg').exists()).toBe(true)
    expect(wrapper.get('[aria-label="Копировать операцию поставщика"]').find('svg').exists()).toBe(true)
    expect(wrapper.get('[aria-label="Закрыть операцию поставщика"]').classes()).toContain('deal-create-action-btn--close')
  })

  it('shows a manually entered key in the same delivery card without a supplier operation', async () => {
    const props = buildProps()
    const wrapper = mount(WorkOzonCatalogDetailsModal, {
      props,
      global: { stubs: { teleport: true } },
    })

    await wrapper.findAll('.ozon-catalog-details-modal__work-block-toggle').at(1).trigger('click')
    await wrapper.get('[aria-label="Открыть выдачу для заказа 92"]').trigger('click')
    await Promise.resolve()

    expect(props.loadOzonDigitalSupplierOperation).not.toHaveBeenCalled()
    expect(props.revealOzonDigitalOrderCodes).toHaveBeenCalledWith(props.ozonDigitalOrders[1])
    expect(wrapper.text()).toContain('Ручной ввод')
    expect(wrapper.text()).toContain('ABCD-EFGH-IJKL')
    expect(wrapper.text()).not.toContain('Agent transaction ID')
  })

  it('shows the hamster while a supplier operation is loading', async () => {
    const props = buildProps()
    props.loadOzonDigitalSupplierOperation = vi.fn(() => new Promise(() => {}))
    const wrapper = mount(WorkOzonCatalogDetailsModal, {
      props,
      global: { stubs: { teleport: true } },
    })

    await wrapper.findAll('.ozon-catalog-details-modal__work-block-toggle').at(1).trigger('click')
    await wrapper.get('[aria-label="Открыть выдачу для заказа 91"]').trigger('click')

    expect(wrapper.get('[aria-label="Закрыть операцию поставщика"]').classes()).toContain('deal-create-action-btn--close')
    expect(wrapper.find('.ozon-catalog-details-modal__supplier-operation-loading .wheel-and-hamster').exists()).toBe(true)
    expect(wrapper.text()).toContain('Загружаем операцию…')
  })

  it('paginates a long order history without increasing the table height', async () => {
    const props = buildProps()
    props.ozonDigitalOrders = Array.from({ length: 11 }, (_, index) => ({
      id: index + 1,
      order_number: `ORD-${index + 1}`,
      posting_number: `POST-${index + 1}`,
      sku: 5196324554,
      status: 'manual_required',
      ozon_status: 'awaiting_code',
      required_qty: 1,
    }))
    const wrapper = mount(WorkOzonCatalogDetailsModal, {
      props,
      global: { stubs: { teleport: true } },
    })

    await wrapper.findAll('.ozon-catalog-details-modal__work-block-toggle').at(1).trigger('click')
    expect(wrapper.findAll('.ozon-catalog-details-modal__order-history-table tbody tr')).toHaveLength(10)
    expect(wrapper.text()).toContain('Показаны 1–10 из 11')
    expect(wrapper.text()).not.toContain('Заказ ORD-11')

    await wrapper.get('[aria-label="Следующая страница заказов"]').trigger('click')

    expect(wrapper.findAll('.ozon-catalog-details-modal__order-history-table tbody tr')).toHaveLength(1)
    expect(wrapper.text()).toContain('Заказ ORD-11')
    expect(wrapper.text()).toContain('Показаны 11–11 из 11')
  })
})
