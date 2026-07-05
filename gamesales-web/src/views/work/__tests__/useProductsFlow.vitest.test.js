import { describe, it, expect, vi } from 'vitest'
import { reactive, ref } from 'vue'

import { useProductsFlow } from '../useProductsFlow.js'

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
  const auth = { state: reactive({ token: 'token-1' }) }
  const apiGet = vi.fn()
  const apiPost = vi.fn()
  const apiPut = vi.fn()
  const apiDelete = vi.fn()

  const showProductForm = ref(false)
  const productEditMode = ref('view')
  const accountsAll = ref([])
  const editProduct = reactive({
    open: false,
    product_id: null,
    type_code: 'game',
    account_ids: [],
    title: '',
    short_title: '',
    link: '',
    text_lang: '',
    audio_lang: '',
    vr_support: '',
    platform_codes: [],
    region_code: '',
    provider: '',
    billing_period: '',
    subscription_notes: '',
  })
  const newProduct = reactive({
    type_code: 'game',
    account_ids: [],
    title: '',
    short_title: '',
    link: '',
    text_lang: '',
    audio_lang: '',
    vr_support: '',
    platform_codes: [],
    region_code: '',
    provider: '',
    billing_period: '',
    subscription_notes: '',
  })

  const deps = {
    auth,
    apiGet,
    apiPost,
    apiPut,
    apiDelete,
    mapApiError: (v) => String(v || ''),
    closeAllModals: vi.fn(),
    resetModalPos: vi.fn(),
    setActiveTab: vi.fn(),
    showProductForm,
    productEditMode,
    editProduct,
    newProduct,
    productError: ref(null),
    productOk: ref(null),
    productsLoading: ref(false),
    productLoading: ref(false),
    productSaving: ref(false),
    products: ref([]),
    productsAll: ref([]),
    productsTotal: ref(0),
    accountsAll,
    productsSort: ref({ key: 'title', dir: 'asc' }),
    productsPage: ref(1),
    productsPageSize: ref(20),
    productFilters: reactive({ q: '', type_code: '', platform_code: '', region_code: '' }),
    productFilterDraft: reactive({ title: '', type: '', platform: '', region: '' }),
    accountFilters: reactive({ login_q: '' }),
    productAccounts: ref([]),
    productAccountsLoading: ref(false),
    productAccountsError: ref(null),
    productAccountOptions: ref([]),
    productAccountsPage: ref(1),
    productSlotAssignments: ref([]),
    productSlotAssignmentsError: ref(null),
    productSlotAssignmentsLoading: ref(false),
    productSubscriptionTerms: ref([]),
    productSubscriptionTermsLoading: ref(false),
    productSubscriptionTermsError: ref(null),
    loadProductSlotAssignments: vi.fn(),
    suppressUnsavedConfirm: ref(false),
    requestUnsavedConfirm: vi.fn(async () => true),
    requestDealConfirm: vi.fn(async () => true),
    loadAccountsAll: vi.fn(async () => undefined),
    canDoAction: () => true,
    quickNewProductAccount: reactive({ login_name: '', domain_code: '', platform_codes: [] }),
    quickNewProductAccountLoading: ref(false),
    quickNewProductAccountError: ref(''),
    quickEditProductAccount: reactive({ login_name: '', domain_code: '', platform_codes: [] }),
    quickEditProductAccountLoading: ref(false),
    quickEditProductAccountError: ref(''),
  }

  return {
    deps,
    apiGet,
    apiPost,
    products: deps.products,
    accountsAll,
    productsAll: deps.productsAll,
    editProduct,
    productFilters: deps.productFilters,
    newProduct,
    flow: useProductsFlow(deps),
  }
}

describe('useProductsFlow', () => {
  it('loadProducts requests /products and maps product fields', async () => {
    const h = createHarness()
    h.productFilters.type_code = 'subscription'
    h.apiGet.mockResolvedValueOnce({
      total: 1,
      items: [
        {
          product_id: 8,
          type_code: 'subscription',
          title: 'PS Plus',
          platform_codes: [],
        },
      ],
    })

    await h.flow.loadProducts()

    expect(h.apiGet).toHaveBeenCalledWith('/products?type_code=subscription&sort_key=title&sort_dir=asc&page=1&page_size=20', { token: 'token-1' })
    expect(h.products.value[0]).toMatchObject({ product_id: 8, type_code: 'subscription' })
  })

  it('loadProductsAll keeps both game and subscription products from /products response', async () => {
    const h = createHarness()
    h.apiGet.mockResolvedValueOnce({
      items: [
        { product_id: 10, type_code: 'game', title: 'Game A', platform_codes: ['ps5'] },
        { product_id: 12, type_code: 'game', title: 'Game B', platform_codes: ['ps4'] },
        { product_id: 11, type_code: 'subscription', title: 'PS Plus', platform_codes: [] },
      ],
    })

    await h.flow.loadProductsAll()

    expect(h.apiGet).toHaveBeenCalledWith('/products?all=true&sort_key=title&sort_dir=asc', { token: 'token-1' })
    expect(h.productsAll.value).toEqual([
      expect.objectContaining({ product_id: 10, type_code: 'game' }),
      expect.objectContaining({ product_id: 12, type_code: 'game' }),
      expect.objectContaining({ product_id: 11, type_code: 'subscription' }),
    ])
  })

  it('createProduct posts subscription payload to /products', async () => {
    const h = createHarness()
    h.newProduct.type_code = 'subscription'
    h.newProduct.title = 'PS Plus'
    h.newProduct.provider = 'sony'
    h.newProduct.billing_period = 'month'
    h.newProduct.subscription_notes = 'base'
    h.apiPost.mockResolvedValueOnce({ product_id: 77 })
    h.apiGet.mockResolvedValue({ items: [], total: 0 })

    await h.flow.createProduct()

    expect(h.apiPost).toHaveBeenCalledWith(
      '/products',
      expect.objectContaining({
        type_code: 'subscription',
        title: 'PS Plus',
        provider: 'sony',
        billing_period: 'month',
        subscription_notes: 'base',
        platform_codes: [],
      }),
      { token: 'token-1' },
    )
  })

  it('createProduct posts game payload with forced game type and comment', async () => {
    const h = createHarness()
    h.newProduct.type_code = 'unexpected'
    h.newProduct.title = 'GTA V'
    h.newProduct.text_lang = 'RU'
    h.newProduct.audio_lang = 'EN'
    h.newProduct.vr_support = 'нет'
    h.newProduct.platform_codes = ['ps5']
    h.newProduct.subscription_notes = 'Тестовый комментарий'
    h.apiPost.mockResolvedValueOnce({ product_id: 78 })
    h.apiGet.mockResolvedValue({ items: [], total: 0 })

    await h.flow.createProduct()

    expect(h.apiPost).toHaveBeenCalledWith(
      '/products',
      expect.objectContaining({
        type_code: 'game',
        title: 'GTA V',
        text_lang: 'RU',
        audio_lang: 'EN',
        vr_support: 'нет',
        platform_codes: ['ps5'],
        subscription_notes: 'Тестовый комментарий',
      }),
      { token: 'token-1' },
    )
  })

  it('createProduct binds game product to selected account', async () => {
    const h = createHarness()
    h.newProduct.type_code = 'game'
    h.newProduct.title = 'GTA V'
    h.newProduct.account_ids = [15]
    h.apiPost.mockResolvedValueOnce({ product_id: 88 })
    h.apiGet
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([{ product_id: 10 }])
      .mockResolvedValue({ items: [], total: 0 })

    await h.flow.createProduct()

    expect(h.deps.apiPut).toHaveBeenCalledWith(
      '/accounts/15/products',
      { product_ids: [88] },
      { token: 'token-1' },
    )
  })

  it('createProduct skips account binding without reflect accounts permission', async () => {
    const h = createHarness()
    h.deps.canDoAction = (actionCode) => actionCode !== 'products.reflect_accounts'
    h.flow = useProductsFlow(h.deps)
    h.newProduct.type_code = 'game'
    h.newProduct.title = 'GTA V'
    h.newProduct.account_ids = [15]
    h.apiPost.mockResolvedValueOnce({ product_id: 88 })
    h.apiGet.mockResolvedValue({ items: [], total: 0 })

    await h.flow.createProduct()

    expect(h.deps.apiPut).not.toHaveBeenCalled()
  })

  it('loadProductAccounts requests product endpoint', async () => {
    const h = createHarness()
    h.apiGet.mockResolvedValueOnce([])

    await h.flow.loadProductAccounts(55)

    expect(h.apiGet).toHaveBeenCalledWith('/products/55/accounts', { token: 'token-1' })
  })

  it('opens create modal with game type for game button', () => {
    const h = createHarness()
    h.newProduct.type_code = 'subscription'

    h.flow.openCreateGameProductModal()

    expect(h.deps.showProductForm.value).toBe(true)
    expect(h.newProduct.type_code).toBe('game')
  })

  it('createQuickProductAccount creates account and appends it to product form selection', async () => {
    const h = createHarness()
    h.deps.quickNewProductAccount.login_name = 'new-acc'
    h.deps.quickNewProductAccount.domain_code = 'mail'
    h.deps.quickNewProductAccount.platform_codes = ['ps5']
    h.newProduct.region_code = 'RU'
    h.apiPost.mockResolvedValueOnce({ account_id: 77 })

    await h.flow.createQuickProductAccount('new')

    expect(h.apiPost).toHaveBeenCalledWith(
      '/accounts',
      expect.objectContaining({ login_name: 'new-acc', domain_code: 'mail', region_code: 'RU' }),
      { token: 'token-1' },
    )
    expect(h.apiPost.mock.calls[0][1].account_date).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(h.newProduct.account_ids).toEqual([77])
    expect(h.deps.loadAccountsAll).toHaveBeenCalledTimes(1)
  })

  it('opens create modal with subscription type for subscription button', () => {
    const h = createHarness()
    h.newProduct.type_code = 'game'

    h.flow.openCreateSubscriptionProductModal()

    expect(h.deps.showProductForm.value).toBe(true)
    expect(h.newProduct.type_code).toBe('subscription')
  })

  it('closeProductModal does not ask confirm for untouched subscription create form', async () => {
    const h = createHarness()

    h.flow.openCreateSubscriptionProductModal()
    const closed = await h.flow.closeProductModal()

    expect(closed).toBe(true)
    expect(h.deps.requestUnsavedConfirm).not.toHaveBeenCalled()
  })

  it('toggleProductEditMode reverts unsaved changes on second click', () => {
    const h = createHarness()
    h.flow.startEditProduct({
      product_id: 10,
      type_code: 'game',
      title: 'Game A',
      short_title: 'GA',
      text_lang: 'RU',
      platform_codes: ['ps5'],
      region_code: 'RU',
      subscription_notes: 'note',
    })

    h.flow.toggleProductEditMode()
    expect(h.deps.productEditMode.value).toBe('edit')

    h.editProduct.title = 'Changed'
    h.editProduct.subscription_notes = 'Changed note'

    h.flow.toggleProductEditMode()
    expect(h.deps.productEditMode.value).toBe('view')
    expect(h.editProduct.title).toBe('Game A')
    expect(h.editProduct.subscription_notes).toBe('note')
  })

  it('archiveProduct uses custom confirm callback before delete', async () => {
    const h = createHarness()
    h.editProduct.open = true
    h.editProduct.product_id = 55
    h.deps.requestDealConfirm.mockResolvedValueOnce(true)
    h.deps.apiDelete.mockResolvedValueOnce({})
    h.apiGet.mockResolvedValue({ items: [], total: 0 })

    await h.flow.archiveProduct()

    expect(h.deps.requestDealConfirm).toHaveBeenCalledTimes(1)
    expect(h.deps.apiDelete).toHaveBeenCalledWith('/products/55', { token: 'token-1' })
  })

  it('loadProductAccounts ignores stale response after product switch', async () => {
    const h = createHarness()
    const first = createDeferred()
    const second = createDeferred()
    h.apiGet
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise)

    const requestA = h.flow.loadProductAccounts(55)
    const requestB = h.flow.loadProductAccounts(77)
    second.resolve([{ account_id: 2 }])
    await requestB
    first.resolve([{ account_id: 1 }])
    await requestA

    expect(h.deps.productAccounts.value).toEqual([{ account_id: 2 }])
  })

  it('loadProducts ignores stale response after quick filter changes', async () => {
    const h = createHarness()
    const first = createDeferred()
    const second = createDeferred()
    h.apiGet
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise)

    h.productFilters.q = 'old'
    const requestA = h.flow.loadProducts()
    h.productFilters.q = 'new'
    const requestB = h.flow.loadProducts()

    second.resolve({ items: [{ product_id: 200, title: 'New Product' }], total: 1 })
    await requestB
    first.resolve({ items: [{ product_id: 100, title: 'Old Product' }], total: 1 })
    await requestA

    expect(h.products.value).toEqual([expect.objectContaining({ product_id: 200, title: 'New Product' })])
  })
})
