import { describe, it, expect, vi } from 'vitest'
import { reactive, ref } from 'vue'

import { useWorkFilters } from '../useWorkFilters.js'

function createHarness() {
  const loadAccounts = vi.fn()
  const loadProducts = vi.fn()
  const loadDeals = vi.fn()

  const accountSort = ref('login_asc')
  const accountsPage = ref(2)
  const accountsPageInput = ref(1)
  const accountsTotalPages = ref(5)

  const productsSort = ref({ key: 'title', dir: 'asc' })
  const productsPage = ref(2)
  const productsPageInput = ref(1)
  const productsTotalPages = ref(4)

  const usersSort = ref({ key: 'created_at', dir: 'desc' })
  const domainsSortAsc = ref(true)
  const sourcesSort = ref({ key: 'code', dir: 'asc' })
  const platformsSort = ref({ key: 'code', dir: 'asc' })
  const regionsSort = ref({ key: 'code', dir: 'asc' })

  const activeDealFilter = ref('')
  const dealFilters = reactive({
    search_q: 'abc',
    customer_q: 'customer',
    responsible_q: 'manager',
    region_q: 'RU',
    status_q: 'pending',
    purchase_from: '',
    purchase_to: '',
    type_q: 'sale',
  })

  const activeGameFilter = ref('')
  const gameFilters = reactive({
    q: 'old',
    type_code: 'game',
    platform_code: 'ps5',
    region_code: 'RU',
  })
  const gameFilterDraft = reactive({
    title: '',
    type: '',
    platform: '',
    region: '',
  })

  const activeAccountFilter = ref('')
  const accountFilters = reactive({
    search_q: 's',
    login_q: 'login',
    product_q: 'game',
    region_q: 'RU',
    status_q: 'active',
    date_from: '',
    date_to: '',
  })
  const accountFilterDraft = reactive({
    login: '',
    product: '',
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
    productsSort,
    productsPage,
    productsPageInput,
    productsTotalPages,
    loadProducts,
    usersSort,
    domainsSortAsc,
    sourcesSort,
    platformsSort,
    regionsSort,
    activeDealFilter,
    dealFilters,
    loadDeals,
    activeProductFilter: activeGameFilter,
    productFilters: gameFilters,
    productFilterDraft: gameFilterDraft,
    activeAccountFilter,
    accountFilters,
    accountFilterDraft,
  })

  return {
    api,
    loadAccounts,
    loadProducts,
    loadDeals,
    accountSort,
    accountsPage,
    accountsPageInput,
    accountsTotalPages,
    productsSort,
    productsPage,
    productsPageInput,
    productsTotalPages,
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

  it('setProductsPage clamps range and reloads only when page changed', () => {
    const h = createHarness()
    h.api.setProductsPage(999)
    expect(h.productsPage.value).toBe(4)
    expect(h.loadProducts).toHaveBeenCalledTimes(1)

    h.api.setProductsPage(4)
    expect(h.loadProducts).toHaveBeenCalledTimes(1)
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
    expect(h.dealFilters.responsible_q).toBe('')
    expect(h.dealFilters.region_q).toBe('')
    expect(h.dealFilters.status_q).toBe('')
    expect(h.dealFilters.purchase_from).toBe('')
    expect(h.dealFilters.purchase_to).toBe('')
    expect(h.activeDealFilter.value).toBe('')
    expect(h.loadDeals).toHaveBeenCalledWith(1)
  })

  it('openProductFilter copies values to draft and applyProductFilter trims input', () => {
    const h = createHarness()
    h.api.openProductFilter('title')
    expect(h.gameFilterDraft.title).toBe('old')
    expect(h.gameFilterDraft.type).toBe('game')
    expect(h.activeGameFilter.value).toBe('title')

    h.gameFilterDraft.title = '  New title  '
    h.api.applyProductFilter('title')
    expect(h.gameFilters.q).toBe('New title')
    expect(h.productsPage.value).toBe(1)
    expect(h.activeGameFilter.value).toBe('')
    expect(h.loadProducts).toHaveBeenCalledTimes(1)
  })

  it('apply/reset game type filter updates type_code and reloads list', () => {
    const h = createHarness()
    h.api.openProductFilter('type')
    h.gameFilterDraft.type = 'subscription'
    h.api.applyProductFilter('type')
    expect(h.gameFilters.type_code).toBe('subscription')
    expect(h.loadProducts).toHaveBeenCalledTimes(1)

    h.api.resetProductFilter('type')
    expect(h.gameFilters.type_code).toBe('')
    expect(h.gameFilterDraft.type).toBe('')
    expect(h.loadProducts).toHaveBeenCalledTimes(2)
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
    h.accountFilterDraft.product = 'y'
    h.accountFilterDraft.region = 'z'
    h.accountFilterDraft.status = 'blocked'
    h.accountFilterDraft.date_from = '2026-01-01'
    h.accountFilterDraft.date_to = '2026-02-01'

    h.api.resetAccountFilter('all')
    expect(h.accountFilters.search_q).toBe('')
    expect(h.accountFilters.login_q).toBe('')
    expect(h.accountFilters.product_q).toBe('')
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
