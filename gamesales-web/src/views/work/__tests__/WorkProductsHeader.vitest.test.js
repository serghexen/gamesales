import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import WorkProductsHeader from '../sections/WorkProductsHeader.vue'

function buildProps(overrides = {}) {
  return {
    productFilters: { q: '' },
    applyProductSearch: vi.fn(),
    openCreateGameProductModal: vi.fn(),
    openCreateSubscriptionProductModal: vi.fn(),
    openProductImport: vi.fn(),
    openOzonCatalog: vi.fn(),
    canManageOzon: false,
    loadProducts: vi.fn(),
    productsLoading: false,
    ...overrides,
  }
}

describe('WorkProductsHeader', () => {
  it('shows the Ozon catalog button only to the owner', () => {
    const operator = mount(WorkProductsHeader, { props: buildProps() })
    const owner = mount(WorkProductsHeader, { props: buildProps({ canManageOzon: true }) })

    expect(operator.find('[aria-label="Каталог Ozon"]').exists()).toBe(false)
    expect(owner.find('[aria-label="Каталог Ozon"]').exists()).toBe(true)
  })
})
