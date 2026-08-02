import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import WorkInterhubSection from '../sections/WorkInterhubSection.vue'

function buildCtx(overrides = {}) {
  // Собираем каталог как его отдаёт внутренний endpoint InterHub.
  return {
    loading: false,
    error: '',
    search: '',
    balance: 10000,
    currency: 'RUB',
    overBalance: 0,
    overLimit: 0,
    services: [
      {
        service_id: 7,
        title: 'Mobile top up',
        category: 'Mobile',
        type: 'TOP_UP_FIXED',
        min_amount: 10,
        max_amount: 100,
        fields: [{ name: 'nominal', type: 'LIST', required: true, value_list: [{ id: 15, title: '15' }] }],
      },
      {
        service_id: 8,
        title: 'Gift PIN',
        category: 'Games',
        type: 'PIN',
        min_amount: 0,
        max_amount: 0,
        fields: [],
      },
    ],
    reload: vi.fn(),
    calculate: vi.fn(),
    checkPayment: vi.fn(),
    calculation: null,
    calculationLoading: false,
    check: null,
    checkLoading: false,
    payment: null,
    paymentLoading: false,
    canPay: false,
    canManagePrices: false,
    cachedPrices: [],
    priceRefresh: null,
    priceRefreshLoading: false,
    priceError: '',
    salesHistory: [],
    salesHistoryLoading: false,
    salesHistoryError: '',
    pay: vi.fn(),
    refreshPaymentStatus: vi.fn(),
    refreshPrices: vi.fn(),
    exportPrices: vi.fn(),
    loadSalesHistory: vi.fn(),
    resetPaymentFlow: vi.fn(),
    setSearchFromEvent: vi.fn(),
    ...overrides,
  }
}

async function selectServiceByTitle(wrapper, title) {
  // Выбираем строку по названию, чтобы тест не зависел от пользовательской сортировки каталога.
  const row = wrapper.findAll('tbody tr').find((item) => item.text().includes(title))
  await row.trigger('click')
}

describe('WorkInterhubSection', () => {
  it('renders normalized services and payment types', () => {
    const wrapper = mount(WorkInterhubSection, { props: { ctx: buildCtx() } })

    expect(wrapper.text()).toContain('Mobile top up')
    expect(wrapper.text()).toContain('Фикс. номинал')
    expect(wrapper.text()).toContain('PIN-код')
    expect(wrapper.findAll('thead th')).toHaveLength(3)
    expect(wrapper.text()).not.toContain('Лимит:')
    expect(wrapper.text()).not.toContain('Реквизиты')
    expect(wrapper.text()).toContain('10 000 ₽')
  })

  it('shows the signed overdraft balance and available amount next to the InterHub deposit', () => {
    const wrapper = mount(WorkInterhubSection, { props: { ctx: buildCtx({ balance: 0, overBalance: -2328.76, overLimit: 100000 }) } })

    expect(wrapper.text()).toContain('Депозит InterHub')
    expect(wrapper.text()).toContain('Овердрафт: -2 328,76 ₽ из 100 000 ₽')
    expect(wrapper.text()).toContain('Доступно для оплат: 97 671,24 ₽')
  })

  it('filters catalog locally and reloads on demand', async () => {
    const ctx = buildCtx()
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await wrapper.find('input[type="search"]').setValue('games')
    expect(ctx.setSearchFromEvent).toHaveBeenCalledTimes(1)

    await wrapper.setProps({ ctx: { ...ctx, search: 'games' } })
    expect(wrapper.text()).not.toContain('Mobile top up')
    expect(wrapper.text()).toContain('Gift PIN')

    await wrapper.find('[aria-label="Обновить каталог InterHub"]').trigger('click')
    expect(ctx.reload).toHaveBeenCalledTimes(1)
  })

  it('hides the technical po_ prefix and finds a service without hyphens', async () => {
    const ctx = buildCtx({
      canPay: true,
      services: [
        { service_id: 14, title: 'po_Age of Legends - Global', category: 'Games', type: 'VOUCHER', fields: [] },
        { service_id: 15, title: 'po_Other service', category: 'Games', type: 'VOUCHER', fields: [] },
      ],
    })
    ctx.calculate = vi.fn(async () => { ctx.calculation = { success: true, fixed_amount: 117.47 } })
    ctx.checkPayment = vi.fn(async () => { ctx.check = { success: true, message: 'Доступно' } })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    expect(wrapper.text()).toContain('Age of Legends - Global')
    expect(wrapper.text()).not.toContain('po_Age of Legends - Global')
    await wrapper.setProps({ ctx: { ...ctx, search: 'age of legends global' } })
    expect(wrapper.text()).toContain('Age of Legends - Global')
    expect(wrapper.text()).not.toContain('Other service')

    await wrapper.find('tbody tr').trigger('click')
    expect(wrapper.find('.interhub-catalog__service-summary').text()).toContain('Age of Legends - Global')
    await wrapper.find('.interhub-catalog__form').trigger('submit')
    await Promise.resolve()
    await Promise.resolve()
    expect(document.body.querySelector('.interhub-confirm__service')?.textContent).toContain('Age of Legends - Global')
    wrapper.unmount()
  })

  it('sorts services by title in both directions', async () => {
    const wrapper = mount(WorkInterhubSection, { props: { ctx: buildCtx() } })

    expect(wrapper.findAll('tbody tr')[0].text()).toContain('Gift PIN')
    await wrapper.find('.interhub-catalog__sort').trigger('click')
    expect(wrapper.findAll('tbody tr')[0].text()).toContain('Mobile top up')
  })

  it('opens paid sales history with a date range filter', async () => {
    const ctx = buildCtx({
      salesHistory: [{ service_id: 7, service_title: 'Steam Wallet', nominal: '15', nominal_title: '15 USD', price: 12.5, gift_code: 'GIFT-15', created_at: '2026-07-27T10:30:00Z' }],
    })
    const wrapper = mount(WorkInterhubSection, { props: { ctx }, attachTo: document.body })

    await wrapper.get('.interhub-catalog__history-action').trigger('click')
    expect(ctx.loadSalesHistory).toHaveBeenCalledWith({ dateFrom: '', dateTo: '' })
    expect(document.body.querySelector('.interhub-history-backdrop')?.classList.contains('work-modal-root')).toBe(true)
    expect(document.body.querySelector('.interhub-history__head')?.classList.contains('modal__head')).toBe(true)
    expect(document.body.querySelector('[aria-label="Закрыть"]')?.classList.contains('deal-create-action-btn--close')).toBe(true)
    expect(document.body.textContent).toContain('История продаж')
    expect(document.body.textContent).toContain('Steam Wallet')
    expect(document.body.textContent).toContain('15 USD')
    expect(document.body.textContent).toContain('GIFT-15')
    expect(document.body.querySelector('.interhub-history__cards').textContent).toContain('Сумма платежей')
    expect(document.body.querySelector('.interhub-history__cards').textContent).toContain('12,50 ₽')

    const dates = document.body.querySelectorAll('.interhub-history input[type="date"]')
    dates[0].value = '2026-07-01'
    await dates[0].dispatchEvent(new Event('input'))
    dates[1].value = '2026-07-27'
    await dates[1].dispatchEvent(new Event('input'))
    await document.body.querySelector('.interhub-history__filters').dispatchEvent(new Event('submit', { cancelable: true }))
    expect(ctx.loadSalesHistory).toHaveBeenLastCalledWith({ dateFrom: '2026-07-01', dateTo: '2026-07-27' })
    wrapper.unmount()
  })

  it('sorts paid sales history by visible table columns', async () => {
    const wrapper = mount(WorkInterhubSection, {
      props: {
        ctx: buildCtx({
          salesHistory: [
            { service_id: 8, nominal: '50', price: 40, gift_code: 'Z-CODE', created_at: '2026-07-26T10:30:00Z' },
            { service_id: 7, nominal: '15', price: 12.5, gift_code: 'A-CODE', created_at: '2026-07-27T10:30:00Z' },
          ],
        }),
      },
      attachTo: document.body,
    })
    await wrapper.get('.interhub-catalog__history-action').trigger('click')
    const priceHeader = document.body.querySelectorAll('.interhub-history__sort')[2]
    await priceHeader.dispatchEvent(new Event('click'))

    const rows = [...document.body.querySelectorAll('.interhub-history tbody tr')]
    expect(rows[0].textContent).toContain('12,50 ₽')
    wrapper.unmount()
  })

  it('filters paid sales history by service title and nominal', async () => {
    const wrapper = mount(WorkInterhubSection, {
      props: {
        ctx: buildCtx({
          salesHistory: [
            { service_id: 7, service_title: 'Steam Wallet', nominal_title: '300 NC', price: 79.2, gift_code: 'STEAM-CODE', created_at: '2026-07-27T10:30:00Z' },
            { service_id: 8, service_title: 'Apple Gift Card', nominal_title: 'TRY 250', price: 492, gift_code: 'APPLE-CODE', created_at: '2026-07-26T10:30:00Z' },
          ],
        }),
      },
      attachTo: document.body,
    })
    await wrapper.get('.interhub-catalog__history-action').trigger('click')
    const search = document.body.querySelector('.interhub-history input[type="search"]')

    search.value = 'steam'
    await search.dispatchEvent(new Event('input'))
    expect(document.body.querySelectorAll('.interhub-history tbody tr')).toHaveLength(1)
    expect(document.body.querySelector('.interhub-history tbody tr').textContent).toContain('Steam Wallet')

    search.value = '250'
    await search.dispatchEvent(new Event('input'))
    expect(document.body.querySelector('.interhub-history tbody tr').textContent).toContain('Apple Gift Card')
    wrapper.unmount()
  })

  it('paginates paid sales history without loading the data again', async () => {
    const salesHistory = Array.from({ length: 26 }, (_, index) => ({
      service_id: 7,
      nominal: String(index + 1),
      price: index + 1,
      gift_code: `CODE-${index + 1}`,
      created_at: `2026-07-27T10:${String(59 - index).padStart(2, '0')}:00Z`,
    }))
    const ctx = buildCtx({ salesHistory })
    const wrapper = mount(WorkInterhubSection, { props: { ctx }, attachTo: document.body })

    await wrapper.get('.interhub-catalog__history-action').trigger('click')
    expect(document.body.querySelector('.interhub-history__pagination').textContent).toContain('Показаны 1–25 из 26')
    const rows = document.body.querySelectorAll('.interhub-history tbody tr')
    expect(rows).toHaveLength(25)

    const next = document.body.querySelector('[aria-label="Следующая страница истории продаж"]')
    await next.dispatchEvent(new Event('click'))
    expect(document.body.querySelector('.interhub-history__pagination').textContent).toContain('Показаны 26–26 из 26')
    expect(document.body.querySelector('.interhub-history tbody tr').textContent).toContain('CODE-26')
    expect(ctx.loadSalesHistory).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('prepares price and availability before an explicit purchase confirmation', async () => {
    const ctx = buildCtx({ canPay: true })
    ctx.calculate = vi.fn(async () => { ctx.calculation = { success: true, fixed_amount: 117.47 } })
    ctx.checkPayment = vi.fn(async () => { ctx.check = { success: true, message: 'Доступно' } })
    ctx.pay = vi.fn(async () => { ctx.payment = { success: true, status: 0, params: { gift_code: 'TESTGIFTCODE' } } })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await selectServiceByTitle(wrapper, 'Mobile top up')
    expect(wrapper.text()).toContain('Получение')

    await wrapper.find('.interhub-catalog__form select').setValue('15')
    ctx.resetPaymentFlow.mockClear()
    await wrapper.find('.interhub-catalog__form').trigger('submit')
    await Promise.resolve()
    await Promise.resolve()

    expect(ctx.calculate).toHaveBeenCalledWith({
      service_id: 7,
      account: '',
      params: { nominal: 15 },
      flow_type: 'TOP_UP_FIXED',
    })
    expect(ctx.checkPayment).toHaveBeenCalledWith({
      service_id: 7,
      account: '',
      params: { nominal: 15 },
      flow_type: 'TOP_UP_FIXED',
    })
    expect(ctx.pay).not.toHaveBeenCalled()
    expect(ctx.resetPaymentFlow).toHaveBeenCalledTimes(1)
    expect(document.body.querySelector('.interhub-confirm')?.classList.contains('modal--auto')).toBe(true)
    expect(document.body.querySelector('.interhub-confirm__nominal')?.textContent).toBe('15')
    expect(document.body.textContent).toContain('Актуальная цена')
    expect(document.body.textContent).toContain('117,47 ₽')
    expect(document.body.textContent).toContain('Готов к покупке')

    await document.body.querySelector('.interhub-confirm__actions .btn').dispatchEvent(new Event('click'))
    expect(ctx.pay).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('shows the provider availability error and disables purchase confirmation', async () => {
    const ctx = buildCtx({ canPay: true })
    ctx.calculate = vi.fn(async () => { ctx.calculation = { success: true, fixed_amount: 117.47 } })
    ctx.checkPayment = vi.fn(async () => { ctx.check = { success: false, message: 'У поставщика закончились ключи' } })
    const wrapper = mount(WorkInterhubSection, { props: { ctx }, attachTo: document.body })

    await selectServiceByTitle(wrapper, 'Mobile top up')
    await wrapper.find('.interhub-catalog__form select').setValue('15')
    await wrapper.find('.interhub-catalog__form').trigger('submit')
    await Promise.resolve()
    await Promise.resolve()

    const buyButton = document.body.querySelector('.interhub-confirm__actions .btn')
    expect(document.body.textContent).toContain('У поставщика закончились ключи')
    expect(buyButton.disabled).toBe(true)
    expect(ctx.pay).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('scrolls the selected service payment form into view', async () => {
    const scrollIntoView = vi.fn()
    const originalDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollIntoView')
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', { configurable: true, value: scrollIntoView })
    try {
      const wrapper = mount(WorkInterhubSection, { props: { ctx: buildCtx() } })
      await selectServiceByTitle(wrapper, 'Mobile top up')

      expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'center' })
    } finally {
      if (originalDescriptor) Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', originalDescriptor)
      else delete HTMLElement.prototype.scrollIntoView
    }
  })

  it('paginates a long catalog so the selected service form stays close to its row', async () => {
    const services = Array.from({ length: 21 }, (_, index) => ({
      service_id: index + 1,
      title: `Service ${index + 1}`,
      category: 'Games',
      type: 'VOUCHER',
      fields: [],
    }))
    const wrapper = mount(WorkInterhubSection, { props: { ctx: buildCtx({ services }) } })

    expect(wrapper.text()).toContain('Service 20')
    expect(wrapper.text()).not.toContain('Service 21')
    await wrapper.find('[aria-label="Следующая страница"]').trigger('click')
    expect(wrapper.text()).toContain('Страница 2 из 2')
    expect(wrapper.text()).toContain('Service 21')
    expect(wrapper.text()).not.toContain('Service 1')
  })

  it('derives TOP_UP amount from the selected nominal instead of rendering a manual amount input', async () => {
    const ctx = buildCtx({
      services: [{ service_id: 9, title: 'PlayStation', category: '', type: 'TOP_UP', fields: [{ name: 'nominal', type: 'LIST', required: true, value_list: [{ id: 250, title: 'TRY 250' }] }] }],
    })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await wrapper.find('tbody tr').trigger('click')
    await wrapper.find('.interhub-catalog__form select').setValue('250')
    expect(wrapper.text()).toContain('TRY 250')
    expect(wrapper.find('.interhub-catalog__form input[type="number"]').exists()).toBe(false)
  })

  it('asks for amount when a TOP_UP service does not provide nominal options', async () => {
    const ctx = buildCtx({
      services: [{ service_id: 10, title: 'Steam CIS', category: '', type: 'TOP_UP', min_amount: 7.79, max_amount: 701550, fields: [] }],
    })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await selectServiceByTitle(wrapper, 'Steam CIS')
    expect(wrapper.find('.interhub-catalog__form input[type="number"]').exists()).toBe(true)
    expect(wrapper.find('.interhub-catalog__form input:not([type="number"])').attributes('required')).toBeDefined()
    expect(wrapper.text()).toContain('Аккаунт или номер *')
    expect(wrapper.text()).toContain('Лимит: 7.79–701550')
    await wrapper.find('.interhub-catalog__form input[type="number"]').setValue('200')
    const actions = wrapper.find('.interhub-catalog__actions')
    expect(actions.classes()).toContain('is-single')
    expect(actions.find('.interhub-catalog__action-btn').text()).toContain('Получить')
    expect(actions.find('.interhub-catalog__action-btn').attributes('disabled')).toBeDefined()
  })

  it('hides the account field and shows a bounded quantity for voucher services', async () => {
    const ctx = buildCtx({
      services: [{ service_id: 11, title: 'Steam voucher', category: '', type: 'VOUCHER', fields: [{ name: 'nominal', type: 'LIST', required: true, value_list: [{ id: 25, title: 'USD 25' }] }] }],
    })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await wrapper.find('tbody tr').trigger('click')
    expect(wrapper.find('.interhub-catalog__form input:not([type="number"])').exists()).toBe(false)
    const quantityInput = wrapper.find('.interhub-catalog__form input[type="number"]')
    expect(quantityInput.attributes('min')).toBe('1')
    expect(quantityInput.attributes('max')).toBe('20')
    expect(wrapper.text()).toContain('Количество ключей')
    expect(wrapper.text()).not.toContain('Аккаунт (временно необязательно)')
  })

  it('passes the selected voucher quantity only to the internal payment flow', async () => {
    const ctx = buildCtx({
      canPay: true,
      services: [{ service_id: 12, title: 'Three keys', category: '', type: 'VOUCHER', fields: [] }],
    })
    ctx.calculate = vi.fn(async () => { ctx.calculation = { success: true, fixed_amount: 117.47 } })
    ctx.checkPayment = vi.fn(async () => { ctx.check = { success: true, message: 'Доступно' } })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await wrapper.find('tbody tr').trigger('click')
    await wrapper.find('.interhub-catalog__form input[type="number"]').setValue('3')
    await wrapper.find('.interhub-catalog__form').trigger('submit')
    await Promise.resolve()
    await Promise.resolve()

    expect(ctx.calculate).toHaveBeenCalledWith({
      service_id: 12,
      account: '',
      params: {},
      flow_type: 'VOUCHER',
      quantity: 3,
    })
    expect(document.body.textContent).toContain('К покупке, шт.')
    expect(document.body.textContent).toContain('3')
  })

  it('resets voucher quantity to one when another service is selected', async () => {
    const ctx = buildCtx({
      services: [
        { service_id: 12, title: 'First voucher', category: '', type: 'VOUCHER', fields: [] },
        { service_id: 13, title: 'Second voucher', category: '', type: 'VOUCHER', fields: [] },
      ],
    })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await selectServiceByTitle(wrapper, 'First voucher')
    await wrapper.find('.interhub-catalog__form input[type="number"]').setValue('3')
    await selectServiceByTitle(wrapper, 'Second voucher')

    expect(wrapper.find('.interhub-catalog__form input[type="number"]').element.value).toBe('1')
  })

  it('groups extra provider fields separately from the purchase action', async () => {
    const ctx = buildCtx({
      services: [{
        service_id: 14,
        title: 'Voucher with count',
        category: '',
        type: 'VOUCHER',
        fields: [
          { name: 'nominal', type: 'LIST', required: true, value_list: [{ id: 25, title: 'USD 25' }] },
          { name: 'count', type: 'TEXT', required: false },
        ],
      }],
    })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await selectServiceByTitle(wrapper, 'Voucher with count')

    expect(wrapper.find('.interhub-catalog__fields').findAll('.field')).toHaveLength(3)
    expect(wrapper.find('.interhub-catalog__form > .interhub-catalog__actions').exists()).toBe(true)
  })

  it('shows an optional account field for fixed nominal services', async () => {
    const wrapper = mount(WorkInterhubSection, { props: { ctx: buildCtx() } })

    await selectServiceByTitle(wrapper, 'Mobile top up')
    const formInputs = wrapper.findAll('.interhub-catalog__form input')
    expect(formInputs).toHaveLength(1)
    expect(formInputs[0].attributes('required')).toBeUndefined()
    expect(wrapper.text()).toContain('Аккаунт (необязательно)')
    expect(wrapper.find('.interhub-catalog__form').classes()).toContain('has-optional-account')
  })

  it('shows the gift code after a completed obtain operation', async () => {
    const ctx = buildCtx({
      canPay: true,
      calculation: { success: true, message: 'Success', fixed_amount: 117.47 },
      check: { success: true, message: 'Success' },
      payment: { success: true, status: 0, params: { gift_code: 'TESTGIFTCODE' } },
    })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await wrapper.find('tbody tr').trigger('click')
    expect(wrapper.text()).toContain('TESTGIFTCODE')
    expect(wrapper.text()).toContain('Оплата успешна')

    expect(wrapper.find('.interhub-catalog__action-btn').text()).toContain('Получить')
  })

  it('shows one obtain button instead of technical payment steps', async () => {
    const ctx = buildCtx({ canPay: true })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await selectServiceByTitle(wrapper, 'Mobile top up')
    await wrapper.find('.interhub-catalog__form select').setValue('15')
    expect(wrapper.findAll('.interhub-catalog__action-btn')).toHaveLength(1)
    expect(wrapper.find('.interhub-catalog__action-btn').text()).toContain('Получить')
    expect(wrapper.text()).not.toContain('Узнать цену')
    expect(wrapper.text()).not.toContain('Сначала узнайте цену')
  })

  it('shows the hamster until the obtain sequence receives a result', async () => {
    let resolveCalculation
    const ctx = buildCtx({ canPay: true })
    ctx.calculate = vi.fn(() => new Promise((resolve) => { resolveCalculation = () => { ctx.calculation = { success: false, message: 'Нет цены' }; resolve() } }))
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await selectServiceByTitle(wrapper, 'Mobile top up')
    await wrapper.find('.interhub-catalog__form select').setValue('15')
    await wrapper.find('.interhub-catalog__form').trigger('submit')

    expect(wrapper.find('.interhub-catalog__obtain-overlay .wheel-and-hamster').exists()).toBe(true)
    resolveCalculation()
    await Promise.resolve()
    await Promise.resolve()
    expect(wrapper.find('.interhub-catalog__obtain-overlay').exists()).toBe(false)
    expect(document.body.textContent).toContain('Нет цены')
    expect(document.body.textContent).toContain('Не получена')
    wrapper.unmount()
  })

  it('keeps the hamster visible while a voucher batch is received in the background', async () => {
    const ctx = buildCtx({
      canPay: true,
      services: [{ service_id: 11, title: 'Steam voucher', category: '', type: 'VOUCHER', fields: [] }],
      payment: { success: false, status: 1, batch_id: 'batch-1', state: 'running', requested_quantity: 3, received_quantity: 1 },
    })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await wrapper.find('tbody tr').trigger('click')

    expect(wrapper.find('.interhub-catalog__obtain-overlay .wheel-and-hamster').exists()).toBe(true)
    expect(wrapper.find('.interhub-catalog__action-btn').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Получаем ключи: 1 из 3')
  })

  it('renders multiple received keys in a vertical list', async () => {
    const ctx = buildCtx({
      canPay: true,
      payment: { success: true, status: 0, gift_codes: ['FIRST-CODE', 'SECOND-CODE'] },
    })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await wrapper.find('tbody tr').trigger('click')
    const codes = wrapper.find('.interhub-catalog__gift-codes')
    expect(codes.exists()).toBe(true)
    expect(codes.findAll('.interhub-catalog__gift-code')).toHaveLength(2)
    expect(codes.text()).toContain('FIRST-CODE')
    expect(codes.text()).toContain('SECOND-CODE')
  })

  it('shows the cached purchase price for the selected nominal without calculate', async () => {
    const ctx = buildCtx({
      cachedPrices: [{ service_id: 7, nominal_id: 15, fixed_amount: 117.47, calculated_at: '2026-07-21T09:10:00+03:00' }],
    })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await selectServiceByTitle(wrapper, 'Mobile top up')
    await wrapper.find('.interhub-catalog__form select').setValue('15')

    expect(wrapper.text()).toContain('Закупочная цена из кэша: 117,47 ₽')
  })

  it('shows the full saved calculate response for a selected nominal', async () => {
    const ctx = buildCtx({
      cachedPrices: [{ service_id: 7, nominal_id: 15, fixed_amount: 117.47, provider_response: { success: true, fixed_amount: 117.47, currency: 'TRY' } }],
    })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await selectServiceByTitle(wrapper, 'Mobile top up')
    await wrapper.find('.interhub-catalog__form select').setValue('15')
    expect(wrapper.text()).toContain('Полный ответ calculate')
    expect(wrapper.text()).toContain('"fixed_amount": 117.47')
  })

  it('sorts nominal options by their numeric value', async () => {
    const ctx = buildCtx({
      services: [{ service_id: 11, title: 'Sorted voucher', category: '', type: 'VOUCHER', fields: [{ name: 'nominal', type: 'LIST', required: true, value_list: [{ id: 100, title: 'USD 100' }, { id: 5, title: 'USD 5' }, { id: 25, title: 'USD 25' }] }] }],
    })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await selectServiceByTitle(wrapper, 'Sorted voucher')
    expect(wrapper.find('.interhub-catalog__form select').findAll('option').map((option) => option.text())).toEqual(['Выберите значение', 'USD 5', 'USD 25', 'USD 100'])
  })

  it('allows only the owner to start the cached price refresh and export', async () => {
    const ctx = buildCtx({
      canManagePrices: true,
      priceRefresh: { processed: 4, total: 10, successes: 3, errors: 1, message: 'Расчёт цен завершён' },
    })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    const buttons = wrapper.findAll('button')
    await buttons.find((button) => button.text().includes('Обновить закупочные цены')).trigger('click')
    await buttons.find((button) => button.text() === 'Выгрузить Excel').trigger('click')

    expect(ctx.refreshPrices).toHaveBeenCalledTimes(1)
    expect(ctx.exportPrices).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('Обновление цен: 4 из 10')
  })

  it('explains the documented polling schedule for a processing payment', async () => {
    const ctx = buildCtx({
      calculation: { success: true, message: 'Success' },
      payment: { success: true, status: 1, params: {} },
    })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await wrapper.find('tbody tr').trigger('click')
    expect(wrapper.text()).toContain('Первая проверка статуса — через 1 минуту')
  })
})
