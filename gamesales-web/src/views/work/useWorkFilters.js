import { reactive } from 'vue'

export function useWorkFilters({
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
}) {
  // Ошибки валидации фильтров (например, диапазон дат).
  const dealFilterErrors = reactive({
    date: '',
  })

  const accountFilterErrors = reactive({
    date: '',
  })

  // Переключает сортировку списка аккаунтов.
  function toggleAccountSort(key) {
    const map = {
      login: ['login_asc', 'login_desc'],
      games: ['games_asc', 'games_desc'],
      region: ['region_asc', 'region_desc'],
      status: ['status_asc', 'status_desc'],
      date: ['date_asc', 'date_desc'],
    }
    const [asc, desc] = map[key] || []
    if (!asc) return
    accountSort.value = accountSort.value === asc ? desc : asc
    accountsPage.value = 1
    loadAccounts()
  }

  // Переключает сортировку списка игр.
  function toggleGamesSort(key) {
    const current = gamesSort.value
    if (current.key === key) {
      current.dir = current.dir === 'asc' ? 'desc' : 'asc'
    } else {
      gamesSort.value = { key, dir: 'asc' }
    }
    gamesPage.value = 1
    loadGames()
  }

  function toggleUsersSort(key) {
    const current = usersSort.value
    if (current.key === key) {
      current.dir = current.dir === 'asc' ? 'desc' : 'asc'
    } else {
      usersSort.value = { key, dir: 'asc' }
    }
  }

  function toggleDomainsSort() {
    domainsSortAsc.value = !domainsSortAsc.value
  }

  function toggleSourcesSort(key) {
    const current = sourcesSort.value
    if (current.key === key) {
      current.dir = current.dir === 'asc' ? 'desc' : 'asc'
    } else {
      sourcesSort.value = { key, dir: 'asc' }
    }
  }

  function togglePlatformsSort(key) {
    const current = platformsSort.value
    if (current.key === key) {
      current.dir = current.dir === 'asc' ? 'desc' : 'asc'
    } else {
      platformsSort.value = { key, dir: 'asc' }
    }
  }

  function toggleRegionsSort(key) {
    const current = regionsSort.value
    if (current.key === key) {
      current.dir = current.dir === 'asc' ? 'desc' : 'asc'
    } else {
      regionsSort.value = { key, dir: 'asc' }
    }
  }

  // Переход по страницам игр.
  function setGamesPage(page) {
    const target = Math.min(Math.max(1, Number(page) || 1), gamesTotalPages.value)
    if (target === gamesPage.value) return
    gamesPage.value = target
    loadGames()
  }

  function jumpGamesPage() {
    setGamesPage(gamesPageInput.value)
  }

  function prevGamesPage() {
    setGamesPage(gamesPage.value - 1)
  }

  function nextGamesPage() {
    setGamesPage(gamesPage.value + 1)
  }

  // Переход по страницам аккаунтов.
  function setAccountsPage(page) {
    const target = Math.min(Math.max(1, Number(page) || 1), accountsTotalPages.value)
    if (target === accountsPage.value) return
    accountsPage.value = target
    loadAccounts()
  }

  function jumpAccountsPage() {
    setAccountsPage(accountsPageInput.value)
  }

  function prevAccountsPage() {
    setAccountsPage(accountsPage.value - 1)
  }

  function nextAccountsPage() {
    setAccountsPage(accountsPage.value + 1)
  }

  // Проверяет, что дата "с" не позже даты "по".
  const validateDealRange = (kind) => {
    let error = ''
    if (kind === 'date') {
      const from = dealFilters.purchase_from
      const to = dealFilters.purchase_to
      if (from && to && new Date(from) > new Date(to)) {
        error = 'Дата "с" не может быть позже даты "по"'
      }
    }
    dealFilterErrors[kind] = error
    return !error
  }

  // Сбрасывает фильтр сделок и перезагружает список.
  const resetDealFilter = (kind) => {
    if (kind === 'customer') {
      dealFilters.customer_q = ''
    } else if (kind === 'region') {
      dealFilters.region_q = ''
    } else if (kind === 'type') {
      dealFilters.type_q = ''
    } else if (kind === 'status') {
      dealFilters.status_q = ''
    } else if (kind === 'search') {
      dealFilters.search_q = ''
    } else if (kind === 'date') {
      dealFilters.purchase_from = ''
      dealFilters.purchase_to = ''
      dealFilterErrors.date = ''
    } else if (kind === 'all') {
      dealFilters.search_q = ''
      dealFilters.type_q = ''
      dealFilters.customer_q = ''
      dealFilters.region_q = ''
      dealFilters.status_q = ''
      dealFilters.purchase_from = ''
      dealFilters.purchase_to = ''
      dealFilterErrors.date = ''
    }
    activeDealFilter.value = ''
    loadDeals(1)
  }

  // Сбрасывает фильтр игр и перезагружает список.
  const resetGameFilter = (kind) => {
    if (kind === 'title') {
      gameFilters.q = ''
      gameFilterDraft.title = ''
    } else if (kind === 'platform') {
      gameFilters.platform_code = ''
      gameFilterDraft.platform = ''
    } else if (kind === 'region') {
      gameFilters.region_code = ''
      gameFilterDraft.region = ''
    } else if (kind === 'all') {
      gameFilters.q = ''
      gameFilters.platform_code = ''
      gameFilters.region_code = ''
      gameFilterDraft.title = ''
      gameFilterDraft.platform = ''
      gameFilterDraft.region = ''
    }
    gamesPage.value = 1
    activeGameFilter.value = ''
    loadGames()
  }

  // Открывает выпадающий фильтр по играм и копирует текущие значения в черновик.
  const openGameFilter = (kind) => {
    gameFilterDraft.title = gameFilters.q || ''
    gameFilterDraft.platform = gameFilters.platform_code || ''
    gameFilterDraft.region = gameFilters.region_code || ''
    activeGameFilter.value = activeGameFilter.value === kind ? '' : kind
  }

  // Применяет выбранный фильтр по играм.
  const applyGameFilter = (kind) => {
    if (kind === 'title') {
      gameFilters.q = gameFilterDraft.title.trim()
    } else if (kind === 'platform') {
      gameFilters.platform_code = gameFilterDraft.platform.trim()
    } else if (kind === 'region') {
      gameFilters.region_code = gameFilterDraft.region.trim()
    }
    gamesPage.value = 1
    activeGameFilter.value = ''
    loadGames()
  }

  const validateAccountDateRange = () => {
    let error = ''
    if (accountFilterDraft.date_from && accountFilterDraft.date_to) {
      if (new Date(accountFilterDraft.date_from) > new Date(accountFilterDraft.date_to)) {
        error = 'Дата "с" не может быть позже даты "по"'
      }
    }
    accountFilterErrors.date = error
    return !error
  }

  const resetAccountFilter = (kind) => {
    if (kind === 'search') {
      accountFilters.search_q = ''
    } else if (kind === 'login') {
      accountFilters.login_q = ''
      accountFilterDraft.login = ''
    } else if (kind === 'game') {
      accountFilters.game_q = ''
      accountFilterDraft.game = ''
    } else if (kind === 'region') {
      accountFilters.region_q = ''
      accountFilterDraft.region = ''
    } else if (kind === 'status') {
      accountFilters.status_q = ''
      accountFilterDraft.status = ''
    } else if (kind === 'date') {
      accountFilters.date_from = ''
      accountFilters.date_to = ''
      accountFilterDraft.date_from = ''
      accountFilterDraft.date_to = ''
      accountFilterErrors.date = ''
    } else if (kind === 'all') {
      accountFilters.search_q = ''
      accountFilters.login_q = ''
      accountFilters.game_q = ''
      accountFilters.region_q = ''
      accountFilters.status_q = ''
      accountFilters.date_from = ''
      accountFilters.date_to = ''
      accountFilterDraft.login = ''
      accountFilterDraft.game = ''
      accountFilterDraft.region = ''
      accountFilterDraft.status = ''
      accountFilterDraft.date_from = ''
      accountFilterDraft.date_to = ''
      accountFilterErrors.date = ''
    }
    activeAccountFilter.value = ''
    accountsPage.value = 1
    loadAccounts()
  }

  const openAccountFilter = (kind) => {
    accountFilterDraft.login = accountFilters.login_q || ''
    accountFilterDraft.game = accountFilters.game_q || ''
    accountFilterDraft.region = accountFilters.region_q || ''
    accountFilterDraft.status = accountFilters.status_q || ''
    accountFilterDraft.date_from = accountFilters.date_from || ''
    accountFilterDraft.date_to = accountFilters.date_to || ''
    activeAccountFilter.value = activeAccountFilter.value === kind ? '' : kind
  }

  const applyAccountFilter = (kind) => {
    if (kind === 'login') {
      accountFilters.login_q = accountFilterDraft.login.trim()
    } else if (kind === 'game') {
      accountFilters.game_q = accountFilterDraft.game.trim()
    } else if (kind === 'region') {
      accountFilters.region_q = accountFilterDraft.region.trim()
    } else if (kind === 'status') {
      accountFilters.status_q = accountFilterDraft.status.trim()
    } else if (kind === 'date') {
      if (!validateAccountDateRange()) return
      accountFilters.date_from = accountFilterDraft.date_from
      accountFilters.date_to = accountFilterDraft.date_to
    }
    activeAccountFilter.value = ''
    accountsPage.value = 1
    loadAccounts()
  }

  return {
    toggleAccountSort,
    toggleGamesSort,
    toggleUsersSort,
    toggleDomainsSort,
    toggleSourcesSort,
    togglePlatformsSort,
    toggleRegionsSort,
    setGamesPage,
    jumpGamesPage,
    prevGamesPage,
    nextGamesPage,
    setAccountsPage,
    jumpAccountsPage,
    prevAccountsPage,
    nextAccountsPage,
    resetDealFilter,
    validateDealRange,
    dealFilterErrors,
    resetGameFilter,
    openGameFilter,
    applyGameFilter,
    resetAccountFilter,
    openAccountFilter,
    applyAccountFilter,
    accountFilterErrors,
    validateAccountDateRange,
  }
}
