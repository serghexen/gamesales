import { describe, it, expect, vi } from 'vitest'
import { reactive, ref } from 'vue'

import { useWorkFilters } from '../useWorkFilters.js'

function createHarness() {
  const loadAccounts = vi.fn()
  const loadGames = vi.fn()
  const loadDeals = vi.fn()

  const accountSort = ref('login_asc')
  const accountsPage = ref(2)
  const accountsPageInput = ref(1)
  const accountsTotalPages = ref(5)

  const gamesSort = ref({ key: 'title', dir: 'asc' })
  const gamesPage = ref(2)
  const gamesPageInput = ref(1)
  const gamesTotalPages = ref(4)

  const usersSort = ref({ key: 'created_at', dir: 'desc' })
  const domainsSortAsc = ref(true)
  const sourcesSort = ref({ key: 'code', dir: 'asc' })
  const platformsSort = ref({ key: 'code', dir: 'asc' })
  const regionsSort = ref({ key: 'code', dir: 'asc' })

  const activeDealFilter = ref('')
  const dealFilters = reactive({
    search_q: 'abc',
    customer_q: 'customer',
    region_q: 'RU',
    status_q: 'pending',
    purchase_from: '',
    purchase_to: '',
    type_q: 'sale',
  })

  const activeGameFilter = ref('')
  const gameFilters = reactive({
    q: 'old',
    platform_code: 'ps5',
    region_code: 'RU',
  })
  const gameFilterDraft = reactive({
    title: '',
    platform: '',
    region: '',
  })

  const activeAccountFilter = ref('')
  const accountFilters = reactive({
    search_q: 's',
    login_q: 'login',
    game_q: 'game',
    region_q: 'RU',
    status_q: 'active',
    date_from: '',
    date_to: '',
  })
  const accountFilterDraft = reactive({
    login: '',
    game: '',
    region: '',
    status: '',
    date_from: '',
    date_to: '',
  })

  const api = useWorkFilters({
    accountSort,
    accountsPage,
    accountsPageInput,
    accountsTotalPages,
    loadAccounts,
    gamesSort,
    gamesPage,
    gamesPageInput,
    gamesTotalPages,
    loadGames,
    usersSort,
    domainsSortAsc,
    sourcesSort,
    platformsSort,
    regionsSort,
    activeDealFilter,
    dealFilters,
    loadDeals,
    activeGameFilter,
    gameFilters,
    gameFilterDraft,
    activeAccountFilter,
    accountFilters,
    accountFilterDraft,
  })

  return {
    api,
    loadAccounts,
    loadGames,
    loadDeals,
    accountSort,
    accountsPage,
    accountsPageInput,
    accountsTotalPages,
    gamesSort,
    gamesPage,
    gamesPageInput,
    gamesTotalPages,
    activeDealFilter,
    dealFilters,
    activeGameFilter,
    gameFilters,
    gameFilterDraft,
    activeAccountFilter,
    accountFilters,
    accountFilterDraft,
  }
}

describe('useWorkFilters', () => {
  it('toggleAccountSort flips order, resets page and reloads accounts', () => {
    const h = createHarness()
    h.api.toggleAccountSort('login')
    expect(h.accountSort.value).toBe('login_desc')
    expect(h.accountsPage.value).toBe(1)
    expect(h.loadAccounts).toHaveBeenCalledTimes(1)
  })

  it('setGamesPage clamps range and reloads only when page changed', () => {
    const h = createHarness()
    h.api.setGamesPage(999)
    expect(h.gamesPage.value).toBe(4)
    expect(h.loadGames).toHaveBeenCalledTimes(1)

    h.api.setGamesPage(4)
    expect(h.loadGames).toHaveBeenCalledTimes(1)
  })

  it('validateDealRange detects invalid period', () => {
    const h = createHarness()
    h.dealFilters.purchase_from = '2026-02-10'
    h.dealFilters.purchase_to = '2026-02-09'
    expect(h.api.validateDealRange('date')).toBe(false)
    expect(h.api.dealFilterErrors.date).toContain('не может быть позже')
  })

  it('resetDealFilter all clears values and reloads first page', () => {
    const h = createHarness()
    h.activeDealFilter.value = 'search'
    h.api.resetDealFilter('all')

    expect(h.dealFilters.search_q).toBe('')
    expect(h.dealFilters.type_q).toBe('')
    expect(h.dealFilters.customer_q).toBe('')
    expect(h.dealFilters.region_q).toBe('')
    expect(h.dealFilters.status_q).toBe('')
    expect(h.dealFilters.purchase_from).toBe('')
    expect(h.dealFilters.purchase_to).toBe('')
    expect(h.activeDealFilter.value).toBe('')
    expect(h.loadDeals).toHaveBeenCalledWith(1)
  })

  it('openGameFilter copies values to draft and applyGameFilter trims input', () => {
    const h = createHarness()
    h.api.openGameFilter('title')
    expect(h.gameFilterDraft.title).toBe('old')
    expect(h.activeGameFilter.value).toBe('title')

    h.gameFilterDraft.title = '  New title  '
    h.api.applyGameFilter('title')
    expect(h.gameFilters.q).toBe('New title')
    expect(h.gamesPage.value).toBe(1)
    expect(h.activeGameFilter.value).toBe('')
    expect(h.loadGames).toHaveBeenCalledTimes(1)
  })

  it('applyAccountFilter date blocks reload on invalid range', () => {
    const h = createHarness()
    h.accountFilterDraft.date_from = '2026-02-10'
    h.accountFilterDraft.date_to = '2026-02-09'

    h.api.applyAccountFilter('date')
    expect(h.api.accountFilterErrors.date).toContain('не может быть позже')
    expect(h.loadAccounts).not.toHaveBeenCalled()
  })

  it('applyAccountFilter date applies valid range and reloads', () => {
    const h = createHarness()
    h.activeAccountFilter.value = 'date'
    h.accountFilterDraft.date_from = '2026-02-09'
    h.accountFilterDraft.date_to = '2026-02-10'

    h.api.applyAccountFilter('date')
    expect(h.accountFilters.date_from).toBe('2026-02-09')
    expect(h.accountFilters.date_to).toBe('2026-02-10')
    expect(h.activeAccountFilter.value).toBe('')
    expect(h.accountsPage.value).toBe(1)
    expect(h.loadAccounts).toHaveBeenCalledTimes(1)
  })

  it('resetAccountFilter all clears draft and applied filters', () => {
    const h = createHarness()
    h.accountFilterDraft.login = 'x'
    h.accountFilterDraft.game = 'y'
    h.accountFilterDraft.region = 'z'
    h.accountFilterDraft.status = 'blocked'
    h.accountFilterDraft.date_from = '2026-01-01'
    h.accountFilterDraft.date_to = '2026-02-01'

    h.api.resetAccountFilter('all')
    expect(h.accountFilters.search_q).toBe('')
    expect(h.accountFilters.login_q).toBe('')
    expect(h.accountFilters.game_q).toBe('')
    expect(h.accountFilters.region_q).toBe('')
    expect(h.accountFilters.status_q).toBe('')
    expect(h.accountFilters.date_from).toBe('')
    expect(h.accountFilters.date_to).toBe('')
    expect(h.accountFilterDraft.login).toBe('')
    expect(h.accountFilterDraft.date_to).toBe('')
    expect(h.accountsPage.value).toBe(1)
    expect(h.loadAccounts).toHaveBeenCalledTimes(1)
  })
})
