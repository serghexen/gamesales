import { describe, it, expect, vi } from 'vitest'
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
    markDealReturned: () => {},
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
    expect(text).toContain('Соз.:')
    expect(text).toContain('Зав.:')
    expect(text).toContain('2026-02-11 11:00')
  })

  it('shows return action for completed non-refund sale', async () => {
    const markDealReturned = vi.fn()
    const wrapper = mount(WorkDealsTableSection, {
      props: buildProps({
        dealShowCompleted: true,
        markDealReturned,
        sortedDeals: [
          {
            deal_id: 1,
            deal_type: 'Продажа',
            deal_type_code: 'sale',
            customer_nickname: 'Покупатель',
            region_code: 'RU',
            purchase_at: '2026-02-11 10:00',
            created_at: '2026-02-11 09:00',
            completed_at: '2026-02-11 11:00',
            flow_status: 'Завершен',
            responsible_username: 'manager',
            is_refund: false,
          },
        ],
      }),
    })

    await wrapper.find('button.mini-btn--danger').trigger('click')
    expect(markDealReturned).toHaveBeenCalledTimes(1)
  })

  it('supports multi-select for type filter', async () => {
    const dealFilters = {
      type_q: '',
      customer_q: '',
      region_q: '',
      purchase_from: '',
      purchase_to: '',
      status_q: '',
      responsible_q: '',
    }
    const wrapper = mount(WorkDealsTableSection, {
      props: buildProps({
        dealFilters,
        activeDealFilter: 'type',
        dealTypeOptions: [
          { code: 'sale', name: 'Продажа' },
          { code: 'share', name: 'Шеринг' },
        ],
      }),
    })

    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    await checkboxes[0].setValue(true)
    await checkboxes[1].setValue(true)

    expect(dealFilters.type_q).toBe('sale,share')
  })

  it('applies type multi-filter immediately on checkbox click', async () => {
    const loadDeals = vi.fn()
    const wrapper = mount(WorkDealsTableSection, {
      props: buildProps({
        loadDeals,
        activeDealFilter: 'type',
        dealTypeOptions: [{ code: 'sale', name: 'Продажа' }],
      }),
    })

    await wrapper.find('input[type="checkbox"]').setValue(true)

    expect(loadDeals).toHaveBeenCalledWith(1)
    expect(wrapper.text()).not.toContain('Применить')
    expect(wrapper.text()).not.toContain('Сбросить')
  })

  it('supports multi-select for region and status filters', async () => {
    const dealFilters = {
      type_q: '',
      customer_q: '',
      region_q: '',
      purchase_from: '',
      purchase_to: '',
      status_q: '',
      responsible_q: '',
    }

    const regionWrapper = mount(WorkDealsTableSection, {
      props: buildProps({
        dealFilters,
        activeDealFilter: 'region',
        regions: [
          { code: 'TR', name: 'Turkey' },
          { code: 'PL', name: 'Poland' },
        ],
      }),
    })
    const regionCheckboxes = regionWrapper.findAll('input[type="checkbox"]')
    await regionCheckboxes[0].setValue(true)
    await regionCheckboxes[1].setValue(true)
    expect(dealFilters.region_q).toBe('TR,PL')

    const statusWrapper = mount(WorkDealsTableSection, {
      props: buildProps({
        dealFilters,
        activeDealFilter: 'status',
        dealFlowStatusOptions: [
          { code: 'pending', name: 'В ожидании' },
          { code: 'draft', name: 'Черновик' },
        ],
      }),
    })
    const statusCheckboxes = statusWrapper.findAll('input[type="checkbox"]')
    await statusCheckboxes[0].setValue(true)
    await statusCheckboxes[1].setValue(true)
    expect(dealFilters.status_q).toBe('pending,draft')
  })
})
