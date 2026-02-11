import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import WorkDealsTableSection from '../sections/WorkDealsTableSection.vue'

function buildProps(overrides = {}) {
  return {
    sortedDeals: [],
    dealFilters: {
      type_q: '',
      customer_q: '',
      region_q: '',
      purchase_from: '',
      purchase_to: '',
      status_q: '',
      responsible_q: '',
    },
    dealTypeOptions: [],
    dealFlowStatusOptions: [],
    responsibleOptions: [],
    regions: [],
    activeDealFilter: '',
    setActiveDealFilter: () => {},
    toggleDealSort: () => {},
    getDealSortClass: () => '',
    loadDeals: () => {},
    resetDealFilter: () => {},
    validateDealRange: () => true,
    dealFilterErrors: { date: '' },
    minDate: '2020-01-01',
    maxDate: '2026-12-31',
    editDeal: { open: false, deal_id: null },
    startEditDeal: () => {},
    formatDateTimeMinutes: (value) => String(value || ''),
    dealShowCompleted: false,
    markDealCompleted: () => {},
    dealSaving: false,
    dealCompletingId: null,
    ...overrides,
  }
}

describe('WorkDealsTableSection', () => {
  it('shows created/completed timestamps in completed list mode', () => {
    const wrapper = mount(WorkDealsTableSection, {
      props: buildProps({
        dealShowCompleted: true,
        sortedDeals: [
          {
            deal_id: 1,
            deal_type: 'Продажа',
            customer_nickname: 'Покупатель',
            region_code: 'RU',
            purchase_at: '2026-02-11 10:00',
            created_at: '2026-02-11 09:00',
            completed_at: '2026-02-11 11:00',
            flow_status: 'Завершен',
            responsible_username: 'manager',
          },
        ],
      }),
    })

    const text = wrapper.text()
    expect(text).toContain('Создана:')
    expect(text).toContain('Завершена:')
    expect(text).toContain('2026-02-11 11:00')
  })
})
