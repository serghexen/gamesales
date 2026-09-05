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
  it.each(['TR', 'PL'])('clears manual cost on switching new and edited services to %s', async (region) => {
    // Возврат к обычному региону не должен воскресить ранее введённый закуп.
    const h = createHarness()
    for (const deal of [h.newDeal, h.editDeal]) {
      Object.assign(deal, { deal_type_code: 'sale', region_code: 'US', purchase_cost: 500 })
    }
    await nextTick()
    for (const deal of [h.newDeal, h.editDeal]) deal.region_code = region
    await nextTick()
    for (const deal of [h.newDeal, h.editDeal]) {
      expect(deal.purchase_cost).toBe(0)
      deal.region_code = 'US'
    }
    await nextTick()
    expect(h.newDeal.purchase_cost).toBe(0)
    expect(h.editDeal.purchase_cost).toBe(0)
  })

  it('preserves loaded voucher totals during initialization and payment synchronization', async () => {
    // Применение сохранённой карточки под блокировкой не является ручной сменой региона.
    const h = createHarness()
    h.dealInitLock.value = true
    Object.assign(h.editDeal, { deal_type_code: 'sale', region_code: 'TR', purchase_cost: 475.04 })
    await nextTick()
    h.dealInitLock.value = false
    expect(h.editDeal.purchase_cost).toBe(475.04)
    h.editDeal.purchase_cost = 950.08
    await nextTick()
    expect(h.editDeal.purchase_cost).toBe(950.08)
  })

  it('leaves rental cost alone but clears it when switching to a voucher service', async () => {
    // Ограничение касается услуг, а не всех сделок региона.
    const h = createHarness()
    Object.assign(h.newDeal, { deal_type_code: 'rental', region_code: 'TR', purchase_cost: 500 })
    await nextTick()
    expect(h.newDeal.purchase_cost).toBe(500)
    h.newDeal.deal_type_code = 'sale'
    await nextTick()
    expect(h.newDeal.purchase_cost).toBe(0)
  })

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
