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
      duplicate_assignment_id: '',
      price: 0,
      purchase_cost: 0,
      login: '',
      password: '',
      product_link: '',
      purchase_at: '',
      slots_used: 1,
      notes: '',
      is_duplicate_flow: false,
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
      duplicate_assignment_id: '',
      price: 0,
      purchase_cost: 0,
      login: '',
      password: '',
      product_link: '',
      purchase_at: '',
      slots_used: 1,
      notes: '',
      flow_status_code: '',
      is_duplicate_flow: false,
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
    reopenAccountByIdFromDealReturn: vi.fn(),
    loadAccountForDealNavigation: vi.fn().mockImplementation(async (account_id) => ({ account_id, is_deactivated: true })),
    startEditAccount: vi.fn(),
    canOpenAccountFromDeal: vi.fn().mockReturnValue(true),
    isDealNavigationBlocked: vi.fn().mockReturnValue(false),
  }
}

describe('useDealModalFlow', () => {
  it('opens the actual account from a saved deal without returning to the former source', async () => {
    // Явный переход должен открыть аккаунт сделки, а не карточку, из которой её открыли раньше.
    const deps = createDeps()
    const api = useDealModalFlow(deps)
    await api.startEditDeal({ deal_id: 42, account_id: 9, deal_type_code: 'rental', flow_status_code: 'completed' },
      { returnTab: 'accounts', returnAccountId: 7 })
    expect(await api.openAccountFromDeal('edit')).toBe(true)
    expect(deps.loadAccountForDealNavigation).toHaveBeenCalledWith(9)
    expect(deps.startEditAccount).toHaveBeenCalledWith({ account_id: 9, is_deactivated: true }, { onClose: expect.any(Function) })
    expect(deps.setActiveTab).toHaveBeenLastCalledWith('accounts')
    expect(deps.reopenAccountByIdFromDealReturn).not.toHaveBeenCalled()
    expect(deps.editDeal.open).toBe(false)
    expect(deps.dealLoading.value).toBe(false)
    // Закрытие аккаунта возвращает ту же завершённую сделку и сохраняет её прежний маршрут назад.
    await deps.startEditAccount.mock.calls[0][1].onClose()
    expect(deps.editDeal.open).toBe(true)
    expect(deps.editDeal.deal_id).toBe(42)
    expect(deps.editDeal.account_id).toBe(9)
    expect(deps.editDeal.flow_status_code).toBe('completed')
    expect(deps.setActiveTab).toHaveBeenLastCalledWith('deals')
    await api.closeDealModal()
    expect(deps.reopenAccountByIdFromDealReturn).toHaveBeenCalledExactlyOnceWith(7)
  })

  it('returns to the saved deal without resurrecting discarded edits', async () => {
    // Подтверждённый сброс правок действует и после возврата из карточки аккаунта.
    const deps = createDeps()
    const api = useDealModalFlow(deps)
    await api.startEditDeal({ deal_id: 42, account_id: 9, deal_type_code: 'rental', lock_version: 3, notes: 'Сохранено' })
    api.toggleDealEditMode()
    deps.editDeal.notes = 'Несохранённое'
    await api.openAccountFromDeal()
    await deps.startEditAccount.mock.calls[0][1].onClose()
    expect(deps.editDeal.deal_id).toBe(42)
    expect(deps.editDeal.notes).toBe('Сохранено')
    expect(deps.editDeal.lock_version).toBe(3)
    expect(deps.dealEditMode.value).toBe('view')
    expect(deps.loadAccountSlotStatus).toHaveBeenLastCalledWith('edit')
  })

  it('keeps unsaved deal changes and return destination when navigation is cancelled', async () => {
    // Отказ подтверждения сохраняет и текст, и обычный путь возврата из сделки.
    const deps = createDeps()
    const api = useDealModalFlow(deps)
    await api.startEditDeal({ deal_id: 42, account_id: 9, deal_type_code: 'rental' },
      { returnTab: 'accounts', returnAccountId: 7 })
    api.toggleDealEditMode()
    deps.editDeal.notes = 'Несохранённая правка'
    deps.requestUnsavedConfirm.mockResolvedValueOnce(false).mockResolvedValue(true)
    expect(await api.openAccountFromDeal('edit')).toBe(false)
    expect(deps.editDeal.notes).toBe('Несохранённая правка')
    expect(deps.editDeal.open).toBe(true)
    expect(deps.startEditAccount).not.toHaveBeenCalled()
    await api.closeDealModal()
    expect(deps.reopenAccountByIdFromDealReturn).toHaveBeenCalledWith(7)
  })

  it('opens the selected account from a new deal after confirming unsaved changes', async () => {
    // Выбор аккаунта новой сделки не должен теряться без штатного подтверждения.
    const deps = createDeps()
    const api = useDealModalFlow(deps)
    api.openCreateSharingModal()
    deps.newDeal.account_id = 8
    deps.newDeal.notes = 'Новая сделка'
    expect(await api.openAccountFromDeal('new')).toBe(true)
    expect(deps.requestUnsavedConfirm).toHaveBeenCalled()
    expect(deps.startEditAccount).toHaveBeenCalledWith({ account_id: 8, is_deactivated: true }, { onClose: expect.any(Function) })
    expect(deps.showDealForm.value).toBe(false)
    await deps.startEditAccount.mock.calls[0][1].onClose()
    expect(deps.showDealForm.value).toBe(true)
    expect(deps.newDeal.deal_type_code).toBe('rental')
    expect(deps.newDeal.notes).toBe('')
    expect(deps.setActiveTab).toHaveBeenLastCalledWith('deals')
  })

  it('leaves the deal intact if account loading fails', async () => {
    // Ошибка API не закрывает исходную карточку и не предлагает отбросить её правки.
    const deps = createDeps()
    const api = useDealModalFlow(deps)
    await api.startEditDeal({ deal_id: 42, account_id: 9, deal_type_code: 'rental' })
    deps.loadAccountForDealNavigation.mockRejectedValue(new Error('offline'))
    expect(await api.openAccountFromDeal('edit')).toBe(false)
    expect(deps.editDeal.open).toBe(true)
    expect(deps.editDeal.account_id).toBe(9)
    expect(deps.startEditAccount).not.toHaveBeenCalled()
    expect(deps.requestUnsavedConfirm).not.toHaveBeenCalled()
    expect(deps.showDealWarning).toHaveBeenCalled()
    expect(deps.dealLoading.value).toBe(false)
  })

  it('ignores duplicate clicks and an outdated account response', async () => {
    // Поздний ответ не должен открыть прежний аккаунт после смены выбора.
    const deps = createDeps()
    const api = useDealModalFlow(deps)
    await api.startEditDeal({ deal_id: 42, account_id: 9, deal_type_code: 'rental' })
    let resolveAccount
    deps.loadAccountForDealNavigation.mockReturnValue(new Promise((resolve) => { resolveAccount = resolve }))
    const opening = api.openAccountFromDeal('edit')
    expect(await api.openAccountFromDeal('edit')).toBe(false)
    deps.editDeal.account_id = 10
    resolveAccount({ account_id: 9 })
    expect(await opening).toBe(false)
    expect(deps.loadAccountForDealNavigation).toHaveBeenCalledTimes(1)
    expect(deps.startEditAccount).not.toHaveBeenCalled()
    expect(deps.editDeal.open).toBe(true)
  })

  it.each(['permission', 'busy', 'no-account'])('does not navigate when blocked: %s', async (reason) => {
    // Проверка действует в обработчике, а не только через доступность кнопки.
    const deps = createDeps()
    const api = useDealModalFlow(deps)
    await api.startEditDeal({ deal_id: 42, account_id: 9, deal_type_code: 'rental' })
    if (reason === 'permission') deps.canOpenAccountFromDeal.mockReturnValue(false)
    if (reason === 'busy') deps.isDealNavigationBlocked.mockReturnValue(true)
    if (reason === 'no-account') deps.editDeal.account_id = ''
    expect(await api.openAccountFromDeal('edit')).toBe(false)
    expect(deps.loadAccountForDealNavigation).not.toHaveBeenCalled()
    expect(deps.startEditAccount).not.toHaveBeenCalled()
  })

  it('synchronizes supplier cost, version and baseline before the next edit and cancel', async () => {
    // После покупки отмена следующей правки возвращает новую сумму, а не старый снимок до оплаты.
    const deps = createDeps()
    const api = useDealModalFlow(deps)
    const deal = { deal_id: 42, deal_type_code: 'sale', region_code: 'TR', flow_status_code: 'pending', lock_version: 1, purchase_cost: 0 }
    await api.startEditDeal(deal)
    expect(api.syncSavedDealFromSupplier({ ...deal, lock_version: 2, purchase_cost: 475.04, notes: 'Сохранено' })).toBe(true)
    expect(deps.editDeal.lock_version).toBe(2)
    expect(deps.editDeal.purchase_cost).toBe(475.04)
    api.toggleDealEditMode()
    deps.editDeal.purchase_cost = 0
    deps.editDeal.notes = 'Правка'
    api.toggleDealEditMode()
    expect(deps.editDeal.deal_id).toBe(42)
    expect(deps.editDeal.lock_version).toBe(2)
    expect(deps.editDeal.purchase_cost).toBe(475.04)
    expect(deps.editDeal.notes).toBe('Сохранено')
    api.toggleDealEditMode()
    expect(await api.closeDealModal()).toBe(true)
    expect(deps.requestUnsavedConfirm).not.toHaveBeenCalled()
  })

  it('does not overwrite an editing form, another deal or a newer version', async () => {
    // Запоздалое чтение не меняет другую карточку и не подменяет локальные правки свежей версией.
    const deps = createDeps()
    const api = useDealModalFlow(deps)
    const deal = { deal_id: 42, deal_type_code: 'sale', lock_version: 3, purchase_cost: 950.08 }
    await api.startEditDeal(deal)
    expect(api.syncSavedDealFromSupplier({ ...deal, deal_id: 44, lock_version: 4 })).toBe(false)
    expect(api.syncSavedDealFromSupplier({ ...deal, lock_version: 2 })).toBe(false)
    api.toggleDealEditMode()
    deps.editDeal.notes = 'Не сохранено'
    expect(api.syncSavedDealFromSupplier({ ...deal, lock_version: 4, notes: 'Чужая правка' })).toBe(false)
    expect(deps.editDeal.notes).toBe('Не сохранено')
    expect(deps.editDeal.lock_version).toBe(3)
  })

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

  it('opens edit modal without waiting for heavy accounts preload', async () => {
    const deps = createDeps()
    let resolveAccountsAll
    deps.loadAccountsAll = vi.fn().mockImplementation(
      () => new Promise((resolve) => { resolveAccountsAll = resolve })
    )
    const api = useDealModalFlow(deps)

    const openPromise = api.startEditDeal({
      deal_id: 33,
      created_at: '2026-02-09T10:00:00Z',
      completed_at: '',
      deal_type_code: 'sale',
      account_id: 7,
      product_id: 55,
      customer_nickname: 'buyer',
      order_number: 'A-3',
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

    await openPromise

    expect(deps.loadAccountsAll).toHaveBeenCalledTimes(1)
    expect(deps.editDeal.open).toBe(true)
    expect(deps.dealLoading.value).toBe(false)
    resolveAccountsAll?.()
  })

  it('returns to source tab after closing deal opened from accounts', async () => {
    const deps = createDeps()
    const api = useDealModalFlow(deps)

    await api.startEditDeal(
      {
        deal_id: 44,
        created_at: '2026-02-09T10:00:00Z',
        completed_at: '',
        deal_type_code: 'sale',
        account_id: 7,
        product_id: 55,
        customer_nickname: 'buyer',
        order_number: 'A-4',
        source_id: 1,
        region_code: 'RU',
        slot_type_code: '',
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
      },
      { returnTab: 'accounts', returnAccountId: 7 },
    )

    const closed = await api.closeDealModal()
    expect(closed).toBe(true)
    expect(deps.setActiveTab).toHaveBeenNthCalledWith(1, 'deals')
    expect(deps.setActiveTab).toHaveBeenNthCalledWith(2, 'accounts')
    expect(deps.reopenAccountByIdFromDealReturn).toHaveBeenCalledWith(7)
  })

  it('keeps return tab even when closeAllModals triggers closeDealModal during opening', async () => {
    let api
    const deps = createDeps()
    deps.closeAllModals = vi.fn(() => {
      if (!api) return
      // Имитируем глобальное закрытие модалок, которое во WorkView вызывает closeDealModal.
      void api.closeDealModal()
    })
    api = useDealModalFlow(deps)

    await api.startEditDeal(
      {
        deal_id: 45,
        created_at: '2026-02-09T10:00:00Z',
        completed_at: '',
        deal_type_code: 'sale',
        account_id: 7,
        product_id: 55,
        customer_nickname: 'buyer',
        order_number: 'A-5',
        source_id: 1,
        region_code: 'RU',
        slot_type_code: '',
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
      },
      { returnTab: 'accounts', returnAccountId: 7 },
    )

    const closed = await api.closeDealModal()
    expect(closed).toBe(true)
    expect(deps.setActiveTab).toHaveBeenCalledWith('accounts')
    expect(deps.reopenAccountByIdFromDealReturn).toHaveBeenCalledWith(7)
  })
})
