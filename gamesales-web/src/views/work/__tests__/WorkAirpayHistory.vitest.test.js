import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { apiGet, apiGetFile, apiPost } from '../../../api/http'
import WorkAirpayHistory from '../sections/WorkAirpayHistory.vue'

vi.mock('../../../api/http', () => ({ apiGet: vi.fn(), apiGetFile: vi.fn(), apiPost: vi.fn() }))
const item = { agent_transaction_id: '1645129032053759724', state: 'paid', purchase_kind: 'voucher' }
let wrapper
function openHistory() {
  // Карточки заглушены: проверяем только чтение, фильтры и скачивание журнала.
  wrapper = mount(WorkAirpayHistory, { props: { token: 'crm' }, global: { stubs: { teleport: true, WorkAirpayTransaction: true } } })
  return wrapper
}
function button(text) {
  // Ищем действие по видимому названию, не привязываясь к расположению кнопок.
  return wrapper.findAll('button').find(node => node.text() === text)
}
afterEach(() => {
  // Убираем диалог и подмены браузерного скачивания между независимыми сценариями.
  wrapper?.unmount()
  vi.restoreAllMocks()
  vi.resetAllMocks()
  vi.unstubAllGlobals()
})

describe('Airpay history filters and export', () => {
  it('applies filters from page one and exports the applied search, not edited draft', async () => {
    // После просмотра другой страницы поиск сбрасывает offset; Excel читает всю выборку.
    apiGet.mockResolvedValue({ items: Array.from({ length: 21 }, () => item) })
    openHistory()
    await flushPromises()
    await button('Далее').trigger('click'); await flushPromises()
    await wrapper.get('input[type="search"]').setValue('A0217 + email')
    await wrapper.findAll('select')[0].setValue('awaiting_voucher')
    await wrapper.findAll('select')[1].setValue('voucher')
    await wrapper.findAll('input[type="date"]')[0].setValue('2026-09-01')
    await wrapper.findAll('input[type="date"]')[1].setValue('2026-09-23')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    const query = new URL(apiGet.mock.calls.at(-1)[0], 'http://test').searchParams
    expect(query.get('offset')).toBe('0')
    expect(query.get('q')).toBe('A0217 + email')
    expect(query.get('date_to')).toBe('2026-09-23')
    expect(query.get('status')).toBe('awaiting_voucher')
    await wrapper.get('input[type="search"]').setValue('not applied')
    const create = vi.fn().mockReturnValue('blob:export')
    const revoke = vi.fn()
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: create, revokeObjectURL: revoke }))
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    apiGetFile.mockResolvedValue(new Blob(['xlsx']))
    await button('Выгрузить Excel').trigger('click'); await flushPromises()
    expect(apiGetFile.mock.calls[0][0]).toContain('q=A0217+%2B+email')
    expect(apiGetFile.mock.calls[0][0]).not.toMatch(/offset|limit|not.applied/)
    expect(click).toHaveBeenCalledOnce()
    expect(revoke).toHaveBeenCalledWith('blob:export')
    expect(apiPost).not.toHaveBeenCalled()
    await button('Сбросить').trigger('click'); await flushPromises()
    expect(apiGet.mock.calls.at(-1)[0]).toBe('/integrations/airpay/transactions?limit=21&offset=0')
  })

  it('keeps filters when switching to the CRM archive and exports that source', async () => {
    // Источник нельзя потерять при скачивании: архив никогда не обращается к операциям Hub.
    apiGet.mockResolvedValue({ items: [item], legacy_available: true })
    openHistory(); await flushPromises()
    await wrapper.get('input[type="search"]').setValue('1645129032053759724')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    await wrapper.get('select').setValue('true'); await flushPromises()
    expect(apiGet.mock.calls.at(-1)[0]).toContain('q=1645129032053759724&archive=crm')
    apiGetFile.mockRejectedValue(new Error('Уточните фильтры'))
    await button('Выгрузить Excel').trigger('click'); await flushPromises()
    expect(apiGetFile.mock.calls[0][0]).toContain('archive=crm')
    expect(wrapper.get('[role="alert"]').text()).toBe('Уточните фильтры')
    expect(wrapper.emitted('busy-change').at(-1)).toEqual([false])
    expect(apiPost).not.toHaveBeenCalled()
  })

  it('locks export against double clicks and discards a response after session change', async () => {
    // Файл старого владельца не сохраняется после изменения токена.
    apiGet.mockResolvedValue({ items: [item] })
    let finish
    apiGetFile.mockImplementation(() => new Promise(resolve => { finish = resolve }))
    const create = vi.fn()
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: create }))
    openHistory(); await flushPromises()
    await button('Выгрузить Excel').trigger('click')
    expect(wrapper.text()).toContain('Готовим Excel')
    expect(wrapper.find('form').exists()).toBe(false)
    expect(apiGetFile).toHaveBeenCalledOnce()
    await wrapper.setProps({ token: 'other' }); await flushPromises()
    finish(new Blob(['old']))
    await flushPromises()
    expect(create).not.toHaveBeenCalled()
    expect(apiGet.mock.calls.at(-1)[1]).toEqual({ token: 'other' })
  })
})
