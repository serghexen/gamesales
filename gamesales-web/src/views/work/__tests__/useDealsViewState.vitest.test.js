import { describe, it, expect } from 'vitest'
import { reactive, ref } from 'vue'

import { useDealsViewState } from '../useDealsViewState.js'

function createHarness() {
  const gamesAll = ref([
    { game_id: 1, title: 'God of War' },
    { game_id: 2, title: 'FIFA 24' },
  ])
  const newDeal = reactive({ game_id: null, slot_type_code: '' })
  const editDeal = reactive({ game_id: null, slot_type_code: '' })
  const newDealGameSearch = ref('')
  const editDealGameSearch = ref('')
  const dealAccountsForGameNew = ref([{ account_id: 10 }])
  const dealAccountsForGameEdit = ref([{ account_id: 20 }])
  const dealGameAssignmentsNew = ref([
    { slot_type_code: 'full', released_at: null },
    { slot_type_code: 'full', released_at: '2026-01-01' },
  ])
  const dealGameAssignmentsEdit = ref([
    { slot_type_code: 'share', released_at: null },
  ])

  const state = useDealsViewState({
    gamesAll,
    newDeal,
    editDeal,
    newDealGameSearch,
    editDealGameSearch,
    dealAccountsForGameNew,
    dealAccountsForGameEdit,
    dealGameAssignmentsNew,
    dealGameAssignmentsEdit,
  })

  return {
    state,
    newDeal,
    editDeal,
    newDealGameSearch,
    editDealGameSearch,
  }
}

describe('useDealsViewState', () => {
  it('filters games by search and selected game fallback', () => {
    const h = createHarness()
    h.newDealGameSearch.value = 'god'
    expect(h.state.filteredNewDealGames.value.map((g) => g.game_id)).toEqual([1])

    h.newDealGameSearch.value = ''
    h.newDeal.game_id = 2
    expect(h.state.filteredNewDealGames.value.map((g) => g.game_id)).toEqual([2])
  })

  it('reports no matches for non-empty search', () => {
    const h = createHarness()
    h.editDealGameSearch.value = 'zzz'
    expect(h.state.editDealGameNoMatches.value).toBe(true)
    expect(h.state.filteredEditDealGames.value).toEqual([])
  })

  it('returns accounts only when game and slot type are selected', () => {
    const h = createHarness()
    expect(h.state.dealAccountsForNew.value).toEqual([])
    h.newDeal.game_id = 1
    h.newDeal.slot_type_code = 'full'
    expect(h.state.dealAccountsForNew.value).toEqual([{ account_id: 10 }])
  })

  it('filters assignments by slot and released flag', () => {
    const h = createHarness()
    h.newDeal.slot_type_code = 'full'
    h.editDeal.slot_type_code = 'share'

    expect(h.state.dealGameAssignmentsForSelectedSlotNew.value).toEqual([
      { slot_type_code: 'full', released_at: null },
    ])
    expect(h.state.dealGameAssignmentsForSelectedSlotEdit.value).toEqual([
      { slot_type_code: 'share', released_at: null },
    ])
    expect(h.state.hasAnyGameAssignmentsNew.value).toBe(true)
    expect(h.state.hasAnyGameAssignmentsEdit.value).toBe(true)
  })
})
