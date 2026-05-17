import { describe, it, expect, vi } from 'vitest'
import { reactive, ref } from 'vue'

import { useDealsFlow } from '../useDealsFlow.js'

function createDeferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

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
    quickNewAccount: reactive({ login_name: 'qa', domain_code: 'gmail.com', platform_codes: ['ps5'], password: 'pwd', notes: 'note', subscription_product_id: '' }),
    quickEditAccount: reactive({ login_name: '', domain_code: '', platform_codes: [], password: '', notes: '', subscription_product_id: '' }),
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
    subscriptionTermsNew: ref([]),
    subscriptionTermsEdit: ref([]),
    subscriptionTermsLoadingNew: ref(false),
    subscriptionTermsLoadingEdit: ref(false),
    subscriptionAvailableItemsNew: ref([]),
    subscriptionAvailableItemsEdit: ref([]),
    subscriptionAvailableItemsLoadingNew: ref(false),
    subscriptionAvailableItemsLoadingEdit: ref(false),
    quickNewSubscriptionTerm: reactive({ account_id: '', valid_until: '', notes: '' }),
    quickEditSubscriptionTerm: reactive({ account_id: '', valid_until: '', notes: '' }),
    quickNewSubscriptionTermLoading: ref(false),
    quickEditSubscriptionTermLoading: ref(false),
    quickNewSubscriptionTermError: ref(''),
    quickEditSubscriptionTermError: ref(''),
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

    expect(h.apiPost).toHaveBeenNthCalledWith(
      1,
      '/accounts',
      expect.objectContaining({ region_code: 'RU' }),
      { token: 'token-1' },
    )
    expect(h.apiPost.mock.calls[0][1].account_date).toMatch(/^\d{4}-\d{2}-\d{2}$/)
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

  it('createQuickAccount does not require platform selection', async () => {
    const h = createHarness()
    h.quickNewAccount.platform_codes = []
    h.apiPost.mockResolvedValueOnce({ account_id: 10 })

    await h.createQuickAccount('new')

    expect(h.quickNewAccountError.value).toBe('')
    expect(h.apiPost).toHaveBeenCalledWith(
      '/accounts',
      expect.objectContaining({
        login_name: 'qa',
        domain_code: 'gmail.com',
      }),
      { token: 'token-1' },
    )
  })

  it('createQuickAccount creates subscription term when product selected in quick block', async () => {
    const h = createHarness()
    h.newDeal.deal_type_code = 'rental'
    h.newDeal.slot_type_code = 'play_ps5'
    h.newDeal.product_id = ''
    h.newDeal.account_id = ''
    h.quickNewAccount.subscription_product_id = 88
    h.productsAll.value = [{ product_id: 88, type_code: 'subscription' }]
    h.apiPost
      .mockResolvedValueOnce({ account_id: 19 })
      .mockResolvedValueOnce({})
      .mockResolvedValueOnce({ term_id: 105, account_id: 19 })

    await h.createQuickAccount('new')

    expect(h.apiPost).toHaveBeenNthCalledWith(
      3,
      '/products/subscriptions/88/terms',
      expect.objectContaining({ account_id: 19 }),
      { token: 'token-1' },
    )
    expect(h.newDeal.product_id).toBe(88)
    expect(h.newDeal.subscription_term_id).toBe(105)
    expect(h.newDeal.account_id).toBe(19)
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

  it('loadDealProductAssignments skips API for subscription', async () => {
    const h = createHarness()
    h.productsAll.value = [{ product_id: 55, type_code: 'subscription' }]
    h.newDeal.product_id = 55

    await h.loadDealProductAssignments('new')

    expect(h.apiGet).not.toHaveBeenCalledWith('/products/55/slot-assignments', { token: 'token-1' })
    expect(h.dealGameAssignmentsNew.value).toEqual([])
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

  it('loadAvailableSubscriptionItems loads flat list of available items by slot', async () => {
    const h = createHarness()
    h.newDeal.slot_type_code = 'play_ps5'
    h.apiGet.mockResolvedValueOnce([{ term_id: 10, product_id: 55 }])

    await h.loadAvailableSubscriptionItems('new', 'play_ps5')

    expect(h.apiGet).toHaveBeenCalledWith(
      '/products/subscriptions/terms/available-for-deal?slot_type_code=play_ps5',
      { token: 'token-1' },
    )
    expect(h.subscriptionAvailableItemsNew.value).toEqual([{ term_id: 10, product_id: 55 }])
  })

  it('createQuickSubscriptionTerm resets date to today plus one year', async () => {
    const h = createHarness()
    h.productsAll.value = [{ product_id: 55, type_code: 'subscription' }]
    h.quickNewSubscriptionTerm.account_id = 7
    h.quickNewSubscriptionTerm.valid_until = '2026-02-01'
    h.quickNewSubscriptionTerm.notes = 'n'
    h.apiPost.mockResolvedValueOnce({ term_id: 101, account_id: 7 })
    h.apiGet.mockResolvedValueOnce([])

    await h.createQuickSubscriptionTerm('new')

    const nextYearDate = new Date()
    nextYearDate.setFullYear(nextYearDate.getFullYear() + 1)
    const expectedDate = `${nextYearDate.getFullYear()}-${String(nextYearDate.getMonth() + 1).padStart(2, '0')}-${String(nextYearDate.getDate()).padStart(2, '0')}`
    expect(h.quickNewSubscriptionTerm.valid_until).toBe(expectedDate)
  })

  it('clearNewDealProduct resets term and account for subscription', () => {
    const h = createHarness()
    h.productsAll.value = [{ product_id: 55, type_code: 'subscription' }]
    h.newDeal.product_id = 55
    h.newDeal.subscription_term_id = 10
    h.newDeal.account_id = 7

    h.clearNewDealProduct()

    expect(h.newDeal.product_id).toBe('')
    expect(h.newDeal.subscription_term_id).toBe('')
    expect(h.newDeal.account_id).toBe('')
  })

  it('loadDealAccountsForProduct ignores stale response after slot switch', async () => {
    const h = createHarness()
    const first = createDeferred()
    const second = createDeferred()
    h.apiGet
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise)

    h.newDeal.slot_type_code = 'slot_a'
    const requestA = h.loadDealAccountsForProduct('new')
    h.newDeal.slot_type_code = 'slot_b'
    const requestB = h.loadDealAccountsForProduct('new')

    second.resolve([{ account_id: 22 }])
    await requestB
    first.resolve([{ account_id: 11 }])
    await requestA

    expect(h.dealAccountsForProductNew.value).toEqual([{ account_id: 22 }])
  })

  it('loadAvailableSubscriptionItems ignores stale response after slot switch', async () => {
    const h = createHarness()
    const first = createDeferred()
    const second = createDeferred()
    h.apiGet
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise)

    h.newDeal.slot_type_code = 'slot_a'
    const requestA = h.loadAvailableSubscriptionItems('new', 'slot_a')
    h.newDeal.slot_type_code = 'slot_b'
    const requestB = h.loadAvailableSubscriptionItems('new', 'slot_b')

    second.resolve([{ term_id: 2 }])
    await requestB
    first.resolve([{ term_id: 1 }])
    await requestA

    expect(h.subscriptionAvailableItemsNew.value).toEqual([{ term_id: 2 }])
  })

  it('loadSubscriptionTerms ignores stale response after slot switch', async () => {
    const h = createHarness()
    h.productsAll.value = [{ product_id: 55, type_code: 'subscription' }]
    const first = createDeferred()
    const second = createDeferred()
    h.apiGet
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise)

    h.newDeal.product_id = 55
    h.newDeal.slot_type_code = 'slot_a'
    const requestA = h.loadSubscriptionTerms('new')
    h.newDeal.slot_type_code = 'slot_b'
    const requestB = h.loadSubscriptionTerms('new')

    second.resolve([{ term_id: 200, account_id: 9, valid_until: '2027-01-01' }])
    await requestB
    first.resolve([{ term_id: 100, account_id: 7, valid_until: '2026-01-01' }])
    await requestA

    expect(h.subscriptionTermsNew.value).toEqual([{ term_id: 200, account_id: 9, valid_until: '2027-01-01' }])
  })
})
