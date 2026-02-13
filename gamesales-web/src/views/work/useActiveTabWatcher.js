import { watch } from 'vue'

export function useActiveTabWatcher({
  activeTab,
  isAdmin,
  dealFilters,
  defaultDealsResponsibleFilter,
  mustPrefillDealsResponsible,
  showUserForm,
  showProductForm,
  showProductFilters,
  showDealForm,
  showAccountFilters,
  activeProductFilter,
  activeAccountFilter,
  editProduct,
  pwdOk,
  showPwdForm,
  catalogsLoadedOnce,
  domainsLoadedOnce,
  sourcesLoadedOnce,
  slotTypesLoadedOnce,
  accountsAllLoadedOnce,
  productsAllLoadedOnce,
  dealsBootstrapped,
  platforms,
  regions,
  domains,
  sources,
  slotTypes,
  products,
  productsAll,
  accountsAll,
  productsPage,
  accountsPage,
  checkApi,
  loadUsers,
  loadCatalogs,
  loadDomains,
  loadSources,
  loadSlotTypes,
  loadProducts,
  loadProductsAll,
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
    if (tab === 'products') {
      if (!catalogsLoadedOnce.value && (!platforms.value.length || !regions.value.length)) {
        await loadCatalogs()
        if (platforms.value.length || regions.value.length) catalogsLoadedOnce.value = true
      }
      productsPage.value = 1
      if (!products.value.length) {
        await loadProducts()
      }
      if (!productsAllLoadedOnce.value && !productsAll.value.length) {
        await loadProductsAll()
        if (productsAll.value.length) productsAllLoadedOnce.value = true
      }
      showProductForm.value = false
      showProductFilters.value = false
      activeProductFilter.value = ''
      editProduct.open = false
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
      if (!productsAllLoadedOnce.value && !productsAll.value.length) {
        await loadProductsAll()
        if (productsAll.value.length) productsAllLoadedOnce.value = true
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
      const needResponsiblePrefill = typeof mustPrefillDealsResponsible === 'object' && mustPrefillDealsResponsible
        ? Boolean(mustPrefillDealsResponsible.value)
        : Boolean(mustPrefillDealsResponsible)
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
      const canLoadDealsNow = !needResponsiblePrefill || Boolean(String(dealFilters.responsible_q || '').trim())
      const tasks = canLoadDealsNow ? [loadDeals(1)] : []
      if (!dealsBootstrapped.value) {
        if (!accountsAllLoadedOnce.value) {
          tasks.push(loadAccountsAll().then(() => {
            if (accountsAll.value.length) accountsAllLoadedOnce.value = true
          }))
        }
        if (!productsAllLoadedOnce.value) {
          tasks.push(loadProductsAll().then(() => {
            if (productsAll.value.length) productsAllLoadedOnce.value = true
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
