import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { resolveAirpayJob } from '../airpayJob'
import WorkAirpayBatch from '../sections/WorkAirpayBatch.vue'
import WorkAirpayTransaction from '../sections/WorkAirpayTransaction.vue'
import WorkAirpayHistory from '../sections/WorkAirpayHistory.vue'
import { apiGet, apiPost } from '../../../api/http'

vi.mock('../../../api/http', () => ({ apiGet: vi.fn(), apiPost: vi.fn() }))
const item = { agent_transaction_id: '1', service_title: 'Voucher', account: 'test', purchase_kind: 'voucher',
  state: 'checked', amount: '10.00', currency: 'RUB', payments_enabled: true }
const batch = { batch_id: '1', quantity: 2, state: 'partial', paid_quantity: 1, received_quantity: 0,
  total_amount: '20.00', remaining_amount: '10.00', currency: 'RUB', payments_enabled: true,
  items: [{ ...item, state: 'paid' }, { ...item, agent_transaction_id: '2' }] }
let wrapper
afterEach(() => {
  // Не оставляем таймеры опроса после закрытия тестовой формы.
  wrapper?.unmount()
  wrapper = null
  vi.useRealTimers()
  vi.resetAllMocks()
})

describe('Airpay queued workflow', () => {
  it('polls only saved job state and returns its completed result', async () => {
    // Длительная работа не создаёт новых check/pay при каждом обновлении прогресса.
    vi.useFakeTimers()
    const job = { job_id: 'queue-id', state: 'queued', progress: 0 }
    const progress = vi.fn()
    apiGet.mockResolvedValueOnce({ job: { ...job, state: 'running', progress: 1 } })
      .mockResolvedValueOnce({ job: { ...job, state: 'succeeded', result: batch } })
    const pending = resolveAirpayJob({ job }, { token: 'crm', progress })
    await vi.advanceTimersByTimeAsync(2000)
    expect(await pending).toEqual(batch)
    expect(apiGet).toHaveBeenCalledTimes(2)
    expect(apiGet).toHaveBeenCalledWith('/integrations/airpay/jobs/queue-id', { token: 'crm' })
    expect(progress).toHaveBeenCalledTimes(3)
    expect(apiPost).not.toHaveBeenCalled()
  })

  it('stops polling a closed view and never cancels the saved purchase', async () => {
    // Закрытие вкладки отменяет только просмотр, серверную оплату нельзя считать отменённой.
    vi.useFakeTimers()
    const pending = resolveAirpayJob({ job: { job_id: 'queue', state: 'running' } }, { active: () => false }).catch(error => error)
    await vi.advanceTimersByTimeAsync(1000)
    expect((await pending).cancelled).toBe(true)
    expect(apiGet).not.toHaveBeenCalled()
    expect(apiPost).not.toHaveBeenCalled()
  })

  it('surfaces a saved job failure without retrying a payment', async () => {
    // Ошибка очереди требует чтения журнала, а не повторного платёжного POST.
    await expect(resolveAirpayJob({ job: { state: 'failed', error: 'Цена устарела', error_status: 410 } })).rejects.toMatchObject({ status: 410 })
    expect(apiPost).not.toHaveBeenCalled()
  })

  it('renews only the remaining group and checks it without buying', async () => {
    // После переоценки остаётся отдельная кнопка подтверждения уже новой суммы.
    const renewed = { ...batch, batch_id: '3', quantity: 1, paid_quantity: 0, total_amount: '11.00', remaining_amount: '11.00', state: 'checked', items: [{ ...item, agent_transaction_id: '3', amount: '11.00' }] }
    apiPost.mockResolvedValueOnce({ draft: { preparation_token: 'new-draft' }, batch: renewed }).mockResolvedValueOnce({ success: true })
    apiGet.mockResolvedValueOnce(renewed)
    wrapper = mount(WorkAirpayBatch, { props: { batch }, global: { stubs: { teleport: true } } })
    await wrapper.findAll('button').find(button => button.text() === 'Проверить неоплаченный остаток').trigger('click')
    await flushPromises()
    expect(apiPost.mock.calls.map(call => call[0])).toEqual(['/integrations/airpay/batches/1/renew', '/integrations/airpay/batches/3/check'])
    expect(wrapper.text()).toContain('Покупка 1 ключей')
    expect(wrapper.text()).toContain('11.00 RUB')
    expect(wrapper.text()).toContain('Продолжить покупку')
  })

  it('reveals stored codes separately even when payments are disabled', async () => {
    // Наличие результата не запускает выдачу у поставщика; просмотр использует собственный endpoint.
    wrapper = mount(WorkAirpayTransaction, { props: { transaction: { ...item, state: 'paid', result_available: true, payments_enabled: false } } })
    expect(wrapper.find('code').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Осталось получить код')
    apiPost.mockResolvedValueOnce({ value: 'STORED-TEST-CODE' })
    await wrapper.findAll('button').find(button => button.text() === 'Показать сохранённый код').trigger('click')
    await flushPromises()
    expect(apiPost.mock.calls[0][0]).toBe('/integrations/airpay/transactions/1/result')
    expect(wrapper.get('code').text()).toBe('STORED-TEST-CODE')
  })

  it('keeps the CRM archive separate from Hub history and payment routes', async () => {
    // Архив не предлагает покупку пачки, а чтение его записи не обращается в Hub по совпавшему ID.
    apiGet.mockResolvedValueOnce({ items: [], legacy_available: true }).mockResolvedValueOnce({ items: [{ ...item, state: 'paid', result_available: true, payments_enabled: false, batch: { quantity: 2 } }], legacy_available: true })
    wrapper = mount(WorkAirpayHistory, { global: { stubs: { teleport: true } } })
    await flushPromises()
    await wrapper.findAll('.airpay-history-sources button')[1].trigger('click')
    await flushPromises()
    expect(apiGet.mock.calls[1][0]).toContain('archive=crm')
    expect(wrapper.text()).not.toContain('Открыть покупку')
    apiGet.mockResolvedValueOnce({ ...item, state: 'paid', result_available: true, payments_enabled: false, batch: { quantity: 2 } })
    await wrapper.get('.airpay-history-service').trigger('click'); await flushPromises()
    expect(apiGet.mock.calls[2][0]).toBe('/integrations/airpay/legacy/transactions/1')
    expect(wrapper.text()).not.toContain('Открыть покупку')
    apiPost.mockResolvedValueOnce({ value: 'ARCHIVED-CODE' })
    await wrapper.findAll('button').find(button => button.text() === 'Показать сохранённый код').trigger('click')
    await flushPromises()
    expect(apiPost.mock.calls[0][0]).toBe('/integrations/airpay/legacy/transactions/1/result')
  })
})
