import { describe, it, expect } from 'vitest'
import { ref } from 'vue'

import { useAccountsDerivedState } from '../useAccountsDerivedState.js'

describe('useAccountsDerivedState', () => {
  it('returns accounts copy and filters products by search and type for create/edit', () => {
    const accounts = ref([{ account_id: 1 }, { account_id: 2 }])
    const productsAll = ref([
      { product_id: 101, title: 'God of War', type_code: 'game' },
      { product_id: 102, title: 'FIFA 24', type_code: 'game' },
      { product_id: 103, title: 'PS Plus Deluxe', type_code: 'subscription' },
    ])
    const accountProductSearch = ref('god')
    const editAccountProductSearch = ref('plus')
    const accountProductType = ref('game')
    const editAccountProductType = ref('subscription')

    const s = useAccountsDerivedState({
      accounts,
      productsAll,
      accountProductSearch,
      editAccountProductSearch,
      accountProductType,
      editAccountProductType,
    })

    expect(s.sortedAccounts.value).toEqual(accounts.value)
    expect(s.sortedAccounts.value).not.toBe(accounts.value)
    expect(s.filteredAccountProducts.value.map((g) => g.product_id)).toEqual([101])
    expect(s.filteredEditAccountProducts.value.map((g) => g.product_id)).toEqual([103])
  })
})
