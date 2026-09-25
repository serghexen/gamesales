import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import WorkAirpayQueue from '../sections/WorkAirpayQueue.vue'
import { resolveAirpayJob } from '../airpayJob'
import { apiGet, apiPost } from '../../../api/http'
vi.mock('../../../api/http', () => ({ apiGet: vi.fn(), apiPost: vi.fn() }))
const report = { summary: { queued: 1, running: 1, stale: 1, blocked_by_config: 1, failed_24h: 0 }, items: [
  { job_id: 'queue', transaction_id: '123', action: 'pay', state: 'queued', progress: 0, reason: 'payments_disabled' },
  { job_id: 'lost', transaction_id: '456', action: 'pay', state: 'running', progress: 1, reason: 'interrupted' },
] }
let wrapper
afterEach(() => {
  // Незавершённый опрос не переходит в другой тест.
  wrapper?.unmount()
  vi.useRealTimers()
  vi.resetAllMocks()
})
describe('Airpay queue recovery', () => {
  it('reads diagnostics only on request and opens saved purchase without payment', async () => {
    // Раскрытие панели читает БД; переход к покупке передаёт только ID.
    apiGet.mockResolvedValue(report)
    wrapper = mount(WorkAirpayQueue, { props: { token: 'crm' } })
    expect(apiGet).not.toHaveBeenCalled()
    await wrapper.get('button').trigger('click'); await flushPromises()
    expect(wrapper.text()).toContain('Исполнитель потерян')
    expect(wrapper.text()).toContain('Остановлены настройкой оплаты: 1')
    await wrapper.findAll('button').find(button => button.text() === 'Открыть сохранённую покупку').trigger('click')
    expect(wrapper.emitted('open')[0]).toEqual(['123'])
    expect(apiPost).not.toHaveBeenCalled()
  })
  it('cancels only a queued job after explicit confirmation and displays a worker conflict', async () => {
    // Подтверждение отмены не является отменой платежа; сервер может уже занять задание.
    apiGet.mockResolvedValue(report)
    apiPost.mockRejectedValue(new Error('Задание уже выполняется'))
    wrapper = mount(WorkAirpayQueue)
    await wrapper.get('button').trigger('click'); await flushPromises()
    const cancel = wrapper.findAll('button').filter(button => button.text() === 'Отменить запуск задания')
    expect(cancel).toHaveLength(1)
    await cancel[0].trigger('click')
    expect(apiPost).not.toHaveBeenCalled()
    await wrapper.findAll('button').find(button => button.text() === 'Да, отменить запуск').trigger('click'); await flushPromises()
    expect(apiPost.mock.calls[0][0]).toBe('/integrations/airpay/jobs/queue/cancel')
    expect(wrapper.get('[role="alert"]').text()).toBe('Задание уже выполняется')
  })
  it('stops waiting after two minutes without cancelling or repeating the job', async () => {
    // Долгое задание продолжает жить на сервере, но больше не удерживает модалку.
    vi.useFakeTimers()
    const job = { job_id: 'saved', state: 'running' }
    apiGet.mockResolvedValue({ job })
    const pending = resolveAirpayJob({ job }).catch(error => error)
    await vi.advanceTimersByTimeAsync(120000)
    expect((await pending).message).toContain('Ожидание затянулось')
    expect(apiPost).not.toHaveBeenCalled()
  })
  it('releases the view even if a read request never answers', async () => {
    // Таймаут GET не может считаться отказом оплаты или поводом для нового pay.
    vi.useFakeTimers()
    apiGet.mockImplementation(() => new Promise(() => {}))
    const pending = resolveAirpayJob({ job: { job_id: 'saved', state: 'running' } }).catch(error => error)
    await vi.advanceTimersByTimeAsync(16000)
    expect((await pending).message).toContain('Нет ответа очереди')
    expect(apiPost).not.toHaveBeenCalled()
  })
})
