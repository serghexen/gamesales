import { describe, it, expect, vi } from 'vitest'
import { ref, nextTick } from 'vue'

import { useProductsViewState } from '../useProductsViewState.js'

function createHarness() {
  const products = ref([{ product_id: 1 }, { product_id: 2 }])
  const productsTotal = ref(40)
  const productsPage = ref(3)
  const productsPageInput = ref(1)
  const productsPageSize = ref(20)
  const loadProducts = vi.fn()
  const productAccounts = ref([
    { login_name: 'beta', score: 2 },
    { login_name: 'alpha', score: 1 },
    { login_name: 'gamma', score: 3 },
  ])
  const productAccountsSort = ref({ key: 'login_name', dir: 'asc' })
  const productAccountsPage = ref(1)
  const productAccountsPageSize = 2

  const state = useProductsViewState({
    products,
    productsTotal,
    productsPage,
    productsPageInput,
    productsPageSize,
    loadProducts,
    productAccounts,
    productAccountsSort,
    productAccountsPage,
    productAccountsPageSize,
  })

  return {
    state,
    productsTotal,
    productsPage,
    productsPageInput,
    productsPageSize,
    loadProducts,
    productAccountsSort,
    productAccountsPage,
  }
}

describe('useProductsViewState', () => {
  it('computes pages and syncs page input', async () => {
    const h = createHarness()
    expect(h.state.productsTotalPages.value).toBe(2)

    h.productsPage.value = 2
    await nextTick()
    expect(h.productsPageInput.value).toBe(2)
  })

  it('clamps page when total pages decrease', async () => {
    const h = createHarness()
    h.productsTotal.value = 10
    await nextTick()
    expect(h.state.productsTotalPages.value).toBe(1)
    expect(h.productsPage.value).toBe(1)
  })

  it('reloads list and resets page when page size changes', async () => {
    const h = createHarness()
    h.productsPageSize.value = 10
    await nextTick()
    expect(h.productsPage.value).toBe(1)
    expect(h.loadProducts).toHaveBeenCalledTimes(1)
  })

  it('sorts and paginates game accounts', () => {
    const h = createHarness()
    expect(h.state.productAccountsTotalPages.value).toBe(2)
    expect(h.state.pagedProductAccounts.value.map((a) => a.login_name)).toEqual(['alpha', 'beta'])

    h.productAccountsSort.value = { key: 'score', dir: 'desc' }
    h.productAccountsPage.value = 2
    expect(h.state.pagedProductAccounts.value.map((a) => a.score)).toEqual([1])
  })
})
