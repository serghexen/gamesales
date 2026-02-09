import { describe, it, expect, vi } from 'vitest'

import { useDealsActions } from '../useDealsActions.js'

function ref(initial) {
  return { value: initial }
}

function createDeps(overrides = {}) {
  return {
    auth: { state: { token: 'token' } },
    apiPost: vi.fn().mockResolvedValue({}),
    apiPut: vi.fn().mockResolvedValue({}),
    mapApiError: vi.fn((msg) => String(msg || 'Ошибка')),
    toUtcDateTime: vi.fn((value) => (value ? `${value}T00:00:00Z` : null)),
    newDeal: {
      deal_type_code: 'sale',
      account_id: '',
      game_id: '',
      customer_nickname: 'buyer',
      source_id: '',
      region_code: 'RU',
      slot_type_code: '',
      price: 100,
      purchase_cost: 50,
      game_link: '',
      purchase_at: '',
      notes: '',
    },
    editDeal: {
      deal_id: 1,
      deal_type_code: 'sale',
      account_id: '',
      game_id: '',
      customer_nickname: 'buyer',
      source_id: '',
      region_code: 'RU',
      slot_type_code: '',
      price: 100,
      purchase_cost: 50,
      game_link: '',
      purchase_at: '',
      notes: '',
      flow_status_code: '',
    },
    dealPage: ref(1),
    dealError: ref(null),
    dealOk: ref(null),
    dealLoading: ref(false),
    dealSaving: ref(false),
    dealBackgroundSync: ref(false),
    loadDeals: vi.fn().mockResolvedValue(undefined),
    loadAccountsAll: vi.fn().mockResolvedValue(undefined),
    closeDealModal: vi.fn(),
    ...overrides,
  }
}

describe('useDealsActions', () => {
  it('createDeal closes modal and unlocks UI even when background reload fails', async () => {
    const deps = createDeps({
      loadAccountsAll: vi.fn().mockRejectedValue(new Error('network')),
    })
    const { createDeal } = useDealsActions(deps)

    await createDeal()

    expect(deps.apiPost).toHaveBeenCalledTimes(1)
    expect(deps.closeDealModal).toHaveBeenCalledTimes(1)
    expect(deps.dealLoading.value).toBe(false)
    expect(deps.dealSaving.value).toBe(false)
    expect(deps.dealBackgroundSync.value).toBe(false)
    expect(deps.dealError.value).toBeNull()
  })

  it('createDeal keeps modal open and unlocks UI on save error', async () => {
    const deps = createDeps({
      apiPost: vi.fn().mockRejectedValue(new Error('save failed')),
    })
    const { createDeal } = useDealsActions(deps)

    await createDeal()

    expect(deps.closeDealModal).not.toHaveBeenCalled()
    expect(deps.dealLoading.value).toBe(false)
    expect(deps.dealSaving.value).toBe(false)
    expect(deps.dealBackgroundSync.value).toBe(false)
    expect(deps.dealError.value).toBe('save failed')
  })
})
