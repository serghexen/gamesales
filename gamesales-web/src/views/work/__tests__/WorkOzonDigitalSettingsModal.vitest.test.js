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
    ozonDigitalOrdersSyncing: false,
    ozonDigitalOrders: [],
    interhubServices: [{
      service_id: 91,
      title: 'PlayStation Wallet',
      category: 'Gift cards',
      fields: [{ name: 'nominal', value_list: [{ id: 500, name: '500 RUB' }] }],
    }],
    saveOzonDigitalSettings: vi.fn(),
    syncOzonDigitalOrders: vi.fn(),
    deliverOzonDigitalOrder: vi.fn(),
  }
}

describe('WorkOzonDigitalSettingsModal', () => {
  it('groups manual limit, messages and counters in the settings card', () => {
    const wrapper = mount(WorkOzonDigitalSettingsModal, {
      props: buildProps(),
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.find('.ozon-digital-modal__setup').exists()).toBe(true)
    expect(wrapper.findAll('.ozon-digital-modal__messages textarea')).toHaveLength(2)
    expect(wrapper.find('.ozon-digital-modal__stats').text()).toContain('Требуют выдачи')
    expect(wrapper.find('.ozon-digital-modal__stats').text()).toContain('2')
  })

  it('shows the first Interhub supplier and its nominal without a technical ID field', async () => {
    const props = buildProps()
    props.ozonDigitalSettings.interhub_service_id = 91
    const wrapper = mount(WorkOzonDigitalSettingsModal, {
      props,
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.find('.ozon-digital-modal__supplier').text()).toContain('Приоритет №1')
    expect(wrapper.find('.ozon-digital-modal__supplier').text()).toContain('PlayStation Wallet')
    expect(wrapper.find('.ozon-digital-modal__supplier').text()).toContain('500 RUB')
  })
})
