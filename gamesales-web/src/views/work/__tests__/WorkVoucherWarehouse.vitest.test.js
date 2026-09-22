import { effectScope } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import WorkVoucherWarehouseSection from '../sections/WorkVoucherWarehouseSection.vue'
import WorkMarketplaceKeyPoolModal from '../sections/WorkMarketplaceKeyPoolModal.vue'
import WorkMarketplaceKeyPoolPanel from '../sections/WorkMarketplaceKeyPoolPanel.vue'
import WorkVoucherCatalogSnapshot from '../sections/WorkVoucherCatalogSnapshot.vue'
import { useVoucherWarehouse } from '../useVoucherWarehouse'
import { useVoucherCatalog } from '../useVoucherCatalog'
import { apiDelete, apiGet, apiPost, apiPut } from '../../../api/http'

vi.mock('../../../api/http', () => ({ apiGet: vi.fn(), apiPost: vi.fn(), apiPut: vi.fn(), apiDelete: vi.fn() }))
const dispose = []
const position = (id = 11) => ({ catalog_nominal_id: id, item_id: 1, service_name: 'Apple — USA', name: id === 11 ? 'USD 30' : 'USD 50', sku: `HT00000${id}`, price: null, free_count: 0, total: 0 })
const pool = (id = 11) => ({ ...position(id), items: [{ id: 1, masked_code: '••••TEST', status: 'free', expires_at: null }], through_key_id: 1, total: 1, free_count: 1, expired_count: 0, reserved_count: 0, delivered_count: 0, page: 1, page_size: 20 })

function setupHook(confirm = vi.fn().mockResolvedValue(true)) {
  // Хук получает отдельную область, как при входе на вкладку и выходе с неё.
  const scope = effectScope()
  const hook = scope.run(() => useVoucherWarehouse(() => 'token', confirm))
  dispose.push(() => scope.stop())
  return hook
}

async function setupUi(canManage = true, { expand = true, items = [position(), position(12)] } = {}) {
  // Реальные компоненты работают с фикстурами без ключей пользователя и сети.
  apiGet.mockImplementation(async (path) => path === '/voucher-warehouse' ? { items, can_manage: canManage } : pool())
  const wrapper = mount(WorkVoucherWarehouseSection, {
    attachTo: document.body,
    props: { ctx: { token: 'token', routeQuery: {}, canViewVoucherCatalogSection: true, canViewVoucherWarehouseSection: true, requestDealConfirm: vi.fn().mockResolvedValue(true) } },
    global: { stubs: { teleport: true, RouterLink: { props: ['to'], template: '<a><slot /></a>' } } },
  })
  dispose.push(() => wrapper.unmount())
  await flushPromises()
  // Рабочие сценарии начинают с явного раскрытия услуги; отдельные проверки проверяют вход.
  if (expand) {
    for (const button of wrapper.findAll('.voucher-warehouse__group-title')) await button.trigger('click')
  }
  return wrapper
}

beforeEach(() => {
  // Все чтения явно воспроизводятся через API-фикстуры.
  vi.resetAllMocks()
  apiDelete.mockResolvedValue({ removed: 1 })
  apiPut.mockResolvedValue({ price_updated_at: null })
  apiGet.mockImplementation(async (path) => path === '/voucher-warehouse' ? { items: [position(), position(12)], can_manage: true } : pool())
})
afterEach(() => {
  // Освобождаем обработчики модалок и раскрытые коды между сценариями.
  dispose.splice(0).reverse().forEach((fn) => fn())
  document.body.innerHTML = ''
})

describe('Склад', () => {
  it('groups by service ID, starts collapsed and sorts nominals numerically', async () => {
    const rows = [position(), { ...position(12), name: 'USD 100' }, { ...position(13), name: 'USD 5' },
      { ...position(14), item_id: 2, name: 'EUR 20' }]
    const wrapper = await setupUi(true, { expand: false, items: rows })
    const titles = wrapper.findAll('.voucher-warehouse__group-title')
    expect(titles).toHaveLength(2)
    expect(titles.every((title) => title.attributes('aria-expanded') === 'false')).toBe(true)
    expect(wrapper.findAll('table')).toHaveLength(0)
    expect(titles[0].text()).toContain('Номиналов: 3')
    await titles[0].trigger('click')
    expect(wrapper.findAll('.voucher-warehouse__table > tbody > tr > td:first-child > strong').map((cell) => cell.text())).toEqual(['USD 5', 'USD 30', 'USD 100'])
    expect(titles[1].attributes('aria-expanded')).toBe('false')
    expect(wrapper.text()).not.toContain('EUR 20')
  })

  it('search expands matching groups and clears back to collapsed state', async () => {
    const wrapper = await setupUi(true, { expand: false })
    const search = wrapper.get('[aria-label="Поиск по складу"]')
    await search.setValue('ht0000012')
    expect(wrapper.get('.voucher-warehouse__group-title').attributes('aria-expanded')).toBe('true')
    expect(wrapper.text()).toContain('USD 50')
    expect(wrapper.text()).not.toContain('USD 30')
    await search.setValue('')
    expect(wrapper.get('.voucher-warehouse__group-title').attributes('aria-expanded')).toBe('false')
    expect(wrapper.find('table').exists()).toBe(false)
  })

  it('collapsing a service closes its keys but preserves an edited price', async () => {
    const wrapper = await setupUi()
    await wrapper.get('[aria-label="Цена пула HT0000011"]').setValue('123')
    await wrapper.get('[aria-label="Ключи HT0000011"]').trigger('click')
    await flushPromises()
    expect(wrapper.findComponent(WorkMarketplaceKeyPoolPanel).exists()).toBe(true)
    await wrapper.get('.voucher-warehouse__group-title').trigger('click')
    await wrapper.get('.voucher-warehouse__group-title').trigger('click')
    expect(wrapper.findComponent(WorkMarketplaceKeyPoolPanel).exists()).toBe(false)
    expect(wrapper.get('[aria-label="Цена пула HT0000011"]').element.value).toBe('123')
    const fresh = await setupUi(true, { expand: false })
    expect(fresh.find('table').exists()).toBe(false)
  })

  it('shows empty catalogue positions, warehouse tab and SKU search', async () => {
    const wrapper = await setupUi()
    expect(wrapper.text()).toContain('USD 30')
    expect(wrapper.text()).toContain('USD 50')
    expect(wrapper.findComponent(WorkMarketplaceKeyPoolPanel).exists()).toBe(false)
    expect(wrapper.findAll('a').map((link) => link.text())).toEqual(['Каталог', 'Склад'])
    await wrapper.get('[aria-label="Поиск по складу"]').setValue('ht0000012')
    expect(wrapper.text()).toContain('USD 50')
    expect(wrapper.text()).not.toContain('USD 30')
  })

  it('opens a compact key list without a second accordion or duplicate stock cards', async () => {
    // Встроенный пул сразу показывает действия, не наследуя крупную карточку селлера.
    const wrapper = await setupUi()
    await wrapper.get('[aria-label="Ключи HT0000011"]').trigger('click')
    await flushPromises()
    const panel = wrapper.getComponent(WorkMarketplaceKeyPoolPanel)
    expect(panel.text()).toContain('Ключи номинала')
    expect(panel.text()).toContain('••••TEST')
    expect(panel.text()).toContain('Добавить ключи')
    expect(panel.text()).not.toContain('Список ключей')
    expect(panel.find('.marketplace-key-pool-panel__stats').exists()).toBe(false)
    expect(panel.findAll('thead th').map((head) => head.text())).toEqual(['Ключ', 'Статус', 'Активировать до', 'Действия'])
  })

  it('keeps the standard seller key panel collapsed with its own header', async () => {
    // Компактное отображение склада не меняет поведение существующих пулов маркетплейсов.
    const wrapper = mount(WorkMarketplaceKeyPoolPanel, { props: { marketplace: 'ozon', marketplaceKeyPool: pool() } })
    dispose.push(() => wrapper.unmount())
    expect(wrapper.text()).toContain('Список ключей')
    expect(wrapper.text()).not.toContain('Добавить ключи')
    await wrapper.get('.ozon-catalog-details-modal__work-block-toggle').trigger('click')
    expect(wrapper.find('.marketplace-key-pool-panel__stats').exists()).toBe(true)
    expect(wrapper.findAll('thead th').map((head) => head.text())).toContain('Заказ')
  })

  it('saves one pool price only on submit', async () => {
    const wrapper = await setupUi()
    await wrapper.get('[aria-label="Цена пула HT0000011"]').setValue('123,456789')
    expect(apiPut).not.toHaveBeenCalled()
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(apiPut).toHaveBeenCalledWith('/voucher-warehouse/nominals/11/price', { price: '123.456789', expected_updated_at: null }, { token: 'token' })
  })

  it.each([true, false])('requires confirmation after a concurrent price change; replace=%s', async (accepted) => {
    // Серверный конфликт сохраняет ввод; заменить свежую цену можно только после сравнения.
    const confirm = vi.fn().mockResolvedValue(accepted)
    const hook = setupHook(confirm)
    const first = { ...position(), price: 100, price_updated_at: '2026-09-22T09:00:00Z' }
    const fresh = { ...position(), price: 200, price_updated_at: '2026-09-22T10:00:00Z' }
    apiGet.mockResolvedValueOnce({ items: [first], can_manage: true })
    await hook.load()
    hook.prices[11] = '123'
    apiPut.mockRejectedValueOnce(Object.assign(new Error('Цена пула изменилась'), { status: 409 }))
    apiGet.mockResolvedValueOnce({ items: [fresh], can_manage: true })
    await hook.savePrice(first)
    expect(hook.error.value).toBe('Цена пула изменилась')
    expect(hook.prices[11]).toBe('123')
    expect(confirm).not.toHaveBeenCalled()
    apiPut.mockResolvedValueOnce({ price_updated_at: '2026-09-22T11:00:00Z' })
    apiGet.mockResolvedValueOnce({ items: [{ ...fresh, price: 123, price_updated_at: '2026-09-22T11:00:00Z' }], can_manage: true })
    await hook.savePrice(hook.items.value[0])
    expect(confirm).toHaveBeenCalledWith(expect.objectContaining({ message: 'Актуальная цена: 200 ₽. Заменить её на 123 ₽?' }))
    if (accepted) {
      expect(apiPut).toHaveBeenLastCalledWith('/voucher-warehouse/nominals/11/price', { price: '123', expected_updated_at: '2026-09-22T10:00:00Z' }, { token: 'token' })
      expect(apiPut).toHaveBeenCalledTimes(2)
    } else {
      expect(apiPut).toHaveBeenCalledTimes(1)
      expect(hook.prices[11]).toBe('200')
    }
  })

  it('reuses the upload form with warehouse title and separate API', async () => {
    const wrapper = await setupUi()
    await wrapper.get('[aria-label="Ключи HT0000011"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('••••TEST')
    await wrapper.findAll('button').find((button) => button.text() === 'Добавить ключи').trigger('click')
    const modal = wrapper.getComponent(WorkMarketplaceKeyPoolModal)
    expect(modal.text()).toContain('Добавить ключи · Склад')
    expect(modal.text()).toContain('HT0000011')
    await modal.get('textarea').setValue(' KEY-A\n\nKEY-B ')
    apiPost.mockResolvedValue({ added: 2, duplicates: 0 })
    await modal.get('[aria-label="Сохранить ключи"]').trigger('click')
    await flushPromises()
    expect(apiPost).toHaveBeenCalledWith('/voucher-warehouse/nominals/11/keys', { codes: ['KEY-A', 'KEY-B'], expires_at: null }, { token: 'token' })
    expect(modal.get('textarea').element.value).toBe('')
    expect(modal.text()).toContain('Добавлено: 2')
    await modal.get('[aria-label="Закрыть"]').trigger('click')
    expect(wrapper.findComponent(WorkMarketplaceKeyPoolModal).exists()).toBe(false)
    expect(document.body.style.overflow).not.toBe('hidden')
    expect(apiGet.mock.calls.every(([path]) => path.startsWith('/voucher-warehouse'))).toBe(true)
  })

  it('keeps failed upload as unsuccessful and blocks duplicate submission', async () => {
    const hook = setupHook()
    await hook.load()
    await hook.openKeys(position())
    let reject
    apiPost.mockReturnValue(new Promise((_, no) => { reject = no }))
    const first = hook.addKeys('TEST', '')
    expect(await hook.addKeys('TEST', '')).toEqual({ ok: false })
    reject(new Error('Нет соединения'))
    expect(await first).toEqual({ ok: false })
    expect(hook.keysError.value).toBe('Нет соединения')
    expect(apiPost).toHaveBeenCalledTimes(1)
  })

  it('does not expose editing or keys to a viewer', async () => {
    const wrapper = await setupUi(false)
    expect(wrapper.text()).toContain('HT0000011')
    expect(wrapper.find('[aria-label="Цена пула HT0000011"]').exists()).toBe(false)
    expect(wrapper.find('[aria-label="Ключи HT0000011"]').exists()).toBe(false)
  })

  it('distinguishes zero, unset and invalid prices and preserves other drafts', async () => {
    const hook = setupHook()
    await hook.load()
    hook.prices[12] = '77'
    hook.prices[11] = '0'
    await hook.savePrice(hook.items.value[0])
    expect(apiPut).toHaveBeenLastCalledWith('/voucher-warehouse/nominals/11/price', { price: '0', expected_updated_at: null }, { token: 'token' })
    expect(hook.prices[12]).toBe('77')
    hook.prices[11] = ''
    await hook.savePrice(hook.items.value[0])
    expect(apiPut).toHaveBeenLastCalledWith('/voucher-warehouse/nominals/11/price', { price: null, expected_updated_at: null }, { token: 'token' })
    hook.prices[11] = '-1'
    await hook.savePrice(hook.items.value[0])
    expect(apiPut).toHaveBeenCalledTimes(2)
    expect(hook.error.value).toContain('неотрицательную')
  })

  it('reloads after a mutation even when an older summary request is pending', async () => {
    // Завершившийся старый запрос не должен оставлять остаток до загрузки ключей.
    const hook = setupHook()
    await hook.load()
    await hook.openKeys(position())
    let resolveOld
    apiGet.mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve }))
    const old = hook.load()
    apiPost.mockResolvedValue({ added: 2, duplicates: 0 })
    apiGet.mockImplementation(async (path) => path === '/voucher-warehouse'
      ? { items: [{ ...position(), free_count: 3, total: 3 }], can_manage: true } : { ...pool(), free_count: 3, total: 3 })
    const added = hook.addKeys('TEST-A\nTEST-B', '')
    await flushPromises()
    resolveOld({ items: [position()], can_manage: true })
    await old
    await added
    expect(hook.items.value[0].free_count).toBe(3)
    expect(hook.pool.value.free_count).toBe(3)
  })

  it('ignores late list and reveal after switching SKU', async () => {
    const hook = setupHook()
    await hook.load()
    let resolveOld
    apiGet.mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve }))
    const first = hook.openKeys(position())
    apiGet.mockResolvedValueOnce(pool(12))
    await hook.openKeys(position(12))
    resolveOld(pool(11))
    await first
    expect(hook.pool.value.catalog_nominal_id).toBe(12)
    let resolveCode
    apiPost.mockImplementationOnce(() => new Promise((resolve) => { resolveCode = resolve }))
    const reveal = hook.reveal({ id: 1 })
    hook.closeKeys()
    resolveCode({ code: 'PRIVATE-TEST' })
    await reveal
    expect(hook.revealed).toEqual({})
  })

  it('confirms deletion and locks the selected SKU while confirmation is pending', async () => {
    let accept
    const hook = setupHook(vi.fn(() => new Promise((resolve) => { accept = resolve })))
    await hook.load()
    await hook.openKeys(position())
    const pending = hook.remove({ id: 1, masked_code: '••••TEST' })
    await hook.openKeys(position(12))
    expect(hook.selectedId.value).toBe(11)
    expect(apiDelete).not.toHaveBeenCalled()
    accept(false)
    await pending
    expect(apiDelete).not.toHaveBeenCalled()
    const again = hook.remove()
    // Даже обновлённый ответ во время подтверждения не расширяет выбранную границу удаления.
    hook.pool.value.through_key_id = 9
    accept(true)
    await again
    expect(apiDelete).toHaveBeenCalledWith('/voucher-warehouse/nominals/11/keys?through_key_id=1', { token: 'token' })
    expect(hook.keysOk.value).toBe('Удалено ключей: 1')
  })

  it('allows expired-key cleanup in the warehouse variant of shared panel', () => {
    const wrapper = mount(WorkMarketplaceKeyPoolPanel, { props: { marketplace: 'warehouse', initiallyOpen: true, allowExpiredDeletion: true,
      marketplaceKeyPool: { ...pool(), free_count: 0, expired_count: 1, items: [{ id: 1, status: 'expired', masked_code: '••••TEST' }] } } })
    dispose.push(() => wrapper.unmount())
    expect(wrapper.get('[aria-label="Удалить ••••TEST"]').exists()).toBe(true)
    expect(wrapper.get('.marketplace-key-pool-modal__delete-free').element.disabled).toBe(false)
  })
})

describe('Склад в каталоге', () => {
  it.each([true, false])('blocks linking an existing warehouse even when enabled=%s', async (enabled) => {
    // Выключение или нулевой остаток не превращают существующую связку в новую.
    const catalog = useVoucherCatalog(() => 'token')
    catalog.suppliers.value = [{ code: 'interhub', name: 'Интерхаб' }, { code: 'warehouse', name: 'Склад' }]
    const nominal = { catalog_nominal_id: 11, name: 'USD 30', offers: [{ offer_id: 4, supplier_code: 'warehouse', fulfillment_enabled: enabled, stock_count: 0 }] }
    const item = { item_id: 1, name: 'Apple', nominals: [nominal] }
    await catalog.openForm(item, 'nominal', nominal)
    expect(catalog.availableSuppliers.value.find((row) => row.code === 'warehouse')).toMatchObject({ disabled: true, name: 'Склад · уже связан' })
    catalog.draft.supplier_code = 'warehouse'
    await catalog.showBinding()
    expect(apiGet).not.toHaveBeenCalled()
    expect(catalog.formError.value).toContain('Склад уже связан')
    catalog.draft.link_nominal_id = '11'
    await catalog.save()
    expect(apiPost).not.toHaveBeenCalled()
    expect(catalog.formError.value).toContain('уже добавлена')
    // После настоящей отвязки обновлённая карточка разрешает снова связать тот же пул.
    await catalog.openForm(item, 'nominal', { ...nominal, offers: [] })
    expect(catalog.availableSuppliers.value.find((row) => row.code === 'warehouse').disabled).not.toBe(true)
  })

  it('allows binding an empty warehouse with no price and does not duplicate a pending save', async () => {
    // Пустой пул можно настроить заранее; повторный клик не отправляет вторую запись.
    const catalog = useVoucherCatalog(() => 'token')
    await catalog.openForm({ item_id: 1, name: 'Apple' }, 'nominal', { catalog_nominal_id: 11, name: 'USD 30', offers: [] })
    catalog.draft.supplier_code = 'warehouse'
    apiGet.mockResolvedValueOnce({ catalog_nominal_id: 11, price: null, free_count: 0 })
    await catalog.showBinding()
    expect(catalog.warehousePreview.value.free_count).toBe(0)
    expect(catalog.draft.link_nominal_id).toBe('11')
    let finish
    apiPost.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
    apiGet.mockResolvedValueOnce({ items: [], suppliers: [], can_edit: true })
    const pending = catalog.save()
    await catalog.save()
    expect(apiPost).toHaveBeenCalledTimes(1)
    finish({})
    await pending
    expect(catalog.formOpen.value).toBe(false)
  })

  it('cancels a pending warehouse preview without resurrecting its binding', async () => {
    // Отмена связки должна отменять и запоздалое автозаполнение склада.
    const catalog = useVoucherCatalog(() => 'token')
    await catalog.openForm({ item_id: 1, name: 'Apple' }, 'nominal', { catalog_nominal_id: 11, name: 'USD 30', offers: [] })
    catalog.draft.supplier_code = 'warehouse'
    let finish
    apiGet.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
    const pending = catalog.showBinding()
    catalog.hideBinding()
    finish({ price: 0, free_count: 5 })
    await pending
    expect(catalog.draft.link_nominal_id).toBe('')
    expect(catalog.warehousePreview.value).toBeNull()
    expect(catalog.bindingOpen.value).toBe(false)
    expect(catalog.optionsLoading.value).toBe(false)
  })

  it('discards a late warehouse preview after choosing a different supplier', async () => {
    // Ответ склада не должен подставить его номинал в форму другого поставщика.
    const catalog = useVoucherCatalog(() => 'token')
    await catalog.openForm({ item_id: 1, name: 'Apple' }, 'nominal', { catalog_nominal_id: 11, name: 'USD 30', offers: [] })
    catalog.draft.supplier_code = 'warehouse'
    let finish
    apiGet.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
    const pending = catalog.showBinding()
    catalog.draft.supplier_code = 'interhub'
    apiGet.mockResolvedValueOnce([])
    await catalog.loadOptions()
    finish({ free_count: 5, price: 100 })
    await pending
    expect(catalog.warehousePreview.value).toBeNull()
    expect(catalog.draft.link_nominal_id).toBe('')
  })

  it('links current SKU without supplier requests and retains priorities', async () => {
    const catalog = useVoucherCatalog(() => 'token')
    catalog.suppliers.value = [{ code: 'interhub', name: 'Интерхаб' }, { code: 'warehouse', name: 'Склад' }]
    const nominal = { catalog_nominal_id: 11, name: 'USD 30', sku: 'HT0000011', fulfillment_revision: 2, offers: [{ offer_id: 4, fulfillment_enabled: true, fulfillment_priority: 1 }] }
    const item = { item_id: 1, name: 'Apple', nominals: [nominal] }
    await catalog.openForm(item, 'nominal', nominal)
    expect(catalog.availableSuppliers.value).toHaveLength(2)
    catalog.draft.supplier_code = 'warehouse'
    apiGet.mockResolvedValueOnce({ catalog_nominal_id: 11, sku: 'HT0000011', price: 100, free_count: 3 })
    await catalog.showBinding()
    expect(apiGet).toHaveBeenCalledWith('/voucher-catalog/nominals/11/warehouse', { token: 'token' })
    expect(catalog.warehousePreview.value.free_count).toBe(3)
    apiGet.mockResolvedValue({ items: [item], suppliers: [], can_edit: true })
    await catalog.save()
    expect(apiPost).toHaveBeenCalledWith('/voucher-catalog/items/1/nominals', { nominals: [{ catalog_nominal_id: 11, name: 'USD 30', routing: { revision: 2, offers: [{ offer_id: 4, enabled: true }] }, binding: { supplier_code: 'warehouse', service_id: '1', nominal_id: '11' } }] }, { token: 'token' })
    await catalog.openForm(item, 'nominals')
    expect(catalog.availableSuppliers.value.some((supplier) => supplier.code === 'warehouse')).toBe(false)
  })

  it('does not mark manual warehouse price as stale', () => {
    const wrapper = mount(WorkVoucherCatalogSnapshot, { props: { kind: 'price', now: Date.parse('2026-09-22'), offer: { supplier_code: 'warehouse', price: 0, currency: 'RUB', price_updated_at: '2020-01-01' } } })
    dispose.push(() => wrapper.unmount())
    expect(wrapper.text()).not.toContain('требует обновления')
    expect(wrapper.text()).toContain('0,00')
  })

  it('shared seller form keeps its original label without override', () => {
    const wrapper = mount(WorkMarketplaceKeyPoolModal, { props: { showMarketplaceKeyPool: true, closeMarketplaceKeyPool: vi.fn(), marketplaceKeyPool: { marketplace: 'ozon' }, marketplaceKeyPoolLoading: false, marketplaceKeyPoolSaving: false, addMarketplaceKeyPoolKeys: vi.fn() }, global: { stubs: { teleport: true } } })
    dispose.push(() => wrapper.unmount())
    expect(wrapper.text()).toContain('Добавить ключи · Ozon')
    expect(wrapper.text()).not.toContain('Склад')
  })
})
