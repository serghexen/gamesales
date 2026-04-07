import { describe, it, expect, vi } from 'vitest'
import { reactive, ref, nextTick } from 'vue'

import { useDealsWatchers } from '../useDealsWatchers.js'

function createHarness() {
  const deps = {
    newDeal: reactive({ product_id: '', slot_type_code: 'share', account_id: 77, reserve_key: 'reserve1' }),
    editDeal: reactive({ open: true, product_id: '', slot_type_code: 'full', account_id: 88, reserve_key: 'reserve2' }),
    productsAll: ref([
      { product_id: 1, type_code: 'subscription' },
      { product_id: 2, type_code: 'game' },
    ]),
    dealInitLock: ref(false),
    dealSlotAutoAssign: ref(false),
    accountSlotStatusNew: ref([]),
    accountSlotStatusEdit: ref([]),
    dealAccountAssignmentsNew: ref([]),
    dealAccountAssignmentsEdit: ref([]),
    dealSlotAvailabilityNew: ref({}),
    dealSlotAvailabilityEdit: ref({}),
    loadDealAccountsForProduct: vi.fn(),
    loadDealProductAssignments: vi.fn(),
    loadAccountSlotStatus: vi.fn(),
    loadDealAccountAssignments: vi.fn(),
    loadDealSlotAvailability: vi.fn(),
    loadSubscriptionFreeProductIds: vi.fn(),
    loadAvailableSubscriptionItems: vi.fn(),
    ensureAccountSecretsLoaded: vi.fn(),
  }

  useDealsWatchers(deps)
  return deps
}

describe('useDealsWatchers', () => {
  it('keeps slot for new subscription when product changes', async () => {
    const h = createHarness()

    h.newDeal.product_id = 1
    await nextTick()

    expect(h.newDeal.slot_type_code).toBe('share')
    expect(h.newDeal.account_id).toBe('')
    expect(h.newDeal.reserve_key).toBe('')
    expect(h.loadDealSlotAvailability).toHaveBeenCalledWith('new')
  })

  it('resets slot for new game when product changes', async () => {
    const h = createHarness()

    h.newDeal.product_id = 2
    await nextTick()

    expect(h.newDeal.slot_type_code).toBe('')
    expect(h.newDeal.account_id).toBe('')
    expect(h.newDeal.reserve_key).toBe('')
    expect(h.loadDealSlotAvailability).toHaveBeenCalledWith('new')
  })

  it('keeps slot for edited subscription when product changes', async () => {
    const h = createHarness()

    h.editDeal.product_id = 1
    await nextTick()

    expect(h.editDeal.slot_type_code).toBe('full')
    expect(h.editDeal.account_id).toBe('')
    expect(h.editDeal.reserve_key).toBe('')
    expect(h.loadDealSlotAvailability).toHaveBeenCalledWith('edit')
  })

  it('rebuilds subscription free-products list when slot changes', async () => {
    const h = createHarness()

    h.newDeal.slot_type_code = 'ps5_p2'
    await nextTick()

    expect(h.loadSubscriptionFreeProductIds).toHaveBeenCalledWith('new', 'ps5_p2')
    expect(h.loadAvailableSubscriptionItems).toHaveBeenCalledWith('new', 'ps5_p2')
  })

  it('loads account secrets when editing account changes', async () => {
    const h = createHarness()

    h.editDeal.account_id = 99
    await nextTick()

    expect(h.ensureAccountSecretsLoaded).toHaveBeenCalledWith(99)
  })
})
