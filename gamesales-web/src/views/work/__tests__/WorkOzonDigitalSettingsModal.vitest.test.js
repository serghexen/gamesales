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
    expect(wrapper.text()).toContain('Сохраняем настройки выдачи…')
    expect(wrapper.get('.modal__body').classes()).toContain('modal__body--loader')
  })

  it('uses the Ozon card title for the manual key pool', () => {
    const props = buildProps()
    props.ozonDigitalSettings.external_product_id = 17162
    props.ozonDigitalProductTitle = 'PUBG: New State 300 NC (Global) Мгновенная доставка'
    props.loadMarketplaceKeyPoolFor = vi.fn()

    mount(WorkOzonDigitalSettingsModal, {
      props,
      global: { stubs: { teleport: true } },
    })

    expect(props.loadMarketplaceKeyPoolFor).toHaveBeenCalledWith(expect.objectContaining({
      marketplace: 'ozon',
      productKey: '17162',
      productTitle: 'PUBG: New State 300 NC (Global) Мгновенная доставка',
    }))
  })

  it('keeps supplier setup and the delivery queue in the keys screen', async () => {
    const wrapper = mount(WorkOzonDigitalSettingsModal, {
      props: buildProps(),
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.find('.ozon-digital-modal__supplier-fields').exists()).toBe(false)
    await wrapper.get('.ozon-key-settings__block .ozon-catalog-details-modal__work-block-toggle').trigger('click')
    expect(wrapper.find('.ozon-digital-modal__supplier-fields').exists()).toBe(true)
    expect(wrapper.find('.ozon-digital-modal__supplier').text()).toContain('Товар')
    expect(wrapper.find('.ozon-digital-modal__supplier').text()).not.toContain('Номинал')
    expect(wrapper.find('.marketplace-key-pool-panel .marketplace-key-pool-panel__issue-switch').exists()).toBe(true)
    expect(wrapper.find('.ozon-digital-modal__card .marketplace-key-pool-panel__issue-switch').exists()).toBe(false)
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

    expect(wrapper.get('[aria-label="Автовыдача через Interhub"]').exists()).toBe(true)
    await wrapper.get('.ozon-key-settings__block .ozon-catalog-details-modal__work-block-toggle').trigger('click')
    expect(wrapper.find('.ozon-digital-modal__service-search input').element.value).toContain('PlayStation Wallet')
    expect(wrapper.find('.ozon-digital-modal__supplier').text()).toContain('Номинал')
    expect(wrapper.find('.ozon-digital-modal__supplier').text()).toContain('500 RUB')
  })

  it('finds an Interhub service before changing the saved supplier binding', async () => {
    const props = buildProps()
    props.ozonDigitalSettings.interhub_service_id = 91
    props.ozonDigitalSettings.interhub_nominal_id = '500'
    props.interhubServices = [
      ...props.interhubServices,
      { service_id: 92, title: 'Roblox - Global', category: 'Gift cards', fields: [{ name: 'nominal', value_list: [{ id: 800, name: 'Robux 800' }] }] },
      { service_id: 93, title: 'Steam - Turkey', category: 'Gift cards', fields: [] },
    ]
    const wrapper = mount(WorkOzonDigitalSettingsModal, {
      props,
      global: { stubs: { teleport: true } },
    })

    await wrapper.get('.ozon-key-settings__block .ozon-catalog-details-modal__work-block-toggle').trigger('click')
    const search = wrapper.get('.ozon-digital-modal__service-search input')
    await search.setValue('roblox')

    expect(props.ozonDigitalSettings.interhub_service_id).toBe(91)
    expect(wrapper.findAll('.ozon-digital-modal__service-option')).toHaveLength(1)
    expect(wrapper.find('.ozon-digital-modal__service-option').text()).toContain('Roblox - Global')

    await wrapper.find('.ozon-digital-modal__service-option').trigger('click')
    expect(props.ozonDigitalSettings.interhub_service_id).toBe(92)
    expect(props.ozonDigitalSettings.interhub_nominal_id).toBe('')
    expect(wrapper.find('.ozon-digital-modal__service-search input').element.value).toContain('Roblox - Global')
  })

  it('keeps the Interhub and pool switches independent', async () => {
    const props = buildProps()
    props.ozonDigitalSettings.interhub_service_id = 91
    props.ozonDigitalSettings.interhub_enabled = false
    props.ozonDigitalSettings.auto_issue_enabled = false
    props.ozonDigitalSettings.pool_issue_enabled = false
    const wrapper = mount(WorkOzonDigitalSettingsModal, {
      props,
      global: { stubs: { teleport: true } },
    })

    await wrapper.get('.marketplace-key-pool-panel .ozon-catalog-details-modal__work-block-toggle').trigger('click')
    const switches = wrapper.findAll('.ozon-digital-modal__auto-switch input')
    const autoIssue = switches[0]
    await autoIssue.setValue(true)
    expect(props.ozonDigitalSettings.auto_issue_enabled).toBe(true)
    expect(props.ozonDigitalSettings.interhub_enabled).toBe(true)

    await autoIssue.setValue(false)
    expect(props.ozonDigitalSettings.auto_issue_enabled).toBe(false)
    expect(props.ozonDigitalSettings.interhub_enabled).toBe(false)

    await switches[1].setValue(true)
    expect(props.ozonDigitalSettings.pool_issue_enabled).toBe(true)
    expect(props.ozonDigitalSettings.auto_issue_enabled).toBe(false)
  })

  it('opens the supplier block on demand while keeping its auto-issue switch visible', async () => {
    const wrapper = mount(WorkOzonDigitalSettingsModal, {
      props: buildProps(),
      global: { stubs: { teleport: true } },
    })

    const block = wrapper.find('.ozon-key-settings__block')
    expect(block.classes()).not.toContain('is-open')
    expect(block.find('.ozon-digital-modal__auto-switch').exists()).toBe(true)
    await block.get('.ozon-catalog-details-modal__work-block-toggle').trigger('click')

    expect(wrapper.find('.ozon-key-settings__block').classes()).toContain('is-open')
    expect(wrapper.find('.ozon-key-settings__block .ozon-digital-modal__auto-switch').exists()).toBe(true)
    expect(wrapper.find('.ozon-key-settings__block #ozon-key-supplier-content').exists()).toBe(true)
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
