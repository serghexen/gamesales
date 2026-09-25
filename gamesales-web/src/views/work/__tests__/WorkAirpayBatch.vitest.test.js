import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import WorkAirpayPreparation from '../sections/WorkAirpayPreparation.vue'
import WorkAirpayBatch from '../sections/WorkAirpayBatch.vue'
import WorkAirpayHistory from '../sections/WorkAirpayHistory.vue'
import { apiGet, apiPost } from '../../../api/http'

vi.mock('../../../api/http', () => ({ apiGet: vi.fn(), apiPost: vi.fn() }))
const global = { stubs: { teleport: true } }
let wrapper
const service = { service_id: 'A1', title: 'Voucher', inputs: [], fixed_payment: true }
const items = [1, 2, 3].map(id => ({ agent_transaction_id: String(id), service_title: 'Voucher', state: 'checked', amount: '12.50',
  currency: 'RUB', purchase_kind: 'voucher', payments_enabled: true, pin_code: '', batch: { quantity: 3, index: id - 1 } }))
const batch = { batch_id: '1', quantity: 3, state: 'checked', total_amount: '37.50', currency: 'RUB',
  paid_quantity: 0, received_quantity: 0, payments_enabled: true, items }
const result = { success: true, retryable: false, scheme: 'simple', displays: [], quantity: 3, purchase_amount: '37.50',
  unit_amount: '12.50', purchase_currency: 'RUB', purchase_ready: true, payments_enabled: true, batch }

async function openForm() {
  // Подготовка использует реальные компоненты с подменёнными ответами API.
  apiGet.mockResolvedValue(service)
  wrapper = mount(WorkAirpayPreparation, { global, props: { serviceId: 'A1', token: 'crm', canPrepare: true } })
  await flushPromises()
  await wrapper.get('input').setValue('seller@example.com')
}
async function checkQuantity() {
  // Пользователь явно выбирает количество до проверки и подтверждает уже общую цену.
  await openForm()
  await wrapper.get('[aria-label="Количество ключей"]').setValue('3')
  apiPost.mockResolvedValueOnce({ preparation_token: 'signed', agent_transaction_id: '1', quantity: 3 }).mockResolvedValueOnce(result)
  await wrapper.get('form').trigger('submit'); await flushPromises()
}
afterEach(() => {
  // Удаляем формы и модальные слои после каждого сценария.
  wrapper?.unmount()
  document.body.innerHTML = ''
  vi.resetAllMocks()
})

describe('Airpay voucher quantity', () => {
  it('checks the chosen quantity and confirms the total through the batch endpoint', async () => {
    // Цена одного ключа и общий итог различаются; оплата не отправляет сумму пачки за один ваучер.
    await checkQuantity()
    expect(apiPost.mock.calls[0][1].quantity).toBe(3)
    expect(wrapper.get('[role="dialog"]').text()).toContain('Цена за ключ12,50 RUB')
    expect(wrapper.get('[role="dialog"]').text()).toContain('Итого к оплате37,50 RUB')
    expect(wrapper.get('[role="dialog"]').text()).toContain('К покупке, шт.3')
    expect(apiPost).toHaveBeenCalledTimes(2)
    const paid = { ...batch, state: 'paid', paid_quantity: 3, items: items.map(item => ({ ...item, state: 'paid' })) }
    apiPost.mockResolvedValueOnce(paid)
    await wrapper.get('.airpay-check__actions .btn').trigger('click'); await flushPromises()
    expect(apiPost.mock.calls[2]).toEqual(['/integrations/airpay/batches/1/pay', { confirmed_amount: '37.50' }, { token: 'crm' }])
    expect(wrapper.text()).toContain('Оплачено: 3 из 3')
    expect(wrapper.findAll('.airpay-transaction')).toHaveLength(3)
    expect(wrapper.find('form').exists()).toBe(false)
  })

  it('rejects invalid quantities and hides quantity for topups', async () => {
    // Ограничения действуют и при прямом submit; пополнение всегда остаётся одиночным.
    await openForm()
    const input = wrapper.get('[aria-label="Количество ключей"]')
    for (const value of ['0', '21', '1.5', '']) {
      await input.setValue(value)
      await wrapper.get('form').trigger('submit')
      expect(wrapper.get('[role="alert"]').text()).toContain('от 1 до 20')
    }
    expect(apiPost).not.toHaveBeenCalled()
    apiGet.mockResolvedValue({ ...service, fixed_payment: false })
    await wrapper.setProps({ serviceId: 'A2' }); await flushPromises()
    expect(wrapper.find('[aria-label="Количество ключей"]').exists()).toBe(false)
  })

  it('invalidates the quote and preparation key after changing quantity', async () => {
    // Нельзя оплатить старый итог после изменения количества в форме.
    await checkQuantity()
    const key = apiPost.mock.calls[0][1].preparation_key
    await wrapper.get('.airpay-check__actions .ghost').trigger('click')
    await wrapper.get('[aria-label="Количество ключей"]').setValue('2')
    expect(wrapper.find('.airpay-check').exists()).toBe(false)
    apiPost.mockResolvedValueOnce({ preparation_token: 'new' }).mockResolvedValueOnce({ ...result, quantity: 2 })
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(apiPost.mock.calls[2][1].quantity).toBe(2)
    expect(apiPost.mock.calls[2][1].preparation_key).not.toBe(key)
  })

  it('recovers a lost payment response by reading the batch without another pay', async () => {
    // Неизвестный итог блокирует новую форму; чтение восстанавливает все сохранённые операции.
    await checkQuantity()
    apiPost.mockRejectedValueOnce(new Error('Связь прервана'))
    await wrapper.get('.airpay-check__actions .btn').trigger('click'); await flushPromises()
    expect(wrapper.find('form').exists()).toBe(false)
    const partial = { ...batch, state: 'processing', paid_quantity: 1, items: [{ ...items[0], state: 'paid' }, { ...items[1], state: 'processing' }, items[2]] }
    apiGet.mockResolvedValueOnce(partial)
    await wrapper.get('.airpay-batch__actions .ghost').trigger('click'); await flushPromises()
    expect(apiGet.mock.calls.at(-1)[0]).toBe('/integrations/airpay/batches/1')
    expect(wrapper.text()).toContain('Оплачено: 1 из 3')
    expect(wrapper.text()).not.toContain('Продолжить покупку')
    expect(apiPost).toHaveBeenCalledTimes(3)
  })

  it('requires explicit confirmation before continuing unpaid keys and blocks local actions', async () => {
    // Продолжение после восстановления остаётся действием пользователя, а не побочным эффектом чтения.
    wrapper = mount(WorkAirpayBatch, { global, props: { batch: { ...batch, state: 'partial', paid_quantity: 1 }, token: 'crm' } })
    await wrapper.get('.airpay-batch__actions .btn').trigger('click')
    expect(apiPost).not.toHaveBeenCalled()
    expect(wrapper.get('[role="dialog"]').text()).toContain('К покупке осталось: 2')
    apiPost.mockResolvedValueOnce({ ...batch, state: 'paid', paid_quantity: 3 })
    await wrapper.get('[role="dialog"] .airpay-batch__actions .btn').trigger('click'); await flushPromises()
    expect(apiPost.mock.calls[0][0]).toBe('/integrations/airpay/batches/1/pay')
    await wrapper.setProps({ batch: { ...batch, payments_enabled: false } })
    expect(wrapper.get('.airpay-batch__actions .btn').element.disabled).toBe(true)
  })

  it('requires a database refresh after a lost continuation response', async () => {
    // Повторное подтверждение не предлагается, пока сервер не вернул сохранённый итог запроса.
    wrapper = mount(WorkAirpayBatch, { global, props: { batch: { ...batch, state: 'partial', paid_quantity: 1 } } })
    await wrapper.get('.airpay-batch__actions .btn').trigger('click')
    apiPost.mockRejectedValueOnce(new Error('timeout'))
    await wrapper.get('[role="dialog"] .airpay-batch__actions .btn').trigger('click'); await flushPromises()
    expect(wrapper.text()).not.toContain('Продолжить покупку')
    expect(wrapper.text()).toContain('Есть незавершённая оплата')
    expect(apiPost).toHaveBeenCalledTimes(1)
  })

  it('opens a whole batch from a child history record using only a database read', async () => {
    // История восстанавливает группу даже со страницы, на которой видна только одна её позиция.
    apiGet.mockResolvedValueOnce({ items: [items[1]] }).mockResolvedValueOnce(batch)
    wrapper = mount(WorkAirpayHistory, { global, props: { token: 'crm' } })
    await flushPromises()
    const button = wrapper.findAll('button').find(button => button.text() === 'Открыть покупку 3 ключей')
    await button.trigger('click'); await flushPromises()
    expect(apiGet.mock.calls[1][0]).toBe('/integrations/airpay/batches/2')
    expect(wrapper.findComponent(WorkAirpayBatch).exists()).toBe(true)
    expect(apiPost).not.toHaveBeenCalled()
  })
})
