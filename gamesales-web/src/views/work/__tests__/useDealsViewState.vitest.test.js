import { describe, it, expect, vi, afterEach } from 'vitest'
import { reactive, ref } from 'vue'

import { useDealsViewState } from '../useDealsViewState.js'

function createHarness() {
  const productsAll = ref([
    { product_id: 101, title: 'God of War' },
    { product_id: 102, title: 'FIFA 24' },
  ])
  const newDeal = reactive({ product_id: null, slot_type_code: '' })
  const editDeal = reactive({ product_id: null, slot_type_code: '' })
  const newDealProductSearch = ref('')
  const editDealProductSearch = ref('')
  const dealAccountsForProductNew = ref([{ account_id: 10 }])
  const dealAccountsForProductEdit = ref([{ account_id: 20 }])
  const dealGameAssignmentsNew = ref([
    { assignment_id: 1, account_id: 10, slot_type_code: 'full', released_at: null, assigned_at: '2025-10-01T00:00:00Z' },
    { assignment_id: 2, account_id: 20, slot_type_code: 'full', released_at: null, assigned_at: '2025-11-15T00:00:00Z' },
    { account_id: 10, slot_type_code: 'full', released_at: '2026-01-01' },
  ])
  const dealGameAssignmentsEdit = ref([
    { account_id: 30, slot_type_code: 'share', released_at: null, assigned_at: '2025-10-01T00:00:00Z' },
  ])

  const state = useDealsViewState({
    productsAll,
    newDeal,
    editDeal,
    newDealProductSearch,
    editDealProductSearch,
    dealAccountsForProductNew,
    dealAccountsForProductEdit,
    dealGameAssignmentsNew,
    dealGameAssignmentsEdit,
  })

  return {
    state,
    newDeal,
    editDeal,
    newDealProductSearch,
    editDealProductSearch,
    dealGameAssignmentsNew,
    dealGameAssignmentsEdit,
  }
}

describe('useDealsViewState', () => {
  afterEach(() => {
    // Возвращаем реальные таймеры после тестов с фиксированной датой.
    vi.useRealTimers()
  })

  it('filters games by search and selected game fallback', () => {
    const h = createHarness()
    h.newDealProductSearch.value = 'god'
    expect(h.state.filteredNewDealProducts.value.map((g) => g.product_id)).toEqual([101])

    h.newDealProductSearch.value = ''
    h.newDeal.product_id = 102
    expect(h.state.filteredNewDealProducts.value.map((g) => g.product_id)).toEqual([102])
  })

  it('reports no matches for non-empty search', () => {
    const h = createHarness()
    h.editDealProductSearch.value = 'zzz'
    expect(h.state.editDealProductNoMatches.value).toBe(true)
    expect(h.state.filteredEditDealProducts.value).toEqual([])
  })

  it('returns accounts only when game and slot type are selected', () => {
    const h = createHarness()
    expect(h.state.dealAccountsForNew.value).toEqual([])
    h.newDeal.product_id = 101
    h.newDeal.slot_type_code = 'full'
    expect(h.state.dealAccountsForNew.value).toEqual([{ account_id: 10 }])
  })

  it('filters assignments by slot, released flag and 1-month duplicate rule', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-02-25T00:00:00Z'))
    const h = createHarness()
    h.newDeal.slot_type_code = 'full'
    h.editDeal.slot_type_code = 'share'

    expect(h.state.dealProductAssignmentsForSelectedSlotNew.value).toEqual([
      { assignment_id: 1, account_id: 10, slot_type_code: 'full', released_at: null, assigned_at: '2025-10-01T00:00:00Z' },
      { assignment_id: 2, account_id: 20, slot_type_code: 'full', released_at: null, assigned_at: '2025-11-15T00:00:00Z' },
    ])
    expect(h.state.dealProductAssignmentsForSelectedSlotEdit.value).toEqual([
      { account_id: 30, slot_type_code: 'share', released_at: null, assigned_at: '2025-10-01T00:00:00Z' },
    ])
    expect(h.state.hasAnyProductAssignmentsNew.value).toBe(true)
    expect(h.state.hasAnyProductAssignmentsEdit.value).toBe(true)
  })

  it('allows a duplicate exactly after one calendar month and hides newer assignments', () => {
    // Фиксируем точную границу месячного правила, чтобы дальнейшая смена срока была заметна в тестах.
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-02-25T00:00:00Z'))
    const h = createHarness()
    h.newDeal.slot_type_code = 'full'
    h.dealGameAssignmentsNew.value = [
      { assignment_id: 10, account_id: 10, slot_type_code: 'full', released_at: null, assigned_at: '2026-01-25T00:00:00Z' },
      { assignment_id: 11, account_id: 20, slot_type_code: 'full', released_at: null, assigned_at: '2026-01-26T00:00:00Z' },
    ]

    expect(h.state.dealProductAssignmentsForSelectedSlotNew.value.map((item) => item.assignment_id)).toEqual([10])
  })

  it('clamps the one-month boundary to the last day of a shorter month', () => {
    // На 31 марта календарный месяц назад должен означать 28 февраля, а не переполнение в март.
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-03-31T00:00:00Z'))
    const h = createHarness()
    h.newDeal.slot_type_code = 'full'
    h.dealGameAssignmentsNew.value = [
      { assignment_id: 12, account_id: 10, slot_type_code: 'full', released_at: null, assigned_at: '2026-02-28T00:00:00Z' },
      { assignment_id: 13, account_id: 20, slot_type_code: 'full', released_at: null, assigned_at: '2026-03-01T00:00:00Z' },
    ]

    expect(h.state.dealProductAssignmentsForSelectedSlotNew.value.map((item) => item.assignment_id)).toEqual([12])
  })

  it('matches slot codes case-insensitively for release list', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-02-25T00:00:00Z'))
    const h = createHarness()
    h.newDeal.slot_type_code = ' FULL '
    h.editDeal.slot_type_code = ' Share '

    expect(h.state.dealProductAssignmentsForSelectedSlotNew.value.map((item) => item.assignment_id)).toEqual([1, 2])
    expect(h.state.dealProductAssignmentsForSelectedSlotEdit.value).toEqual([
      { account_id: 30, slot_type_code: 'share', released_at: null, assigned_at: '2025-10-01T00:00:00Z' },
    ])
  })

  it('hides only locked account duplicates and keeps other accounts in the list', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-02-25T00:00:00Z'))
    const h = createHarness()
    h.newDeal.slot_type_code = 'full'
    expect(h.state.dealProductAssignmentsForSelectedSlotNew.value.map((item) => item.assignment_id)).toEqual([1, 2])

    // Имитируем свежий дубль на аккаунте 10: его скрываем, но аккаунт 20 должен остаться доступным.
    h.dealGameAssignmentsNew.value = [
      ...h.dealGameAssignmentsNew.value,
      {
        assignment_id: 4,
        account_id: 10,
        slot_type_code: 'full',
        assigned_at: '2026-01-10T00:00:00Z',
        released_at: null,
      },
      {
        assignment_id: 3,
        account_id: 10,
        slot_type_code: 'full',
        assigned_at: '2026-02-20T00:00:00Z',
        released_at: '2026-02-21T00:00:00Z',
      },
    ]
    expect(h.state.dealProductAssignmentsForSelectedSlotNew.value.map((item) => item.assignment_id)).toEqual([2])
  })

  it('unlocks an account when its overlapping duplicate is older than one month', () => {
    // Подтверждаем, что месячный cooldown не блокирует аккаунт после прохождения границы.
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-02-25T00:00:00Z'))
    const h = createHarness()
    h.newDeal.slot_type_code = 'full'
    h.dealGameAssignmentsNew.value = [
      { assignment_id: 20, account_id: 10, slot_type_code: 'full', assigned_at: '2025-10-01T00:00:00Z', released_at: null },
      { assignment_id: 21, account_id: 10, slot_type_code: 'full', assigned_at: '2026-01-20T00:00:00Z', released_at: null },
    ]

    expect(h.state.dealProductAssignmentsForSelectedSlotNew.value.map((item) => item.assignment_id)).toEqual([20, 21])
  })
})
