import { describe, it, expect, vi } from 'vitest'

import { useDealModalFlow } from '../useDealModalFlow.js'

function ref(initial) {
  return { value: initial }
}

function createDeps() {
  return {
    closeAllModals: vi.fn(),
    resetModalPos: vi.fn(),
    setActiveTab: vi.fn(),
    showDealForm: ref(false),
    dealError: ref(null),
    dealOk: ref(null),
    newDeal: {
      deal_type_code: 'sale',
      account_id: '',
      game_id: '',
      customer_nickname: '',
      order_number: '',
      source_id: '',
      region_code: '',
      slot_type_code: '',
      price: 0,
      purchase_cost: 0,
      game_link: '',
      purchase_at: '',
      slots_used: 1,
      notes: '',
    },
    editDeal: {
      open: false,
      deal_id: null,
      created_at: '',
      completed_at: '',
      deal_type_code: 'sale',
      account_id: '',
      game_id: '',
      customer_nickname: '',
      order_number: '',
      source_id: '',
      region_code: '',
      slot_type_code: '',
      price: 0,
      purchase_cost: 0,
      game_link: '',
      purchase_at: '',
      slots_used: 1,
      notes: '',
      flow_status_code: '',
    },
    dealEditMode: ref('view'),
    dealInitLock: ref(false),
    newDealResponsible: ref(''),
    editDealResponsible: ref(''),
    newDealCommentOpen: ref(false),
    newDealGameSearch: ref(''),
    editDealGameSearch: ref(''),
    quickNewGame: { title: '', platform_codes: [] },
    quickEditGame: { title: '', platform_codes: [] },
    quickNewGameError: ref(''),
    quickEditGameError: ref(''),
    quickNewAccount: { login_name: '', domain_code: '', platform_codes: [] },
    quickEditAccount: { login_name: '', domain_code: '', platform_codes: [] },
    quickNewAccountError: ref(''),
    quickEditAccountError: ref(''),
    dealAccountsForGameNew: ref([]),
    dealAccountsForGameEdit: ref([]),
    dealAccountAssignmentsNew: ref([]),
    dealAccountAssignmentsEdit: ref([]),
    dealSlotAvailabilityNew: ref({}),
    dealSlotAvailabilityEdit: ref({}),
    nextTick: (cb) => cb(),
    loadDealSlotAvailability: vi.fn(),
    suppressUnsavedConfirm: ref(false),
    requestUnsavedConfirm: vi.fn().mockResolvedValue(true),
  }
}

describe('useDealModalFlow', () => {
  it('switches to edit mode from view mode', () => {
    const deps = createDeps()
    const api = useDealModalFlow(deps)

    api.toggleDealEditMode()

    expect(deps.dealEditMode.value).toBe('edit')
  })

  it('returns to view mode and restores original deal on second click', () => {
    const deps = createDeps()
    const api = useDealModalFlow(deps)
    api.startEditDeal({
      deal_id: 11,
      created_at: '2026-02-09T10:00:00Z',
      completed_at: '',
      deal_type_code: 'sale',
      account_id: null,
      game_id: '',
      customer_nickname: 'initial-buyer',
      order_number: 'A-1',
      source_id: 1,
      region_code: 'RU',
      slot_type_code: '',
      price: 100,
      purchase_cost: 10,
      game_link: 'https://game',
      purchase_at: '',
      slots_used: 1,
      notes: 'init',
      flow_status_code: 'pending',
      responsible_username: 'admin',
    })

    deps.dealEditMode.value = 'edit'
    deps.editDeal.customer_nickname = 'changed-buyer'
    deps.editDeal.price = 999

    api.toggleDealEditMode()

    expect(deps.dealEditMode.value).toBe('view')
    expect(deps.editDeal.customer_nickname).toBe('initial-buyer')
    expect(deps.editDeal.price).toBe(100)
    expect(deps.editDeal.created_at).toBe('2026-02-09T10:00:00Z')
  })

  it('closes fresh sharing form without unsaved warning', async () => {
    const deps = createDeps()
    const api = useDealModalFlow(deps)

    api.openCreateSharingModal()
    const closed = await api.closeDealModal()

    expect(closed).toBe(true)
    expect(deps.requestUnsavedConfirm).not.toHaveBeenCalled()
  })
})
