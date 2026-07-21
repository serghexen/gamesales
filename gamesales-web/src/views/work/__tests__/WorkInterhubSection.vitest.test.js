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
    pay: vi.fn(),
    refreshPaymentStatus: vi.fn(),
    setSearchFromEvent: vi.fn(),
    ...overrides,
  }
}

describe('WorkInterhubSection', () => {
  it('renders normalized services and payment types', () => {
    const wrapper = mount(WorkInterhubSection, { props: { ctx: buildCtx() } })

    expect(wrapper.text()).toContain('Mobile top up')
    expect(wrapper.text()).toContain('Фикс. номинал')
    expect(wrapper.text()).toContain('PIN-код')
    expect(wrapper.text()).toContain('nominal')
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

  it('opens a dynamic form and sends the same params to a separate check', async () => {
    const ctx = buildCtx()
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await wrapper.findAll('tbody tr')[0].trigger('click')
    expect(wrapper.text()).toContain('Шаги оплаты')

    const inputs = wrapper.findAll('.interhub-catalog__form input')
    await inputs[0].setValue('998877')
    await wrapper.find('.interhub-catalog__form select').setValue('15')
    await wrapper.find('.interhub-catalog__form').trigger('submit.prevent')

    expect(ctx.checkPayment).toHaveBeenCalledWith({
      service_id: 7,
      account: '998877',
      params: { nominal: 15 },
      flow_type: 'TOP_UP_FIXED',
    })
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
      services: [{ service_id: 10, title: 'Steam CIS', category: '', type: 'TOP_UP', min_amount: 7.79, fields: [] }],
    })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await wrapper.find('tbody tr').trigger('click')
    expect(wrapper.find('.interhub-catalog__form input[type="number"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Минимум: 7.79')
  })

  it('keeps account optional for voucher services', async () => {
    const ctx = buildCtx({
      services: [{ service_id: 11, title: 'Steam voucher', category: '', type: 'VOUCHER', fields: [{ name: 'nominal', type: 'LIST', required: true, value_list: [{ id: 25, title: 'USD 25' }] }] }],
    })
    const wrapper = mount(WorkInterhubSection, { props: { ctx } })

    await wrapper.find('tbody tr').trigger('click')
    const accountInput = wrapper.find('.interhub-catalog__form input')
    expect(accountInput.attributes('required')).toBeUndefined()
    expect(wrapper.text()).toContain('Аккаунт (временно необязательно)')
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

    await wrapper.find('tbody tr').trigger('click')
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
