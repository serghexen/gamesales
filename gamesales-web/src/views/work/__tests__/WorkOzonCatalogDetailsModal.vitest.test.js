import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import WorkOzonCatalogDetailsModal from '../sections/WorkOzonCatalogDetailsModal.vue'

function buildProps() {
  // Передает карточку из снимка Ozon, чтобы проверить отображение артикула рядом с рабочими параметрами.
  return {
    showOzonCatalogDetails: true,
    closeOzonCatalogDetails: vi.fn(),
    openOzonDigitalSettings: vi.fn(),
    ozonCatalogDetails: {
      external_product_id: 5224093734,
      offer_id: 'ASAT110',
      title: 'Гта 6 PS5',
      price: '6000',
      price_currency_code: 'RUB',
      available_stock: 0,
      synced_at: '2026-07-23T12:00:00Z',
    },
    ozonCatalogDetailsLoading: false,
  }
}

describe('WorkOzonCatalogDetailsModal', () => {
  it('shows the seller offer id from the saved Ozon card', () => {
    const wrapper = mount(WorkOzonCatalogDetailsModal, {
      props: buildProps(),
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.text()).toContain('Артикул продавца')
    expect(wrapper.text()).toContain('ASAT110')
  })
})
