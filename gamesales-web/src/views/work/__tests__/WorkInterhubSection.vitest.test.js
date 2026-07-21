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
    pay: vi.fn(),
    refreshPaymentStatus: vi.fn(),
    refreshPrices: vi.fn(),
    exportPrices: vi.fn(),
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

  it('sorts services by title in both directions', async () => {
    const wrapper = mount(WorkInterhubSection, { props: { ctx: buildCtx() } })

    expect(wrapper.findAll('tbody tr')[0].text()).toContain('Gift PIN')
    await wrapper.find('.interhub-catalog__sort').trigger('click')
    expect(wrapper.findAll('tbody tr')[0].text()).toContain('Mobile top up')
  })

  it('opens a fixed nominal form and sends its params to a separate check', async () => {
    const ctx = buildCtx()
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await selectServiceByTitle(wrapper, 'Mobile top up')
    expect(wrapper.text()).toContain('Шаги оплаты')

    await wrapper.find('.interhub-catalog__form select').setValue('15')
    await wrapper.find('.interhub-catalog__form').trigger('submit.prevent')

    expect(ctx.checkPayment).toHaveBeenCalledWith({
      service_id: 7,
      account: '',
      params: { nominal: 15 },
      flow_type: 'TOP_UP_FIXED',
    })
    expect(ctx.resetPaymentFlow).toHaveBeenCalledTimes(1)
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
  })

  it('hides the account field for voucher services', async () => {
    const ctx = buildCtx({
      services: [{ service_id: 11, title: 'Steam voucher', category: '', type: 'VOUCHER', fields: [{ name: 'nominal', type: 'LIST', required: true, value_list: [{ id: 25, title: 'USD 25' }] }] }],
    })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await wrapper.find('tbody tr').trigger('click')
    expect(wrapper.find('.interhub-catalog__form input').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Аккаунт (временно необязательно)')
  })

  it('hides the account field for fixed nominal services', async () => {
    const wrapper = mount(WorkInterhubSection, { props: { ctx: buildCtx() } })

    await selectServiceByTitle(wrapper, 'Mobile top up')
    const formInputs = wrapper.findAll('.interhub-catalog__form input')
    expect(formInputs).toHaveLength(0)
    expect(wrapper.text()).not.toContain('Аккаунт (временно необязательно)')
  })

  it('lets only the owner confirm a checked payment and shows the gift code', async () => {
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

    await wrapper.setProps({ ctx: { ...ctx, payment: null } })
    const payButton = wrapper.findAll('button').find((button) => button.text() === 'Оплатить')
    await payButton.trigger('click')
    expect(ctx.pay).toHaveBeenCalledTimes(1)
  })

  it('keeps calculate and check as separate actions', async () => {
    const ctx = buildCtx()
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await selectServiceByTitle(wrapper, 'Mobile top up')
    await wrapper.find('.interhub-catalog__form select').setValue('15')
    const calculateButton = wrapper.findAll('button').find((button) => button.text().includes('Узнать цену'))
    await calculateButton.trigger('click')

    expect(ctx.calculate).toHaveBeenCalledWith({
      service_id: 7,
      account: '',
      params: { nominal: 15 },
      flow_type: 'TOP_UP_FIXED',
    })
    expect(ctx.checkPayment).not.toHaveBeenCalled()
  })

  it('groups price and availability actions into a compact two-button block', async () => {
    const wrapper = mount(WorkInterhubSection, { props: { ctx: buildCtx() } })

    await selectServiceByTitle(wrapper, 'Mobile top up')

    const actions = wrapper.find('.interhub-catalog__actions')
    expect(actions.exists()).toBe(true)
    expect(actions.findAll('.interhub-catalog__action-btn')).toHaveLength(2)
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
