import { describe, it, expect, vi } from 'vitest'
import { reactive, ref } from 'vue'

import { useAccountsFlow } from '../useAccountsFlow.js'

function createDeferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

function createHarness() {
  const h = {
    auth: { state: reactive({ token: 'token-1' }) },
    apiGet: vi.fn(),
    apiPost: vi.fn(),
    apiPut: vi.fn(),
    apiDelete: vi.fn(),
    mapApiError: (m) => {
      const text = String(m || '')
      if (text.includes('Account already exists')) return 'Данный аккаунт уже есть в базе данных'
      return text || 'error'
    },
    resolveAccountSort: () => ({ key: 'login', dir: 'asc' }),
    closeAllModals: vi.fn(),
    resetModalPos: vi.fn(),
    accountModalMode: ref('edit'),
    accountEditMode: ref('view'),
    editAccount: reactive({ open: true, account_id: 5, product_ids: [] }),
    newAccount: reactive({ product_ids: [] }),
    accountProductSearch: ref(''),
    editAccountProductSearch: ref(''),
    accountProductType: ref(''),
    editAccountProductType: ref(''),
    quickNewAccountProduct: reactive({ title: '', platform_codes: [] }),
    quickNewAccountProductLoading: ref(false),
    quickNewAccountProductError: ref(''),
    quickEditAccountProduct: reactive({ title: '', platform_codes: [] }),
    quickEditAccountProductLoading: ref(false),
    quickEditAccountProductError: ref(''),
    loadProductsAll: vi.fn().mockResolvedValue(undefined),
    accountProductsLoading: ref(false),
    accountDeals: ref([]),
    accountDealsError: ref(null),
    accountDealsLoading: ref(false),
    accountSlotAssignments: ref([]),
    accountSlotAssignmentsError: ref(null),
    accountSlotAssignmentsLoading: ref(false),
    accounts: ref([]),
    accountsAll: ref([]),
    accountsTotal: ref(0),
    accountsPage: ref(1),
    accountsPageSize: ref(20),
    accountFilters: reactive({ search_q: '', login_q: '', product_q: '', region_q: '', status_q: '', date_from: '', date_to: '' }),
    accountSort: ref('login_asc'),
    accountSecrets: ref({}),
    accountsError: ref(null),
    accountsOk: ref(null),
    accountsLoading: ref(false),
    accountSaving: ref(false),
    loadAccountSlotAssignments: vi.fn(),
    suppressUnsavedConfirm: ref(false),
    requestUnsavedConfirm: vi.fn(),
    requestDealConfirm: vi.fn(),
    showDealWarning: vi.fn(),
  }
  const flow = useAccountsFlow(h)
  return { ...h, ...flow }
}

describe('useAccountsFlow', () => {
  it('loadAccountProducts prefers /accounts/{id}/products', async () => {
    const h = createHarness()
    h.apiGet.mockResolvedValueOnce([{ product_id: 55, title: 'Game A' }, { product_id: 56, title: 'PS Plus до 09/04/27' }])

    await h.loadAccountProducts(5)

    expect(h.apiGet).toHaveBeenCalledTimes(1)
    expect(h.apiGet).toHaveBeenCalledWith('/accounts/5/products', { token: 'token-1' })
    expect(h.editAccount.product_ids).toEqual([55, 56])
    expect(h.editAccount.product_titles).toEqual(['Game A', 'PS Plus до 09/04/27'])
  })

  it('loadAccountProducts returns empty list on products endpoint error', async () => {
    const h = createHarness()
    h.apiGet.mockRejectedValueOnce(new Error('404'))

    await h.loadAccountProducts(5)

    expect(h.apiGet).toHaveBeenCalledTimes(1)
    expect(h.apiGet).toHaveBeenCalledWith('/accounts/5/products', { token: 'token-1' })
    expect(h.editAccount.product_ids).toEqual([])
  })

  it('loadAccountsAll supports lightweight labels lookup by id list', async () => {
    const h = createHarness()
    h.accountsAll.value = [{ account_id: 5, login_full: 'old@old.com', notes: 'keep' }]
    h.apiGet.mockResolvedValueOnce([
      { account_id: 5, login_name: 'acc5', domain_code: 'mail.com', login_full: 'acc5@mail.com' },
      { account_id: 9, login_name: 'acc9', domain_code: 'mail.com', login_full: 'acc9@mail.com' },
    ])

    await h.loadAccountsAll([5, 9, 9, 0])

    expect(h.apiGet).toHaveBeenCalledWith('/accounts/labels?account_id=5&account_id=9', { token: 'token-1' })
    expect(h.accountsAll.value).toEqual([
      { account_id: 5, login_full: 'acc5@mail.com', notes: 'keep', login_name: 'acc5', domain_code: 'mail.com' },
      { account_id: 9, login_name: 'acc9', domain_code: 'mail.com', login_full: 'acc9@mail.com' },
    ])
  })

  it('openCreateAccountModal sets product type filter to game', () => {
    const h = createHarness()
    h.accountProductType.value = 'subscription'

    h.openCreateAccountModal()

    expect(h.accountProductType.value).toBe('game')
  })

  it('createQuickAccountProduct creates product by selected type and links it to new account', async () => {
    const h = createHarness()
    h.quickNewAccountProduct.title = 'PS Plus Extra'
    h.quickNewAccountProduct.platform_codes = ['ps5']
    h.newAccount.product_ids = [10]
    h.apiPost.mockResolvedValueOnce({ product_id: 77 })

    await h.createQuickAccountProduct('subscription')

    expect(h.apiPost).toHaveBeenCalledWith(
      '/products',
      expect.objectContaining({
        type_code: 'subscription',
        title: 'PS Plus Extra',
        platform_codes: ['ps5'],
      }),
      { token: 'token-1' }
    )
    expect(h.loadProductsAll).toHaveBeenCalledTimes(1)
    expect(h.newAccount.product_ids).toEqual([77])
    expect(h.quickNewAccountProduct.title).toBe('')
    expect(h.quickNewAccountProduct.platform_codes).toEqual([])
  })

  it('createAccount creates subscription term for created account in subscription mode', async () => {
    const h = createHarness()
    h.openCreateAccountModal()
    h.accountProductType.value = 'subscription'
    h.newAccount.login_name = 'sub-user'
    h.newAccount.domain_code = 'mail.com'
    h.newAccount.region_code = 'RU'
    h.newAccount.account_date = '2026-03-26'
    h.newAccount.account_password = 'acc-pass'
    h.newAccount.email_password = 'mail-pass'
    h.newAccount.auth_code = 'auth-code'
    h.newAccount.product_ids = [77]
    h.newAccount.subscription_valid_until = '2027-03-26'
    h.apiPost.mockImplementation(async (url) => {
      if (url === '/accounts') return { account_id: 9 }
      return {}
    })
    h.apiPut.mockResolvedValue({})

    await h.createAccount()

    expect(h.apiPut).toHaveBeenCalledWith(
      '/accounts/9/secrets',
      expect.objectContaining({
        upserts: expect.arrayContaining([
          { secret_key: 'email_password', secret_value: 'mail-pass' },
          { secret_key: 'account_password', secret_value: 'acc-pass' },
          { secret_key: 'auth_code', secret_value: 'auth-code' },
        ]),
      }),
      { token: 'token-1' }
    )
    expect(h.apiPost).toHaveBeenCalledWith(
      '/products/subscriptions/77/terms',
      { account_id: 9, valid_until: '2027-03-26', notes: null },
      { token: 'token-1' }
    )
  })

  it('createQuickAccountProduct supports edit target and links product to edited account', async () => {
    const h = createHarness()
    h.quickEditAccountProduct.title = 'EA FC 26'
    h.quickEditAccountProduct.platform_codes = ['ps5']
    h.editAccount.product_ids = [44]
    h.apiPost.mockResolvedValueOnce({ product_id: 88 })

    await h.createQuickAccountProduct('game', 'edit')

    expect(h.editAccount.product_ids).toEqual([44, 88])
    expect(h.quickEditAccountProduct.title).toBe('')
    expect(h.quickEditAccountProduct.platform_codes).toEqual([])
  })

  it('toggleAccountEditMode reverts unsaved changes on second click', () => {
    const h = createHarness()
    h.startEditAccount({
      account_id: 5,
      login_name: 'user',
      domain_code: 'mail.com',
      region_code: 'RU',
      notes: 'note',
      account_date: '2025-01-01',
      status: 'active',
    })

    h.toggleAccountEditMode()
    expect(h.accountEditMode.value).toBe('edit')

    h.editAccount.login_name = 'changed'
    h.editAccount.notes = 'changed note'

    h.toggleAccountEditMode()
    expect(h.accountEditMode.value).toBe('view')
    expect(h.editAccount.login_name).toBe('user')
    expect(h.editAccount.notes).toBe('note')
  })

  it('createAccount duplicate shows warning modal text instead of inline error', async () => {
    const h = createHarness()
    h.openCreateAccountModal()
    h.newAccount.login_name = 'dup'
    h.newAccount.domain_code = 'mail.com'
    h.newAccount.region_code = 'RU'
    h.newAccount.account_date = '2026-03-04'
    h.newAccount.account_password = 'acc-pass'
    h.newAccount.email_password = 'mail-pass'
    h.newAccount.auth_code = 'auth-code'
    h.apiPost.mockRejectedValueOnce(new Error('Account already exists'))

    await h.createAccount()

    expect(h.showDealWarning).toHaveBeenCalledWith('Данный аккаунт уже есть в базе данных')
    expect(h.accountsError.value).toBeNull()
  })

  it('createAccount requires all main fields in create form', async () => {
    const h = createHarness()
    h.openCreateAccountModal()
    h.newAccount.login_name = 'user'
    h.newAccount.domain_code = 'mail.com'

    await h.createAccount()

    expect(h.apiPost).not.toHaveBeenCalled()
    expect(h.accountsError.value).toContain('Заполните обязательные поля')
    expect(h.accountsError.value).toContain('Регион')
    expect(h.accountsError.value).toContain('Дата')
    expect(h.accountsError.value).toContain('Пароль аккаунта')
    expect(h.accountsError.value).toContain('Пароль почты')
    expect(h.accountsError.value).toContain('Код аутентификатора')
  })

  it('updateAccount sends deactivation flag to backend', async () => {
    const h = createHarness()
    h.editAccount.login_name = 'user'
    h.editAccount.domain_code = 'mail.com'
    h.editAccount.region_code = 'RU'
    h.editAccount.is_deactivated = true
    h.apiPut.mockResolvedValue({ ok: true })
    h.suppressUnsavedConfirm.value = true

    await h.updateAccount()

    expect(h.apiPut).toHaveBeenCalledWith(
      '/accounts/5',
      expect.objectContaining({ is_deactivated: true }),
      { token: 'token-1' }
    )
  })

  it('updateAccount updates secrets atomically via batch endpoint', async () => {
    const h = createHarness()
    h.editAccount.login_name = 'user'
    h.editAccount.domain_code = 'mail.com'
    h.editAccount.region_code = 'RU'
    h.editAccount.email_password = ''
    h.editAccount.email_key = 'email_password'
    h.editAccount.has_email = true
    h.editAccount.account_password = 'acc-pass'
    h.editAccount.account_key = 'account_password'
    h.editAccount.has_account = true
    h.editAccount.auth_code = 'auth-pass'
    h.editAccount.auth_key = 'auth_code'
    h.editAccount.has_auth = true
    h.editAccount.reserve_text = 'r1'
    h.editAccount.existing_reserve_keys = ['reserve1', 'reserve2']
    h.apiPut.mockResolvedValue({ ok: true })
    h.suppressUnsavedConfirm.value = true

    await h.updateAccount()

    expect(h.apiPut).toHaveBeenCalledWith(
      '/accounts/5/secrets',
      {
        upserts: [
          { secret_key: 'account_password', secret_value: 'acc-pass' },
          { secret_key: 'auth_code', secret_value: 'auth-pass' },
          { secret_key: 'reserve1', secret_value: 'r1' },
        ],
        delete_keys: ['email_password', 'reserve2'],
      },
      { token: 'token-1' }
    )
  })

  it('updateAccount refreshes account secrets cache after save', async () => {
    const h = createHarness()
    h.editAccount.login_name = 'user'
    h.editAccount.domain_code = 'mail.com'
    h.editAccount.region_code = 'RU'
    h.editAccount.reserve_text = ''
    h.editAccount.existing_reserve_keys = ['reserve1']
    h.editAccount.has_account = false
    h.editAccount.has_email = false
    h.editAccount.has_auth = false
    h.accountSecrets.value = {
      5: [{ secret_key: 'reserve1', secret_value_b64: 'b2xk' }],
    }
    h.apiPut.mockResolvedValue({ ok: true })
    h.apiGet.mockImplementation(async (url) => {
      if (url === '/accounts/5/secrets') {
        return [{ secret_key: 'reserve2', secret_value_b64: 'bmV3' }]
      }
      return { items: [], total: 0 }
    })
    h.suppressUnsavedConfirm.value = true

    await h.updateAccount()

    expect(h.apiGet).toHaveBeenCalledWith('/accounts/5/secrets', { token: 'token-1' })
    expect(h.accountSecrets.value[5]).toEqual([{ secret_key: 'reserve2', secret_value_b64: 'bmV3' }])
  })

  it('loadAccountProducts ignores stale response after account switch', async () => {
    const h = createHarness()
    const first = createDeferred()
    const second = createDeferred()
    h.apiGet
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise)

    h.editAccount.account_id = 5
    const requestA = h.loadAccountProducts(5)
    h.editAccount.account_id = 9
    const requestB = h.loadAccountProducts(9)

    second.resolve([{ product_id: 99, title: 'Second Product' }])
    await requestB
    first.resolve([{ product_id: 55, title: 'First Product' }])
    await requestA

    expect(h.editAccount.product_ids).toEqual([99])
    expect(h.editAccount.product_titles).toEqual(['Second Product'])
  })

  it('loadAccounts ignores stale list response', async () => {
    const h = createHarness()
    const first = createDeferred()
    const second = createDeferred()
    h.apiGet
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise)
    h.apiPost.mockResolvedValue([])

    const requestA = h.loadAccounts()
    const requestB = h.loadAccounts()
    second.resolve({ items: [{ account_id: 2, login_name: 'new' }], total: 1 })
    await requestB
    first.resolve({ items: [{ account_id: 1, login_name: 'old' }], total: 1 })
    await requestA

    expect(h.accounts.value).toEqual([{ account_id: 2, login_name: 'new' }])
    expect(h.accountsTotal.value).toBe(1)
  })
})
