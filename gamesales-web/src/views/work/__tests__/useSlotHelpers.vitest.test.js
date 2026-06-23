import { describe, it, expect } from 'vitest'
import { reactive, ref } from 'vue'

import { useSlotHelpers } from '../useSlotHelpers.js'

function createHarness() {
  const slotTypes = ref([
    { code: 'share', name: 'Share', platform_code: 'ps5' },
    { code: 'full', name: 'Full', platform_code: 'ps4' },
    { code: 'activate_ps5', name: 'П2 (PS5)', platform_code: 'ps5', mode: 'activate' },
    { code: 'play_ps5', name: 'П3 (PS5)', platform_code: 'ps5', mode: 'play' },
  ])
  const productsAll = ref([
    { product_id: 1, type_code: 'subscription', title: 'ПОДПИСКА EA PLAY до 26.02.2026', platform_codes: ['ps5'] },
    { product_id: 2, type_code: 'game', title: 'FC 26', platform_codes: ['ps5'] },
  ])
  const newDeal = reactive({ product_id: 1, slot_type_code: 'share', account_id: null })
  const editDeal = reactive({ product_id: null, slot_type_code: '', account_id: null })
  const dealAccountsForProductNew = ref([])
  const dealAccountsForProductEdit = ref([])
  const dealSlotAvailabilityNew = ref({ share: { hasFree: false } })
  const dealSlotAvailabilityEdit = ref({})
  const hasAnyProductAssignmentsNew = ref(false)
  const hasAnyProductAssignmentsEdit = ref(false)
  const accountSlotAssignments = ref([])
  const accountSlotAssignmentsSort = ref({ key: 'slot', dir: 'asc' })

  return useSlotHelpers({
    slotTypes,
    productsAll,
    newDeal,
    editDeal,
    dealAccountsForProductNew,
    dealAccountsForProductEdit,
    dealSlotAvailabilityNew,
    dealSlotAvailabilityEdit,
    hasAnyProductAssignmentsNew,
    hasAnyProductAssignmentsEdit,
    accountSlotAssignments,
    accountSlotAssignmentsSort,
  })
}

describe('useSlotHelpers', () => {
  it('treats subscription slot options as free even when availability says occupied', () => {
    const h = createHarness()
    const options = h.getDealSlotTypeOptions('new')
    const share = options.find((item) => item.code === 'share')

    expect(share?.hasFree).toBe(true)
    expect(h.getDealSlotTypeLabel(share)).toBe('Share')
  })

  it('returns free slots for subscription regardless of availability map', () => {
    const h = createHarness()

    expect(h.hasFreeDealSlots('new')).toBe(true)
  })

  it('normalizes subscription title for sharing label', () => {
    const h = createHarness()

    expect(h.getProductLabelById(1)).toBe('EA PLAY')
    expect(h.getProductLabelById(2)).toBe('FC 26')
  })

  it('shows P2 capacity per platform while keeping P3 capacity from backend', () => {
    const h = createHarness()
    const account = {
      slot_status: [
        { slot_type_code: 'activate_ps5', mode: 'activate', occupied: 1, capacity: 2 },
        { slot_type_code: 'play_ps5', mode: 'play', occupied: 2, capacity: 2 },
      ],
    }

    expect(h.formatAccountSlotStatusLine(account.slot_status[0])).toBe('П2 (PS5) - 1/1')
    expect(h.formatAccountSlotStatusLine(account.slot_status[1])).toBe('П3 (PS5) - 2/2')
    expect(h.getAccountSlotsText(account)).toBe('П2 (PS5) 1/1 · П3 (PS5) 2/2')
  })
})
