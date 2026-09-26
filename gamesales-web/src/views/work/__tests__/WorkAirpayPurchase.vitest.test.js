import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import WorkAirpayPreparation from '../sections/WorkAirpayPreparation.vue'
import WorkAirpayTransaction from '../sections/WorkAirpayTransaction.vue'
import WorkAirpayHistory from '../sections/WorkAirpayHistory.vue'
import WorkAirpayDialog from '../sections/WorkAirpayDialog.vue'
import { apiGet, apiPost } from '../../../api/http'

vi.mock('../../../api/http', () => ({ apiGet: vi.fn(), apiPost: vi.fn() }))
let wrapper
const transaction = { agent_transaction_id: '9007199254740993', service_id: 'A0008', service_title: 'Voucher', account: '12345',
  amount: '12.50', currency: 'RUB', state: 'checked', purchase_kind: 'voucher', pin_code: '', payments_enabled: true }
const checked = { success: true, result: 0, retryable: false, message: 'Успешно', scheme: 'simple', displays: [],
  fixed_price: '12.50', purchase_amount: '12.50', purchase_currency: 'RUB', purchase_ready: true, purchase_block_reason: '',
  payments_enabled: true, agent_transaction_id: transaction.agent_transaction_id, final_amount: '999', currency: 'USD', transaction }

async function openChecked(overrides = {}) {
  // Полная форма получает проверенный ответ и сохранённый ID, не обращаясь к реальному Airpay.
  apiGet.mockResolvedValue({ service_id: 'A0008', title: 'Voucher', inputs: [], fixed_payment: true })
  apiPost.mockResolvedValueOnce({ preparation_token: 'signed', agent_transaction_id: transaction.agent_transaction_id }).mockResolvedValueOnce({ ...checked, ...overrides })
  wrapper = mount(WorkAirpayPreparation, { global: { stubs: { teleport: true } }, props: { serviceId: 'A0008', token: 'crm', canPrepare: true, currency: 'RUB' } })
  await flushPromises()
  await wrapper.get('input').setValue('12345')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
}

afterEach(() => {
  // Убираем модальные слои, таймеры и подменённые вызовы после каждого сценария.
  wrapper?.unmount()
  document.body.innerHTML = ''
  vi.useRealTimers()
  vi.resetAllMocks()
})

describe('Airpay durable purchase UI', () => {
  it('shows the currency of the checked price even when the balance widget is stale', async () => {
    // Подтверждение должно показывать валюту проверенной суммы, а не прежнего баланса RUB.
    await openChecked({ purchase_currency: 'USD' })
    const confirmation = wrapper.get('.airpay-check__confirmation').text()
    expect(confirmation).toContain('12,50 USD')
    expect(confirmation).not.toContain('12,50 RUB')
    expect(apiPost).toHaveBeenCalledTimes(2)
  })

  it('requires explicit confirmation and retrieves voucher separately after paid', async () => {
    // Цена fixedPrice показывается в подтверждении, а finalAmount не используется при оплате.
    await openChecked()
    expect(apiPost).toHaveBeenCalledTimes(2)
    expect(wrapper.get('.airpay-check__confirmation').text()).toContain('12,50 RUB')
    apiPost.mockResolvedValueOnce({ ...transaction, state: 'paid' })
    await wrapper.get('.airpay-check__confirmation button.btn').trigger('click')
    await flushPromises()
    expect(apiPost.mock.calls[2]).toEqual([`/integrations/airpay/transactions/${transaction.agent_transaction_id}/pay`, { confirmed_amount: '12.50' }, { token: 'crm' }])
    expect(wrapper.find('form').exists()).toBe(false)
    expect(wrapper.text()).toContain('Осталось получить код')
    expect(apiPost).toHaveBeenCalledTimes(3)
    apiPost.mockResolvedValueOnce({ ...transaction, state: 'paid', pin_code: 'TEST-VOUCHER' })
    await wrapper.get('.airpay-transaction__actions button.btn').trigger('click')
    await flushPromises()
    expect(apiPost.mock.calls[3][0]).toMatch(/\/voucher$/)
    expect(wrapper.get('code').text()).toBe('TEST-VOUCHER')
    expect(wrapper.find('.airpay-transaction__actions button.btn').exists()).toBe(false)
  })

  it('blocks pay locally even with a successful quote', async () => {
    // Подготовку можно просмотреть, но локальная кнопка не отправляет никаких платных запросов.
    await openChecked({ payments_enabled: false })
    const pay = wrapper.get('.airpay-check__confirmation button.btn')
    expect(pay.attributes('disabled')).toBeDefined()
    await pay.trigger('click')
    expect(apiPost).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('отключены в этом окружении')
  })

  it('blocks recovery actions while the initial pay is still in flight', async () => {
    // Карточка статуса появляется сразу, но не должна снимать блокировку незавершённой оплаты.
    await openChecked()
    let finish
    apiPost.mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
    await wrapper.get('.airpay-check__confirmation button.btn').trigger('click')
    await flushPromises()
    expect(wrapper.get('.airpay-transaction__actions button.btn').attributes('disabled')).toBeDefined()
    await wrapper.get('.airpay-transaction__actions button.btn').trigger('click')
    expect(apiPost).toHaveBeenCalledTimes(3)
    finish({ ...transaction, state: 'paid' })
    await flushPromises()
    expect(wrapper.get('.airpay-transaction__actions button.btn').attributes('disabled')).toBeUndefined()
  })

  it('blocks payment when the server has not confirmed price or availability', async () => {
    // Наличие суммы конвертации не обходит серверный запрет покупки фиксированной позиции.
    await openChecked({ purchase_ready: false, purchase_block_reason: 'Не получен fixedPrice' })
    expect(wrapper.get('.airpay-check__confirmation button.btn').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Не получен fixedPrice')
  })

  it('keeps an uncertain payment locked and reads its saved state without a second pay', async () => {
    // Потеря HTTP-ответа не возвращает пользователя к кнопке новой оплаты.
    await openChecked()
    apiPost.mockRejectedValueOnce(new Error('Связь прервана'))
    await wrapper.get('.airpay-check__confirmation button.btn').trigger('click')
    await flushPromises()
    expect(wrapper.find('form').exists()).toBe(false)
    apiGet.mockResolvedValueOnce({ ...transaction, state: 'paid', pin_code: 'SAVED-CODE' })
    await wrapper.get('.airpay-transaction__actions button.ghost').trigger('click')
    await flushPromises()
    expect(apiGet.mock.calls.at(-1)[0]).toBe(`/integrations/airpay/transactions/${transaction.agent_transaction_id}`)
    expect(apiPost.mock.calls.filter(([path]) => path.endsWith('/pay'))).toHaveLength(1)
    expect(wrapper.get('code').text()).toBe('SAVED-CODE')
  })

  it('unlocks preparation only if saved state confirms that pay never started', async () => {
    // Отказ до списания позволяет подготовить заново лишь после чтения записи сервера.
    await openChecked()
    apiPost.mockRejectedValueOnce(new Error('Цена устарела'))
    await wrapper.get('.airpay-check__confirmation button.btn').trigger('click')
    await flushPromises()
    apiGet.mockResolvedValueOnce(transaction)
    await wrapper.get('.airpay-transaction__actions button.ghost').trigger('click')
    await flushPromises()
    expect(wrapper.find('form').exists()).toBe(true)
    expect(wrapper.find('.airpay-check__confirmation').exists()).toBe(false)
  })

  it('reuses the preparation key after a lost response and replaces it after editing', async () => {
    // Идемпотентность начинается до check: повтор потерянного prepare не создаёт ещё один ID.
    apiGet.mockResolvedValue({ service_id: 'A0008', title: 'Voucher', inputs: [], fixed_payment: true })
    apiPost.mockRejectedValue(new Error('timeout'))
    wrapper = mount(WorkAirpayPreparation, { global: { stubs: { teleport: true } }, props: { serviceId: 'A0008', canPrepare: true } })
    await flushPromises()
    await wrapper.get('input').setValue('12345')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(apiPost.mock.calls[0][1].preparation_key).toBe(apiPost.mock.calls[1][1].preparation_key)
    await wrapper.get('input').setValue('67890')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(apiPost.mock.calls[2][1].preparation_key).not.toBe(apiPost.mock.calls[0][1].preparation_key)
  })

  it('reconciles only the selected processing transaction', async () => {
    // Кнопка сверки передаёт ID сохранённой операции и не формирует новые реквизиты.
    wrapper = mount(WorkAirpayTransaction, { props: { transaction: { ...transaction, state: 'processing' }, token: 'crm' } })
    expect(wrapper.text()).toContain('повторно отправляет в Airpay сохранённый запрос оплаты')
    expect(apiPost).not.toHaveBeenCalled()
    apiPost.mockResolvedValue({ ...transaction, state: 'paid' })
    await wrapper.get('button.btn').trigger('click'); await flushPromises()
    expect(apiPost).toHaveBeenCalledWith(`/integrations/airpay/transactions/${transaction.agent_transaction_id}/reconcile`, {}, { token: 'crm' })
    expect(wrapper.text()).toContain('Осталось получить код')
  })

  it('starts a new preparation key after the saved draft expires', async () => {
    // Повтор после 410 не должен бесконечно восстанавливать уже истёкшую запись.
    apiGet.mockResolvedValue({ service_id: 'A0008', title: 'Voucher', inputs: [], fixed_payment: true })
    apiPost.mockResolvedValueOnce({ preparation_token: 'expired' }).mockRejectedValueOnce(Object.assign(new Error('Срок истёк'), { status: 410 }))
    wrapper = mount(WorkAirpayPreparation, { global: { stubs: { teleport: true } }, props: { serviceId: 'A0008', canPrepare: true } })
    await flushPromises()
    await wrapper.get('input').setValue('12345')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    const firstKey = apiPost.mock.calls[0][1].preparation_key
    apiPost.mockResolvedValueOnce({ preparation_token: 'new' }).mockResolvedValueOnce(checked)
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(apiPost.mock.calls[2][1].preparation_key).not.toBe(firstKey)
  })

  it('shows stored codes locally but never retrieves codes from the supplier', async () => {
    // Локальное чтение истории и выдача нового кода — разные действия.
    wrapper = mount(WorkAirpayTransaction, { props: { transaction: { ...transaction, state: 'paid', payments_enabled: false } } })
    expect(wrapper.get('button.btn').attributes('disabled')).toBeDefined()
    await wrapper.get('button.btn').trigger('click')
    expect(apiPost).not.toHaveBeenCalled()
    apiGet.mockResolvedValue({ ...transaction, state: 'paid', payments_enabled: false, pin_code: 'STORED' })
    await wrapper.get('button.ghost').trigger('click'); await flushPromises()
    expect(wrapper.get('code').text()).toBe('STORED')
  })

  it('loads history only on opening and pages without payment calls', async () => {
    // История читает журнал постранично; открытие не запускает сверку или выдачу у поставщика.
    apiGet.mockResolvedValue({ items: Array.from({ length: 21 }, (_, index) => ({ ...transaction, agent_transaction_id: String(index) })) })
    wrapper = mount(WorkAirpayHistory, { props: { token: 'crm' }, global: { stubs: { teleport: true } } })
    await flushPromises()
    expect(wrapper.findAllComponents(WorkAirpayTransaction)).toHaveLength(0)
    expect(wrapper.findAll('.airpay-history-row')).toHaveLength(20)
    await wrapper.findAll('nav button')[1].trigger('click'); await flushPromises()
    expect(apiGet.mock.calls.at(-1)[0]).toBe('/integrations/airpay/transactions?limit=21&offset=20')
    expect(apiPost).not.toHaveBeenCalled()
  })

  it('traps keyboard focus and blocks closing during an active request', async () => {
    // Модальное окно возвращает фокус и не закрывается по Escape посреди покупки.
    const trigger = document.createElement('button')
    document.body.appendChild(trigger); trigger.focus()
    wrapper = mount(WorkAirpayDialog, { attachTo: document.body, props: { title: 'Подготовка', busy: true }, slots: { default: '<input aria-label="Аккаунт" />' } })
    const dialog = document.querySelector('[role="dialog"]')
    expect(document.activeElement).toBe(dialog)
    dialog.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    expect(wrapper.emitted('close')).toBeUndefined()
    await wrapper.setProps({ busy: false })
    dialog.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    expect(wrapper.emitted('close')).toHaveLength(1)
    const input = dialog.querySelector('input'); input.focus()
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true }))
    expect(document.activeElement).toBe(dialog.querySelector('button'))
    wrapper.unmount(); wrapper = null
    expect(document.activeElement).toBe(trigger)
  })
})
