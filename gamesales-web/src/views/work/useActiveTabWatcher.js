import { watch } from 'vue'

export function useActiveTabWatcher({
  activeTab,
  isAdmin,
  dealFilters,
  productFilters,
  accountFilters,
  productFilterDraft,
  accountFilterDraft,
  defaultDealsResponsibleFilter,
  mustPrefillDealsResponsible,
  showUserForm,
  showProductForm,
  showProductFilters,
  showDealForm,
  showAccountFilters,
  activeProductFilter,
  activeAccountFilter,
  nsGiftOk,
  nsGiftError,
  editProduct,
  pwdOk,
  showPwdForm,
  catalogsLoadedOnce,
  domainsLoadedOnce,
  sourcesLoadedOnce,
  messengersLoadedOnce = { value: false },
  slotTypesLoadedOnce,
  accountsAllLoadedOnce,
  productsAllLoadedOnce,
  dealsBootstrapped,
  platforms,
  regions,
  domains,
  sources,
  messengers = { value: [] },
  slotTypes,
  productsAll,
  accountsAll,
  productsPage,
  accountsPage,
  checkApi,
  loadUsers,
  loadCatalogs,
  loadDomains,
  loadSources,
  loadMessengers = async () => {},
  loadSlotTypes,
  loadProducts,
  loadProductsAll,
  loadAccounts,
  loadAccountsAll,
  loadDeals,
  loadNsGiftBalance,
  loadNsGiftCategories,
  reloadNsGiftData,
  loadTelegramStatus,
  startTelegramPolling,
  stopTelegramPolling,
}) {
  let activeTabRequestSeq = 0

  // Главный watcher вкладок: подгружает данные только для активного раздела.
  watch(activeTab, async (tab) => {
    const requestId = ++activeTabRequestSeq
    // Гарантирует, что пост-эффекты применяются только для самого свежего переключения вкладки.
    const isCurrentRequest = (expectedTab = null) => {
      if (requestId !== activeTabRequestSeq) return false
      if (!expectedTab) return true
      return activeTab.value === expectedTab
    }

    // На каждом входе во вкладку очищаем поисковые поля, чтобы не тянуть старый запрос.
    if (tab === 'deals' && dealFilters) {
      dealFilters.search_q = ''
    }
    if (tab === 'accounts' && accountFilters) {
      // Сбрасываем все примененные фильтры аккаунтов, чтобы таблица не оставалась в старом состоянии.
      accountFilters.search_q = ''
      accountFilters.login_q = ''
      accountFilters.product_q = ''
      accountFilters.region_q = ''
      accountFilters.status_q = ''
      accountFilters.date_from = ''
      accountFilters.date_to = ''
    }
    if (tab === 'products' && productFilters) {
      // Сбрасываем все фильтры товаров, не только строку поиска.
      productFilters.q = ''
      productFilters.type_code = ''
      productFilters.platform_code = ''
      productFilters.region_code = ''
    }
    // Черновики фильтров тоже чистим, чтобы попапы не показывали старый поиск.
    if (tab === 'accounts' && accountFilterDraft) {
      accountFilterDraft.login = ''
      accountFilterDraft.product = ''
      accountFilterDraft.region = ''
      accountFilterDraft.status = ''
      accountFilterDraft.date_from = ''
      accountFilterDraft.date_to = ''
    }
    if (tab === 'products' && productFilterDraft) {
      productFilterDraft.title = ''
      productFilterDraft.type = ''
      productFilterDraft.platform = ''
      productFilterDraft.region = ''
    }

    if (tab !== 'telegram') {
      // Если ушли с Telegram, сразу останавливаем опрос.
      stopTelegramPolling()
    }
    if (tab === 'dashboard') {
      if (!isCurrentRequest('dashboard')) return
      checkApi()
      return
    }
    if (tab === 'profile') {
      if (!isCurrentRequest('profile')) return
      pwdOk.value = false
      showPwdForm.value = false
      return
    }
    if (tab === 'products') {
      // Сбрасываем состояние сразу при входе на вкладку, чтобы асинхронная загрузка не закрывала модалки позже.
      showProductForm.value = false
      showProductFilters.value = false
      activeProductFilter.value = ''
      editProduct.open = false
      if (!catalogsLoadedOnce.value && (!platforms.value.length || !regions.value.length)) {
        await loadCatalogs()
        if (!isCurrentRequest('products')) return
        if (platforms.value.length || regions.value.length) catalogsLoadedOnce.value = true
      }
      if (!isCurrentRequest('products')) return
      productsPage.value = 1
      // Всегда перезагружаем список после сброса фильтров, иначе останется старый отфильтрованный массив.
      await loadProducts()
      if (!isCurrentRequest('products')) return
      if (!productsAllLoadedOnce.value && !productsAll.value.length) {
        await loadProductsAll()
        if (!isCurrentRequest('products')) return
        if (productsAll.value.length) productsAllLoadedOnce.value = true
      }
      return
    }
    if (tab === 'accounts') {
      // Фильтры сбрасываем до await, чтобы избежать гонки с действиями пользователя.
      showAccountFilters.value = false
      activeAccountFilter.value = ''
      accountsPage.value = 1
      // Список аккаунтов грузим первым, а вспомогательные справочники подтягиваем в фоне.
      await loadAccounts()
      if (!isCurrentRequest('accounts')) return
      const backgroundTasks = []
      if (!catalogsLoadedOnce.value && (!platforms.value.length || !regions.value.length)) {
        backgroundTasks.push(loadCatalogs().then(() => {
          if (!isCurrentRequest('accounts')) return
          if (platforms.value.length || regions.value.length) catalogsLoadedOnce.value = true
        }))
      }
      if (!domainsLoadedOnce.value && !domains.value.length) {
        backgroundTasks.push(loadDomains().then(() => {
          if (!isCurrentRequest('accounts')) return
          if (domains.value.length) domainsLoadedOnce.value = true
        }))
      }
      if (!productsAllLoadedOnce.value && !productsAll.value.length) {
        backgroundTasks.push(loadProductsAll().then(() => {
          if (!isCurrentRequest('accounts')) return
          if (productsAll.value.length) productsAllLoadedOnce.value = true
        }))
      }
      if (!slotTypesLoadedOnce.value && !slotTypes.value.length) {
        backgroundTasks.push(loadSlotTypes().then(() => {
          if (!isCurrentRequest('accounts')) return
          if (slotTypes.value.length) slotTypesLoadedOnce.value = true
        }))
      }
      void Promise.all(backgroundTasks)
      return
    }
    if (tab === 'deals') {
      // Флаг формы сбрасываем сразу при входе, чтобы первый bootstrap не закрывал форму постфактум.
      showDealForm.value = false
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
            if (!isCurrentRequest('deals')) return
            if (accountsAll.value.length) accountsAllLoadedOnce.value = true
          }))
        }
        if (!productsAllLoadedOnce.value) {
          tasks.push(loadProductsAll().then(() => {
            if (!isCurrentRequest('deals')) return
            if (productsAll.value.length) productsAllLoadedOnce.value = true
          }))
        }
        if (!catalogsLoadedOnce.value) {
          tasks.push(loadCatalogs().then(() => {
            if (!isCurrentRequest('deals')) return
            if (platforms.value.length || regions.value.length) catalogsLoadedOnce.value = true
          }))
        }
        if (!sourcesLoadedOnce.value) {
          tasks.push(loadSources().then(() => {
            if (!isCurrentRequest('deals')) return
            if (sources.value.length) sourcesLoadedOnce.value = true
          }))
        }
        if (!messengersLoadedOnce.value) {
          tasks.push(loadMessengers().then(() => {
            if (!isCurrentRequest('deals')) return
            if (messengers.value.length) messengersLoadedOnce.value = true
          }))
        }
        if (!domainsLoadedOnce.value) {
          tasks.push(loadDomains().then(() => {
            if (!isCurrentRequest('deals')) return
            if (domains.value.length) domainsLoadedOnce.value = true
          }))
        }
        if (!slotTypesLoadedOnce.value) {
          tasks.push(loadSlotTypes().then(() => {
            if (!isCurrentRequest('deals')) return
            if (slotTypes.value.length) slotTypesLoadedOnce.value = true
          }))
        }
      }
      await Promise.all(tasks)
      if (!isCurrentRequest('deals')) return
      dealsBootstrapped.value = true
      return
    }
    if (tab === 'analytics') {
      const tasks = []
      if (!catalogsLoadedOnce.value && (!platforms.value.length || !regions.value.length)) {
        tasks.push(loadCatalogs().then(() => {
          if (!isCurrentRequest('analytics')) return
          if (platforms.value.length || regions.value.length) catalogsLoadedOnce.value = true
        }))
      }
      if (!sourcesLoadedOnce.value && !sources.value.length) {
        tasks.push(loadSources().then(() => {
          if (!isCurrentRequest('analytics')) return
          if (sources.value.length) sourcesLoadedOnce.value = true
        }))
      }
      if (!messengersLoadedOnce.value && !messengers.value.length) {
        tasks.push(loadMessengers().then(() => {
          if (!isCurrentRequest('analytics')) return
          if (messengers.value.length) messengersLoadedOnce.value = true
        }))
      }
      await Promise.all(tasks)
      return
    }
    if (tab === 'ns-gift') {
      // При открытии вкладки очищаем прошлые сообщения и загружаем свежие данные.
      nsGiftOk.value = ''
      nsGiftError.value = ''
      await (typeof reloadNsGiftData === 'function'
        ? reloadNsGiftData()
        : Promise.all([loadNsGiftBalance(), loadNsGiftCategories()]))
      return
    }
    if (tab === 'telegram') {
      await loadTelegramStatus()
      if (!isCurrentRequest('telegram')) return
      startTelegramPolling()
      return
    }
    if (tab === 'catalogs') {
      const tasks = []
      if (!domainsLoadedOnce.value && !domains.value.length) tasks.push(loadDomains().then(() => {
        if (!isCurrentRequest('catalogs')) return
        if (domains.value.length) domainsLoadedOnce.value = true
      }))
      if (!sourcesLoadedOnce.value && !sources.value.length) tasks.push(loadSources().then(() => {
        if (!isCurrentRequest('catalogs')) return
        if (sources.value.length) sourcesLoadedOnce.value = true
      }))
      if (!messengersLoadedOnce.value && !messengers.value.length) tasks.push(loadMessengers().then(() => {
        if (!isCurrentRequest('catalogs')) return
        if (messengers.value.length) messengersLoadedOnce.value = true
      }))
      if (!catalogsLoadedOnce.value && (!platforms.value.length || !regions.value.length)) tasks.push(loadCatalogs().then(() => {
        if (!isCurrentRequest('catalogs')) return
        if (platforms.value.length || regions.value.length) catalogsLoadedOnce.value = true
      }))
      await Promise.all(tasks)
      return
    }
    if (tab === 'users' && isAdmin.value) {
      // Закрываем модалку до загрузки списка, чтобы не ловить закрытие после await.
      showUserForm.value = false
      await loadUsers()
    }
  }, { immediate: true })
}
