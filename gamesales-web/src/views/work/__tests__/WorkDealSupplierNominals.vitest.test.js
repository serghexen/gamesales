import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import WorkDealSupplierNominals from '../sections/WorkDealSupplierNominals.vue'

const { apiGet, apiPost } = vi.hoisted(() => ({ apiGet: vi.fn(), apiPost: vi.fn() }))

vi.mock('../../../api/http', () => ({
  apiGet: (...args) => apiGet(...args),
  apiPost: (...args) => apiPost(...args),
}))

vi.mock('../../../stores/auth', () => ({
  useAuth: () => ({ state: { token: 'operator-token', role: 'operator', user: 'operator' } }),
}))

function supplierPayload(overrides = {}) {
  // Каталог приходит вместе с состоянием и версией сохранённой сделки.
  return {
    deal_id: 42,
    region_code: 'TR',
    flow_status_code: 'pending',
    lock_version: 1,
    purchase_allowed: true,
    service_id: 11125,
    service_title: 'po_PlayStation - Turkey',
    nominals: [
      { id: '28632', title: 'TRY 250' },
      { id: '28633', title: 'TRY 500' },
    ],
    purchase: null,
    purchases: [],
    ...overrides,
  }
}

function checkedPurchase(overrides = {}) {
  // Проверка цены сохраняет версию, по которой пользователь подтвердил покупку.
  return { success: true, state: 'checked', lock_version: 1, agent_transaction_id: 'deal-42-one', nominal_id: '28632', nominal_title: 'TRY 250', amount: 475.04, ...overrides }
}

async function openConfirmation(wrapper) {
  // Проходим пользовательские действия до подтверждения без доступа к внутренним refs компонента.
  await wrapper.find('select').setValue('28632')
  await wrapper.find('.deal-supplier__obtain').trigger('click')
  await flushPromises()
}

function confirmBuy() {
  // Подтверждение находится в teleport, как и в настоящем окне сделки.
  document.body.querySelector('.deal-supplier-confirm__actions .btn').click()
}

describe('WorkDealSupplierNominals', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    document.body.innerHTML = ''
  })

  it('shows the embedded supplier block only for Turkey and Poland', async () => {
    apiGet.mockResolvedValue(supplierPayload())
    const tr = mount(WorkDealSupplierNominals, { props: { deal: { deal_id: 42, region_code: 'TR', flow_status_code: 'pending', lock_version: 1 } } })
    await flushPromises()
    expect(tr.text()).toContain('Номиналы поставщика')
    expect(tr.text()).toContain('Поставщик · Турция')
    expect(tr.text()).not.toMatch(/interhub/i)
    expect(tr.text()).toContain('Турция')
    tr.unmount()

    const unsupported = mount(WorkDealSupplierNominals, { props: { deal: { deal_id: 43, region_code: 'US' } } })
    expect(unsupported.find('.deal-supplier').exists()).toBe(false)
    expect(apiGet).toHaveBeenCalledTimes(1)
  })

  it('requires a saved deal before obtaining a code', () => {
    const wrapper = mount(WorkDealSupplierNominals, { props: { deal: { region_code: 'PL' } } })
    expect(wrapper.text()).toContain('Сначала сохраните сделку')
    expect(wrapper.find('.deal-supplier__obtain').exists()).toBe(false)
    wrapper.unmount()
  })

  it('blocks a draft until it is saved as pending, and blocks every edit before saving', async () => {
    // Несохранённая смена статуса не открывает покупку, пока форма остаётся в редактировании.
    const deal = { deal_id: 42, region_code: 'TR', flow_status_code: 'draft', lock_version: 1 }
    apiGet.mockResolvedValueOnce(supplierPayload({ flow_status_code: 'draft', purchase_allowed: false, nominals: [] }))
    const wrapper = mount(WorkDealSupplierNominals, { props: { deal } })
    await flushPromises()
    expect(wrapper.text()).toContain('Покупка в черновике недоступна')
    expect(wrapper.find('.deal-supplier__obtain').element.disabled).toBe(true)
    await wrapper.setProps({ editing: true, deal: { ...deal, flow_status_code: 'pending' } })
    expect(wrapper.text()).toContain('Сначала сохраните изменения сделки')
    expect(apiGet).toHaveBeenCalledTimes(1)
    expect(apiPost).not.toHaveBeenCalled()

    apiGet.mockResolvedValue(supplierPayload({ lock_version: 2 }))
    apiPost.mockResolvedValue(checkedPurchase({ lock_version: 2 }))
    await wrapper.setProps({ editing: false, deal: { ...deal, flow_status_code: 'pending', lock_version: 2 } })
    await flushPromises()
    await openConfirmation(wrapper)
    expect(apiPost).toHaveBeenCalledWith('/deals/42/interhub/prepare', { nominal_id: '28632', lock_version: 2 }, { token: 'operator-token' })
    wrapper.unmount()
  })

  it('drops the old confirmation when region is edited and buys only from the newly saved region', async () => {
    // Турецкая проверка не переживает редактирование региона; после сохранения выбирается только Польша.
    const deal = { deal_id: 42, region_code: 'TR', flow_status_code: 'pending', lock_version: 1 }
    apiGet.mockResolvedValue(supplierPayload())
    apiPost.mockResolvedValue(checkedPurchase())
    const wrapper = mount(WorkDealSupplierNominals, { attachTo: document.body, props: { deal } })
    await flushPromises()
    await openConfirmation(wrapper)
    expect(document.body.querySelector('.deal-supplier-confirm')).not.toBeNull()
    await wrapper.setProps({ editing: true, deal: { ...deal, region_code: 'PL' } })
    expect(document.body.querySelector('.deal-supplier-confirm')).toBeNull()
    expect(apiPost).toHaveBeenCalledTimes(1)
    expect(apiGet).toHaveBeenCalledTimes(1)
    apiGet.mockResolvedValue(supplierPayload({ region_code: 'PL', service_id: 9811, service_title: 'PlayStation - Poland', lock_version: 2, nominals: [{ id: '16793', title: 'PLN 100' }] }))
    apiPost.mockResolvedValue(checkedPurchase({ lock_version: 2, nominal_id: '16793', nominal_title: 'PLN 100' }))
    await wrapper.setProps({ editing: false, deal: { ...deal, region_code: 'PL', lock_version: 2 } })
    await flushPromises()
    expect(wrapper.text()).not.toContain('TRY 250')
    await wrapper.find('select').setValue('16793')
    await wrapper.find('.deal-supplier__obtain').trigger('click')
    await flushPromises()
    confirmBuy()
    await flushPromises()
    expect(apiPost).toHaveBeenLastCalledWith('/deals/42/interhub/pay', { agent_transaction_id: 'deal-42-one', lock_version: 2 }, { token: 'operator-token' })
    wrapper.unmount()
  })

  it('ignores a late price response after switching to another deal', async () => {
    // Ответ первой сделки не открывает окно оплаты поверх второй карточки.
    let finishPrepare
    apiGet.mockResolvedValue(supplierPayload())
    apiPost.mockImplementation(() => new Promise((resolve) => { finishPrepare = resolve }))
    const wrapper = mount(WorkDealSupplierNominals, { attachTo: document.body, props: { deal: { deal_id: 42, region_code: 'TR', lock_version: 1 } } })
    await flushPromises()
    await openConfirmation(wrapper)
    apiGet.mockResolvedValue(supplierPayload({ deal_id: 44 }))
    await wrapper.setProps({ deal: { deal_id: 44, region_code: 'TR', lock_version: 1 } })
    await flushPromises()
    finishPrepare(checkedPurchase())
    await flushPromises()
    expect(document.body.querySelector('.deal-supplier-confirm')).toBeNull()
    expect(wrapper.text()).not.toContain('deal-42-one')
    wrapper.unmount()
  })

  it('keeps the received code and blocks actions until a failed form synchronization is retried', async () => {
    // Ошибка чтения карточки не повторяет списание и не скрывает уже купленный код.
    const paid = { ...checkedPurchase(), state: 'paid', gift_code: 'PAID-CODE' }
    apiGet.mockResolvedValue(supplierPayload())
    apiPost.mockResolvedValueOnce(checkedPurchase()).mockResolvedValueOnce(paid)
    const syncDeal = vi.fn().mockRejectedValueOnce(new Error('network')).mockResolvedValue(undefined)
    const wrapper = mount(WorkDealSupplierNominals, { attachTo: document.body, props: { deal: { deal_id: 42, region_code: 'TR', lock_version: 1 }, syncDeal } })
    await flushPromises()
    await openConfirmation(wrapper)
    confirmBuy()
    await flushPromises()
    expect(syncDeal).toHaveBeenCalledWith(42)
    expect(wrapper.text()).toContain('PAID-CODE')
    expect(wrapper.find('.deal-supplier__buy-more').element.disabled).toBe(true)
    expect(wrapper.emitted('busy-change').at(-1)[0].busy).toBe(true)

    apiGet.mockResolvedValue(supplierPayload({ purchases: [paid] }))
    await wrapper.findAll('button').find((button) => button.text() === 'Обновить данные сделки').trigger('click')
    await flushPromises()
    expect(syncDeal).toHaveBeenCalledTimes(2)
    expect(apiPost).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('PAID-CODE')
    expect(wrapper.find('.deal-supplier__buy-more').element.disabled).toBe(false)
    expect(wrapper.emitted('busy-change').at(-1)[0].busy).toBe(false)
    wrapper.unmount()
  })

  it('synchronizes a background confirmation and stops polling after unmount', async () => {
    // Даже когда поставщик ответил позже, новая версия попадает в форму перед следующей покупкой.
    vi.useFakeTimers()
    const processing = { ...checkedPurchase(), state: 'processing' }
    const syncDeal = vi.fn().mockResolvedValue(undefined)
    apiGet.mockResolvedValueOnce(supplierPayload({ purchases: [processing] }))
    const wrapper = mount(WorkDealSupplierNominals, { props: { deal: { deal_id: 42, region_code: 'TR', lock_version: 1 }, syncDeal } })
    await flushPromises()
    expect(wrapper.emitted('busy-change').at(-1)[0].busy).toBe(true)
    apiGet.mockResolvedValue(supplierPayload({ lock_version: 2, purchases: [{ ...processing, state: 'paid', gift_code: 'LATE-CODE' }] }))
    await vi.advanceTimersByTimeAsync(3000)
    await flushPromises()
    expect(syncDeal).toHaveBeenCalledWith(42)
    expect(wrapper.text()).toContain('LATE-CODE')
    expect(wrapper.emitted('busy-change').at(-1)[0].busy).toBe(false)
    wrapper.unmount()
    await vi.advanceTimersByTimeAsync(9000)
    expect(apiGet).toHaveBeenCalledTimes(2)
  })

  it('keeps edit and buy-more blocked while the refreshed deal is still loading', async () => {
    // Полученный код уже виден, но новая покупка и редактирование ждут обновления всей формы.
    let finishSync
    const syncDeal = vi.fn(() => new Promise((resolve) => { finishSync = resolve }))
    apiGet.mockResolvedValue(supplierPayload())
    apiPost.mockResolvedValueOnce(checkedPurchase()).mockResolvedValueOnce({ ...checkedPurchase(), state: 'paid', gift_code: 'SAVED-CODE' })
    const wrapper = mount(WorkDealSupplierNominals, { attachTo: document.body, props: { deal: { deal_id: 42, region_code: 'TR', lock_version: 1 }, syncDeal } })
    await flushPromises()
    await openConfirmation(wrapper)
    confirmBuy()
    await flushPromises()
    expect(wrapper.text()).toContain('SAVED-CODE')
    expect(wrapper.find('.deal-supplier__buy-more').element.disabled).toBe(true)
    expect(wrapper.emitted('busy-change').at(-1)[0].busy).toBe(true)
    await wrapper.setProps({ deal: { deal_id: 42, region_code: 'TR', lock_version: 2 } })
    finishSync()
    await flushPromises()
    expect(wrapper.find('.deal-supplier__buy-more').element.disabled).toBe(false)
    expect(wrapper.emitted('busy-change').at(-1)[0].busy).toBe(false)
    wrapper.unmount()
  })

  it('prepares, confirms and returns the code linked to the current deal', async () => {
    // Скрытие закупа не меняет подготовку, оплату и копирование полученного кода.
    apiGet.mockResolvedValue(supplierPayload())
    apiPost
      .mockResolvedValueOnce({
        success: true,
        status: 0,
        state: 'checked', lock_version: 1,
        agent_transaction_id: 'gamesales-deal-42-first',
        service_title: 'po_PlayStation - Turkey',
        nominal_id: '28632',
        nominal_title: 'TRY 250',
        amount: 475.04,
      })
      .mockResolvedValueOnce({
        success: true,
        status: 0,
        state: 'paid',
        agent_transaction_id: 'gamesales-deal-42-first',
        nominal_id: '28632',
        nominal_title: 'TRY 250',
        amount: 475.04,
        gift_code: 'TR-DEAL-42-CODE',
        created_by: 'operator',
      })
    const wrapper = mount(WorkDealSupplierNominals, {
      attachTo: document.body,
      props: { deal: { deal_id: 42, region_code: 'TR', flow_status_code: 'pending', lock_version: 1 } },
    })
    await flushPromises()

    await wrapper.find('select').setValue('28632')
    await wrapper.find('.deal-supplier__obtain').trigger('click')
    await flushPromises()
    expect(apiPost).toHaveBeenNthCalledWith(1, '/deals/42/interhub/prepare', { nominal_id: '28632', lock_version: 1 }, { token: 'operator-token' })
    expect(document.body.textContent).toContain('Проверьте покупку')
    expect(document.body.textContent).not.toContain('Актуальная цена')
    expect(document.body.textContent).not.toContain('475,04')
    expect(document.body.textContent).not.toContain('₽')
    expect(document.body.textContent).toContain('TRY 250')

    const buyButton = [...document.body.querySelectorAll('.deal-supplier-confirm__actions .btn')]
      .find((button) => button.textContent.includes('Купить'))
    buyButton.click()
    await flushPromises()
    expect(apiPost).toHaveBeenNthCalledWith(2, '/deals/42/interhub/pay', { agent_transaction_id: 'gamesales-deal-42-first', lock_version: 1 }, { token: 'operator-token' })
    expect(wrapper.text()).toContain('TR-DEAL-42-CODE')
    expect(wrapper.find('.deal-supplier__voucher-info small').text()).toBe('operator · —')
    expect(wrapper.text()).not.toContain('475,04')
    expect(wrapper.text()).not.toContain('Сумма закупки')

    await wrapper.find('.deal-supplier__voucher .ghost').trigger('click')
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('TR-DEAL-42-CODE')
    wrapper.unmount()
  })

  it('keeps several voucher nominals in one deal and offers to buy another', async () => {
    // Несколько кодов и их номиналы остаются видны, но цены и общий закуп не выводятся.
    apiGet.mockResolvedValue(supplierPayload())
    apiPost
      .mockResolvedValueOnce({
        success: true, state: 'checked', lock_version: 1, agent_transaction_id: 'gamesales-deal-42-first',
        nominal_id: '28632', nominal_title: 'TRY 250', amount: 475.04,
      })
      .mockResolvedValueOnce({
        success: true, state: 'paid', agent_transaction_id: 'gamesales-deal-42-first',
        nominal_id: '28632', nominal_title: 'TRY 250', amount: 475.04,
        gift_code: 'FIRST-CODE', created_by: 'operator',
      })
      .mockResolvedValueOnce({
        success: true, state: 'checked', lock_version: 1, agent_transaction_id: 'gamesales-deal-42-second',
        nominal_id: '28633', nominal_title: 'TRY 500', amount: 900,
      })
      .mockResolvedValueOnce({
        success: true, state: 'paid', agent_transaction_id: 'gamesales-deal-42-second',
        nominal_id: '28633', nominal_title: 'TRY 500', amount: 900,
        gift_code: 'SECOND-CODE', created_by: 'operator',
      })
    const wrapper = mount(WorkDealSupplierNominals, {
      attachTo: document.body,
      props: { deal: { deal_id: 42, region_code: 'TR', flow_status_code: 'pending', lock_version: 1 } },
    })
    await flushPromises()

    await wrapper.find('select').setValue('28632')
    await wrapper.find('.deal-supplier__obtain').trigger('click')
    await flushPromises()
    document.body.querySelector('.deal-supplier-confirm__actions .btn').click()
    await flushPromises()
    expect(wrapper.text()).toContain('FIRST-CODE')

    await wrapper.find('.deal-supplier__buy-more').trigger('click')
    await wrapper.find('select').setValue('28633')
    await wrapper.find('.deal-supplier__obtain').trigger('click')
    await flushPromises()
    document.body.querySelector('.deal-supplier-confirm__actions .btn').click()
    await flushPromises()

    expect(wrapper.text()).toContain('Получено: 2')
    expect(wrapper.text()).toContain('TRY 250')
    expect(wrapper.text()).toContain('TRY 500')
    expect(wrapper.text()).toContain('FIRST-CODE')
    expect(wrapper.text()).toContain('SECOND-CODE')
    expect(wrapper.text()).not.toContain('1 375,04')
    expect(wrapper.text()).not.toContain('₽')
    expect(wrapper.find('.deal-supplier__vouchers-summary').exists()).toBe(false)
    expect(apiPost).toHaveBeenNthCalledWith(4, '/deals/42/interhub/pay', { agent_transaction_id: 'gamesales-deal-42-second', lock_version: 1 }, { token: 'operator-token' })
    wrapper.unmount()
  })

  it.each([
    ['TR', 'TRY 250', 'checked'],
    ['TR', 'TRY 250', 'processing'],
    ['TR', 'TRY 250', 'paid'],
    ['PL', 'PLN 100', 'checked'],
    ['PL', 'PLN 100', 'processing'],
    ['PL', 'PLN 100', 'paid'],
  ])('hides purchase costs when reopening %s vouchers in state %s %s', async (region, nominal, state) => {
    // Ответ сервера по-прежнему содержит закуп, но при повторном открытии он не появляется в интерфейсе.
    const purchase = checkedPurchase({ state, nominal_title: nominal, amount: 477.13, gift_code: state === 'paid' ? 'SAVED-CODE' : '', created_by: 'operator' })
    apiGet.mockResolvedValue(supplierPayload({ region_code: region, purchases: [purchase] }))
    const wrapper = mount(WorkDealSupplierNominals, { props: { deal: { deal_id: 42, region_code: region, flow_status_code: 'pending', lock_version: 1 } } })
    await flushPromises()
    expect(wrapper.text()).toContain(nominal)
    expect(wrapper.text()).not.toMatch(/477[,.]13|₽|Закупочная цена|Сумма закупки|Актуальная цена/)
    if (state === 'paid') expect(wrapper.text()).toContain('SAVED-CODE')
    if (state === 'processing') expect(wrapper.find('.deal-supplier__obtain').element.disabled).toBe(true)
    wrapper.unmount()
  })
})
