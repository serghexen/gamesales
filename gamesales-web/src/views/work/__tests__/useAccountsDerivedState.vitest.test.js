import { describe, it, expect } from 'vitest'
import { ref } from 'vue'

import { useAccountsDerivedState } from '../useAccountsDerivedState.js'

describe('useAccountsDerivedState', () => {
  it('returns accounts copy and filters games by search for create/edit', () => {
    const accounts = ref([{ account_id: 1 }, { account_id: 2 }])
    const gamesAll = ref([
      { game_id: 1, title: 'God of War' },
      { game_id: 2, title: 'FIFA 24' },
    ])
    const accountGameSearch = ref('god')
    const editAccountGameSearch = ref('fifa')

    const s = useAccountsDerivedState({
      accounts,
      gamesAll,
      accountGameSearch,
      editAccountGameSearch,
    })

    expect(s.sortedAccounts.value).toEqual(accounts.value)
    expect(s.sortedAccounts.value).not.toBe(accounts.value)
    expect(s.filteredAccountGames.value.map((g) => g.game_id)).toEqual([1])
    expect(s.filteredEditAccountGames.value.map((g) => g.game_id)).toEqual([2])
  })
})
