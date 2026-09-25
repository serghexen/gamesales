import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import WorkAirpayPreparation from '../sections/WorkAirpayPreparation.vue'
import WorkAirpayCheckResult from '../sections/WorkAirpayCheckResult.vue'
import { airpayCents, invoiceSelection } from '../airpayCheckSummary'
import { apiGet, apiPost } from '../../../api/http'

vi.mock('../../../api/http', () => ({ apiGet: vi.fn(), apiPost: vi.fn() }))
let wrapper
const service = { service_id: 'A1', title: 'Test voucher', inputs: [{ name: 'account', title: 'Аккаунт', required: true, regexp: '^\\d+$' }], displays: [], fixed_payment: true }
const success = { success: true, retryable: false, result: 0, message: 'Успешно', displays: [],
  scheme: 'simple', fixed_amount: '10.50', amount_to: '', amount_from: '', agent_transaction_id: '123', transaction_id: '456',
  contracts: null, invoice: null, currency_rate: '', final_amount: '', currency: '' }

async function openForm(canPrepare = true, description = service) {
  // Открываем настоящую форму с контролируемым описанием услуги без доступа к поставщику.
  apiGet.mockResolvedValue(description)
  wrapper = mount(WorkAirpayPreparation, { global: { stubs: { teleport: true } }, props: { serviceId: 'A1', token: 'crm', canPrepare, currency: 'RUB' } })
  await flushPromises()
  await wrapper.get('input').setValue('1234')
}

afterEach(() => {
  // Таймер паузы и обработчики старой формы не должны влиять на следующий сценарий.
  wrapper?.unmount()
  vi.useRealTimers()
  vi.resetAllMocks()
})

describe('Airpay preparation before pay', () => {
  it('prepares, checks and shows confirmation without ever sending pay', async () => {
    // Оплата остаётся недоступной после успешной проверки и просмотра итоговых данных.
    apiPost.mockResolvedValueOnce({ preparation_token: 'signed-1' }).mockResolvedValueOnce(success)
    await openForm()
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(apiPost).toHaveBeenNthCalledWith(1, '/integrations/airpay/prepare', {
      service_id: 'A1', fields: { account: '1234' }, amount_to: null, quantity: 1,
      preparation_key: expect.any(String),
    }, { token: 'crm' })
    expect(apiPost).toHaveBeenNthCalledWith(2, '/integrations/airpay/check', { preparation_token: 'signed-1' }, { token: 'crm' })
    expect(wrapper.get('[role="dialog"]').attributes('aria-label')).toBe('Проверьте покупку')
    const confirmation = wrapper.get('[aria-label="Подтверждение покупки Airpay"]')
    expect(confirmation.text()).toContain('10,50 RUB')
    expect(confirmation.text()).toContain('1234')
    expect(confirmation.findAll('button').at(-1).attributes('disabled')).toBeDefined()
    await wrapper.get('form').trigger('submit')
    expect(apiPost).toHaveBeenCalledTimes(2)
    await wrapper.get('input').setValue('5678')
    expect(wrapper.find('.airpay-check').exists()).toBe(false)
    apiPost.mockResolvedValueOnce({ preparation_token: 'signed-2' }).mockResolvedValueOnce(success)
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(apiPost.mock.calls.filter(([path]) => path.endsWith('/prepare'))).toHaveLength(2)
    expect(apiPost.mock.calls.some(([path]) => path.endsWith('/pay'))).toBe(false)
  })

  it('shows the shared hamster through preparation and check, then opens confirmation', async () => {
    // Оба сетевых шага закрыты одним лоадером; успешный ответ открывает итог без дополнительного клика.
    let finishPrepare, finishCheck
    apiPost.mockImplementationOnce(() => new Promise(resolve => { finishPrepare = resolve }))
      .mockImplementationOnce(() => new Promise(resolve => { finishCheck = resolve }))
    await openForm()
    await wrapper.get('form').trigger('submit')
    expect(wrapper.get('[aria-label="Хомяк бежит в колесе"]').exists()).toBe(true)
    expect(wrapper.get('input').element.disabled).toBe(true)
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    await wrapper.get('form').trigger('submit')
    expect(apiPost).toHaveBeenCalledTimes(1)
    finishPrepare({ preparation_token: 'hamster' })
    await flushPromises()
    expect(wrapper.find('[aria-label="Хомяк бежит в колесе"]').exists()).toBe(true)
    expect(apiPost).toHaveBeenCalledTimes(2)
    finishCheck(success)
    await flushPromises()
    expect(wrapper.find('[aria-label="Хомяк бежит в колесе"]').exists()).toBe(false)
    expect(wrapper.get('[role="dialog"]').text()).toContain('Актуальная цена')
    expect(wrapper.get('[role="dialog"]').text()).toContain('Поставщик не сообщает')
    expect(wrapper.get('details').element.open).toBe(false)
    expect(apiPost).toHaveBeenCalledTimes(2)
    await wrapper.get('.airpay-check__actions .ghost').trigger('click')
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    await wrapper.get('.airpay-check > button').trigger('click')
    expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
    expect(apiPost).toHaveBeenCalledTimes(2)
  })

  it('removes the hamster on failure and leaves the form available for retry', async () => {
    // Ошибка не оставляет перекрытую форму и не открывает подтверждение покупки.
    let fail
    apiPost.mockImplementationOnce(() => new Promise((resolve, reject) => { fail = reject }))
    await openForm()
    await wrapper.get('form').trigger('submit')
    expect(wrapper.find('[aria-label="Хомяк бежит в колесе"]').exists()).toBe(true)
    fail(new Error('Нет соединения'))
    await flushPromises()
    expect(wrapper.find('[aria-label="Хомяк бежит в колесе"]').exists()).toBe(false)
    expect(wrapper.get('input').element.disabled).toBe(false)
    expect(wrapper.get('[role="alert"]').text()).toContain('Нет соединения')
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it('shows a blocked confirmation when a successful check has no usable price', async () => {
    // Успешная проверка реквизитов без цены не даёт оплатить по сумме конвертации.
    wrapper = mount(WorkAirpayCheckResult, { global: { stubs: { teleport: true } }, props: { service,
      result: { ...success, fixed_amount: '', final_amount: '999', payments_enabled: true, purchase_ready: true } } })
    expect(wrapper.get('[role="dialog"]').text()).toContain('Не получена')
    expect(wrapper.get('.airpay-check__actions .btn').element.disabled).toBe(true)
    await wrapper.get('.airpay-check__actions .btn').trigger('click')
    expect(wrapper.emitted('pay')).toBeUndefined()
  })

  it('shows topup confirmation without voucher quantity and stock rows', () => {
    // Общий вид подтверждения сохраняется, но поля выдачи кода не относятся к пополнению.
    wrapper = mount(WorkAirpayCheckResult, { global: { stubs: { teleport: true } }, props: {
      service: { ...service, fixed_payment: false }, account: 'player-id', currency: 'RUB',
      result: { ...success, purchase_ready: true, purchase_amount: '10.50', payments_enabled: false },
    } })
    const dialog = wrapper.get('[role="dialog"]')
    expect(dialog.text()).toContain('player-id')
    expect(dialog.text()).toContain('10,50 RUB')
    expect(dialog.text()).not.toContain('К покупке, шт.')
    expect(dialog.text()).not.toContain('Актуальный остаток')
    expect(dialog.text()).not.toContain('Выдача ваучера')
  })

  it('prefills voucher email and sends the edited value without restoring a cleared field', async () => {
    // Подстановка видна до check, а ручная правка или очистка остаются под контролем пользователя.
    apiGet.mockResolvedValue({ ...service, inputs: [{ name: 'account', title: 'Введите Email', required: true }] })
    wrapper = mount(WorkAirpayPreparation, { global: { stubs: { teleport: true } }, props: { serviceId: 'A1', token: 'crm', canPrepare: true } })
    await flushPromises()
    const account = wrapper.get('input')
    expect(account.element.value).toBe('seller@homtech.ru')
    expect(account.element.disabled).toBe(false)
    expect(apiPost).not.toHaveBeenCalled()
    apiPost.mockResolvedValueOnce({ preparation_token: 'default' }).mockResolvedValueOnce(success)
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(apiPost.mock.calls[0][1].fields.account).toBe('seller@homtech.ru')
    await account.setValue('another@example.com')
    apiPost.mockResolvedValueOnce({ preparation_token: 'edited' }).mockResolvedValueOnce(success)
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(apiPost.mock.calls[2][1].fields.account).toBe('another@example.com')
    await account.setValue('')
    expect(account.element.value).toBe('')
    expect(account.element.checkValidity()).toBe(false)
    expect(wrapper.find('.airpay-check').exists()).toBe(false)
  })

  it('does not use the voucher email as a topup recipient or a numeric account', async () => {
    // При смене услуги служебный адрес не переносится в реквизиты получателя пополнения.
    apiGet.mockResolvedValue({ ...service, inputs: [{ name: 'account', title: 'Электронная почта', required: true }] })
    wrapper = mount(WorkAirpayPreparation, { global: { stubs: { teleport: true } }, props: { serviceId: 'A1', canPrepare: true } })
    await flushPromises()
    expect(wrapper.get('input').element.value).toBe('seller@homtech.ru')
    apiGet.mockResolvedValue({ ...service, fixed_payment: false, inputs: [{ name: 'account', title: 'Email', required: true }] })
    await wrapper.setProps({ serviceId: 'A2' })
    await flushPromises()
    expect(wrapper.get('input').element.value).toBe('')
    apiGet.mockResolvedValue(service)
    await wrapper.setProps({ serviceId: 'A3' })
    await flushPromises()
    expect(wrapper.get('input').element.value).toBe('')
  })

  it('sends numeric inputs as decimal strings and leaves zero for server validation', async () => {
    // Реальные number-поля Vue преобразуют ввод в числа; контракт API всё равно требует строки.
    apiPost.mockResolvedValueOnce({ preparation_token: 'amounts' }).mockResolvedValueOnce(success)
    await openForm(true, { ...service, fixed_payment: false })
    const amounts = wrapper.findAll('input[type="number"]')
    expect(amounts).toHaveLength(1)
    expect(wrapper.text()).not.toContain('Принято от клиента')
    await amounts[0].setValue('10.50')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(apiPost.mock.calls[0][1]).toMatchObject({ amount_to: '10.5' })
    expect(apiPost.mock.calls[0][1]).not.toHaveProperty('amount_from')
    await amounts[0].setValue('0')
    apiPost.mockRejectedValue(Object.assign(new Error('Сумма должна быть положительной'), { status: 422 }))
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(apiPost.mock.calls[2][1].amount_to).toBe('0')
  })

  it('infers vouchers and keeps provider-required fields without an editable amount', async () => {
    // Тип убирает ручную сумму, но не отменяет обязательный account и реквизиты поставщика.
    await openForm(true, { ...service, inputs: [
      { name: 'account', title: 'Email', required: false },
      { name: 'requiredExtra', title: 'Номер', required: true },
      { name: 'optionalExtra', title: 'Комментарий', required: false },
    ] })
    expect(wrapper.find('select').exists()).toBe(false)
    expect(wrapper.text()).toContain('Код ваучера')
    expect(wrapper.text()).not.toContain('Принято от клиента')
    const fields = wrapper.findAll('input:not([type="number"])')
    expect(fields.map(field => field.element.required)).toEqual([true, true, false])
    expect(wrapper.findAll('input[type="number"]')).toHaveLength(1)
    expect(wrapper.get('[aria-label="Количество ключей"]').element.value).toBe('1')
  })

  it('requires an amount for topups and clears it when switching to a voucher', async () => {
    // При смене услуги прежние суммы и реквизиты не переходят в новый запрос.
    await openForm(true, { ...service, fixed_payment: false })
    expect(wrapper.text()).toContain('Пополнение аккаунта')
    const amount = wrapper.findAll('input[type="number"]')[0]
    expect(amount.element.required).toBe(true)
    expect(amount.element.checkValidity()).toBe(false)
    await amount.setValue('20')
    expect(amount.element.checkValidity()).toBe(true)
    apiGet.mockResolvedValue({ ...service, service_id: 'A2' })
    await wrapper.setProps({ serviceId: 'A2' })
    await flushPromises()
    expect(wrapper.text()).toContain('Код ваучера')
    expect(wrapper.text()).not.toContain('Принято от клиента')
    expect(wrapper.findAll('input[type="number"]')).toHaveLength(1)
    expect(wrapper.get('[aria-label="Количество ключей"]').element.value).toBe('1')
    expect(wrapper.get('input').element.value).toBe('')
    apiPost.mockResolvedValueOnce({ preparation_token: 'voucher' }).mockResolvedValueOnce(success)
    await wrapper.get('input').setValue('5678')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(apiPost.mock.calls[0][1]).toMatchObject({ service_id: 'A2', amount_to: null })
  })

  it('does not guess a purchase kind when the payment flag is missing', async () => {
    // Неизвестная классификация видна пользователю и не допускает запрос check.
    await openForm(true, { ...service, fixed_payment: null })
    expect(wrapper.text()).toContain('Тип услуги не определён')
    expect(wrapper.get('button[type="submit"]').element.disabled).toBe(true)
    await wrapper.get('form').trigger('submit')
    expect(apiPost).not.toHaveBeenCalled()
  })

  it('retries a temporary code with the same draft and increasing delays', async () => {
    // Повтор после паузы не создаёт новую операцию; преждевременное нажатие ничего не отправляет.
    vi.useFakeTimers()
    apiPost.mockResolvedValueOnce({ preparation_token: 'same' }).mockResolvedValue({ ...success, success: false, retryable: true, result: 1 })
    await openForm()
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    await wrapper.get('form').trigger('submit')
    expect(apiPost).toHaveBeenCalledTimes(2)
    await vi.advanceTimersByTimeAsync(5000)
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(apiPost).toHaveBeenCalledTimes(3)
    expect(apiPost.mock.calls[2]).toEqual(apiPost.mock.calls[1])
    expect(wrapper.text()).toContain('Повтор через 15 с')
  })

  it('ignores late checks after changing services', async () => {
    // Завершение запроса старой услуги не открывает подтверждение для новой.
    let resolveCheck
    apiPost.mockResolvedValueOnce({ preparation_token: 'old' }).mockImplementationOnce(() => new Promise(resolve => { resolveCheck = resolve }))
    await openForm()
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    apiGet.mockResolvedValue({ ...service, service_id: 'A2', title: 'Other service' })
    await wrapper.setProps({ serviceId: 'A2' })
    await flushPromises()
    resolveCheck(success)
    await flushPromises()
    expect(wrapper.find('.airpay-check').exists()).toBe(false)
    expect(wrapper.get('input').element.value).toBe('')
  })

  it('blocks checks without permission and shows validation failures', async () => {
    // Отключённая форма защищена и от прямого submit, а серверная ошибка остаётся видимой.
    await openForm(false)
    await wrapper.get('form').trigger('submit')
    expect(apiPost).not.toHaveBeenCalled()
    await wrapper.setProps({ canPrepare: true })
    apiPost.mockRejectedValue(Object.assign(new Error('Проверьте формат: Аккаунт'), { status: 422 }))
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('Проверьте формат')
  })

  it('omits the customer amount from check results saved by older forms', () => {
    // Старые ответы могут содержать amount_from, но удалённое поле больше не показываем.
    wrapper = mount(WorkAirpayCheckResult, { global: { stubs: { teleport: true } }, props: { service, account: '1234', currency: 'RUB',
      result: { ...success, amount_from: '123.45' } } })
    expect(wrapper.text()).not.toContain('Принято от клиента')
    expect(wrapper.text()).not.toContain('123.45')
  })

  it('requires contract selection and invalidates confirmation when it changes', async () => {
    // Нельзя подтвердить первый договор по умолчанию или сохранить итог после выбора другого.
    wrapper = mount(WorkAirpayCheckResult, { global: { stubs: { teleport: true } }, props: { service, account: '1234', currency: 'RUB',
      result: { ...success, scheme: 'contracts', contracts: [{ contractId: '001', contractSum: '10.00' }, { contractId: '002', contractSum: '20.00' }] } } })
    expect(wrapper.get('.airpay-check > button').attributes('disabled')).toBeDefined()
    await wrapper.get('select').setValue('0')
    await wrapper.get('.airpay-check > button').trigger('click')
    expect(wrapper.get('.airpay-check__confirmation').text()).toContain('10,00 RUB')
    await wrapper.get('select').setValue('1')
    expect(wrapper.find('.airpay-check__confirmation').exists()).toBe(false)
  })

  it('validates invoice selections in exact cents and requires meter readings', () => {
    // Ограничения сумм и показания проверяются до формирования итогов по квитанции.
    const invoice = { invoiceId: '01', services: [
      { subServiceId: 'a', data: { minSum: 1, maxSum: 20 } },
      { subServiceId: 'b', data: { isMeter: true, prevCount: '10' } },
    ] }
    expect(airpayCents('0')).toBeNull()
    expect(airpayCents('1.001')).toBeNull()
    expect(invoiceSelection(invoice, [0, 1], { 0: '10.20', 1: '0.10' }, { 1: '11' }).cents).toBe(1030)
    expect(invoiceSelection(invoice, [0], { 0: '21' }, {}).error).toContain('ограничения')
    expect(invoiceSelection(invoice, [1], { 1: '1' }, { 1: '9' }).error).toContain('показания')
    expect(invoiceSelection(invoice, [], {}, {}).error).toContain('Выберите')
  })

  it('renders invoice choices and clears confirmation when amounts change', async () => {
    // Сумма подтверждения включает только отмеченную услугу выбранной квитанции.
    wrapper = mount(WorkAirpayCheckResult, { global: { stubs: { teleport: true } }, props: { service, account: '1234', currency: 'RUB', result: {
      ...success, scheme: 'invoice', invoice: { invoices: [{ invoiceId: '01', services: [
        { subServiceId: 'a', subServiceName: 'Услуга А', data: { paySum: '10.20' } },
      ] }] },
    } } })
    await wrapper.get('select').setValue('0')
    await wrapper.get('input[type="checkbox"]').setValue(true)
    await wrapper.get('.airpay-check > button').trigger('click')
    expect(wrapper.get('.airpay-check__confirmation').text()).toContain('10,20 RUB')
    await wrapper.get('input[type="number"]').setValue('12.30')
    expect(wrapper.find('.airpay-check__confirmation').exists()).toBe(false)
  })
})
