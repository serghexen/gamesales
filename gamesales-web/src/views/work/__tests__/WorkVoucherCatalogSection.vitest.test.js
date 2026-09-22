import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DOMWrapper, flushPromises, mount } from '@vue/test-utils'
import WorkVoucherCatalogSection from '../sections/WorkVoucherCatalogSection.vue'
import { useVoucherCatalog } from '../useVoucherCatalog'
import { apiDelete, apiGet, apiPost, apiPut } from '../../../api/http'

vi.mock('../../../api/http', () => ({ apiGet: vi.fn(), apiPost: vi.fn(), apiPut: vi.fn(), apiDelete: vi.fn() }))
const suppliers = [{ code: 'interhub', name: 'Интерхаб' }]
const options = [
  { service_id: 10, service_title: 'PlayStation Turkey', nominal_id: 1, nominal_title: '500 TRY' },
  { service_id: 10, service_title: 'PlayStation Turkey', nominal_id: 2, nominal_title: '1000 TRY' },
  { service_id: 20, service_title: 'Steam', nominal_id: 3, nominal_title: 'USD 10' },
]
let wrappers = []

function snapshot(overrides = {}) {
  // Услуга содержит собственный номинал, а снимок цены и остатка принадлежит его предложению.
  return { item_id: 1, name: 'PlayStation — Turkey', nominals: [{ catalog_nominal_id: 11, name: '500 TRY', sku: 'HT0000001', offers: [{
    offer_id: 2, supplier_code: 'interhub', supplier_name: 'Интерхаб', service_id: '10', nominal_id: '1',
    service_title: 'PlayStation Turkey', nominal_title: '500 TRY', price: 0, currency: 'RUB', stock_count: null,
    price_updated_at: '2026-09-20T06:00:00Z', stock_updated_at: null,
    price_error: '', stock_error: 'Не удалось получить остатки', stock_checked_at: '2026-09-20T07:00:00Z', ...overrides,
  }] }] }
}

async function setup({ items = [snapshot()], canEdit = true, teleport = true, expand = true } = {}) {
  // Открытие таблицы читает БД, а модальная форма отдельно запрашивает номиналы поставщика.
  apiGet.mockImplementation(async (path) => path === '/voucher-catalog' ? { items, suppliers, can_edit: canEdit } : options)
  const wrapper = mount(WorkVoucherCatalogSection, {
    attachTo: document.body,
    props: { ctx: { token: 'test-token', routeQuery: {}, canViewFinanceSection: true, canViewVoucherCatalogSection: true } },
    global: { stubs: { teleport, RouterLink: { props: ['to'], template: '<a><slot /></a>' } } },
  })
  wrappers.push(wrapper)
  await flushPromises()
  // Сценарии работы с номиналами начинают с явного раскрытия услуги пользователем.
  if (expand) {
    for (const title of wrapper.findAll('.voucher-catalog__group-title')) await title.trigger('click')
  }
  return wrapper
}

async function chooseService(wrapper, id) {
  // Выбираем услугу через пользовательское меню, проверяя передачу значения в форму.
  await wrapper.get('[data-test="catalog-service"]').trigger('click')
  const title = id === '10' ? 'PlayStation Turkey' : 'Steam'
  const option = wrapper.findAll('[role="option"]').find((row) => row.text() === title)
  await option.trigger('click')
}

function button(wrapper, label) {
  // Действие доступно по тексту или по подписи иконки для экранного диктора.
  return wrapper.findAll('button').find((item) => item.text() === label || item.attributes('aria-label') === label)
}

beforeEach(() => {
  // Фиксированная дата позволяет проверить свежесть сохранённых снимков.
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-09-20T07:30:00Z'))
  vi.resetAllMocks()
})
afterEach(() => {
  // Каждая модалка освобождает фокус, прокрутку и таймеры независимо от исхода теста.
  wrappers.forEach((wrapper) => wrapper.unmount())
  wrappers = []
  vi.useRealTimers()
  vi.unstubAllEnvs()
})

describe('WorkVoucherCatalogSection', () => {
  it('starts with all services collapsed and resets nested expansion when returning to the catalog', async () => {
    const items = [snapshot(), { item_id: 2, name: 'Steam', nominals: [] }]
    const wrapper = await setup({ items, expand: false })
    expect(wrapper.findAll('.voucher-catalog__group-title').every((title) => title.attributes('aria-expanded') === 'false')).toBe(true)
    expect(wrapper.find('.catalog-nominal').exists()).toBe(false)
    await wrapper.find('.voucher-catalog__group-title').trigger('click')
    expect(wrapper.find('.catalog-nominal__expand').attributes('aria-expanded')).toBe('false')
    await wrapper.find('.catalog-nominal__expand').trigger('click')
    expect(wrapper.find('.catalog-nominal__details').exists()).toBe(true)
    await button(wrapper, 'Обновить список').trigger('click')
    await flushPromises()
    expect(wrapper.find('.catalog-nominal__details').exists()).toBe(true)
    // WorkView размонтирует каталог при переходе на другую вкладку через v-if.
    wrapper.unmount()
    wrappers = []
    const reopened = await setup({ items, expand: false })
    expect(reopened.findAll('.voucher-catalog__group-title').every((title) => title.attributes('aria-expanded') === 'false')).toBe(true)
    expect(reopened.find('.catalog-nominal').exists()).toBe(false)
    await reopened.find('.voucher-catalog__group-title').trigger('click')
    expect(reopened.find('.catalog-nominal__expand').attributes('aria-expanded')).toBe('false')
    expect(reopened.find('.catalog-nominal__details').exists()).toBe(false)
  })

  it('shows only real supplier settings without demo controls even in development', async () => {
    vi.stubEnv('DEV', true)
    const wrapper = await setup()
    await flushPromises()
    expect(wrapper.find('[data-test="catalog-open-demo"]').exists()).toBe(false)
    await wrapper.find('.voucher-catalog__nominal').trigger('click')
    await flushPromises()
    expect(wrapper.text()).not.toContain('Демо порядка')
    expect(wrapper.text()).not.toContain('Демо-поставщик')
    expect(wrapper.findAll('.catalog-routing__row')).toHaveLength(1)
    expect(wrapper.find('.voucher-catalog-editor__save').element.disabled).toBe(false)
    expect(apiGet).toHaveBeenCalledTimes(1)
  })

  it('uses round deal action buttons in the header and an icon-only refresh button', async () => {
    // Настоящий Teleport позволяет проверить отправку формы кнопкой из шапки окна.
    await setup({ teleport: false })
    const wrapper = new DOMWrapper(document.body)
    await flushPromises()
    const refresh = button(wrapper, 'Обновить список')
    expect(refresh.classes()).toContain('account-refresh-btn')
    expect(refresh.text()).toBe('')
    await button(wrapper, 'Изменить услугу').trigger('click')
    await flushPromises()
    const save = button(wrapper, 'Сохранить')
    const close = button(wrapper, 'Закрыть')
    expect(save.element.closest('.modal__head')).not.toBeNull()
    expect(save.classes()).toContain('deal-create-action-btn--save')
    expect(close.classes()).toContain('deal-create-action-btn--close')
    expect(save.text()).toBe('')
    expect(close.text()).toBe('')
    expect(wrapper.find('.voucher-catalog-editor__footer button').exists()).toBe(false)
    await wrapper.find('[data-test="catalog-name"]').setValue('Новое имя')
    save.element.click()
    await flushPromises()
    expect(apiPut).toHaveBeenCalledWith('/voucher-catalog/items/1', { name: 'Новое имя' }, { token: 'test-token' })
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it('shows service and nominal hierarchy, saved snapshots and Moscow time', async () => {
    const wrapper = await setup()
    await flushPromises()
    expect(wrapper.find('.voucher-catalog__group-title').text()).toContain('PlayStation — Turkey')
    expect(wrapper.find('.voucher-catalog__nominal').text()).toBe('500 TRY')
    expect(wrapper.findAll('.voucher-catalog__number').map((cell) => cell.text())).toEqual(['0,00 ₽', '—'])
    expect(wrapper.text()).toContain('Не удалось получить остатки')
    expect(wrapper.text()).toContain('09:00')
    expect(apiGet).toHaveBeenCalledTimes(1)
    expect(wrapper.findAll('.profile-admin-links .tab').map((tab) => tab.text())).toEqual(['Финансы', 'Каталог'])
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it('expands suppliers inside the selected nominal only and finds them by supplier name', async () => {
    const item = snapshot()
    const base = item.nominals[0].offers[0]
    item.nominals[0].offers.push({ ...base, offer_id: 3, supplier_code: 'second', supplier_name: 'Второй поставщик', fulfillment_priority: 2 })
    item.nominals.push({ catalog_nominal_id: 12, name: '1000 TRY', offers: [{ ...base, offer_id: 4, nominal_title: '1000 TRY' }] })
    const wrapper = await setup({ items: [item] })
    await flushPromises()
    const first = wrapper.find('[data-nominal-id="11"]')
    const second = wrapper.find('[data-nominal-id="12"]')
    expect(wrapper.findAll('.catalog-nominal__details')).toHaveLength(0)
    await first.find('.catalog-nominal__expand').trigger('click')
    expect(first.findAll('.catalog-nominal__offer').map((row) => row.attributes('data-offer-id'))).toEqual(['2', '3'])
    expect(second.find('.catalog-nominal__details').exists()).toBe(false)
    await first.find('.catalog-nominal__expand').trigger('click')
    await wrapper.find('input[type="search"]').setValue('Второй поставщик')
    expect(wrapper.findAll('.voucher-catalog__group')).toHaveLength(1)
    expect(first.find('.catalog-nominal__details').exists()).toBe(true)
    expect(second.find('.catalog-nominal__details').exists()).toBe(false)
    expect(apiGet).toHaveBeenCalledTimes(1)
  })

  it('finds a nominal by SKU and keeps its code readonly when renaming', async () => {
    const wrapper = await setup({ items: [snapshot(), { item_id: 2, name: 'Steam', nominals: [] }], expand: false })
    await wrapper.find('input[type="search"]').setValue('ht0000001')
    expect(wrapper.findAll('.voucher-catalog__group')).toHaveLength(1)
    expect(wrapper.find('.catalog-nominal__sku').text()).toBe('HT0000001')
    expect(wrapper.find('.catalog-nominal__details').exists()).toBe(true)
    await wrapper.find('.voucher-catalog__nominal').trigger('click')
    await flushPromises()
    expect(wrapper.find('.voucher-catalog-editor__sku').text()).toBe('SKU HT0000001')
    expect(wrapper.find('.voucher-catalog-editor__sku input').exists()).toBe(false)
    await wrapper.find('[data-test="catalog-own-nominal"]').setValue('Другое название')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    const saved = apiPost.mock.calls[0][1].nominals[0]
    expect(saved.name).toBe('Другое название')
    expect(saved).not.toHaveProperty('sku')
    expect(saved).not.toHaveProperty('sku_number')
    expect(wrapper.find('.catalog-nominal__sku').text()).toBe('HT0000001')
  })

  it('creates a service with several editable nominal names inside a modal', async () => {
    const wrapper = await setup({ items: [] })
    await flushPromises()
    await wrapper.find('[data-test="catalog-create-service"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
    await chooseService(wrapper, '10')
    expect(wrapper.find('[data-test="catalog-name"]').element.value).toBe('PlayStation Turkey')
    await wrapper.find('[data-test="catalog-name"]').setValue('PlayStation — Turkey')
    await button(wrapper, 'Выбрать все').trigger('click')
    await wrapper.find('input[aria-label="Наше название для 1000 TRY"]').setValue('1 000 TRY')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(apiPost).toHaveBeenCalledWith('/voucher-catalog/items', { name: 'PlayStation — Turkey', nominals: [
      { name: '500 TRY', binding: { supplier_code: 'interhub', service_id: '10', nominal_id: '1' } },
      { name: '1 000 TRY', binding: { supplier_code: 'interhub', service_id: '10', nominal_id: '2' } },
    ] }, { token: 'test-token' })
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it('resets selected nominals when supplier service changes', async () => {
    const wrapper = await setup({ items: [] })
    await flushPromises()
    await wrapper.find('[data-test="catalog-create-service"]').trigger('click')
    await flushPromises()
    await chooseService(wrapper, '10')
    await wrapper.find('[data-test="catalog-select-1"]').setValue(true)
    await chooseService(wrapper, '20')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.text()).toContain('Отметьте хотя бы один номинал')
    expect(apiPost).not.toHaveBeenCalled()
  })

  it('adds only unlinked nominals to an existing service without renaming it', async () => {
    const wrapper = await setup()
    await flushPromises()
    await button(wrapper, '+ Номиналы').trigger('click')
    await flushPromises()
    await chooseService(wrapper, '10')
    expect(wrapper.find('[data-test="catalog-select-1"]').element.disabled).toBe(true)
    await button(wrapper, 'Выбрать все').trigger('click')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(apiPost).toHaveBeenCalledWith('/voucher-catalog/items/1/nominals', { nominals: [
      { name: '1000 TRY', binding: { supplier_code: 'interhub', service_id: '10', nominal_id: '2' } },
    ] }, { token: 'test-token' })
  })

  it('can create a nominal manually and rename an existing nominal', async () => {
    const wrapper = await setup()
    await flushPromises()
    await button(wrapper, '+ Номиналы').trigger('click')
    await flushPromises()
    await button(wrapper, 'Добавить вручную').trigger('click')
    await wrapper.find('[data-test="catalog-own-nominal"]').setValue('2000 TRY')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(apiPost).toHaveBeenLastCalledWith('/voucher-catalog/items/1/nominals', { nominals: [{ name: '2000 TRY' }] }, { token: 'test-token' })
    await wrapper.find('.voucher-catalog__nominal').trigger('click')
    await flushPromises()
    await wrapper.find('[data-test="catalog-own-nominal"]').setValue('500 лир')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(apiPost).toHaveBeenLastCalledWith('/voucher-catalog/items/1/nominals', { nominals: [{ catalog_nominal_id: 11, name: '500 лир', routing: { revision: 0, offers: [{ offer_id: 2, enabled: true }] } }] }, { token: 'test-token' })
  })

  it('preserves input on save failure and asks before closing dirty modal', async () => {
    apiPost.mockRejectedValueOnce(new Error('Не удалось сохранить'))
    const wrapper = await setup({ items: [] })
    await flushPromises()
    await wrapper.find('[data-test="catalog-create-service"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-test="catalog-name"]').setValue('Новая услуга')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('form').exists()).toBe(true)
    expect(wrapper.find('[data-test="catalog-name"]').element.value).toBe('Новая услуга')
    await wrapper.find('[role="dialog"]').trigger('keydown', { key: 'Escape' })
    expect(wrapper.find('.unsaved-confirm__title').text()).toBe('Несохраненные изменения')
    expect(wrapper.find('.unsaved-confirm__text').text()).toBe('Закрыть без сохранения?')
    expect(wrapper.findAll('.unsaved-confirm__actions button').map((item) => item.text())).toEqual(['Остаться', 'Закрыть'])
    expect(wrapper.find('.unsaved-confirm__actions .catalog-modal-action').exists()).toBe(false)
    await button(wrapper, 'Остаться').trigger('click')
    expect(wrapper.find('[data-test="catalog-name"]').element.value).toBe('Новая услуга')
    await wrapper.find('button[aria-label="Закрыть"]').trigger('click')
    await wrapper.find('.unsaved-confirm__actions .btn').trigger('click')
    expect(wrapper.find('form').exists()).toBe(false)
    expect(document.body.style.overflow).not.toBe('hidden')
  })

  it('does not close the modal during a save and restores focus afterwards', async () => {
    let finish
    apiPost.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
    const wrapper = await setup({ items: [] })
    await flushPromises()
    wrapper.find('[data-test="catalog-create-service"]').element.focus()
    await wrapper.find('[data-test="catalog-create-service"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-test="catalog-name"]').setValue('Новая услуга')
    await wrapper.find('form').trigger('submit')
    await wrapper.find('[role="dialog"]').trigger('keydown', { key: 'Escape' })
    expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
    expect(wrapper.find('button[aria-label="Закрыть"]').element.disabled).toBe(true)
    finish({ item_id: 2 })
    await flushPromises()
    expect(document.activeElement).toBe(wrapper.find('[data-test="catalog-create-service"]').element)
  })

  it('closes after browsing services or modes without asking to discard empty changes', async () => {
    const wrapper = await setup()
    await flushPromises()
    for (const action of ['close', 'escape', 'backdrop']) {
      await button(wrapper, '+ Номиналы').trigger('click')
      await flushPromises()
      await chooseService(wrapper, '10')
      await button(wrapper, 'Добавить вручную').trigger('click')
      await button(wrapper, 'Выбрать у поставщика').trigger('click')
      if (action === 'close') await wrapper.find('button[aria-label="Закрыть"]').trigger('click')
      if (action === 'escape') await wrapper.find('[role="dialog"]').trigger('keydown', { key: 'Escape' })
      if (action === 'backdrop') await wrapper.find('.modal-backdrop').trigger('click')
      expect(wrapper.find('.voucher-catalog-editor').exists()).toBe(false)
    }
    expect(apiPost).not.toHaveBeenCalled()
  })

  it('keeps confirmation outside the scrolling list and traps focus until the user chooses', async () => {
    // Настоящий Teleport сохраняет DOM и прокрутку; заглушка пересоздаёт содержимое при обновлении.
    await setup({ teleport: false })
    const wrapper = new DOMWrapper(document.body)
    await flushPromises()
    apiGet.mockResolvedValueOnce(Array.from({ length: 80 }, (_, index) => ({
      service_id: 10, service_title: 'PlayStation Turkey', nominal_id: index + 20, nominal_title: `TRY ${index + 20}`,
    })))
    await button(wrapper, '+ Номиналы').trigger('click')
    await flushPromises()
    await chooseService(wrapper, '10')
    await wrapper.find('[data-test="catalog-select-20"]').setValue(true)
    const close = wrapper.find('button[aria-label="Закрыть"]')
    close.element.focus()
    wrapper.find('.voucher-catalog-editor__list').element.scrollTop = 1000
    await close.trigger('click')
    await flushPromises()
    const confirm = wrapper.find('.voucher-catalog-editor__confirm')
    expect(confirm.exists()).toBe(true)
    expect(confirm.element.closest('form')).toBeNull()
    expect(wrapper.find('.voucher-catalog-editor__content').attributes('inert')).toBeDefined()
    expect(document.activeElement).toBe(button(wrapper, 'Остаться').element)
    await button(wrapper, 'Остаться').trigger('keydown', { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(wrapper.find('.unsaved-confirm__actions .btn').element)
    await wrapper.find('.unsaved-confirm__actions .btn').trigger('keydown', { key: 'Tab' })
    expect(document.activeElement).toBe(button(wrapper, 'Остаться').element)
    await wrapper.find('[role="alertdialog"]').trigger('keydown', { key: 'Escape' })
    await flushPromises()
    expect(document.activeElement).toBe(close.element)
    expect(wrapper.find('[data-test="catalog-select-20"]').element.checked).toBe(true)
    expect(wrapper.find('.voucher-catalog-editor__list').element.scrollTop).toBe(1000)
    await close.trigger('click')
    await wrapper.find('.unsaved-confirm__actions .btn').trigger('click')
    expect(wrapper.find('.voucher-catalog-editor').exists()).toBe(false)
  })

  it('sorts provider nominals naturally and closes directly after deselecting all', async () => {
    const wrapper = await setup()
    await flushPromises()
    apiGet.mockResolvedValueOnce([100, 25, 50].map((value) => ({
      service_id: 10, service_title: 'PlayStation Turkey', nominal_id: value, nominal_title: `TRY ${value}`,
    })))
    await button(wrapper, '+ Номиналы').trigger('click')
    await flushPromises()
    await chooseService(wrapper, '10')
    expect(wrapper.findAll('.voucher-catalog-editor__check').map((row) => row.text())).toEqual(['TRY 25', 'TRY 50', 'TRY 100'])
    await button(wrapper, 'Выбрать все').trigger('click')
    expect(button(wrapper, 'Добавить · 3').element.closest('form')).toBeNull()
    expect(button(wrapper, 'Добавить · 3').attributes('form')).toBe('voucher-catalog-editor-form')
    await button(wrapper, 'Снять выбор').trigger('click')
    await wrapper.find('button[aria-label="Закрыть"]').trigger('click')
    expect(wrapper.find('.voucher-catalog-editor').exists()).toBe(false)
  })

  it('hides editing from readers and does not reload the list on a timer', async () => {
    const wrapper = await setup({ canEdit: false })
    await flushPromises()
    expect(wrapper.find('[data-test="catalog-create-service"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Отвязать')
    expect(wrapper.find('.voucher-catalog__delete-nominal').exists()).toBe(false)
    expect(wrapper.find('.voucher-catalog__delete-service').exists()).toBe(false)
    await vi.advanceTimersByTimeAsync(180000)
    expect(apiGet).toHaveBeenCalledTimes(1)
    expect(button(wrapper, 'Обновить список').attributes('aria-busy')).toBe('false')
    expect(wrapper.find('.voucher-catalog__refresh .is-loading').exists()).toBe(false)
    wrapper.unmount()
    wrappers = []
    await vi.advanceTimersByTimeAsync(180000)
    expect(apiGet).toHaveBeenCalledTimes(1)
  })

  it('expands search results and keeps zero stock distinct from missing stock', async () => {
    const wrapper = await setup({ items: [snapshot({ stock_count: 0, stock_updated_at: '2026-09-19T10:00:00Z', stock_error: '' })] })
    await flushPromises()
    expect(wrapper.text()).toContain('Остаток требует обновления')
    expect(wrapper.findAll('.voucher-catalog__number')[1].text()).toBe('0')
    await wrapper.find('.voucher-catalog__group-title').trigger('click')
    expect(wrapper.find('.catalog-nominal').exists()).toBe(false)
    await wrapper.find('input[type="search"]').setValue('500 TRY')
    expect(wrapper.find('.catalog-nominal').exists()).toBe(true)
    await wrapper.find('input[type="search"]').setValue('нет такого')
    expect(wrapper.find('.catalog-nominal').exists()).toBe(false)
  })

  it('shows the number of matching services next to search and restores the total', async () => {
    const wrapper = await setup({ items: [snapshot(), { item_id: 2, name: 'Steam', nominals: [] }] })
    await flushPromises()
    expect(wrapper.find('.voucher-catalog__total').text()).toBe('Услуг: 2')
    await wrapper.find('input[type="search"]').setValue('500 TRY')
    expect(wrapper.find('.voucher-catalog__total').text()).toBe('Найдено: 1 из 2')
    expect(wrapper.findAll('.voucher-catalog__group')).toHaveLength(1)
    await wrapper.find('input[type="search"]').setValue('нет такого')
    expect(wrapper.find('.voucher-catalog__total').text()).toBe('Найдено: 0 из 2')
    await wrapper.find('input[type="search"]').setValue(' ')
    expect(wrapper.find('.voucher-catalog__total').text()).toBe('Услуг: 2')
    expect(wrapper.findAll('.voucher-catalog__group')).toHaveLength(2)
  })

  it('keeps the refresh label and existing rows while loading a fresh snapshot', async () => {
    const wrapper = await setup()
    await flushPromises()
    let finish
    apiGet.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
    await button(wrapper, 'Обновить список').trigger('click')
    expect(button(wrapper, 'Обновить список').element.disabled).toBe(true)
    expect(button(wrapper, 'Обновить список').attributes('aria-busy')).toBe('true')
    expect(wrapper.find('.voucher-catalog__refresh .is-loading').exists()).toBe(true)
    expect(apiGet).toHaveBeenCalledTimes(2)
    expect(wrapper.find('.voucher-catalog__group-title').text()).toContain('PlayStation — Turkey')
    finish({ items: [snapshot()], suppliers, can_edit: true })
    await flushPromises()
    expect(button(wrapper, 'Обновить список').element.disabled).toBe(false)
    expect(button(wrapper, 'Обновить список').attributes('aria-busy')).toBe('false')
  })

  it('renames a service without loading or replacing its existing nominals', async () => {
    const wrapper = await setup()
    await flushPromises()
    await button(wrapper, 'Изменить услугу').trigger('click')
    await flushPromises()
    expect(apiGet).toHaveBeenCalledTimes(1)
    await wrapper.find('[data-test="catalog-name"]').setValue('Другое имя')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(apiPut).toHaveBeenCalledWith('/voucher-catalog/items/1', { name: 'Другое имя' }, { token: 'test-token' })
    await wrapper.find('.catalog-nominal__expand').trigger('click')
    await button(wrapper, 'Отвязать').trigger('click')
    expect(apiDelete).not.toHaveBeenCalled()
    await button(wrapper, 'Да').trigger('click')
    await flushPromises()
    expect(apiDelete).toHaveBeenCalledWith('/voucher-catalog/items/1/offers/2', { token: 'test-token' })
  })

  it('rejects duplicate nominal names before making a save request', async () => {
    const catalog = useVoucherCatalog(() => 'test-token')
    catalog.draft.name = 'Test'
    catalog.draft.service_id = '10'
    catalog.draft.selected = [{ id: '1', name: 'Same' }, { id: '2', name: 'Same' }]
    await catalog.save()
    expect(catalog.formError.value).toBe('Названия номиналов должны различаться')
    expect(apiPost).not.toHaveBeenCalled()
  })

  it('confirms service deletion with its contents and preserves other services', async () => {
    const other = { item_id: 2, name: 'Steam', nominals: [] }
    const wrapper = await setup({ items: [snapshot(), other] })
    await flushPromises()
    await wrapper.find('[aria-label="Удалить услугу PlayStation — Turkey"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alertdialog"]').text()).toContain('Удалить услугу «PlayStation — Turkey»?')
    expect(wrapper.find('[role="alertdialog"]').text()).toContain('все её номиналы (1)')
    expect(apiDelete).not.toHaveBeenCalled()
    await button(wrapper, 'Оставить услугу').trigger('click')
    expect(wrapper.find('[role="alertdialog"]').exists()).toBe(false)
    await wrapper.find('[data-test="catalog-name"]').setValue('Несохранённое имя')
    await button(wrapper, 'Удалить услугу').trigger('click')
    expect(wrapper.find('[role="alertdialog"]').text()).toContain('PlayStation — Turkey')
    apiGet.mockResolvedValueOnce({ items: [other], suppliers, can_edit: true })
    await wrapper.find('.voucher-catalog-editor__confirm .voucher-catalog-editor__delete').trigger('click')
    await flushPromises()
    expect(apiDelete).toHaveBeenCalledExactlyOnceWith('/voucher-catalog/items/1', { token: 'test-token' })
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    expect(wrapper.findAll('.voucher-catalog__group')).toHaveLength(1)
    expect(wrapper.find('.voucher-catalog__group-title').text()).toContain('Steam')
    expect(document.activeElement).toBe(wrapper.find('input[type="search"]').element)
  })

  it('keeps a service on deletion failure and prevents duplicate requests', async () => {
    const wrapper = await setup()
    await flushPromises()
    await wrapper.find('.voucher-catalog__delete-service').trigger('click')
    await flushPromises()
    let fail
    apiDelete.mockImplementationOnce(() => new Promise((resolve, reject) => { fail = reject }))
    await wrapper.find('.voucher-catalog-editor__confirm .voucher-catalog-editor__delete').trigger('click')
    await wrapper.find('.voucher-catalog-editor__confirm .voucher-catalog-editor__delete').trigger('click')
    await wrapper.find('[role="alertdialog"]').trigger('keydown', { key: 'Escape' })
    expect(button(wrapper, 'Оставить услугу').element.disabled).toBe(true)
    expect(apiDelete).toHaveBeenCalledTimes(1)
    fail(new Error('Услуга уже используется'))
    await flushPromises()
    expect(wrapper.find('.voucher-catalog-editor__confirm [role="alert"]').text()).toBe('Услуга уже используется')
    expect(wrapper.find('.voucher-catalog__nominal').exists()).toBe(true)
    await wrapper.find('[role="alertdialog"]').trigger('keydown', { key: 'Escape' })
    expect(wrapper.find('[role="alertdialog"]').exists()).toBe(false)
    expect(apiGet).toHaveBeenCalledTimes(1)
  })

  it('allows deleting an empty service but does not offer deletion for a new draft', async () => {
    const wrapper = await setup({ items: [{ item_id: 2, name: 'Steam', nominals: [] }] })
    await flushPromises()
    await wrapper.find('[data-test="catalog-create-service"]').trigger('click')
    await flushPromises()
    expect(button(wrapper, 'Удалить услугу')).toBeUndefined()
    await wrapper.find('[aria-label="Закрыть"]').trigger('click')
    await wrapper.find('.voucher-catalog__delete-service').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alertdialog"]').text()).toContain('все её номиналы (0)')
    apiGet.mockResolvedValueOnce({ items: [], suppliers, can_edit: true })
    await wrapper.find('.voucher-catalog-editor__confirm .voucher-catalog-editor__delete').trigger('click')
    await flushPromises()
    expect(apiDelete).toHaveBeenCalledExactlyOnceWith('/voucher-catalog/items/2', { token: 'test-token' })
    expect(wrapper.find('.voucher-catalog__group').exists()).toBe(false)
  })

  it('deletes an unlinked nominal only after confirmation and keeps its service', async () => {
    const item = { item_id: 7, name: 'Blizzard — EUR', nominals: [{ catalog_nominal_id: 15, name: '150', offers: [] }] }
    const wrapper = await setup({ items: [item] })
    await flushPromises()
    await wrapper.find('[aria-label="Удалить номинал 150"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alertdialog"]').text()).toContain('Удалить номинал «150»?')
    expect(apiDelete).not.toHaveBeenCalled()
    await button(wrapper, 'Оставить номинал').trigger('click')
    expect(wrapper.find('.voucher-catalog-editor__confirm').exists()).toBe(false)
    expect(wrapper.find('.voucher-catalog__nominal').text()).toBe('150')
    await button(wrapper, 'Удалить номинал').trigger('click')
    apiGet.mockResolvedValueOnce({ items: [{ ...item, nominals: [] }], suppliers, can_edit: true })
    await wrapper.find('.voucher-catalog-editor__confirm .voucher-catalog-editor__delete').trigger('click')
    await flushPromises()
    expect(apiDelete).toHaveBeenCalledWith('/voucher-catalog/items/7/nominals/15', { token: 'test-token' })
    expect(wrapper.find('.voucher-catalog-editor').exists()).toBe(false)
    expect(wrapper.find('.voucher-catalog__nominal').exists()).toBe(false)
    expect(wrapper.find('.voucher-catalog__group-title').text()).toContain('Blizzard — EUR')
    expect(document.activeElement).toBe(wrapper.find('input[type="search"]').element)
  })

  it('keeps failed deletion visible and blocks repeat actions while deleting a linked nominal', async () => {
    const wrapper = await setup()
    await flushPromises()
    await wrapper.find('[aria-label="Удалить номинал 500 TRY"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('.voucher-catalog-editor__confirm').text()).toContain('все его связки')
    let fail
    apiDelete.mockImplementationOnce(() => new Promise((resolve, reject) => { fail = reject }))
    await wrapper.find('.voucher-catalog-editor__confirm .voucher-catalog-editor__delete').trigger('click')
    await wrapper.find('[role="alertdialog"]').trigger('keydown', { key: 'Escape' })
    expect(button(wrapper, 'Оставить номинал').element.disabled).toBe(true)
    expect(wrapper.find('[role="alertdialog"]').exists()).toBe(true)
    fail(new Error('Номинал уже используется'))
    await flushPromises()
    expect(wrapper.find('.voucher-catalog-editor__confirm [role="alert"]').text()).toBe('Номинал уже используется')
    expect(wrapper.find('.voucher-catalog__nominal').exists()).toBe(true)
    expect(apiDelete).toHaveBeenCalledTimes(1)
    await wrapper.find('[role="alertdialog"]').trigger('keydown', { key: 'Escape' })
    expect(wrapper.find('.voucher-catalog-editor__confirm').exists()).toBe(false)
  })
})
