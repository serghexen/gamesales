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
    dealLoading: ref(false),
    newDeal: {
      deal_type_code: 'sale',
      account_id: '',
      product_id: '',
      customer_nickname: '',
      order_number: '',
      source_id: '',
      region_code: '',
      slot_type_code: '',
      reserve_key: '',
      price: 0,
      purchase_cost: 0,
      login: '',
      password: '',
      product_link: '',
      purchase_at: '',
      slots_used: 1,
      notes: '',
      is_refund: false,
    },
    editDeal: {
      open: false,
      deal_id: null,
      created_at: '',
      completed_at: '',
      deal_type_code: 'sale',
      account_id: '',
      product_id: '',
      customer_nickname: '',
      order_number: '',
      source_id: '',
      region_code: '',
      slot_type_code: '',
      reserve_key: '',
      price: 0,
      purchase_cost: 0,
      login: '',
      password: '',
      product_link: '',
      purchase_at: '',
      slots_used: 1,
      notes: '',
      flow_status_code: '',
      is_refund: false,
    },
    dealEditMode: ref('view'),
    dealInitLock: ref(false),
    newDealResponsible: ref(''),
    editDealResponsible: ref(''),
    newDealCommentOpen: ref(false),
    editDealCommentOpen: ref(false),
    newDealProductSearch: ref(''),
    editDealProductSearch: ref(''),
    quickNewProduct: { title: '', platform_codes: [] },
    quickEditProduct: { title: '', platform_codes: [] },
    quickNewProductError: ref(''),
    quickEditProductError: ref(''),
    quickNewAccount: { login_name: '', domain_code: '', platform_codes: [] },
    quickEditAccount: { login_name: '', domain_code: '', platform_codes: [] },
    quickNewAccountError: ref(''),
    quickEditAccountError: ref(''),
    quickNewSubscriptionTerm: { account_id: '', valid_until: '', notes: '' },
    quickEditSubscriptionTerm: { account_id: '', valid_until: '', notes: '' },
    quickNewSubscriptionTermError: ref(''),
    quickEditSubscriptionTermError: ref(''),
    dealAccountsForProductNew: ref([]),
    dealAccountsForProductEdit: ref([]),
    dealAccountAssignmentsNew: ref([]),
    dealAccountAssignmentsEdit: ref([]),
    dealSlotAvailabilityNew: ref({}),
    dealSlotAvailabilityEdit: ref({}),
    nextTick: (cb) => cb(),
    loadDealAccountsForProduct: vi.fn(),
    loadDealProductAssignments: vi.fn(),
    loadAccountSlotStatus: vi.fn(),
    loadDealAccountAssignments: vi.fn(),
    loadDealSlotAvailability: vi.fn(),
    loadSubscriptionTerms: vi.fn(),
    loadAvailableSubscriptionItems: vi.fn(),
    ensureAccountSecretsLoaded: vi.fn(),
    accountsAll: ref([]),
    loadAccountsAll: vi.fn(),
    suppressUnsavedConfirm: ref(false),
    requestUnsavedConfirm: vi.fn().mockResolvedValue(true),
    currentResponsibleName: 'Тестер',
    canEditCompletedDeal: ref(true),
    showDealWarning: vi.fn(),
  }
}

describe('useDealModalFlow', () => {
  it('switches to edit mode from view mode', () => {
    const deps = createDeps()
    const api = useDealModalFlow(deps)

    api.toggleDealEditMode()

    expect(deps.dealEditMode.value).toBe('edit')
  })

  it('returns to view mode and restores original deal on second click', async () => {
    const deps = createDeps()
    const api = useDealModalFlow(deps)
    await api.startEditDeal({
      deal_id: 11,
      created_at: '2026-02-09T10:00:00Z',
      completed_at: '',
      deal_type_code: 'sale',
      account_id: null,
      product_id: 55,
      customer_nickname: 'initial-buyer',
      order_number: 'A-1',
      source_id: 1,
      region_code: 'RU',
      slot_type_code: '',
      reserve_key: '',
      price: 100,
      purchase_cost: 10,
      login: 'deal-login',
      password: 'deal-pass',
      product_link: 'https://game',
      purchase_at: '',
      slots_used: 1,
      notes: 'init',
      flow_status_code: 'pending',
      is_refund: true,
      responsible_username: 'admin',
    })

    deps.dealEditMode.value = 'edit'
    deps.editDeal.customer_nickname = 'changed-buyer'
    deps.editDeal.price = 999

    api.toggleDealEditMode()

    expect(deps.dealEditMode.value).toBe('view')
    expect(deps.editDeal.customer_nickname).toBe('initial-buyer')
    expect(deps.editDeal.price).toBe(100)
    expect(deps.editDeal.login).toBe('deal-login')
    expect(deps.editDeal.password).toBe('deal-pass')
    expect(deps.editDeal.created_at).toMatch(/^2026-02-09T\d{2}:\d{2}$/)
    expect(deps.editDeal.is_refund).toBe(true)
  })

  it('closes fresh sharing form without unsaved warning', async () => {
    const deps = createDeps()
    const api = useDealModalFlow(deps)

    deps.editDealCommentOpen.value = true
    api.openCreateSharingModal()
    const closed = await api.closeDealModal()

    expect(closed).toBe(true)
    expect(deps.requestUnsavedConfirm).not.toHaveBeenCalled()
    expect(deps.editDealCommentOpen.value).toBe(false)
  })

  it('sets default quick subscription date as today plus one year in create sharing', () => {
    const deps = createDeps()
    const api = useDealModalFlow(deps)

    deps.quickNewSubscriptionTerm.valid_until = ''
    api.openCreateSharingModal()

    const nextYearDate = new Date()
    nextYearDate.setFullYear(nextYearDate.getFullYear() + 1)
    const expectedDate = `${nextYearDate.getFullYear()}-${String(nextYearDate.getMonth() + 1).padStart(2, '0')}-${String(nextYearDate.getDate()).padStart(2, '0')}`
    expect(deps.quickNewSubscriptionTerm.valid_until).toBe(expectedDate)
  })

  it('prefills responsible with current session user for new sale', () => {
    const deps = createDeps()
    const api = useDealModalFlow(deps)

    api.openCreateSaleModal()

    expect(deps.newDealResponsible.value).toBe('Тестер')
  })

  it('blocks edit mode for completed deal when user has no privileges', () => {
    const deps = createDeps()
    deps.canEditCompletedDeal.value = false
    const api = useDealModalFlow(deps)
    deps.editDeal.flow_status_code = 'completed'

    api.toggleDealEditMode()

    expect(deps.dealEditMode.value).toBe('view')
    expect(deps.showDealWarning).toHaveBeenCalledWith('Редактирование завершенных сделок доступно только администратору и владельцу')
  })

  it('keeps modal loading until primary edit dependencies are loaded', async () => {
    const deps = createDeps()
    const api = useDealModalFlow(deps)
    await api.startEditDeal({
      deal_id: 22,
      created_at: '2026-02-09T10:00:00Z',
      completed_at: '',
      deal_type_code: 'rental',
      account_id: 7,
      product_id: 55,
      customer_nickname: 'buyer',
      order_number: 'A-2',
      source_id: 1,
      region_code: 'RU',
      slot_type_code: 'ps5_p1',
      reserve_key: '',
      price: 100,
      purchase_cost: 10,
      login: '',
      password: '',
      product_link: '',
      purchase_at: '',
      slots_used: 1,
      notes: '',
      flow_status_code: 'pending',
      is_refund: false,
      responsible_username: 'admin',
    })

    expect(deps.loadDealAccountsForProduct).toHaveBeenCalledWith('edit')
    expect(deps.loadDealProductAssignments).toHaveBeenCalledWith('edit')
    expect(deps.loadDealSlotAvailability).toHaveBeenCalledWith('edit')
    expect(deps.loadAccountSlotStatus).toHaveBeenCalledWith('edit')
    expect(deps.loadDealAccountAssignments).toHaveBeenCalledWith('edit')
    expect(deps.loadSubscriptionTerms).toHaveBeenCalledWith('edit')
    expect(deps.loadAvailableSubscriptionItems).toHaveBeenCalledWith('edit', 'ps5_p1')
    expect(deps.ensureAccountSecretsLoaded).toHaveBeenCalledWith(7)
    expect(deps.dealLoading.value).toBe(false)
  })
})
