import { describe, it, expect, vi } from 'vitest'
import { reactive, ref } from 'vue'

import { useAccountsFlow } from '../useAccountsFlow.js'

function createHarness() {
  const h = {
    auth: { state: reactive({ token: 'token-1' }) },
    apiGet: vi.fn(),
    apiPost: vi.fn(),
    apiPut: vi.fn(),
    apiDelete: vi.fn(),
    mapApiError: (m) => m || 'error',
    resolveAccountSort: () => ({ key: 'login', dir: 'asc' }),
    closeAllModals: vi.fn(),
    resetModalPos: vi.fn(),
    accountModalMode: ref('edit'),
    accountEditMode: ref('view'),
    editAccount: reactive({ open: true, account_id: 5, product_ids: [] }),
    newAccount: reactive({ product_ids: [] }),
    accountProductSearch: ref(''),
    editAccountProductSearch: ref(''),
    accountProductsLoading: ref(false),
    accountDeals: ref([]),
    accountDealsError: ref(null),
    accountDealsLoading: ref(false),
    accountSlotAssignments: ref([]),
    accountSlotAssignmentsError: ref(null),
    accountSlotAssignmentsLoading: ref(false),
    accounts: ref([]),
    accountsAll: ref([]),
    accountsTotal: ref(0),
    accountsPage: ref(1),
    accountsPageSize: ref(20),
    accountFilters: reactive({ search_q: '', login_q: '', product_q: '', region_q: '', status_q: '', date_from: '', date_to: '' }),
    accountSort: ref('login_asc'),
    accountSecrets: ref({}),
    accountsError: ref(null),
    accountsOk: ref(null),
    accountsLoading: ref(false),
    accountSaving: ref(false),
    loadAccountSlotAssignments: vi.fn(),
    suppressUnsavedConfirm: ref(false),
    requestUnsavedConfirm: vi.fn(),
  }
  const flow = useAccountsFlow(h)
  return { ...h, ...flow }
}

describe('useAccountsFlow', () => {
  it('loadAccountProducts prefers /accounts/{id}/products', async () => {
    const h = createHarness()
    h.apiGet.mockResolvedValueOnce([{ product_id: 55 }, { product_id: 56 }])

    await h.loadAccountProducts(5)

    expect(h.apiGet).toHaveBeenCalledWith('/accounts/5/products', { token: 'token-1' })
    expect(h.editAccount.product_ids).toEqual([55, 56])
  })

  it('loadAccountProducts returns empty list on products endpoint error', async () => {
    const h = createHarness()
    h.apiGet.mockRejectedValueOnce(new Error('404'))

    await h.loadAccountProducts(5)

    expect(h.apiGet).toHaveBeenCalledTimes(1)
    expect(h.apiGet).toHaveBeenCalledWith('/accounts/5/products', { token: 'token-1' })
    expect(h.editAccount.product_ids).toEqual([])
  })
})
