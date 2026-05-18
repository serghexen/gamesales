import { describe, it, expect, vi } from 'vitest'
import { ref, reactive } from 'vue'

import { useActiveTabWatcher } from '../useActiveTabWatcher.js'

function createDeferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

function createHarness({ role = 'manager', responsible = '', preset = '', tab = 'deals' } = {}) {
  const activeTab = ref(tab)
  const isAdmin = ref(role === 'admin')
  const dealFilters = reactive({
    responsible_q: preset,
    search_q: '',
  })
  const productFilters = reactive({ q: '', type_code: '', platform_code: '', region_code: '' })
  const accountFilters = reactive({ search_q: '', login_q: '', product_q: '', region_q: '', status_q: '', date_from: '', date_to: '' })
  const productFilterDraft = reactive({ title: '', type: '', platform: '', region: '' })
  const accountFilterDraft = reactive({ login: '', product: '', region: '', status: '', date_from: '', date_to: '' })
  const defaultDealsResponsibleFilter = ref(responsible)

  const loadDeals = vi.fn().mockResolvedValue(undefined)
  const loadNsGiftBalance = vi.fn().mockResolvedValue(undefined)
  const loadNsGiftCategories = vi.fn().mockResolvedValue(undefined)
  const reloadNsGiftData = vi.fn().mockResolvedValue(undefined)

  const loadProducts = vi.fn().mockResolvedValue(undefined)

  useActiveTabWatcher({
    activeTab,
    isAdmin,
    dealFilters,
    productFilters,
    accountFilters,
    productFilterDraft,
    accountFilterDraft,
    defaultDealsResponsibleFilter,
    mustPrefillDealsResponsible: ref(role === 'manager' || role === 'operator'),
    showUserForm: ref(false),
    showProductForm: ref(false),
    showProductFilters: ref(false),
    showDealForm: ref(false),
    showAccountFilters: ref(false),
    activeProductFilter: ref(''),
    activeAccountFilter: ref(''),
    nsGiftOk: ref(''),
    nsGiftError: ref(''),
    editProduct: reactive({ open: false }),
    pwdOk: ref(false),
    showPwdForm: ref(false),
    catalogsLoadedOnce: ref(true),
    domainsLoadedOnce: ref(true),
    sourcesLoadedOnce: ref(true),
    slotTypesLoadedOnce: ref(true),
    accountsAllLoadedOnce: ref(true),
    productsAllLoadedOnce: ref(true),
    dealsBootstrapped: ref(false),
    platforms: ref([]),
    regions: ref([]),
    domains: ref([]),
    sources: ref([]),
    slotTypes: ref([]),
    products: ref([]),
    productsAll: ref([]),
    accountsAll: ref([]),
    productsPage: ref(1),
    accountsPage: ref(1),
    checkApi: vi.fn(),
    loadUsers: vi.fn().mockResolvedValue(undefined),
    loadCatalogs: vi.fn().mockResolvedValue(undefined),
    loadDomains: vi.fn().mockResolvedValue(undefined),
    loadSources: vi.fn().mockResolvedValue(undefined),
    loadSlotTypes: vi.fn().mockResolvedValue(undefined),
    loadProducts,
    loadProductsAll: vi.fn().mockResolvedValue(undefined),
    loadAccounts: vi.fn().mockResolvedValue(undefined),
    loadAccountsAll: vi.fn().mockResolvedValue(undefined),
    loadDeals,
    loadNsGiftBalance,
    loadNsGiftCategories,
    reloadNsGiftData,
    loadTelegramStatus: vi.fn().mockResolvedValue(undefined),
    startTelegramPolling: vi.fn(),
    stopTelegramPolling: vi.fn(),
  })

  return {
    activeTab,
    dealFilters,
    productFilters,
    accountFilters,
    productFilterDraft,
    accountFilterDraft,
    loadDeals,
    loadProducts,
    loadNsGiftBalance,
    loadNsGiftCategories,
    reloadNsGiftData,
  }
}

describe('useActiveTabWatcher', () => {
  it('sets responsible filter by default for manager', async () => {
    const h = createHarness({ role: 'manager', responsible: 'Иван Менеджер' })
    await Promise.resolve()
    expect(h.dealFilters.responsible_q).toBe('Иван Менеджер')
    expect(h.loadDeals).toHaveBeenCalledWith(1)
  })

  it('does not overwrite an already selected responsible filter', async () => {
    const h = createHarness({ role: 'operator', responsible: 'Оператор', preset: 'Другой ответственный' })
    await Promise.resolve()
    expect(h.dealFilters.responsible_q).toBe('Другой ответственный')
    expect(h.loadDeals).toHaveBeenCalledWith(1)
  })

  it('keeps filter empty for admin', async () => {
    const h = createHarness({ role: 'admin', responsible: '' })
    await Promise.resolve()
    expect(h.dealFilters.responsible_q).toBe('')
    expect(h.loadDeals).toHaveBeenCalledWith(1)
  })

  it('does not load deals immediately for manager when default responsible is not ready yet', async () => {
    const h = createHarness({ role: 'manager', responsible: '', preset: '' })
    await Promise.resolve()
    expect(h.dealFilters.responsible_q).toBe('')
    expect(h.loadDeals).not.toHaveBeenCalled()
  })

  it('does not close opened deal modal after first async bootstrap resolves', async () => {
    let resolveDeals
    let resolveAccounts
    const loadDeals = vi.fn().mockImplementation(() => new Promise((resolve) => { resolveDeals = resolve }))
    const loadAccountsAll = vi.fn().mockImplementation(() => new Promise((resolve) => { resolveAccounts = resolve }))
    const showDealForm = ref(false)

    useActiveTabWatcher({
      activeTab: ref('deals'),
      isAdmin: ref(false),
      dealFilters: reactive({ responsible_q: 'Иван' }),
      defaultDealsResponsibleFilter: ref('Иван'),
      mustPrefillDealsResponsible: ref(true),
      showUserForm: ref(false),
      showProductForm: ref(false),
      showProductFilters: ref(false),
      showDealForm,
      showAccountFilters: ref(false),
      activeProductFilter: ref(''),
      activeAccountFilter: ref(''),
      nsGiftOk: ref(''),
      nsGiftError: ref(''),
      editProduct: reactive({ open: false }),
      pwdOk: ref(false),
      showPwdForm: ref(false),
      catalogsLoadedOnce: ref(true),
      domainsLoadedOnce: ref(true),
      sourcesLoadedOnce: ref(true),
      slotTypesLoadedOnce: ref(true),
      accountsAllLoadedOnce: ref(false),
      productsAllLoadedOnce: ref(true),
      dealsBootstrapped: ref(false),
      platforms: ref([]),
      regions: ref([]),
      domains: ref([]),
      sources: ref([]),
      slotTypes: ref([]),
      products: ref([]),
      productsAll: ref([]),
      accountsAll: ref([]),
      productsPage: ref(1),
      accountsPage: ref(1),
      checkApi: vi.fn(),
      startManagersWorkloadPolling: vi.fn(),
      loadUsers: vi.fn().mockResolvedValue(undefined),
      loadCatalogs: vi.fn().mockResolvedValue(undefined),
      loadDomains: vi.fn().mockResolvedValue(undefined),
      loadSources: vi.fn().mockResolvedValue(undefined),
      loadSlotTypes: vi.fn().mockResolvedValue(undefined),
      loadProducts: vi.fn().mockResolvedValue(undefined),
      loadProductsAll: vi.fn().mockResolvedValue(undefined),
      loadAccounts: vi.fn().mockResolvedValue(undefined),
      loadAccountsAll,
      loadDeals,
      loadNsGiftBalance: vi.fn().mockResolvedValue(undefined),
      loadNsGiftCategories: vi.fn().mockResolvedValue(undefined),
      reloadNsGiftData: vi.fn().mockResolvedValue(undefined),
      loadTelegramStatus: vi.fn().mockResolvedValue(undefined),
      startTelegramPolling: vi.fn(),
      stopTelegramPolling: vi.fn(),
    })

    await Promise.resolve()
    showDealForm.value = true
    resolveDeals?.()
    resolveAccounts?.()
    await Promise.resolve()
    await Promise.resolve()

    expect(showDealForm.value).toBe(true)
  })

  it('loads NS Gift data on ns-gift tab', async () => {
    const h = createHarness({ tab: 'ns-gift' })
    await Promise.resolve()
    expect(h.reloadNsGiftData).toHaveBeenCalledTimes(1)
    expect(h.loadNsGiftBalance).not.toHaveBeenCalled()
    expect(h.loadNsGiftCategories).not.toHaveBeenCalled()
  })

  it('clears search fields after switching top tabs', async () => {
    const h = createHarness({ tab: 'accounts' })
    h.accountFilters.search_q = 'тест'
    h.accountFilters.login_q = 'acc'
    h.accountFilters.product_q = 'game'
    h.accountFilters.region_q = 'TR'
    h.accountFilters.status_q = 'active'
    h.accountFilters.date_from = '2026-01-01'
    h.accountFilters.date_to = '2026-01-31'
    h.accountFilterDraft.login = 'mail'
    h.activeTab.value = 'deals'
    await Promise.resolve()
    expect(h.dealFilters.search_q).toBe('')

    h.dealFilters.search_q = 'поиск'
    h.productFilters.type_code = 'subscription'
    h.productFilters.platform_code = 'ps4'
    h.productFilters.region_code = 'TR'
    h.activeTab.value = 'products'
    await Promise.resolve()
    expect(h.productFilters.q).toBe('')
    expect(h.productFilters.type_code).toBe('')
    expect(h.productFilters.platform_code).toBe('')
    expect(h.productFilters.region_code).toBe('')
    expect(h.productFilterDraft.title).toBe('')
    expect(h.loadProducts).toHaveBeenCalled()

    h.activeTab.value = 'accounts'
    await Promise.resolve()
    expect(h.accountFilters.search_q).toBe('')
    expect(h.accountFilters.login_q).toBe('')
    expect(h.accountFilters.product_q).toBe('')
    expect(h.accountFilters.region_q).toBe('')
    expect(h.accountFilters.status_q).toBe('')
    expect(h.accountFilters.date_from).toBe('')
    expect(h.accountFilters.date_to).toBe('')
  })

  it('does not start telegram polling when tab changed before status load resolved', async () => {
    const telegramStatusDeferred = createDeferred()
    const startTelegramPolling = vi.fn()
    const stopTelegramPolling = vi.fn()
    const activeTab = ref('telegram')

    useActiveTabWatcher({
      activeTab,
      isAdmin: ref(false),
      dealFilters: reactive({ responsible_q: '' }),
      productFilters: reactive({ q: '', type_code: '', platform_code: '', region_code: '' }),
      accountFilters: reactive({ search_q: '', login_q: '', product_q: '', region_q: '', status_q: '', date_from: '', date_to: '' }),
      productFilterDraft: reactive({ title: '', type: '', platform: '', region: '' }),
      accountFilterDraft: reactive({ login: '', product: '', region: '', status: '', date_from: '', date_to: '' }),
      defaultDealsResponsibleFilter: ref(''),
      mustPrefillDealsResponsible: ref(false),
      showUserForm: ref(false),
      showProductForm: ref(false),
      showProductFilters: ref(false),
      showDealForm: ref(false),
      showAccountFilters: ref(false),
      activeProductFilter: ref(''),
      activeAccountFilter: ref(''),
      nsGiftOk: ref(''),
      nsGiftError: ref(''),
      editProduct: reactive({ open: false }),
      pwdOk: ref(false),
      showPwdForm: ref(false),
      catalogsLoadedOnce: ref(true),
      domainsLoadedOnce: ref(true),
      sourcesLoadedOnce: ref(true),
      slotTypesLoadedOnce: ref(true),
      accountsAllLoadedOnce: ref(true),
      productsAllLoadedOnce: ref(true),
      dealsBootstrapped: ref(false),
      platforms: ref([]),
      regions: ref([]),
      domains: ref([]),
      sources: ref([]),
      slotTypes: ref([]),
      productsAll: ref([]),
      accountsAll: ref([]),
      productsPage: ref(1),
      accountsPage: ref(1),
      checkApi: vi.fn(),
      loadUsers: vi.fn().mockResolvedValue(undefined),
      loadCatalogs: vi.fn().mockResolvedValue(undefined),
      loadDomains: vi.fn().mockResolvedValue(undefined),
      loadSources: vi.fn().mockResolvedValue(undefined),
      loadSlotTypes: vi.fn().mockResolvedValue(undefined),
      loadProducts: vi.fn().mockResolvedValue(undefined),
      loadProductsAll: vi.fn().mockResolvedValue(undefined),
      loadAccounts: vi.fn().mockResolvedValue(undefined),
      loadAccountsAll: vi.fn().mockResolvedValue(undefined),
      loadDeals: vi.fn().mockResolvedValue(undefined),
      loadNsGiftBalance: vi.fn().mockResolvedValue(undefined),
      loadNsGiftCategories: vi.fn().mockResolvedValue(undefined),
      reloadNsGiftData: vi.fn().mockResolvedValue(undefined),
      loadTelegramStatus: vi.fn().mockImplementation(() => telegramStatusDeferred.promise),
      startTelegramPolling,
      stopTelegramPolling,
    })

    await Promise.resolve()
    activeTab.value = 'deals'
    await Promise.resolve()
    telegramStatusDeferred.resolve()
    await Promise.resolve()
    await Promise.resolve()

    expect(stopTelegramPolling).toHaveBeenCalled()
    expect(startTelegramPolling).not.toHaveBeenCalled()
  })

  it('does not mark deals bootstrapped when user leaves deals tab before load resolves', async () => {
    const loadDealsDeferred = createDeferred()
    const dealsBootstrapped = ref(false)
    const activeTab = ref('deals')

    useActiveTabWatcher({
      activeTab,
      isAdmin: ref(false),
      dealFilters: reactive({ responsible_q: 'Иван' }),
      productFilters: reactive({ q: '', type_code: '', platform_code: '', region_code: '' }),
      accountFilters: reactive({ search_q: '', login_q: '', product_q: '', region_q: '', status_q: '', date_from: '', date_to: '' }),
      productFilterDraft: reactive({ title: '', type: '', platform: '', region: '' }),
      accountFilterDraft: reactive({ login: '', product: '', region: '', status: '', date_from: '', date_to: '' }),
      defaultDealsResponsibleFilter: ref('Иван'),
      mustPrefillDealsResponsible: ref(true),
      showUserForm: ref(false),
      showProductForm: ref(false),
      showProductFilters: ref(false),
      showDealForm: ref(false),
      showAccountFilters: ref(false),
      activeProductFilter: ref(''),
      activeAccountFilter: ref(''),
      nsGiftOk: ref(''),
      nsGiftError: ref(''),
      editProduct: reactive({ open: false }),
      pwdOk: ref(false),
      showPwdForm: ref(false),
      catalogsLoadedOnce: ref(true),
      domainsLoadedOnce: ref(true),
      sourcesLoadedOnce: ref(true),
      slotTypesLoadedOnce: ref(true),
      accountsAllLoadedOnce: ref(true),
      productsAllLoadedOnce: ref(true),
      dealsBootstrapped,
      platforms: ref([]),
      regions: ref([]),
      domains: ref([]),
      sources: ref([]),
      slotTypes: ref([]),
      productsAll: ref([]),
      accountsAll: ref([]),
      productsPage: ref(1),
      accountsPage: ref(1),
      checkApi: vi.fn(),
      loadUsers: vi.fn().mockResolvedValue(undefined),
      loadCatalogs: vi.fn().mockResolvedValue(undefined),
      loadDomains: vi.fn().mockResolvedValue(undefined),
      loadSources: vi.fn().mockResolvedValue(undefined),
      loadSlotTypes: vi.fn().mockResolvedValue(undefined),
      loadProducts: vi.fn().mockResolvedValue(undefined),
      loadProductsAll: vi.fn().mockResolvedValue(undefined),
      loadAccounts: vi.fn().mockResolvedValue(undefined),
      loadAccountsAll: vi.fn().mockResolvedValue(undefined),
      loadDeals: vi.fn().mockImplementation(() => loadDealsDeferred.promise),
      loadNsGiftBalance: vi.fn().mockResolvedValue(undefined),
      loadNsGiftCategories: vi.fn().mockResolvedValue(undefined),
      reloadNsGiftData: vi.fn().mockResolvedValue(undefined),
      loadTelegramStatus: vi.fn().mockResolvedValue(undefined),
      startTelegramPolling: vi.fn(),
      stopTelegramPolling: vi.fn(),
    })

    await Promise.resolve()
    activeTab.value = 'accounts'
    await Promise.resolve()
    loadDealsDeferred.resolve()
    await Promise.resolve()
    await Promise.resolve()

    expect(dealsBootstrapped.value).toBe(false)
  })

})
