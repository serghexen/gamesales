import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import WorkSbpPaymentCenter from '../sections/WorkSbpPaymentCenter.vue'
import { apiGet, apiPost } from '../../../api/http'

vi.mock('../../../api/http', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
}))

function payment(overrides = {}) {
  // Даём компоненту полный публичный объект операции без банковских секретов.
  return {
    id: '32f79af6-285e-4a37-a74f-10116fb963bb',
    order_id: 'crm_123',
    description: 'A Way Out для PS5',
    buyer: 'Покупатель из Telegram',
    created_by: 'manager-1',
    amount: 199000,
    currency: 'RUB',
    state: 'pending',
    provider_status: 'NEW',
    qr_data_url: 'data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=',
    last_error: '',
    expires_at: '2026-08-31T15:15:00Z',
    confirmed_at: null,
    created_at: '2026-08-31T15:00:00Z',
    is_seen: false,
    ...overrides,
  }
}

function mountCenter() {
  // Teleport оставляем внутри wrapper, чтобы тест проверял реальную форму модалки.
  return mount(WorkSbpPaymentCenter, {
    props: { ctx: { authToken: 'token-1', currentUsername: 'manager-1' } },
    global: { stubs: { teleport: true, transition: false, 'transition-group': false } },
  })
}

afterEach(() => {
  vi.clearAllMocks()
})

describe('WorkSbpPaymentCenter', () => {
  it('sends description, internal buyer and amount in kopecks without preset buttons', async () => {
    apiGet.mockImplementation(async (path) => path.includes('/config')
      ? { enabled: true, min_amount: 1000, max_amount: 10000000, qr_lifetime_minutes: 15 }
      : { total: 0, unseen_confirmed_count: 0, items: [] })
    apiPost.mockResolvedValue(payment())
    const wrapper = mountCenter()
    await flushPromises()

    await wrapper.find('[data-test="sbp-open"]').trigger('click')
    await wrapper.find('[data-test="sbp-description"]').setValue('A Way Out для PS5')
    await wrapper.find('[data-test="sbp-buyer"]').setValue('Покупатель из Telegram')
    await wrapper.find('[data-test="sbp-amount"]').setValue('1990')
    expect(wrapper.text()).not.toContain('500 ₽')
    await wrapper.find('[data-test="sbp-create"]').trigger('submit')
    await flushPromises()

    expect(apiPost).toHaveBeenCalledWith('/payments/tbank/sbp', {
      description: 'A Way Out для PS5',
      buyer: 'Покупатель из Telegram',
      amount: 199000,
    }, { token: 'token-1' })
    expect(wrapper.find('[data-test="sbp-payment-result"]').text()).toContain('Покупатель из Telegram')
    wrapper.unmount()
  })

  it('shows shared history and marks confirmed payments seen only when history is opened', async () => {
    const confirmed = payment({ state: 'confirmed', confirmed_at: '2026-08-31T15:02:00Z' })
    apiGet.mockImplementation(async (path) => path.includes('/config')
      ? { enabled: true, min_amount: 1000, max_amount: 10000000, qr_lifetime_minutes: 15 }
      : { total: 1, unseen_confirmed_count: 1, items: [confirmed] })
    apiPost.mockResolvedValue(null)
    const wrapper = mountCenter()
    await flushPromises()

    expect(wrapper.find('[data-test="sbp-unseen"]').text()).toBe('1')
    await wrapper.find('[data-test="sbp-open"]').trigger('click')
    await wrapper.find('[data-test="sbp-tab-history"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('A Way Out для PS5')
    expect(wrapper.text()).toContain('manager-1')
    expect(apiPost).toHaveBeenCalledWith('/payments/tbank/sbp/mark-seen', {}, { token: 'token-1' })
    expect(wrapper.find('[data-test="sbp-unseen"]').exists()).toBe(false)
    wrapper.unmount()
  })
})
