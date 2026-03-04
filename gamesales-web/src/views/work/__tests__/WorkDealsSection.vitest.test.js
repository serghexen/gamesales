import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import WorkDealsSection from '../sections/WorkDealsSection.vue'

function buildCtx(overrides = {}) {
  // Базовый контекст для проверки режима загрузки без блокирующего оверлея.
  return {
    isAdmin: true,
    dealsRealtimeStatus: 'online',
    dealFilters: {},
    applyDealSearch: () => {},
    openCreateSaleModal: () => {},
    openCreateSharingModal: () => {},
    dealShowCompleted: false,
    setDealShowCompleted: () => {},
    loadDeals: () => {},
    dealListLoading: false,
    dealListError: '',
    dealError: '',
    dealOk: '',
    activeDealChips: [],
    resetDealFilter: () => {},
    sortedDeals: [],
    dealTypeOptions: [],
    dealFlowStatusOptions: [],
    responsibleUserOptions: [],
    regions: [],
    activeDealFilter: '',
    setActiveDealFilter: () => {},
    toggleDealSort: () => {},
    getDealSortClass: () => '',
    validateDealRange: () => true,
    dealFilterErrors: { date: '' },
    minDate: '2020-01-01',
    maxDate: '2026-12-31',
    editDeal: { open: false, deal_id: null },
    startEditDeal: () => {},
    dealEditingByDealId: {},
    currentUsername: 'admin',
    showDealWarning: () => {},
    formatDateTimeMinutes: (value) => String(value || ''),
    markDealCompleted: () => {},
    markDealReturned: () => {},
    dealSaving: false,
    dealCompletingId: null,
    dealsRealtimeAnimationTick: 0,
    dealTotal: 0,
    dealPageSize: 20,
    setDealPage: () => {},
    dealPage: 1,
    prevDealPage: () => {},
    dealPageInput: 1,
    totalPages: 1,
    jumpDealPage: () => {},
    nextDealPage: () => {},
    ...overrides,
  }
}

describe('WorkDealsSection', () => {
  it('keeps table visible during loading without extra loading text and hamster overlay', () => {
    const wrapper = mount(WorkDealsSection, {
      props: {
        ctx: buildCtx({ dealListLoading: true }),
      },
      global: {
        stubs: {
          WorkDealsHeader: { template: '<div class="header-stub" />' },
          WorkDealFilterChips: { template: '<div class="chips-stub" />' },
          WorkDealsTableSection: { template: '<div class="table-stub" />' },
        },
      },
    })

    expect(wrapper.text()).not.toContain('Обновляем список сделок…')
    expect(wrapper.find('.wheel-and-hamster').exists()).toBe(false)
    expect(wrapper.find('.table-stub').exists()).toBe(true)
  })

  it('shows pager whenever there are deals to keep page size selector available', () => {
    const baseStubs = {
      WorkDealsHeader: { template: '<div class="header-stub" />' },
      WorkDealFilterChips: { template: '<div class="chips-stub" />' },
      WorkDealsTableSection: { template: '<div class="table-stub" />' },
    }

    const hiddenWrapper = mount(WorkDealsSection, {
      props: {
        ctx: buildCtx({ dealTotal: 20, dealPageSize: 20 }),
      },
      global: { stubs: baseStubs },
    })
    expect(hiddenWrapper.find('.pager').exists()).toBe(true)

    const visibleWrapper = mount(WorkDealsSection, {
      props: {
        ctx: buildCtx({ dealTotal: 21, dealPageSize: 20 }),
      },
      global: { stubs: baseStubs },
    })
    expect(visibleWrapper.find('.pager').exists()).toBe(true)

    const emptyWrapper = mount(WorkDealsSection, {
      props: {
        ctx: buildCtx({ dealTotal: 0, dealPageSize: 20 }),
      },
      global: { stubs: baseStubs },
    })
    expect(emptyWrapper.find('.pager').exists()).toBe(false)
  })
})
