import { describe, it, expect, vi } from 'vitest'
import { reactive, ref } from 'vue'

import { useDealsFlow } from '../useDealsFlow.js'

function createHarness() {
  const h = {
    auth: { state: reactive({ token: 'token-1' }) },
    apiGet: vi.fn(),
    apiPost: vi.fn(),
    apiPut: vi.fn(),
    mapApiError: (m) => m || 'error',
    isSlotTypeSupportedForProduct: () => true,
    slotTypes: ref([]),
    productsAll: ref([{ product_id: 55, type_code: 'game' }]),
    accountsAll: ref([]),
    editDeal: reactive({ product_id: '', account_id: '', region_code: '' }),
    newDeal: reactive({ product_id: 55, account_id: '', region_code: 'RU', slot_type_code: 'ps5_p1' }),
    accountSlotStatusNew: ref([]),
    accountSlotStatusEdit: ref([]),
    dealAccountAssignmentsNew: ref([]),
    dealAccountAssignmentsEdit: ref([]),
    dealAccountAssignmentsLoadingNew: ref(false),
    dealAccountAssignmentsLoadingEdit: ref(false),
    dealGameAssignmentsNew: ref([]),
    dealGameAssignmentsEdit: ref([]),
    dealGameAssignmentsLoadingNew: ref(false),
    dealGameAssignmentsLoadingEdit: ref(false),
    dealSlotAvailabilityNew: ref({}),
    dealSlotAvailabilityEdit: ref({}),
    dealSlotAvailabilityLoadingNew: ref(false),
    dealSlotAvailabilityLoadingEdit: ref(false),
    dealAccountsForProductNew: ref([]),
    dealAccountsForProductEdit: ref([]),
    dealAccountsForProductLoading: ref(false),
    accountSlotReleaseLoading: ref(false),
    dealSlotAutoAssign: ref(false),
    dealError: ref(''),
    quickNewProduct: reactive({ title: '', platform_codes: [] }),
    quickEditProduct: reactive({ title: '', platform_codes: [] }),
    quickNewProductLoading: ref(false),
    quickEditProductLoading: ref(false),
    quickNewProductError: ref(''),
    quickEditProductError: ref(''),
    quickNewAccount: reactive({ login_name: 'qa', domain_code: 'gmail.com', platform_codes: ['ps5'] }),
    quickEditAccount: reactive({ login_name: '', domain_code: '', platform_codes: [] }),
    quickNewAccountLoading: ref(false),
    quickEditAccountLoading: ref(false),
    quickNewAccountError: ref(''),
    quickEditAccountError: ref(''),
    newDealProductSearch: ref(''),
    editDealProductSearch: ref(''),
    subscriptionFreeProductIdsNew: ref([]),
    subscriptionFreeProductIdsEdit: ref([]),
    subscriptionFreeProductIdsLoadingNew: ref(false),
    subscriptionFreeProductIdsLoadingEdit: ref(false),
    loadProductsAll: vi.fn(),
    loadAccountsAll: vi.fn().mockResolvedValue(undefined),
  }
  const flow = useDealsFlow(h)
  return { ...h, ...flow }
}

describe('useDealsFlow', () => {
  it('createQuickProduct creates product of type game', async () => {
    const h = createHarness()
    h.quickNewProduct.title = 'Game B'
    h.quickNewProduct.platform_codes = ['ps5']
    h.apiPost.mockResolvedValueOnce({ product_id: 55 })

    await h.createQuickProduct('new')

    expect(h.apiPost).toHaveBeenCalledWith(
      '/products',
      expect.objectContaining({
        type_code: 'game',
        title: 'Game B',
        platform_codes: ['ps5'],
      }),
      { token: 'token-1' },
    )
    expect(h.newDeal.product_id).toBe(55)
  })

  it('createQuickAccount uses product endpoints first', async () => {
    const h = createHarness()
    h.apiPost.mockResolvedValueOnce({ account_id: 7 })
    h.apiGet.mockImplementation(async (url) => {
      if (url === '/accounts/7/products') return [{ product_id: 50 }]
      return []
    })
    h.apiPut.mockResolvedValue(undefined)

    await h.createQuickAccount('new')

    expect(h.apiGet).toHaveBeenCalledWith('/accounts/7/products', { token: 'token-1' })
    expect(h.apiPut).toHaveBeenCalledWith('/accounts/7/products', { product_ids: [50, 55] }, { token: 'token-1' })
  })

  it('createQuickAccount skips attach when products endpoint fails', async () => {
    const h = createHarness()
    h.newDeal.product_id = ''
    h.apiPost.mockResolvedValueOnce({ account_id: 8 })

    await h.createQuickAccount('new')

    expect(h.apiGet).not.toHaveBeenCalledWith('/accounts/8/products', { token: 'token-1' })
    expect(h.apiPut).not.toHaveBeenCalled()
  })

  it('createQuickAccount skips account-products attach for subscription', async () => {
    const h = createHarness()
    h.productsAll.value = [{ product_id: 55, type_code: 'subscription' }]
    h.apiPost.mockResolvedValueOnce({ account_id: 9 })

    await h.createQuickAccount('new')

    expect(h.apiGet).not.toHaveBeenCalledWith('/accounts/9/products', { token: 'token-1' })
    expect(h.apiPut).not.toHaveBeenCalledWith('/accounts/9/products', expect.anything(), { token: 'token-1' })
  })

  it('loadDealAccountsForProduct uses /accounts/for-deal for subscription', async () => {
    const h = createHarness()
    h.productsAll.value = [{ product_id: 55, type_code: 'subscription' }]
    h.apiGet.mockImplementation(async (url) => {
      if (url === '/accounts/for-deal?product_id=55&slot_type_code=ps5_p1') {
        return [
          { account_id: 7, login_full: 'a@x', platform_codes: ['ps5'] },
        ]
      }
      return []
    })

    await h.loadDealAccountsForProduct('new')

    expect(h.apiGet).toHaveBeenCalledWith('/accounts/for-deal?product_id=55&slot_type_code=ps5_p1', { token: 'token-1' })
    expect(h.dealAccountsForProductNew.value).toEqual([
      { account_id: 7, login_full: 'a@x', platform_codes: ['ps5'] },
    ])
  })

  it('loadDealSlotAvailability avoids availability endpoint for subscription', async () => {
    const h = createHarness()
    h.productsAll.value = [{ product_id: 55, type_code: 'subscription' }]
    h.slotTypes.value = [
      { code: 'ps5_p1' },
      { code: 'ps4_p1' },
    ]

    await h.loadDealSlotAvailability('new')

    expect(h.apiGet).not.toHaveBeenCalledWith('/accounts/for-deal/availability?product_id=55', { token: 'token-1' })
    expect(h.dealSlotAvailabilityNew.value).toEqual({
      ps5_p1: { hasFree: true },
      ps4_p1: { hasFree: true },
    })
  })

  it('loadSubscriptionFreeProductIds returns only subscriptions with free selected slot', async () => {
    const h = createHarness()
    h.productsAll.value = [
      { product_id: 55, type_code: 'subscription' },
      { product_id: 56, type_code: 'subscription' },
      { product_id: 57, type_code: 'game' },
    ]
    h.apiGet.mockResolvedValueOnce([55])

    await h.loadSubscriptionFreeProductIds('new', 'ps5_p1')

    expect(h.apiGet).toHaveBeenCalledWith(
      '/products/subscriptions/free-by-slot?slot_type_code=ps5_p1',
      { token: 'token-1' },
    )
    expect(h.subscriptionFreeProductIdsNew.value).toEqual([55])
  })
})
