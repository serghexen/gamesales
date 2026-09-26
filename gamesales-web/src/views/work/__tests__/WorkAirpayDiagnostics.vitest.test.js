import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { apiGet, apiPost } from '../../../api/http'
import WorkAirpayDiagnostics from '../sections/WorkAirpayDiagnostics.vue'

vi.mock('../../../api/http', () => ({ apiGet: vi.fn(), apiPost: vi.fn() }))
let wrapper
const run = { id: 'bbf9af7b-4f3e-4847-9574-ef2e9cc27cf5', state: 'active', total: 2, processed: 0, items: [{ service_id: 'A1', title: 'Email service', state: 'pending' }, { service_id: 'A2', title: 'Direct service', state: 'pending' }] }
function button(text) {
  // Действия находим по видимому тексту, проверяя пользовательский путь.
  return wrapper.findAll('button').find(node => node.text() === text)
}
function open() {
  // Все HTTP подменены: даже запущенный опрос не обращается к реальному поставщику.
  wrapper = mount(WorkAirpayDiagnostics, { props: { token: 'owner' }, global: { stubs: { teleport: true } } })
}
afterEach(() => {
  // Таймер продолжения не должен переживать закрытую форму или тест.
  wrapper?.unmount()
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.resetAllMocks()
})
describe('Airpay diagnostic polling', () => {
  it('reads the saved report without starting checks and shows IDs on demand', async () => {
    // Открытие сохранённого отчёта не означает согласие на новые запросы поставщику.
    apiGet.mockResolvedValue({ run: { ...run, processed: 1, items: [{ ...run.items[0], state: 'rejected', result: 204, message: 'Валюта', agent_transaction_id: '9223372036854775000' }] } })
    open(); await flushPromises()
    expect(apiPost).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Код 204')
    expect(wrapper.get('details dd').text()).toBe('9223372036854775000')
    expect(button('Продолжить опрос')).toBeDefined()
  })

  it('starts one sequential check and pauses before another position', async () => {
    // Пауза не обрывает отправленный check, но не даёт таймеру начать следующий.
    vi.useFakeTimers()
    apiGet.mockResolvedValue({ run: null })
    let finish
    apiPost.mockResolvedValueOnce({ run }).mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
    open(); await flushPromises()
    await button('Начать опрос').trigger('click'); await flushPromises()
    expect(apiPost.mock.calls.map(call => call[0])).toEqual(['/integrations/airpay/diagnostics', `/integrations/airpay/diagnostics/${run.id}/next`])
    await button('Пауза после текущей позиции').trigger('click')
    finish({ run: { ...run, processed: 1, items: [{ ...run.items[0], state: 'ok' }, run.items[1]] } }); await flushPromises()
    await vi.advanceTimersByTimeAsync(5000)
    expect(apiPost).toHaveBeenCalledTimes(2)
    expect(button('Продолжить опрос')).toBeDefined()
  })

  it('stops on a transport error and never retries a check automatically', async () => {
    // Ошибка сети требует осознанного продолжения; ни pay, ни voucher в маршрутах нет.
    vi.useFakeTimers()
    apiGet.mockResolvedValue({ run })
    apiPost.mockResolvedValue({ run: { ...run, processed: 1, items: [{ ...run.items[0], state: 'transport_error', message: 'Нет соединения' }, run.items[1]] } })
    open(); await flushPromises()
    await button('Продолжить опрос').trigger('click'); await flushPromises()
    await vi.advanceTimersByTimeAsync(10000)
    expect(apiPost).toHaveBeenCalledOnce()
    expect(wrapper.get('[role="alert"]').text()).toContain('приостановлен')
  })

  it('discards late responses after changing user and does not continue after unmount', async () => {
    // Отчёт и таймер прежнего владельца не попадают в новый сеанс.
    vi.useFakeTimers()
    apiGet.mockResolvedValueOnce({ run }).mockResolvedValueOnce({ run: null })
    let finish
    apiPost.mockImplementation(() => new Promise(resolve => { finish = resolve }))
    open(); await flushPromises()
    await button('Продолжить опрос').trigger('click')
    await wrapper.setProps({ token: 'other' }); await flushPromises()
    finish({ run }); await flushPromises()
    expect(wrapper.text()).not.toContain('Email service')
    wrapper.unmount(); wrapper = null
    await vi.advanceTimersByTimeAsync(5000)
    expect(apiPost).toHaveBeenCalledOnce()
  })
})
