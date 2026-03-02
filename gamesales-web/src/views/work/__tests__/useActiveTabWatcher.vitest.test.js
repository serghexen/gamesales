import { describe, it, expect, vi } from 'vitest'
import { ref, reactive } from 'vue'

import { useActiveTabWatcher } from '../useActiveTabWatcher.js'

function createHarness({ role = 'manager', responsible = '', preset = '', tab = 'deals' } = {}) {
  const activeTab = ref(tab)
  const isAdmin = ref(role === 'admin')
  const dealFilters = reactive({
    responsible_q: preset,
  })
  const defaultDealsResponsibleFilter = ref(responsible)

  const loadDeals = vi.fn().mockResolvedValue(undefined)

  useActiveTabWatcher({
    activeTab,
    isAdmin,
    dealFilters,
    defaultDealsResponsibleFilter,
    mustPrefillDealsResponsible: ref(role === 'manager' || role === 'operator'),
    showUserForm: ref(false),
    showProductForm: ref(false),
    showProductFilters: ref(false),
    showDealForm: ref(false),
    showAccountFilters: ref(false),
    activeProductFilter: ref(''),
    activeAccountFilter: ref(''),
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
    loadProducts: vi.fn().mockResolvedValue(undefined),
    loadProductsAll: vi.fn().mockResolvedValue(undefined),
    loadAccounts: vi.fn().mockResolvedValue(undefined),
    loadAccountsAll: vi.fn().mockResolvedValue(undefined),
    loadDeals,
    loadTelegramStatus: vi.fn().mockResolvedValue(undefined),
    startTelegramPolling: vi.fn(),
    stopTelegramPolling: vi.fn(),
  })

  return { dealFilters, loadDeals }
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

})
