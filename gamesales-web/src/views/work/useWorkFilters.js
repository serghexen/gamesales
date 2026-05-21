import { reactive } from 'vue'

export function useWorkFilters({
  accountSort,
  accountsPage,
  accountsPageInput,
  accountsTotalPages,
  loadAccounts,
  productsSort,
  productsPage,
  productsPageInput,
  productsTotalPages,
  loadProducts,
  usersSort,
  domainsSortAsc,
  sourcesSort,
  messengersSort,
  platformsSort,
  regionsSort,
  activeDealFilter,
  dealFilters,
  loadDeals,
  activeProductFilter,
  productFilters,
  productFilterDraft,
  activeAccountFilter,
  accountFilters,
  accountFilterDraft,
}) {
  const activeProductFilterRef = activeProductFilter
  const productFiltersState = productFilters
  const productFilterDraftState = productFilterDraft

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
      products: ['products_asc', 'products_desc'],
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

  // Переключает сортировку списка товаров.
  function toggleProductsSort(key) {
    const current = productsSort.value
    if (current.key === key) {
      current.dir = current.dir === 'asc' ? 'desc' : 'asc'
    } else {
      productsSort.value = { key, dir: 'asc' }
    }
    productsPage.value = 1
    loadProducts()
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

  // Переключает сортировку списка мессенджеров.
  function toggleMessengersSort(key) {
    const current = messengersSort.value
    if (current.key === key) {
      current.dir = current.dir === 'asc' ? 'desc' : 'asc'
    } else {
      messengersSort.value = { key, dir: 'asc' }
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

  // Переход по страницам товаров.
  function setProductsPage(page) {
    const target = Math.min(Math.max(1, Number(page) || 1), productsTotalPages.value)
    if (target === productsPage.value) return
    productsPage.value = target
    loadProducts()
  }

  function jumpProductsPage() {
    setProductsPage(productsPageInput.value)
  }

  function prevProductsPage() {
    setProductsPage(productsPage.value - 1)
  }

  function nextProductsPage() {
    setProductsPage(productsPage.value + 1)
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
    } else if (kind === 'responsible') {
      dealFilters.responsible_q = ''
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
      dealFilters.responsible_q = ''
      dealFilters.region_q = ''
      dealFilters.status_q = ''
      dealFilters.purchase_from = ''
      dealFilters.purchase_to = ''
      dealFilterErrors.date = ''
    }
    activeDealFilter.value = ''
    loadDeals(1)
  }

  // Сбрасывает фильтр товаров и перезагружает список.
  const resetProductFilter = (kind) => {
    if (kind === 'title') {
      productFiltersState.q = ''
      productFilterDraftState.title = ''
    } else if (kind === 'type') {
      productFiltersState.type_code = ''
      productFilterDraftState.type = ''
    } else if (kind === 'platform') {
      productFiltersState.platform_code = ''
      productFilterDraftState.platform = ''
    } else if (kind === 'region') {
      productFiltersState.region_code = ''
      productFilterDraftState.region = ''
    } else if (kind === 'all') {
      productFiltersState.q = ''
      productFiltersState.type_code = ''
      productFiltersState.platform_code = ''
      productFiltersState.region_code = ''
      productFilterDraftState.title = ''
      productFilterDraftState.type = ''
      productFilterDraftState.platform = ''
      productFilterDraftState.region = ''
    }
    productsPage.value = 1
    activeProductFilterRef.value = ''
    loadProducts()
  }

  // Открывает выпадающий фильтр по товарам и копирует текущие значения в черновик.
  const openProductFilter = (kind) => {
    productFilterDraftState.title = productFiltersState.q || ''
    productFilterDraftState.type = productFiltersState.type_code || ''
    productFilterDraftState.platform = productFiltersState.platform_code || ''
    productFilterDraftState.region = productFiltersState.region_code || ''
    activeProductFilterRef.value = activeProductFilterRef.value === kind ? '' : kind
  }

  // Применяет выбранный фильтр по товарам.
  const applyProductFilter = (kind) => {
    if (kind === 'title') {
      productFiltersState.q = productFilterDraftState.title.trim()
    } else if (kind === 'type') {
      productFiltersState.type_code = productFilterDraftState.type.trim()
    } else if (kind === 'platform') {
      productFiltersState.platform_code = productFilterDraftState.platform.trim()
    } else if (kind === 'region') {
      productFiltersState.region_code = productFilterDraftState.region.trim()
    }
    productsPage.value = 1
    activeProductFilterRef.value = ''
    loadProducts()
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
    } else if (kind === 'product') {
      accountFilters.product_q = ''
      accountFilterDraft.product = ''
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
      accountFilters.product_q = ''
      accountFilters.region_q = ''
      accountFilters.status_q = ''
      accountFilters.date_from = ''
      accountFilters.date_to = ''
      accountFilterDraft.login = ''
      accountFilterDraft.product = ''
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
    accountFilterDraft.product = accountFilters.product_q || ''
    accountFilterDraft.region = accountFilters.region_q || ''
    accountFilterDraft.status = accountFilters.status_q || ''
    accountFilterDraft.date_from = accountFilters.date_from || ''
    accountFilterDraft.date_to = accountFilters.date_to || ''
    activeAccountFilter.value = activeAccountFilter.value === kind ? '' : kind
  }

  const applyAccountFilter = (kind) => {
    if (kind === 'login') {
      accountFilters.login_q = accountFilterDraft.login.trim()
    } else if (kind === 'product') {
      accountFilters.product_q = accountFilterDraft.product.trim()
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
    toggleProductsSort,
    toggleUsersSort,
    toggleDomainsSort,
    toggleSourcesSort,
    toggleMessengersSort,
    togglePlatformsSort,
    toggleRegionsSort,
    setProductsPage,
    jumpProductsPage,
    prevProductsPage,
    nextProductsPage,
    setAccountsPage,
    jumpAccountsPage,
    prevAccountsPage,
    nextAccountsPage,
    resetDealFilter,
    validateDealRange,
    dealFilterErrors,
    resetProductFilter,
    openProductFilter,
    applyProductFilter,
    resetAccountFilter,
    openAccountFilter,
    applyAccountFilter,
    accountFilterErrors,
    validateAccountDateRange,
  }
}
