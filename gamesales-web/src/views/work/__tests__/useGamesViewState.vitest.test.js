import { describe, it, expect, vi } from 'vitest'
import { ref, nextTick } from 'vue'

import { useGamesViewState } from '../useGamesViewState.js'

function createHarness() {
  const games = ref([{ game_id: 1 }, { game_id: 2 }])
  const gamesTotal = ref(40)
  const gamesPage = ref(3)
  const gamesPageInput = ref(1)
  const gamesPageSize = ref(20)
  const loadGames = vi.fn()
  const gameAccounts = ref([
    { login_name: 'beta', score: 2 },
    { login_name: 'alpha', score: 1 },
    { login_name: 'gamma', score: 3 },
  ])
  const gameAccountsSort = ref({ key: 'login_name', dir: 'asc' })
  const gameAccountsPage = ref(1)
  const gameAccountsPageSize = 2

  const state = useGamesViewState({
    games,
    gamesTotal,
    gamesPage,
    gamesPageInput,
    gamesPageSize,
    loadGames,
    gameAccounts,
    gameAccountsSort,
    gameAccountsPage,
    gameAccountsPageSize,
  })

  return {
    state,
    gamesTotal,
    gamesPage,
    gamesPageInput,
    gamesPageSize,
    loadGames,
    gameAccountsSort,
    gameAccountsPage,
  }
}

describe('useGamesViewState', () => {
  it('computes pages and syncs page input', async () => {
    const h = createHarness()
    expect(h.state.gamesTotalPages.value).toBe(2)

    h.gamesPage.value = 2
    await nextTick()
    expect(h.gamesPageInput.value).toBe(2)
  })

  it('clamps page when total pages decrease', async () => {
    const h = createHarness()
    h.gamesTotal.value = 10
    await nextTick()
    expect(h.state.gamesTotalPages.value).toBe(1)
    expect(h.gamesPage.value).toBe(1)
  })

  it('reloads list and resets page when page size changes', async () => {
    const h = createHarness()
    h.gamesPageSize.value = 10
    await nextTick()
    expect(h.gamesPage.value).toBe(1)
    expect(h.loadGames).toHaveBeenCalledTimes(1)
  })

  it('sorts and paginates game accounts', () => {
    const h = createHarness()
    expect(h.state.gameAccountsTotalPages.value).toBe(2)
    expect(h.state.pagedGameAccounts.value.map((a) => a.login_name)).toEqual(['alpha', 'beta'])

    h.gameAccountsSort.value = { key: 'score', dir: 'desc' }
    h.gameAccountsPage.value = 2
    expect(h.state.pagedGameAccounts.value.map((a) => a.score)).toEqual([1])
  })
})
