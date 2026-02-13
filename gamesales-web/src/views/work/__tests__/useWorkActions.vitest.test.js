import { describe, it, expect, vi } from 'vitest'
import { reactive, ref } from 'vue'

import { useWorkActions } from '../useWorkActions.js'

function createHarness() {
  const auth = { state: reactive({ token: 'token-1' }) }
  const apiGet = vi.fn()
  const apiPost = vi.fn()

  const deps = {
    auth,
    apiGet,
    apiPost,
    mapApiError: (v) => String(v || ''),
    loadDeals: vi.fn(),
    loadAccounts: vi.fn(),
    loadProducts: vi.fn(),
    accountsPage: ref(1),
    accountsPageInput: ref(1),
    productsPage: ref(1),
    productsPageInput: ref(1),
    newDeal: reactive({ product_id: '' }),
    editDeal: reactive({ product_id: '', open: false, account_id: null }),
    newDealProductSearch: ref(''),
    editDealProductSearch: ref(''),
    quickNewProduct: reactive({ title: '' }),
    quickEditProduct: reactive({ title: '' }),
    quickNewProductError: ref(''),
    quickEditProductError: ref(''),
    accountSlotAssignments: ref([]),
    accountSlotAssignmentsLoading: ref(false),
    accountSlotAssignmentsError: ref(null),
    productSlotAssignments: ref([]),
    productSlotAssignmentsLoading: ref(false),
    productSlotAssignmentsError: ref(null),
    accountSlotReleaseLoading: ref(false),
    editAccount: reactive({ open: false, account_id: null }),
    showDealForm: ref(false),
    dealError: ref(null),
    loadAccountSlotStatus: vi.fn(),
    loadDealAccountAssignments: vi.fn(),
    loadDealAccountsForProduct: vi.fn(),
    loadDealProductAssignments: vi.fn(),
    productAccountsSort: ref({ key: 'slot', dir: 'asc' }),
    productAccountsPage: ref(1),
    productAccountsTotalPages: ref(1),
    closeProductModal: vi.fn(),
    goToAccount: vi.fn(),
  }

  return {
    apiGet,
    productSlotAssignments: deps.productSlotAssignments,
    flow: useWorkActions(deps),
  }
}

describe('useWorkActions', () => {
  it('loadProductSlotAssignments prefers product endpoint', async () => {
    const h = createHarness()
    h.apiGet.mockResolvedValueOnce([{ assignment_id: 1 }])

    await h.flow.loadProductSlotAssignments(55)

    expect(h.apiGet).toHaveBeenCalledWith('/products/55/slot-assignments', { token: 'token-1' })
    expect(h.productSlotAssignments.value).toEqual([{ assignment_id: 1 }])
  })

  it('loadProductSlotAssignments returns empty list on product endpoint error', async () => {
    const h = createHarness()
    h.apiGet.mockRejectedValueOnce(new Error('not found'))

    await h.flow.loadProductSlotAssignments(55)

    expect(h.apiGet).toHaveBeenCalledTimes(1)
    expect(h.apiGet).toHaveBeenCalledWith('/products/55/slot-assignments', { token: 'token-1' })
    expect(h.productSlotAssignments.value).toEqual([])
  })
})
