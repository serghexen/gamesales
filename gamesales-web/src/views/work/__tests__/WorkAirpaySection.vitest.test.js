import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import WorkAirpaySection from '../sections/WorkAirpaySection.vue'
import { apiGet } from '../../../api/http'

vi.mock('../../../api/http', () => ({ apiGet: vi.fn(), apiPost: vi.fn() }))
vi.mock('../sections/WorkAirpayCatalog.vue', () => ({ default: { template: '<div />' } }))
let wrapper

afterEach(() => {
  // Завершаем жизненный цикл каждого запроса и очищаем подмену API.
  wrapper?.unmount()
  vi.resetAllMocks()
})

describe('WorkAirpaySection', () => {
  it('labels the allowed overdraft and handles missing provider currency', async () => {
    // Подтверждённый кредит входит в доступную сумму, отсутствие валюты видно оператору.
    apiGet.mockResolvedValue({ configured: true, balance: 12, overdraft: 5000, currency: '' })
    wrapper = mount(WorkAirpaySection)
    await flushPromises()
    expect(wrapper.text()).toContain('Разрешённый овердрафт')
    expect(wrapper.get('[data-testid="airpay-balance"]').text()).toBe('12,00 · валюта не указана')
  })
  it('shows a real zero balance and overdraft in the provider currency', async () => {
    // Нулевой остаток из успешного ответа отличается от отсутствия подключения.
    apiGet.mockResolvedValue({ configured: true, balance: 0, overdraft: 5000, currency: 'RUB' })
    wrapper = mount(WorkAirpaySection, { props: { token: 'crm-token' } })
    await flushPromises()
    expect(wrapper.get('[data-testid="airpay-balance"]').text()).toBe('0,00 ₽')
    expect(wrapper.get('[data-testid="airpay-overdraft"]').text()).toBe('5 000,00 ₽')
    expect(wrapper.get('[data-testid="airpay-available"]').text()).toBe('5 000,00 ₽')
    expect(apiGet).toHaveBeenCalledWith('/integrations/airpay/balance', { token: 'crm-token' })
  })

  it('does not invent amounts when credentials are missing', async () => {
    // Не настроенный сервер показывает подсказку без нулевого баланса и формы с секретами.
    apiGet.mockResolvedValue({ configured: false, balance: null, overdraft: null, currency: '' })
    wrapper = mount(WorkAirpaySection)
    await flushPromises()
    expect(wrapper.text()).toContain('Airpay ещё не подключён')
    expect(wrapper.find('[data-testid="airpay-balance"]').exists()).toBe(false)
    expect(wrapper.find('input').exists()).toBe(false)
  })

  it('clears stale amounts on refresh failure and allows retry', async () => {
    // Ошибка нового запроса не должна оставлять старую сумму под видом актуальной.
    apiGet.mockResolvedValueOnce({ configured: true, balance: 10, overdraft: 0, currency: 'USD' })
      .mockRejectedValueOnce(new Error('Нет соединения с Airpay'))
      .mockResolvedValueOnce({ configured: true, balance: -2, overdraft: 0, currency: 'USD' })
    wrapper = mount(WorkAirpaySection)
    await flushPromises()
    await wrapper.get('button').trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('Нет соединения')
    expect(wrapper.find('[data-testid="airpay-balance"]').exists()).toBe(false)
    await wrapper.get('button').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="airpay-balance"]').text()).toContain('-2,00')
  })

  it('disables refresh while loading and ignores a response from the previous session', async () => {
    // При смене токена запоздалый ответ прежнего пользователя не перезаписывает новый баланс.
    let finishOldRequest
    apiGet.mockImplementationOnce(() => new Promise(resolve => { finishOldRequest = resolve }))
      .mockResolvedValueOnce({ configured: true, balance: 20, overdraft: 0, currency: 'RUB' })
    wrapper = mount(WorkAirpaySection, { props: { token: 'old-token' } })
    expect(wrapper.get('button').attributes('disabled')).toBeDefined()
    await wrapper.setProps({ token: 'new-token' })
    await flushPromises()
    finishOldRequest({ configured: true, balance: 10, overdraft: 0, currency: 'RUB' })
    await flushPromises()
    expect(wrapper.get('[data-testid="airpay-balance"]').text()).toContain('20,00')
  })
})


it('subtracts used credit from the amount available for purchases', async () => {
  // Отрицательный баланс уменьшает кредитный лимит, а не добавляет его повторно.
  apiGet.mockResolvedValue({ configured: true, balance: -4500, overdraft: 5000, currency: 'RUB' })
  wrapper = mount(WorkAirpaySection)
  await flushPromises()
  expect(wrapper.get('[data-testid="airpay-available"]').text()).toBe('500,00 ₽')
})
