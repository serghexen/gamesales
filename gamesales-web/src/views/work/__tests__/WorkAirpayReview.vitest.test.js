import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import WorkAirpayReview from '../sections/WorkAirpayReview.vue'
import WorkAirpayTransaction from '../sections/WorkAirpayTransaction.vue'
import { apiGet, apiPost } from '../../../api/http'

vi.mock('../../../api/http', () => ({ apiGet: vi.fn(), apiPost: vi.fn() }))
let wrapper
const transaction = { agent_transaction_id: '9007199254740993', state: 'processing', purchase_kind: 'voucher',
  updated_at: '2026-09-23T10:00:00Z', resolution_available: true, payments_enabled: false, requires_attention: true }

afterEach(() => {
  // Убираем форму и подменённые ответы после каждого сценария.
  wrapper?.unmount(); vi.resetAllMocks()
})
async function openForm(value = transaction) {
  // Открытие разбора не выполняет ни check, ни pay, ни получение кода.
  wrapper = mount(WorkAirpayReview, { props: { transaction: value, token: 'crm' } })
  await wrapper.findAll('button').find(button => button.text() === 'Ручной разбор').trigger('click')
  await wrapper.get('input[maxlength="128"]').setValue('71')
  await wrapper.get('input[type="password"]').setValue('TEST-ONLY')
  await wrapper.get('textarea').setValue('Подтверждено Airpay в обращении TEST-123')
}

describe('Airpay operator review', () => {
  it('requires external verification and writes only resolve without pay', async () => {
    // Даже при разрешённом сохранении формы платёжные методы не вызываются.
    await openForm()
    await wrapper.get('form').trigger('submit')
    expect(apiPost).not.toHaveBeenCalled()
    await wrapper.get('input[type="checkbox"]').setValue(true)
    apiPost.mockResolvedValue({ ...transaction, state: 'paid', result_available: true, resolution_available: false })
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(apiPost).toHaveBeenCalledTimes(1)
    expect(apiPost.mock.calls[0][0]).toBe(`/integrations/airpay/transactions/${transaction.agent_transaction_id}/resolve`)
    expect(apiPost.mock.calls[0][1]).toMatchObject({ code: 'TEST-ONLY', verified: true, expected_updated_at: transaction.updated_at })
    expect(wrapper.emitted('resolved')).toHaveLength(1)
    expect(wrapper.find('input[type="password"]').exists()).toBe(false)
  })

  it('reuses the exact decision after a lost response', async () => {
    // Повтор не меняет UUID и содержимое решения, даже если первый ответ потерян.
    await openForm(); await wrapper.get('input[type="checkbox"]').setValue(true)
    apiPost.mockRejectedValueOnce(new Error('Связь прервана')).mockResolvedValueOnce({ ...transaction, state: 'paid' })
    await wrapper.get('form').trigger('submit'); await flushPromises()
    const sent = { ...apiPost.mock.calls[0][1] }
    expect(wrapper.get('fieldset').attributes('disabled')).toBeDefined()
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(apiPost.mock.calls[1][1]).toEqual(sent)
  })

  it('does not offer failure for a paid voucher or decisions in the archive', async () => {
    // Оплаченный результат можно дополнить кодом, но нельзя превратить в отсутствие оплаты.
    await openForm({ ...transaction, state: 'paid', provider_transaction_id: '71' })
    expect(wrapper.find('option[value="confirm_failed"]').exists()).toBe(false)
    await wrapper.setProps({ archive: true })
    expect(wrapper.find('form').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Ручной разбор')
    expect(apiPost).not.toHaveBeenCalled()
  })

  it('loads event pages with GET only', async () => {
    // Просмотр даже неизвестной оплаты не выполняет reconcile.
    wrapper = mount(WorkAirpayReview, { props: { transaction, token: 'crm' } })
    apiGet.mockResolvedValueOnce({ items: [{ id: '2', event_type: 'attention_required', created_at: transaction.updated_at, actor: 'owner', state_after: 'processing' }], next_cursor: '2' })
    await wrapper.findAll('button')[0].trigger('click'); await flushPromises()
    expect(wrapper.text()).toContain('Требуется разбор')
    apiGet.mockResolvedValueOnce({ items: [{ id: '1', event_type: 'prepared', created_at: transaction.updated_at, actor: 'owner', state_after: 'prepared' }], next_cursor: null })
    await wrapper.findAll('button').find(button => button.text() === 'Ранее').trigger('click'); await flushPromises()
    expect(apiGet.mock.calls[1][0]).toContain('/events?before=2')
    expect(wrapper.findAll('li')).toHaveLength(2)
    expect(apiPost).not.toHaveBeenCalled()
  })

  it('clears decision secrets and snapshot when transaction changes', async () => {
    // Данные другой покупки не должны получить код или подтверждение из прежней формы.
    await openForm(); await wrapper.get('input[type="checkbox"]').setValue(true)
    await wrapper.setProps({ transaction: { ...transaction, agent_transaction_id: '20' } })
    expect(wrapper.get('input[type="password"]').element.value).toBe('')
    expect(wrapper.get('input[type="checkbox"]').element.checked).toBe(false)
  })

  it('blocks supplier retry at attention limit while keeping review available', async () => {
    // Платёжный флаг не обходит остановку повторов после лимита.
    wrapper = mount(WorkAirpayTransaction, { props: { transaction: { ...transaction, payments_enabled: true } } })
    const retry = wrapper.findAll('button').find(button => button.text() === 'Уточнить результат оплаты')
    expect(retry.attributes('disabled')).toBeDefined()
    await retry.trigger('click')
    expect(apiPost).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Ручной разбор')
  })
})
