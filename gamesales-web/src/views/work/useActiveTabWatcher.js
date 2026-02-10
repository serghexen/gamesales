import { watch } from 'vue'

export function useActiveTabWatcher({
  activeTab,
  isAdmin,
  dealFilters,
  defaultDealsResponsibleFilter,
  showUserForm,
  showGameForm,
  showGameFilters,
  showDealForm,
  showAccountFilters,
  activeGameFilter,
  activeAccountFilter,
  editGame,
  pwdOk,
  showPwdForm,
  catalogsLoadedOnce,
  domainsLoadedOnce,
  sourcesLoadedOnce,
  slotTypesLoadedOnce,
  accountsAllLoadedOnce,
  gamesAllLoadedOnce,
  dealsBootstrapped,
  platforms,
  regions,
  domains,
  sources,
  slotTypes,
  games,
  gamesAll,
  accountsAll,
  gamesPage,
  accountsPage,
  checkApi,
  loadUsers,
  loadCatalogs,
  loadDomains,
  loadSources,
  loadSlotTypes,
  loadGames,
  loadGamesAll,
  loadAccounts,
  loadAccountsAll,
  loadDeals,
  loadTelegramStatus,
  startTelegramPolling,
  stopTelegramPolling,
}) {
  // Главный watcher вкладок: подгружает данные только для активного раздела.
  watch(activeTab, async (tab) => {
    if (tab !== 'telegram') {
      // Если ушли с Telegram, сразу останавливаем опрос.
      stopTelegramPolling()
    }
    if (tab === 'dashboard') {
      checkApi()
      return
    }
    if (tab === 'profile') {
      pwdOk.value = false
      showPwdForm.value = false
      return
    }
    if (tab === 'games') {
      if (!catalogsLoadedOnce.value && (!platforms.value.length || !regions.value.length)) {
        await loadCatalogs()
        if (platforms.value.length || regions.value.length) catalogsLoadedOnce.value = true
      }
      gamesPage.value = 1
      if (!games.value.length) {
        await loadGames()
      }
      if (!gamesAllLoadedOnce.value && !gamesAll.value.length) {
        await loadGamesAll()
        if (gamesAll.value.length) gamesAllLoadedOnce.value = true
      }
      showGameForm.value = false
      showGameFilters.value = false
      activeGameFilter.value = ''
      editGame.open = false
      return
    }
    if (tab === 'accounts') {
      if (!catalogsLoadedOnce.value && (!platforms.value.length || !regions.value.length)) {
        await loadCatalogs()
        if (platforms.value.length || regions.value.length) catalogsLoadedOnce.value = true
      }
      if (!domainsLoadedOnce.value && !domains.value.length) {
        await loadDomains()
        if (domains.value.length) domainsLoadedOnce.value = true
      }
      if (!gamesAllLoadedOnce.value && !gamesAll.value.length) {
        await loadGamesAll()
        if (gamesAll.value.length) gamesAllLoadedOnce.value = true
      }
      if (!slotTypesLoadedOnce.value && !slotTypes.value.length) {
        await loadSlotTypes()
        if (slotTypes.value.length) slotTypesLoadedOnce.value = true
      }
      accountsPage.value = 1
      await loadAccounts()
      showAccountFilters.value = false
      activeAccountFilter.value = ''
      return
    }
    if (tab === 'deals') {
      // Для manager/operator по умолчанию показываем только сделки "на себя".
      if (!dealFilters.responsible_q) {
        const rawDefault = typeof defaultDealsResponsibleFilter === 'object' && defaultDealsResponsibleFilter
          ? defaultDealsResponsibleFilter.value
          : defaultDealsResponsibleFilter
        const normalizedDefault = String(rawDefault || '').trim()
        if (normalizedDefault) {
          dealFilters.responsible_q = normalizedDefault
        }
      }
      const tasks = [loadDeals(1)]
      if (!dealsBootstrapped.value) {
        if (!accountsAllLoadedOnce.value) {
          tasks.push(loadAccountsAll().then(() => {
            if (accountsAll.value.length) accountsAllLoadedOnce.value = true
          }))
        }
        if (!gamesAllLoadedOnce.value) {
          tasks.push(loadGamesAll().then(() => {
            if (gamesAll.value.length) gamesAllLoadedOnce.value = true
          }))
        }
        if (!catalogsLoadedOnce.value) {
          tasks.push(loadCatalogs().then(() => {
            if (platforms.value.length || regions.value.length) catalogsLoadedOnce.value = true
          }))
        }
        if (!sourcesLoadedOnce.value) {
          tasks.push(loadSources().then(() => {
            if (sources.value.length) sourcesLoadedOnce.value = true
          }))
        }
        if (!domainsLoadedOnce.value) {
          tasks.push(loadDomains().then(() => {
            if (domains.value.length) domainsLoadedOnce.value = true
          }))
        }
        if (!slotTypesLoadedOnce.value) {
          tasks.push(loadSlotTypes().then(() => {
            if (slotTypes.value.length) slotTypesLoadedOnce.value = true
          }))
        }
      }
      await Promise.all(tasks)
      dealsBootstrapped.value = true
      showDealForm.value = false
      return
    }
    if (tab === 'analytics') {
      const tasks = []
      if (!catalogsLoadedOnce.value && (!platforms.value.length || !regions.value.length)) {
        tasks.push(loadCatalogs().then(() => {
          if (platforms.value.length || regions.value.length) catalogsLoadedOnce.value = true
        }))
      }
      if (!sourcesLoadedOnce.value && !sources.value.length) {
        tasks.push(loadSources().then(() => {
          if (sources.value.length) sourcesLoadedOnce.value = true
        }))
      }
      await Promise.all(tasks)
      return
    }
    if (tab === 'telegram') {
      await loadTelegramStatus()
      startTelegramPolling()
      return
    }
    if (tab === 'catalogs') {
      const tasks = []
      if (!domainsLoadedOnce.value && !domains.value.length) tasks.push(loadDomains().then(() => {
        if (domains.value.length) domainsLoadedOnce.value = true
      }))
      if (!sourcesLoadedOnce.value && !sources.value.length) tasks.push(loadSources().then(() => {
        if (sources.value.length) sourcesLoadedOnce.value = true
      }))
      if (!catalogsLoadedOnce.value && (!platforms.value.length || !regions.value.length)) tasks.push(loadCatalogs().then(() => {
        if (platforms.value.length || regions.value.length) catalogsLoadedOnce.value = true
      }))
      await Promise.all(tasks)
      return
    }
    if (tab === 'users' && isAdmin.value) {
      await loadUsers()
      showUserForm.value = false
    }
  }, { immediate: true })
}
