import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import WorkAirpayCatalog from '../sections/WorkAirpayCatalog.vue'
import WorkAirpaySection from '../sections/WorkAirpaySection.vue'
import WorkAirpayPreparation from '../sections/WorkAirpayPreparation.vue'
import { apiGet } from '../../../api/http'

vi.mock('../../../api/http', () => ({ apiGet: vi.fn(), apiPost: vi.fn() }))
let wrapper

function service(overrides = {}) {
  // Форма справочника совпадает с нормализованным ответом backend и сохраняет строковый код.
  return { service_id: 'A0002', title: 'Game credits', group: 'Игры', country: 'Казахстан', type: 0,
    fixed_payment: true, inputs: [{ name: 'account', title: 'Номер аккаунта', required: true }],
    displays: [{ name: 'fixedAmount', title: '' }], ...overrides }
}

async function mountCatalog(items) {
  // Заполняем каталог без сетевых запросов к настоящему агенту Airpay.
  apiGet.mockImplementation(async path => path.includes('/service?')
    ? items.find(item => item.service_id === new URLSearchParams(path.split('?')[1]).get('service_id'))
    : { configured: true, items, total: items.length })
  wrapper = mount(WorkAirpayCatalog, { props: { token: 'crm-token' } })
  await flushPromises()
}

afterEach(() => {
  // Очищаем состояние компонента и отложенные обработчики между сценариями.
  wrapper?.unmount()
  vi.resetAllMocks()
})

describe('WorkAirpayCatalog', () => {
  it('sorts the entire catalog and resets pagination like Interhub', async () => {
    // Меняем направление со второй страницы: первой должна стать последняя услуга полного списка.
    await mountCatalog(Array.from({ length: 21 }, (_, index) => service({ service_id: `A${index}`, title: `Service ${index}` })))
    await wrapper.findAll('.airpay-catalog__pagination button')[1].trigger('click')
    await wrapper.get('.supplier-catalog__sort').trigger('click')
    expect(wrapper.get('.airpay-catalog__pagination').text()).toContain('Страница 1 из 2')
    expect(wrapper.findAll('tbody tr')[0].text()).toContain('Service 20')
    expect(wrapper.get('.supplier-catalog__sort').text()).toContain('Я–А')
    await wrapper.get('.supplier-catalog__sort').trigger('click')
    expect(wrapper.findAll('tbody tr')[0].text()).toContain('Service 0')
    expect(apiGet).toHaveBeenCalledTimes(1)
  })

  it('refreshes both blocks from one header button and waits for the catalog', async () => {
    // Общая кнопка не отправляет повторные запросы, пока один из двух блоков ещё загружается.
    const catalogResponse = { configured: true, items: [service()], total: 1 }
    const balanceResponse = { configured: true, balance: 12, overdraft: 5000, currency: 'RUB' }
    apiGet.mockImplementation(async path => path.endsWith('/balance') ? balanceResponse : catalogResponse)
    wrapper = mount(WorkAirpaySection, { props: { token: 'crm-token' } })
    await flushPromises()
    let finishCatalog
    apiGet.mockClear()
    apiGet.mockImplementation(path => path.endsWith('/balance') ? Promise.resolve(balanceResponse)
      : new Promise(resolve => { finishCatalog = resolve }))
    const refresh = wrapper.get('[aria-label="Обновить данные Airpay"]')
    await refresh.trigger('click')
    await flushPromises()
    expect(apiGet).toHaveBeenCalledTimes(2)
    expect(apiGet).toHaveBeenCalledWith('/integrations/airpay/balance', { token: 'crm-token' })
    expect(apiGet).toHaveBeenCalledWith('/integrations/airpay/services', { token: 'crm-token' })
    expect(refresh.attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-testid="airpay-balance"]').text()).toContain('12,00')
    await refresh.trigger('click')
    expect(apiGet).toHaveBeenCalledTimes(2)
    finishCatalog(catalogResponse)
    await flushPromises()
    expect(refresh.attributes('disabled')).toBeUndefined()
    expect(wrapper.get('tbody').text()).toContain('Game credits')
  })

  it('opens preparation below the catalog without a dialog or payment requests', async () => {
    // Услуга раскрывает настоящую форму на странице, без модального слоя и дублирующего списка полей.
    await mountCatalog([service({ fixed_payment: null })])
    expect(wrapper.text()).toContain('Не указана')
    await wrapper.get('.airpay-catalog__service').trigger('click')
    await flushPromises()
    const details = wrapper.get('#airpay-service-details')
    expect(details.text()).toContain('Номер аккаунта')
    expect(details.get('input').attributes('required')).toBeDefined()
    expect(details.get('h3').text()).toBe('Game credits')
    expect(details.text()).toContain('Получить')
    expect(details.text()).toContain('Цена и проверка доступности')
    expect(details.findAll('form')).toHaveLength(1)
    expect(details.find('.airpay-catalog__fields').exists()).toBe(false)
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    expect(document.querySelector('[role="dialog"]')).toBeNull()
    expect(wrapper.get('.airpay-catalog').element.contains(details.element)).toBe(true)
    expect(details.element.compareDocumentPosition(wrapper.get('table').element) & Node.DOCUMENT_POSITION_PRECEDING).toBeTruthy()
    expect(wrapper.get('.airpay-catalog__service').attributes('aria-expanded')).toBe('true')
    expect(apiGet).toHaveBeenCalledWith('/integrations/airpay/service?service_id=A0002', { token: 'crm-token' })
    expect(apiGet).toHaveBeenCalledTimes(2)
    await wrapper.get('.airpay-catalog__service').trigger('click')
    expect(wrapper.find('#airpay-service-details').exists()).toBe(false)
  })

  it('scrolls to the inline preparation after the pagination controls', async () => {
    // Повторяем прокрутку Interhub к блоку под пагинацией, сохраняя всю форму внутри каталога.
    const original = Element.prototype.scrollIntoView
    const scroll = vi.fn()
    Element.prototype.scrollIntoView = scroll
    try {
      await mountCatalog(Array.from({ length: 21 }, (_, index) => service({ service_id: `A${index}`, title: `Service ${index}` })))
      await wrapper.get('.airpay-catalog__service').trigger('click')
      await flushPromises()
      const details = wrapper.get('#airpay-service-details')
      expect(scroll).toHaveBeenCalledWith({ behavior: 'smooth', block: 'center' })
      expect(scroll.mock.instances[0]).toBe(details.element)
      expect(details.element.compareDocumentPosition(wrapper.get('nav').element) & Node.DOCUMENT_POSITION_PRECEDING).toBeTruthy()
    } finally {
      if (original) Element.prototype.scrollIntoView = original
      else delete Element.prototype.scrollIntoView
    }
  })

  it('keeps the inline service selected while its request is running', async () => {
    // Без модального слоя таблица остаётся видна: её кнопки не должны сбросить текущую операцию.
    await mountCatalog([service(), service({ service_id: 'B1', title: 'Other service' })])
    await wrapper.get('.airpay-catalog__service').trigger('click')
    await flushPromises()
    wrapper.getComponent(WorkAirpayPreparation).vm.$emit('busy-change', true)
    await flushPromises()
    const buttons = wrapper.findAll('.airpay-catalog__service')
    expect(buttons.every(button => button.attributes('disabled') !== undefined)).toBe(true)
    await buttons[1].trigger('click')
    expect(wrapper.getComponent(WorkAirpayPreparation).props('serviceId')).toBe('A0002')
    wrapper.getComponent(WorkAirpayPreparation).vm.$emit('busy-change', false)
    await flushPromises()
    await buttons[1].trigger('click')
    await flushPromises()
    expect(wrapper.getComponent(WorkAirpayPreparation).props('serviceId')).toBe('B1')
    expect(wrapper.get('#airpay-service-details h3').text()).toBe('Other service')
  })

  it('combines group and search filters and resets an empty result', async () => {
    // Поиск находит строковые ID, страну и названия, а фильтр группы не смешивает категории.
    await mountCatalog([service(), service({ service_id: '0007', title: 'Mobile', group: 'Связь', country: 'Турция' })])
    await wrapper.get('input[type="search"]').setValue('0007')
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    expect(wrapper.get('tbody').text()).toContain('Mobile')
    await wrapper.get('select').setValue('Игры')
    expect(wrapper.text()).toContain('Услуги по этим условиям не найдены')
    await wrapper.get('.airpay-catalog__empty button').trigger('click')
    expect(wrapper.findAll('tbody tr')).toHaveLength(2)
    await wrapper.get('input[type="search"]').setValue('КАЗАХСТАН')
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
  })

  it('paginates and returns to the first page after changing filters', async () => {
    // Фильтрация с последней страницы не должна оставить пустую таблицу.
    await mountCatalog(Array.from({ length: 21 }, (_, index) => service({ service_id: `A${index}`, title: `Service ${index}` })))
    expect(wrapper.findAll('tbody tr')).toHaveLength(20)
    await wrapper.findAll('.airpay-catalog__pagination button')[1].trigger('click')
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    expect(wrapper.get('tbody').text()).toContain('Service 20')
    await wrapper.get('input').setValue('Service 1')
    expect(wrapper.findAll('tbody tr')).toHaveLength(11)
    expect(wrapper.find('.airpay-catalog__pagination').exists()).toBe(false)
  })

  it('distinguishes unconfigured access, empty catalog and a retryable error', async () => {
    // Ни отсутствие доступа, ни сбой запроса не выдаём за успешный пустой каталог.
    apiGet.mockResolvedValueOnce({ configured: false, items: [], total: 0 })
      .mockRejectedValueOnce(new Error('Нет соединения с Airpay'))
      .mockResolvedValueOnce({ configured: true, items: [], total: 0 })
    wrapper = mount(WorkAirpayCatalog)
    await flushPromises()
    expect(wrapper.text()).toContain('после настройки подключения')
    await wrapper.get('button').trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('Нет соединения')
    await wrapper.get('button').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('пока не вернул доступных услуг')
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })

  it('ignores a late catalog response after changing the token', async () => {
    // Поздний каталог прежней сессии не должен заменить услуги текущего пользователя.
    let resolveOld
    apiGet.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve }))
      .mockResolvedValueOnce({ configured: true, items: [service({ title: 'New service' })], total: 1 })
    wrapper = mount(WorkAirpayCatalog, { props: { token: 'old' } })
    expect(wrapper.get('button').attributes('disabled')).toBeDefined()
    await wrapper.setProps({ token: 'new' })
    await flushPromises()
    resolveOld({ configured: true, items: [service({ title: 'Old service' })], total: 1 })
    await flushPromises()
    expect(wrapper.get('tbody').text()).toContain('New service')
    expect(wrapper.get('tbody').text()).not.toContain('Old service')
  })

  it('keeps catalog visible if only balance fails', async () => {
    // Независимые методы сохраняют полезный экран при частичном сбое поставщика.
    apiGet.mockImplementation(async path => {
      if (path.endsWith('/balance')) throw new Error('Ошибка баланса')
      return { configured: true, items: [service()], total: 1 }
    })
    wrapper = mount(WorkAirpaySection, { props: { token: 'crm-token' } })
    await flushPromises()
    expect(wrapper.text()).toContain('Ошибка баланса')
    expect(wrapper.get('tbody').text()).toContain('Game credits')
  })
})
