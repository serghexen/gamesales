import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { reactive } from 'vue'

import WorkOzonDigitalSettingsModal from '../sections/WorkOzonDigitalSettingsModal.vue'

function buildProps() {
  // Даёт модалке реалистичные данные карточки, чтобы проверить компактные основные блоки.
  return {
    showOzonDigitalSettings: true,
    closeOzonDigitalSettings: vi.fn(),
    ozonDigitalSettings: reactive({
      offer_id: 'PS5-GTA-6',
      manual_stock_limit: 7,
      activation_instruction: '',
      support_error_message: '',
      published_stock: 7,
      available_stock: 5,
      pending_orders: 2,
      delivered_orders: 11,
    }),
    ozonDigitalSettingsLoading: false,
    ozonDigitalSettingsSaving: false,
    ozonDigitalOrders: [],
    interhubServices: [{
      service_id: 91,
      title: 'PlayStation Wallet',
      category: 'Gift cards',
      fields: [{ name: 'nominal', value_list: [{ id: 500, name: '500 RUB' }] }],
    }],
    saveOzonDigitalSettings: vi.fn(),
    deliverOzonDigitalOrder: vi.fn(),
  }
}

describe('WorkOzonDigitalSettingsModal', () => {
  it('shows the hamster while Ozon settings are being saved', () => {
    const props = buildProps()
    props.ozonDigitalSettingsSaving = true
    const wrapper = mount(WorkOzonDigitalSettingsModal, {
      props,
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.find('.modal__body-overlay .wheel-and-hamster').exists()).toBe(true)
    expect(wrapper.text()).toContain('Сохраняем настройки и отправляем остаток…')
    expect(wrapper.get('.modal__body').classes()).toContain('modal__body--loader')
  })

  it('keeps supplier setup and the delivery queue in the keys screen', () => {
    const wrapper = mount(WorkOzonDigitalSettingsModal, {
      props: buildProps(),
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.find('.ozon-digital-modal__supplier-fields').exists()).toBe(true)
    expect(wrapper.findAll('.ozon-digital-modal__messages textarea')).toHaveLength(0)
    expect(wrapper.find('.ozon-digital-modal__orders').exists()).toBe(true)
    expect(wrapper.get('[title="Сохранить настройки"]').classes()).toContain('deal-create-action-btn--save')
    expect(wrapper.get('[title="К карточке"]').classes()).toContain('deal-create-action-btn--edit')
    expect(wrapper.get('[title="Закрыть"]').classes()).toContain('deal-create-action-btn--close')
  })

  it('shows the Interhub service and nominal without a technical ID field', async () => {
    const props = buildProps()
    props.ozonDigitalSettings.interhub_service_id = 91
    const wrapper = mount(WorkOzonDigitalSettingsModal, {
      props,
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.find('.ozon-digital-modal__card').text()).toContain('Автовыдача')
    expect(wrapper.find('.ozon-digital-modal__supplier').text()).toContain('PlayStation Wallet')
    expect(wrapper.find('.ozon-digital-modal__supplier').text()).toContain('500 RUB')
  })

  it('uses one auto-issue switch for the selected Interhub supplier', async () => {
    const props = buildProps()
    props.ozonDigitalSettings.interhub_service_id = 91
    props.ozonDigitalSettings.interhub_enabled = false
    props.ozonDigitalSettings.auto_issue_enabled = false
    const wrapper = mount(WorkOzonDigitalSettingsModal, {
      props,
      global: { stubs: { teleport: true } },
    })

    const autoIssue = wrapper.get('.ozon-digital-modal__auto-switch input')
    await autoIssue.setValue(true)
    expect(props.ozonDigitalSettings.auto_issue_enabled).toBe(true)
    expect(props.ozonDigitalSettings.interhub_enabled).toBe(true)

    await autoIssue.setValue(false)
    expect(props.ozonDigitalSettings.auto_issue_enabled).toBe(false)
    expect(props.ozonDigitalSettings.interhub_enabled).toBe(false)
  })

  it('keeps only manual-required orders in the manual delivery section', () => {
    const props = buildProps()
    props.ozonDigitalOrders = [
      { id: 1, product_name: 'PUBG 300 NC', posting_number: '04259716-0123-1', sku: 5196324554, status: 'manual_required' },
      { id: 2, product_name: 'Выданный товар', posting_number: '04259716-0124-1', sku: 5196324554, status: 'delivered' },
    ]
    const wrapper = mount(WorkOzonDigitalSettingsModal, {
      props,
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.text()).toContain('Ручная выдача')
    expect(wrapper.text()).toContain('PUBG 300 NC')
    expect(wrapper.text()).not.toContain('Выданный товар')
    expect(wrapper.findAll('.ozon-digital-order')).toHaveLength(1)
  })

  it('asks only for the codes missing after a partial supplier issue', () => {
    const props = buildProps()
    props.ozonDigitalOrders = [{
      id: 1,
      product_name: 'PUBG 300 NC',
      posting_number: '04259716-0123-1',
      sku: 5196324554,
      status: 'manual_required',
      required_qty: 3,
      collected_qty: 2,
      remaining_qty: 1,
    }]
    const wrapper = mount(WorkOzonDigitalSettingsModal, {
      props,
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.find('.ozon-digital-order__delivery').text()).toContain('осталось 1 из 3')
  })
})
