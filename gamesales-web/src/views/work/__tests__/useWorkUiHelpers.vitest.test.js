import { describe, it, expect } from 'vitest'
import { ref } from 'vue'

import { useWorkUiHelpers } from '../useWorkUiHelpers.js'

function createHarness() {
  const productsPageSize = ref(20)
  const productsPageInput = ref(1)
  const accountSort = ref('login_asc')
  const productsSort = ref({ key: 'title', dir: 'asc' })
  const dealSort = ref({ key: 'created_at', dir: 'desc' })
  const domainsSortAsc = ref(true)

  const api = useWorkUiHelpers({
    productsPageSize,
    productsPageInput,
    accountSort,
    productsSort,
    dealSort,
    domainsSortAsc,
  })

  return {
    api,
    productsPageSize,
    productsPageInput,
    accountSort,
    productsSort,
    dealSort,
    domainsSortAsc,
  }
}

describe('useWorkUiHelpers', () => {
  it('updates products page fields from events', () => {
    const h = createHarness()
    h.api.setProductsPageSizeFromEvent({ target: { value: '50' } })
    h.api.setProductsPageInputFromEvent({ target: { value: '3' } })
    expect(h.productsPageSize.value).toBe(50)
    expect(h.productsPageInput.value).toBe(3)

    h.api.setProductsPageSizeFromEvent({ target: { value: '0' } })
    h.api.setProductsPageInputFromEvent({ target: { value: 'bad' } })
    expect(h.productsPageSize.value).toBe(50)
    expect(h.productsPageInput.value).toBe(3)
  })

  it('builds sort classes for account/products/deals and keyed sort refs', () => {
    const h = createHarness()
    expect(h.api.getAccountSortClass('login')).toMatchObject({ 'sort-icon--asc': true, 'sort-icon--active': true })
    expect(h.api.getProductsSortClass('title')).toMatchObject({ 'sort-icon--asc': true, 'sort-icon--active': true })
    expect(h.api.getDealSortClass('created_at')).toMatchObject({ 'sort-icon--desc': true, 'sort-icon--active': true })
    expect(h.api.getDomainsSortClass()).toMatchObject({ 'sort-icon--asc': true, 'sort-icon--active': true })
    expect(h.api.getKeyedSortClass(ref({ key: 'code', dir: 'desc' }), 'code')).toMatchObject({ 'sort-icon--desc': true, 'sort-icon--active': true })
  })

  it('formats slot status and note textarea rows', () => {
    const h = createHarness()
    expect(h.api.getSlotAssignmentStatus({ released_at: null })).toBe('Занят')
    expect(h.api.getSlotAssignmentStatus({ released_at: '2026-02-09' })).toBe('Снят')
    expect(h.api.getNotesRows('')).toBe(2)
    expect(h.api.getNotesRows('x'.repeat(200))).toBeGreaterThanOrEqual(3)
    expect(h.api.getCompactNotesRows('')).toBe(2)
    expect(h.api.getCompactNotesRows('x'.repeat(400))).toBeGreaterThanOrEqual(2)
  })
})
