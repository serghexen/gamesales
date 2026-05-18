import { describe, it, expect, vi } from 'vitest'
import { nextTick, ref } from 'vue'

import { useAccountsViewState } from '../useAccountsViewState.js'

function createHarness() {
  const accountsTotal = ref(40)
  const accountsPage = ref(3)
  const accountsPageInput = ref(1)
  const accountsPageSize = ref(20)
  const loadAccounts = vi.fn()

  const state = useAccountsViewState({
    accountsTotal,
    accountsPage,
    accountsPageInput,
    accountsPageSize,
    loadAccounts,
  })

  return {
    state,
    accountsTotal,
    accountsPage,
    accountsPageInput,
    accountsPageSize,
    loadAccounts,
  }
}

describe('useAccountsViewState', () => {
  it('computes pages and syncs page input', async () => {
    const h = createHarness()
    expect(h.state.accountsTotalPages.value).toBe(2)

    h.accountsPage.value = 2
    await nextTick()
    expect(h.accountsPageInput.value).toBe(2)
  })

  it('clamps page and reloads when total pages decrease', async () => {
    const h = createHarness()
    h.accountsTotal.value = 10
    await nextTick()
    expect(h.state.accountsTotalPages.value).toBe(1)
    expect(h.accountsPage.value).toBe(1)
    expect(h.loadAccounts).toHaveBeenCalledTimes(1)
  })

  it('resets page and reloads on page size change', async () => {
    const h = createHarness()
    h.accountsPageSize.value = 10
    await nextTick()
    expect(h.accountsPage.value).toBe(1)
    expect(h.loadAccounts).toHaveBeenCalledTimes(1)
  })
})

