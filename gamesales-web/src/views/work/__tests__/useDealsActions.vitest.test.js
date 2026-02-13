import { describe, it, expect, vi } from 'vitest'

import { useDealsActions } from '../useDealsActions.js'

function ref(initial) {
  return { value: initial }
}

function createDeps(overrides = {}) {
  return {
    auth: { state: { token: 'token', user: 'tester' } },
    apiPost: vi.fn().mockResolvedValue({}),
    apiPut: vi.fn().mockResolvedValue({}),
    apiDelete: vi.fn().mockResolvedValue({}),
    mapApiError: vi.fn((msg) => String(msg || 'Ошибка')),
    toUtcDateTime: vi.fn((value) => (value ? `${value}T00:00:00Z` : null)),
    newDeal: {
      deal_type_code: 'sale',
      account_id: '',
      product_id: 55,
      customer_nickname: 'buyer',
      order_number: 'ORD-1',
      source_id: 10,
      region_code: 'RU',
      slot_type_code: '',
      price: 100,
      purchase_cost: 50,
      login: 'deal-login',
      password: 'deal-pass',
      product_link: '',
      purchase_at: '',
      notes: '',
      is_refund: false,
    },
    editDeal: {
      deal_id: 1,
      deal_type_code: 'sale',
      account_id: '',
      product_id: 56,
      customer_nickname: 'buyer',
      order_number: 'ORD-2',
      source_id: 10,
      region_code: 'RU',
      slot_type_code: '',
      price: 100,
      purchase_cost: 50,
      login: 'edit-login',
      password: 'edit-pass',
      product_link: '',
      purchase_at: '',
      notes: '',
      flow_status_code: 'pending',
      is_refund: false,
    },
    newDealResponsible: ref('current_user'),
    editDealResponsible: ref('alice'),
    dealPage: ref(1),
    dealError: ref(null),
    dealOk: ref(null),
    dealLoading: ref(false),
    dealSaving: ref(false),
    dealBackgroundSync: ref(false),
    suppressUnsavedConfirm: ref(false),
    showDealWarning: vi.fn(),
    requestDealConfirm: vi.fn().mockResolvedValue(true),
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
    expect(deps.apiPost.mock.calls[0][1].order_number).toBe('ORD-1')
    expect(deps.apiPost.mock.calls[0][1].login).toBe('deal-login')
    expect(deps.apiPost.mock.calls[0][1].password).toBe('deal-pass')
    expect(deps.apiPost.mock.calls[0][1].responsible_username).toBe('tester')
    expect(deps.apiPost.mock.calls[0][1].product_id).toBe(55)
    expect(deps.closeDealModal).toHaveBeenCalledTimes(1)
    expect(deps.dealLoading.value).toBe(false)
    expect(deps.dealSaving.value).toBe(false)
    expect(deps.dealBackgroundSync.value).toBe(false)
    expect(deps.suppressUnsavedConfirm.value).toBe(false)
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

  it('createDeal validates required source for sale', async () => {
    const deps = createDeps()
    deps.newDeal.source_id = ''
    const { createDeal } = useDealsActions(deps)

    await createDeal()

    expect(deps.apiPost).not.toHaveBeenCalled()
    expect(deps.dealError.value).toBe('Укажите источник')
  })

  it('createDealDraft allows empty required sale fields and sends draft status', async () => {
    const deps = createDeps()
    deps.newDeal.customer_nickname = ''
    deps.newDeal.source_id = ''
    deps.newDeal.region_code = ''
    deps.newDeal.price = 0
    const { createDealDraft } = useDealsActions(deps)

    await createDealDraft()

    expect(deps.apiPost).toHaveBeenCalledTimes(1)
    expect(deps.apiPost.mock.calls[0][1].flow_status_code).toBe('draft')
    expect(deps.dealError.value).toBeNull()
  })

  it('updateDeal allows zero price for sale', async () => {
    const deps = createDeps()
    deps.editDeal.price = 0
    const { updateDeal } = useDealsActions(deps)

    await updateDeal()

    expect(deps.apiPut).toHaveBeenCalledTimes(1)
    expect(deps.dealError.value).toBeNull()
  })

  it('updateDeal sends responsible and order number', async () => {
    const deps = createDeps()
    const { updateDeal } = useDealsActions(deps)

    await updateDeal()

    expect(deps.apiPut).toHaveBeenCalledTimes(1)
    expect(deps.apiPut.mock.calls[0][1].order_number).toBe('ORD-2')
    expect(deps.apiPut.mock.calls[0][1].login).toBe('edit-login')
    expect(deps.apiPut.mock.calls[0][1].password).toBe('edit-pass')
    expect(deps.apiPut.mock.calls[0][1].responsible_username).toBe('alice')
    expect(deps.apiPut.mock.calls[0][1].is_refund).toBe(false)
  })

  it('updateDeal sends manual created/completed dates for existing deal', async () => {
    const deps = createDeps()
    deps.editDeal.created_at = '2026-02-09T10:00'
    deps.editDeal.completed_at = '2026-02-09T11:30'
    const { updateDeal } = useDealsActions(deps)

    await updateDeal()

    expect(deps.apiPut).toHaveBeenCalledTimes(1)
    expect(deps.apiPut.mock.calls[0][1].created_at).toContain('2026-02-09T')
    expect(deps.apiPut.mock.calls[0][1].completed_at).toContain('2026-02-09T')
  })

  it('updateDealDraft allows empty required sale fields and sends draft status', async () => {
    const deps = createDeps()
    deps.editDeal.customer_nickname = ''
    deps.editDeal.source_id = ''
    deps.editDeal.region_code = ''
    deps.editDeal.price = 0
    const { updateDealDraft } = useDealsActions(deps)

    await updateDealDraft()

    expect(deps.apiPut).toHaveBeenCalledTimes(1)
    expect(deps.apiPut.mock.calls[0][1].flow_status_code).toBe('draft')
    expect(deps.dealError.value).toBeNull()
  })

  it('deleteDeal blocks non-draft deals on client', async () => {
    const deps = createDeps()
    const { deleteDeal } = useDealsActions(deps)

    await deleteDeal()

    expect(deps.apiDelete).not.toHaveBeenCalled()
    expect(deps.dealError.value).toBe('Удалить можно только черновик')
  })

  it('deleteDeal archives draft deal after confirmation', async () => {
    const deps = createDeps()
    deps.editDeal.flow_status_code = 'draft'
    const { deleteDeal } = useDealsActions(deps)

    await deleteDeal()

    expect(deps.requestDealConfirm).toHaveBeenCalledTimes(1)
    expect(deps.apiDelete).toHaveBeenCalledTimes(1)
    expect(deps.apiDelete).toHaveBeenCalledWith('/deals/1', { token: 'token' })
    expect(deps.closeDealModal).toHaveBeenCalledTimes(1)
  })

  it('markDealCompleted blocks refund completion for non-admin roles', async () => {
    const deps = createDeps({
      auth: { state: { token: 'token', user: 'tester', role: 'manager' } },
    })
    const { markDealCompleted } = useDealsActions(deps)

    await markDealCompleted({ deal_id: 10, is_refund: true })

    expect(deps.apiPut).not.toHaveBeenCalled()
    expect(deps.dealError.value).toBeNull()
    expect(deps.showDealWarning).toHaveBeenCalledWith('не достаточно прав для проведения возврата')
  })

  it('updateDeal blocks refund completion for non-admin roles', async () => {
    const deps = createDeps({
      auth: { state: { token: 'token', user: 'tester', role: 'manager' } },
    })
    deps.editDeal.is_refund = true
    deps.editDeal.flow_status_code = 'completed'
    const { updateDeal } = useDealsActions(deps)

    await updateDeal()

    expect(deps.apiPut).not.toHaveBeenCalled()
    expect(deps.dealError.value).toBeNull()
    expect(deps.showDealWarning).toHaveBeenCalledWith('не достаточно прав для проведения возврата')
  })

  it('markDealReturned calls return endpoint for completed sale', async () => {
    const deps = createDeps()
    const { markDealReturned } = useDealsActions(deps)

    await markDealReturned({ deal_id: 15, deal_type_code: 'sale', is_refund: false })

    expect(deps.apiPost).toHaveBeenCalledWith('/deals/15/return', {}, { token: 'token' })
    expect(deps.loadDeals).toHaveBeenCalledWith(1)
  })
})
