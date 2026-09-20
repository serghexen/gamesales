import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { proxyRefs } from 'vue'
import WorkVoucherCatalogRouting from '../sections/WorkVoucherCatalogRouting.vue'
import WorkVoucherCatalogModal from '../sections/WorkVoucherCatalogModal.vue'
import { useVoucherCatalog } from '../useVoucherCatalog'
import { apiGet, apiPost } from '../../../api/http'

vi.mock('../../../api/http', () => ({ apiGet: vi.fn(), apiPost: vi.fn(), apiPut: vi.fn(), apiDelete: vi.fn() }))
const offers = [
  { offer_id: 20, supplier_code: 'second', supplier_name: 'Поставщик 2', service_title: 'Turkey', nominal_title: '1000 TRY', fulfillment_priority: 2, fulfillment_enabled: true, price: 2300, currency: 'RUB', stock_count: 0 },
  { offer_id: 10, supplier_code: 'interhub', supplier_name: 'Интерхаб', service_title: 'Turkey', nominal_title: '1000 TRY', fulfillment_priority: 1, fulfillment_enabled: true, price: 2400, currency: 'RUB', stock_count: null },
]
const item = { item_id: 1, name: 'PlayStation — Turkey', nominals: [] }
const nominal = { catalog_nominal_id: 11, name: '1000 TRY', fulfillment_revision: 3, offers }
let wrapper

afterEach(() => {
  // Убираем модальное окно и его блокировку прокрутки после каждого сценария.
  wrapper?.unmount()
  wrapper = null
  vi.resetAllMocks()
})

async function editor() {
  // Поставщик недоступен: настройка существующих связок всё равно должна работать по данным БД.
  const catalog = useVoucherCatalog(() => 'test-token')
  catalog.suppliers.value = [{ code: 'interhub', name: 'Интерхаб' }]
  apiGet.mockImplementation(async (path) => {
    if (path === '/voucher-catalog') return { items: [], suppliers: [], can_edit: true }
    throw new Error('Поставщик недоступен')
  })
  wrapper = mount(WorkVoucherCatalogModal, { props: { ctx: proxyRefs(catalog) }, global: { stubs: { teleport: true } } })
  await catalog.openForm(item, 'nominal', nominal)
  await flushPromises()
  return catalog
}

describe('voucher catalog supplier routing', () => {
  it('saves priority and disabled state atomically with the nominal without contacting the provider', async () => {
    const catalog = await editor()
    expect(apiGet).not.toHaveBeenCalled()
    expect(wrapper.findAll('.catalog-routing__supplier strong').map((row) => row.text())).toEqual(['Интерхаб', 'Поставщик 2'])
    await wrapper.find('[aria-label="Выше: Поставщик 2"]').trigger('click')
    await wrapper.find('[aria-label="Автовыдача: Интерхаб"]').setValue(false)
    expect(wrapper.findAll('.catalog-routing__supplier strong').map((row) => row.text())).toEqual(['Поставщик 2', 'Интерхаб'])
    expect(offers[1].fulfillment_enabled).toBe(true)
    expect(wrapper.text()).toContain('Остаток: 0')
    expect(wrapper.text()).toContain('Остаток: —')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(apiPost).toHaveBeenCalledWith('/voucher-catalog/items/1/nominals', { nominals: [{
      catalog_nominal_id: 11, name: '1000 TRY', routing: { revision: 3, offers: [{ offer_id: 20, enabled: true }, { offer_id: 10, enabled: false }] },
    }] }, { token: 'test-token' })
    expect(catalog.formOpen.value).toBe(false)
    expect(apiGet).toHaveBeenCalledTimes(1)
    expect(apiGet).toHaveBeenCalledWith('/voucher-catalog', { token: 'test-token' })
  })

  it('protects unsaved routing and preserves it when an outdated save is rejected', async () => {
    const catalog = await editor()
    apiPost.mockRejectedValueOnce(new Error('Настройки поставщиков изменились'))
    catalog.moveOffer(1, 0)
    catalog.toggleOffer(20, false)
    catalog.toggleOffer(10, false)
    await flushPromises()
    expect(wrapper.text()).toContain('Все поставщики отключены')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Настройки поставщиков изменились')
    expect(catalog.draft.routing_offers.map((row) => row.offer_id)).toEqual([20, 10])
    await wrapper.find('[aria-label="Закрыть"]').trigger('click')
    expect(catalog.closeConfirm.value).toBe(true)
    catalog.discard()
    await catalog.openForm(item, 'nominal', nominal)
    expect(catalog.draft.routing_offers.map((row) => row.offer_id)).toEqual([10, 20])
    expect(catalog.draft.routing_offers.every((row) => row.fulfillment_enabled)).toBe(true)
  })

  it('can cancel a failed provider lookup and still save priority', async () => {
    const catalog = await editor()
    catalog.moveOffer(1, 0)
    await wrapper.findAll('button').find((button) => button.text() === '+ Связать поставщика').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Поставщик недоступен')
    await wrapper.findAll('button').find((button) => button.text() === 'Отменить новую связку').trigger('click')
    expect(catalog.draft.routing_offers[0].offer_id).toBe(20)
    expect(catalog.formError.value).toBe('')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(apiPost).toHaveBeenCalledTimes(1)
  })

  it('supports dragging, ignores external drops and locks controls during save', async () => {
    wrapper = mount(WorkVoucherCatalogRouting, { props: { offers, disabled: false } })
    const transfer = { setData: vi.fn() }
    await wrapper.findAll('li')[0].trigger('drop', { dataTransfer: transfer })
    expect(wrapper.emitted('move')).toBeUndefined()
    await wrapper.findAll('.catalog-routing__handle')[0].trigger('dragstart', { dataTransfer: transfer })
    await wrapper.findAll('li')[1].trigger('dragover', { dataTransfer: transfer })
    await wrapper.findAll('li')[1].trigger('drop', { dataTransfer: transfer })
    expect(wrapper.emitted('move')).toEqual([[0, 1]])
    expect(transfer.setData).toHaveBeenCalledWith('text/plain', '20')
    await wrapper.setProps({ disabled: true })
    expect(wrapper.findAll('button, input').every((control) => control.element.disabled)).toBe(true)
    await wrapper.findAll('.catalog-routing__handle')[0].trigger('dragstart', { dataTransfer: transfer })
    await wrapper.findAll('li')[1].trigger('drop', { dataTransfer: transfer })
    expect(wrapper.emitted('move')).toHaveLength(1)
  })

})
