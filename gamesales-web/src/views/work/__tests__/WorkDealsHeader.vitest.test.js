import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import WorkDealsHeader from '../sections/WorkDealsHeader.vue'

function buildProps(overrides = {}) {
  return {
    isAdmin: true,
    dealsRealtimeStatus: 'online',
    dealFilters: { search_q: '' },
    applyDealSearch: () => {},
    canCreateDeals: true,
    canCreateSaleDeals: true,
    canCreateSharingDeals: true,
    canViewCompletedDeals: false,
    openCreateSaleModal: () => {},
    openCreateSharingModal: () => {},
    dealShowCompleted: false,
    setDealShowCompleted: () => {},
    loadDeals: () => {},
    dealListLoading: false,
    ...overrides,
  }
}

describe('WorkDealsHeader', () => {
  it('gates sale and sharing create buttons separately', () => {
    const wrapper = mount(WorkDealsHeader, {
      props: buildProps({
        canCreateSaleDeals: true,
        canCreateSharingDeals: false,
      }),
    })

    expect(wrapper.text()).toContain('Услуга')
    expect(wrapper.text()).not.toContain('Шеринг')
  })
})
