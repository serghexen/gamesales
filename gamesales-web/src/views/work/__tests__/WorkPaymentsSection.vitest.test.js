import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { reactive } from 'vue'
import WorkPaymentsSection from '../sections/WorkPaymentsSection.vue'
import WorkInterhubSection from '../sections/WorkInterhubSection.vue'
import WorkAirpaySection from '../sections/WorkAirpaySection.vue'
import { apiGet, apiPost } from '../../../api/http'

vi.mock('../../../api/http', () => ({ apiGet: vi.fn(), apiPost: vi.fn() }))

const wrappers = []

function mountPayments(overrides = {}) {
  // Оставляем настоящий экран Interhub, чтобы проверить изоляцию его формы и телепортов.
  const ctx = reactive({ services: [], search: '', balance: 12345, currency: 'RUB', token: 'crm-token',
    canViewHistory: true, salesHistory: [], resetPaymentFlow: vi.fn(), loadSalesHistory: vi.fn(), ...overrides })
  const wrapper = mount(WorkPaymentsSection, { props: { ctx }, attachTo: document.body,
    global: { stubs: { WorkSupplierCatalog: true } } })
  wrappers.push(wrapper)
  return { wrapper, ctx }
}

afterEach(() => {
  // Удаляем модалки и сетевые заглушки, чтобы соседние сценарии не влияли друг на друга.
  wrappers.splice(0).forEach(wrapper => wrapper.unmount())
  vi.resetAllMocks()
})

describe('WorkPaymentsSection', () => {
  it('opens Interhub by default without requesting Airpay', () => {
    // Текущий рабочий сценарий доступен сразу, реквизиты Airpay не нужны до выбора.
    const { wrapper } = mountPayments()
    const providers = wrapper.findAll('.work-payments__provider')
    expect(providers).toHaveLength(2)
    expect(providers[0].attributes('aria-pressed')).toBe('true')
    expect(providers[1].text()).toContain('Airpay')
    expect(wrapper.findComponent(WorkInterhubSection).exists()).toBe(true)
    expect(apiGet).not.toHaveBeenCalled()
  })

  it('switches to an isolated Airpay balance and returns to Interhub', async () => {
    // Баланс Interhub и его действия не должны отображаться внутри Airpay.
    apiGet.mockImplementation(async path => {
      // Проверяем оба независимых метода Airpay, пока в Interhub остаётся свой баланс.
      return path.endsWith('/services') ? { configured: true, items: [], total: 0 }
        : { configured: true, balance: 7, overdraft: 5000, currency: 'RUB' }
    })
    const { wrapper, ctx } = mountPayments()
    await wrapper.findAll('.work-payments__provider')[1].trigger('click')
    await flushPromises()
    expect(wrapper.findComponent(WorkInterhubSection).exists()).toBe(false)
    expect(wrapper.find('.interhub-catalog__balance').exists()).toBe(false)
    expect(wrapper.get('[data-testid="airpay-balance"]').text()).toContain('7,00')
    expect(apiGet).toHaveBeenCalledWith('/integrations/airpay/balance', { token: 'crm-token' })
    await wrapper.findAll('.work-payments__provider')[0].trigger('click')
    expect(wrapper.findComponent(WorkInterhubSection).exists()).toBe(true)
    expect(wrapper.find('.airpay').exists()).toBe(false)
    expect(ctx.resetPaymentFlow).toHaveBeenCalledTimes(2)
  })

  it('closes the Interhub history when switching suppliers', async () => {
    // Телепорт истории не должен оставаться поверх экрана другого поставщика.
    apiGet.mockResolvedValue({ configured: false, items: [], total: 0 })
    const { wrapper } = mountPayments()
    await wrapper.get('.interhub-catalog__history-action').trigger('click')
    expect(document.querySelector('.interhub-history')).not.toBeNull()
    await wrapper.findAll('.work-payments__provider')[1].trigger('click')
    expect(document.querySelector('.interhub-history')).toBeNull()
  })

  it('lets an owner fill and check Airpay when supplier payments are disabled', async () => {
    // Проходим реальную цепочку компонентов: запрет pay не блокирует поля и отдельный check.
    const service = { service_id: 'A1', title: 'Voucher', group: '', country: '', fixed_payment: true, inputs: [], displays: [] }
    apiGet.mockImplementation(async path => path.includes('/service?') ? service
      : path.endsWith('/services') ? { configured: true, items: [service], total: 1 }
        : { configured: true, balance: 100, currency: 'RUB' })
    const { wrapper, ctx } = mountPayments({ canPay: false, supplierOffline: true, canPrepareAirpay: true })
    await wrapper.findAll('.work-payments__provider')[1].trigger('click')
    await flushPromises()
    expect(wrapper.getComponent(WorkAirpaySection).props('canPrepare')).toBe(true)
    await wrapper.get('.airpay-catalog__service').trigger('click')
    await flushPromises()
    const form = wrapper.get('#airpay-service-details form')
    expect(form.get('input').attributes('disabled')).toBeUndefined()
    expect(form.find('select').exists()).toBe(false)
    expect(form.text()).toContain('Код ваучера')
    await form.get('input').setValue('12345')
    apiPost.mockResolvedValueOnce({ preparation_token: 'signed', agent_transaction_id: '12' })
      .mockResolvedValueOnce({ success: true, retryable: false, scheme: 'simple', displays: [], purchase_amount: '10.00', purchase_ready: true, payments_enabled: false })
    await form.trigger('submit')
    await flushPromises()
    expect(apiPost.mock.calls.map(([path]) => path)).toEqual(['/integrations/airpay/prepare', '/integrations/airpay/check'])
    expect(apiPost.mock.calls[0][1].fields.account).toBe('12345')
    expect(document.querySelector('[role="dialog"]').getAttribute('aria-label')).toBe('Проверьте покупку')
    expect(document.querySelector('.airpay-check__confirmation button.btn').disabled).toBe(true)
    expect(ctx.canPay).toBe(false)
  })

  it('does not grant Airpay preparation to a user without the owner permission', async () => {
    // Право на check явно передаётся из роли, а не выводится из наличия формы или разрешения чужого поставщика.
    apiGet.mockResolvedValue({ configured: false, items: [], total: 0 })
    const { wrapper } = mountPayments({ canPay: true, canPrepareAirpay: false })
    await wrapper.findAll('.work-payments__provider')[1].trigger('click')
    await flushPromises()
    expect(wrapper.getComponent(WorkAirpaySection).props('canPrepare')).toBe(false)
  })

  it('keeps Interhub usable after an Airpay API failure without changing its balance or actions', async () => {
    // Отсутствующая настройка Airpay не должна портить контекст работающего Interhub.
    apiGet.mockRejectedValue(new Error('Airpay недоступен'))
    const { wrapper, ctx } = mountPayments()
    const originalHistory = ctx.loadSalesHistory
    await wrapper.findAll('.work-payments__provider')[1].trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Airpay недоступен')
    await wrapper.findAll('.work-payments__provider')[0].trigger('click')
    await flushPromises()
    expect(wrapper.findComponent(WorkInterhubSection).exists()).toBe(true)
    expect(ctx.balance).toBe(12345)
    expect(ctx.loadSalesHistory).toBe(originalHistory)
    expect(apiPost).not.toHaveBeenCalled()
  })

  it('locks switching during Airpay work and unlocks only when it completes', async () => {
    // Симметричная блокировка защищает оба экрана от ухода во время операции.
    apiGet.mockResolvedValue({ configured: false, items: [], total: 0 })
    const { wrapper } = mountPayments()
    await wrapper.findAll('.work-payments__provider')[1].trigger('click')
    await flushPromises()
    const airpay = wrapper.getComponent(WorkAirpaySection)
    airpay.vm.$emit('busy-change', true)
    await flushPromises()
    expect(wrapper.findAll('.work-payments__provider')[0].attributes('disabled')).toBeDefined()
    airpay.vm.$emit('busy-change', false)
    await flushPromises()
    expect(wrapper.findAll('.work-payments__provider')[0].attributes('disabled')).toBeUndefined()
  })

  it.each([{ calculationLoading: true }, { checkLoading: true }, { paymentLoading: true }, { payment: { status: 1 } }])('keeps an unfinished operation visible: %j', async (state) => {
    // Смена поставщика не должна отменить ожидание оплаты или потерять её результат.
    const { wrapper, ctx } = mountPayments(state)
    const airpay = wrapper.findAll('.work-payments__provider')[1]
    expect(airpay.attributes('disabled')).toBeDefined()
    await airpay.trigger('click')
    expect(ctx.resetPaymentFlow).not.toHaveBeenCalled()
    expect(apiGet).not.toHaveBeenCalled()
    Object.assign(ctx, { calculationLoading: false, checkLoading: false, paymentLoading: false, payment: { status: 0 } })
    await flushPromises()
    expect(airpay.attributes('disabled')).toBeUndefined()
  })
})
