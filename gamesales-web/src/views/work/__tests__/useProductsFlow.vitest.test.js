import { describe, it, expect, vi } from 'vitest'
import { reactive, ref } from 'vue'

import { useProductsFlow } from '../useProductsFlow.js'

function createHarness() {
  const auth = { state: reactive({ token: 'token-1' }) }
  const apiGet = vi.fn()
  const apiPost = vi.fn()
  const apiPut = vi.fn()
  const apiDelete = vi.fn()

  const showProductForm = ref(false)
  const productEditMode = ref('view')
  const editProduct = reactive({
    open: false,
    product_id: null,
    type_code: 'game',
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
    productsSort: ref({ key: 'title', dir: 'asc' }),
    productsPage: ref(1),
    productsPageSize: ref(20),
    productFilters: reactive({ q: '', type_code: '', platform_code: '', region_code: '' }),
    productFilterDraft: reactive({ title: '', type: '', platform: '', region: '' }),
    accountFilters: reactive({ login_q: '' }),
    productAccounts: ref([]),
    productAccountsLoading: ref(false),
    productAccountsError: ref(null),
    productAccountsPage: ref(1),
    productSlotAssignments: ref([]),
    productSlotAssignmentsError: ref(null),
    productSlotAssignmentsLoading: ref(false),
    loadProductSlotAssignments: vi.fn(),
    suppressUnsavedConfirm: ref(false),
    requestUnsavedConfirm: vi.fn(async () => true),
  }

  return {
    deps,
    apiGet,
    apiPost,
    products: deps.products,
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
})
