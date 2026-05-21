import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

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
    dealEditingByDealId: {},
    currentUsername: 'admin',
    responsibleNameByUsername: {},
    showDealWarning: () => {},
    formatDateTimeMinutes: (value) => String(value || ''),
    dealShowCompleted: false,
    markDealCompleted: () => {},
    markDealReturned: () => {},
    dealSaving: false,
    dealCompletingId: null,
    realtimeAnimationTick: 0,
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

  it('shows return action for completed non-refund rental', async () => {
    const markDealReturned = vi.fn()
    const wrapper = mount(WorkDealsTableSection, {
      props: buildProps({
        dealShowCompleted: true,
        markDealReturned,
        sortedDeals: [
          {
            deal_id: 2,
            deal_type: 'Шеринг',
            deal_type_code: 'rental',
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

  it('shows subscription term date in product column for rental subscriptions', () => {
    const wrapper = mount(WorkDealsTableSection, {
      props: buildProps({
        sortedDeals: [
          {
            deal_id: 21,
            deal_type: 'Шеринг',
            deal_type_code: 'rental',
            customer_nickname: 'Покупатель',
            product_title: 'EA PLAY',
            subscription_term_id: 901,
            subscription_valid_until: '2026-10-28',
            flow_status: 'Завершен',
            responsible_username: 'manager',
          },
        ],
      }),
    })

    expect(wrapper.text()).toContain('EA PLAY до 28.10.2026')
  })

  it('calls completion action from complete button in pending list', async () => {
    const markDealCompleted = vi.fn()
    const wrapper = mount(WorkDealsTableSection, {
      props: buildProps({
        markDealCompleted,
        dealShowCompleted: false,
        sortedDeals: [
          {
            deal_id: 1,
            deal_type: 'Продажа',
            customer_nickname: 'Покупатель',
            region_code: 'RU',
            purchase_at: '2026-02-11 10:00',
            created_at: '2026-02-11 09:00',
            completed_at: null,
            flow_status: 'В ожидании',
            responsible_username: 'manager',
          },
        ],
      }),
    })

    await wrapper.find('button.mini-btn--complete').trigger('click')
    expect(markDealCompleted).toHaveBeenCalledTimes(1)
  })

  it('does not show complete action for draft deal in pending list', () => {
    const markDealCompleted = vi.fn()
    const wrapper = mount(WorkDealsTableSection, {
      props: buildProps({
        markDealCompleted,
        dealShowCompleted: false,
        sortedDeals: [
          {
            deal_id: 3,
            deal_type: 'Продажа',
            deal_type_code: 'sale',
            flow_status: 'Черновик',
            flow_status_code: 'draft',
            customer_nickname: 'Покупатель',
            responsible_username: 'manager',
            is_refund: false,
          },
        ],
      }),
    })

    expect(wrapper.find('button.mini-btn--complete').exists()).toBe(false)
    expect(wrapper.find('button.mini-btn--danger').exists()).toBe(false)
    expect(markDealCompleted).not.toHaveBeenCalled()
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

  it('supports multi-select for status filter', async () => {
    const dealFilters = {
      type_q: '',
      customer_q: '',
      region_q: '',
      purchase_from: '',
      purchase_to: '',
      status_q: '',
      responsible_q: '',
    }

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

  it('marks newly added rows with flip animation class', async () => {
    const wrapper = mount(WorkDealsTableSection, {
      props: buildProps({
        sortedDeals: [
          { deal_id: 1, deal_type: 'Продажа', customer_nickname: 'A', region_code: 'RU', flow_status: 'В ожидании', responsible_username: 'm1' },
        ],
      }),
    })

    await wrapper.setProps({
      sortedDeals: [
        { deal_id: 1, deal_type: 'Продажа', customer_nickname: 'A', region_code: 'RU', flow_status: 'В ожидании', responsible_username: 'm1' },
        { deal_id: 2, deal_type: 'Продажа', customer_nickname: 'B', region_code: 'RU', flow_status: 'В ожидании', responsible_username: 'm1' },
      ],
      realtimeAnimationTick: 1,
    })
    await nextTick()

    const rows = wrapper.findAll('tbody tr')
    expect(rows[1].classes()).toContain('deal-row-flip-in')
  })

  it('does not animate rows when list changed without websocket tick', async () => {
    const wrapper = mount(WorkDealsTableSection, {
      props: buildProps({
        sortedDeals: [
          { deal_id: 1, deal_type: 'Продажа', customer_nickname: 'A', region_code: 'RU', flow_status: 'В ожидании', responsible_username: 'm1' },
        ],
        realtimeAnimationTick: 0,
      }),
    })

    await wrapper.setProps({
      sortedDeals: [
        { deal_id: 1, deal_type: 'Продажа', customer_nickname: 'A', region_code: 'RU', flow_status: 'В ожидании', responsible_username: 'm1' },
        { deal_id: 2, deal_type: 'Продажа', customer_nickname: 'B', region_code: 'RU', flow_status: 'В ожидании', responsible_username: 'm1' },
      ],
      realtimeAnimationTick: 0,
    })
    await nextTick()

    const rows = wrapper.findAll('tbody tr')
    expect(rows[1].classes()).not.toContain('deal-row-flip-in')
  })

  it('animates removed row and blocks click while it disappears', async () => {
    vi.useFakeTimers()
    const startEditDeal = vi.fn()
    const wrapper = mount(WorkDealsTableSection, {
      props: buildProps({
        startEditDeal,
        sortedDeals: [
          { deal_id: 1, deal_type: 'Продажа', customer_nickname: 'A', region_code: 'RU', flow_status: 'В ожидании', responsible_username: 'm1' },
          { deal_id: 2, deal_type: 'Продажа', customer_nickname: 'B', region_code: 'RU', flow_status: 'В ожидании', responsible_username: 'm1' },
        ],
      }),
    })

    await wrapper.setProps({
      sortedDeals: [
        { deal_id: 1, deal_type: 'Продажа', customer_nickname: 'A', region_code: 'RU', flow_status: 'В ожидании', responsible_username: 'm1' },
      ],
      realtimeAnimationTick: 1,
    })
    await nextTick()

    const row = wrapper.find('tbody tr[data-deal-id="2"]')
    expect(row.exists()).toBe(true)
    expect(row.classes()).toContain('deal-row-flip-out')

    await row.trigger('click')
    expect(startEditDeal).not.toHaveBeenCalled()

    vi.advanceTimersByTime(820)
    await nextTick()
    expect(wrapper.find('tbody tr[data-deal-id="2"]').exists()).toBe(false)
    vi.useRealTimers()
  })

  it('blocks row open when deal is edited by another user', async () => {
    const startEditDeal = vi.fn()
    const showDealWarning = vi.fn()
    const wrapper = mount(WorkDealsTableSection, {
      props: buildProps({
        startEditDeal,
        showDealWarning,
        currentUsername: 'admin',
        dealEditingByDealId: {
          10: { actor: 'manager-1', changedAt: '2026-02-16T20:00:00Z' },
        },
        responsibleNameByUsername: {
          'manager-1': 'Иван',
        },
        sortedDeals: [
          { deal_id: 10, deal_type: 'Продажа', customer_nickname: 'A', region_code: 'RU', flow_status: 'В ожидании', responsible_username: 'm1' },
        ],
      }),
    })

    await wrapper.find('tbody tr[data-deal-id="10"]').trigger('click')

    expect(startEditDeal).not.toHaveBeenCalled()
    expect(showDealWarning).toHaveBeenCalledWith('Сделку сейчас редактирует Иван')
    expect(wrapper.find('tbody tr[data-deal-id="10"]').classes()).toContain('deal-row-locked')
    expect(wrapper.find('tbody tr[data-deal-id="10"]').attributes('data-lock-label')).toBe('Редактирует: Иван')
  })
})
