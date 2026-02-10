import { describe, it, expect, vi } from 'vitest'
import { ref, reactive } from 'vue'

import { useActiveTabWatcher } from '../useActiveTabWatcher.js'

function createHarness({ role = 'manager', responsible = '', preset = '' } = {}) {
  const activeTab = ref('deals')
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
    showUserForm: ref(false),
    showGameForm: ref(false),
    showGameFilters: ref(false),
    showDealForm: ref(false),
    showAccountFilters: ref(false),
    activeGameFilter: ref(''),
    activeAccountFilter: ref(''),
    editGame: reactive({ open: false }),
    pwdOk: ref(false),
    showPwdForm: ref(false),
    catalogsLoadedOnce: ref(true),
    domainsLoadedOnce: ref(true),
    sourcesLoadedOnce: ref(true),
    slotTypesLoadedOnce: ref(true),
    accountsAllLoadedOnce: ref(true),
    gamesAllLoadedOnce: ref(true),
    dealsBootstrapped: ref(false),
    platforms: ref([]),
    regions: ref([]),
    domains: ref([]),
    sources: ref([]),
    slotTypes: ref([]),
    games: ref([]),
    gamesAll: ref([]),
    accountsAll: ref([]),
    gamesPage: ref(1),
    accountsPage: ref(1),
    checkApi: vi.fn(),
    loadUsers: vi.fn().mockResolvedValue(undefined),
    loadCatalogs: vi.fn().mockResolvedValue(undefined),
    loadDomains: vi.fn().mockResolvedValue(undefined),
    loadSources: vi.fn().mockResolvedValue(undefined),
    loadSlotTypes: vi.fn().mockResolvedValue(undefined),
    loadGames: vi.fn().mockResolvedValue(undefined),
    loadGamesAll: vi.fn().mockResolvedValue(undefined),
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
})
