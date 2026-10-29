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
    apiGet: vi.fn().mockImplementation(async (url) => url.endsWith('/authenticator-image') ? { image: '', version: '' } : url.endsWith('/secrets') || url.endsWith('/products') ? [] : { items: [], total: 0 }),
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
    accountFilters: reactive({ search_q: '', login_q: '', product_q: '', region_q: '', status_q: '', without_products: false, date_from: '', date_to: '' }),
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
  it('returns once to the source after closing an account', async () => {
    // Перед возвратом карточка уже закрыта; повторное закрытие не открывает старую сделку.
    const h = createHarness()
    const onClose = vi.fn(() => {
      expect(h.editAccount.open).toBe(false)
      expect(h.editAccount.account_id).toBeNull()
    })
    h.startEditAccount({ account_id: 5 }, { onClose })
    expect(await h.cancelEditAccount()).toBe(true)
    await h.cancelEditAccount()
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('keeps the return destination when account discard is cancelled', async () => {
    // Отказ закрыть несохранённый аккаунт не теряет путь обратно в сделку.
    const h = createHarness()
    const onClose = vi.fn()
    await h.startEditAccount({ account_id: 5, notes: 'Сохранено' }, { onClose })
    h.toggleAccountEditMode()
    h.editAccount.notes = 'Изменено'
    h.requestUnsavedConfirm.mockResolvedValueOnce(false).mockResolvedValueOnce(true)
    expect(await h.cancelEditAccount()).toBe(false)
    expect(h.editAccount.open).toBe(true)
    expect(onClose).not.toHaveBeenCalled()
    expect(await h.cancelEditAccount()).toBe(true)
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('does not return when another modal replaces the account', async () => {
    // Общий closeAllModals должен погасить возврат, чтобы не открыть две сделки одновременно.
    const h = createHarness()
    const onClose = vi.fn()
    h.startEditAccount({ account_id: 5 }, { onClose })
    await h.cancelEditAccount({ returnToSource: false })
    await h.cancelEditAccount()
    expect(onClose).not.toHaveBeenCalled()
    h.startEditAccount({ account_id: 5 }, { onClose })
    h.startEditAccount({ account_id: 9 })
    await h.cancelEditAccount()
    expect(onClose).not.toHaveBeenCalled()
  })

  it('returns to the source after saving account changes', async () => {
    // Успешное сохранение и крестик используют одинаковый путь закрытия карточки.
    const h = createHarness()
    const onClose = vi.fn()
    await h.startEditAccount({ account_id: 5, login_name: 'user', domain_code: 'mail.com', region_code: 'RU' }, { onClose })
    h.apiPut.mockResolvedValue({ ok: true })
    await h.updateAccount()
    expect(h.accountsError.value).toBeNull()
    expect(onClose).toHaveBeenCalledTimes(1)
    expect(h.editAccount.open).toBe(false)
  })

  it('loadAccounts sends without_products only when the quick filter is active', async () => {
    const h = createHarness()
    h.accountFilters.without_products = true
    h.apiGet.mockResolvedValueOnce({ total: 0, items: [] })

    await h.loadAccounts()

    expect(h.apiGet).toHaveBeenCalledWith(
      expect.stringContaining('without_products=true'),
      { token: 'token-1' },
    )
  })

  it('loadAccountProducts prefers /accounts/{id}/products', async () => {
    const h = createHarness()
    h.apiGet.mockResolvedValueOnce([{ product_id: 55, title: 'Game A' }, { product_id: 56, title: 'PS Plus до 09/04/27' }])

    await h.loadAccountProducts(5)

    expect(h.apiGet).toHaveBeenCalledTimes(1)
    expect(h.apiGet).toHaveBeenCalledWith('/accounts/5/products', { token: 'token-1' })
    expect(h.editAccount.product_ids).toEqual([55, 56])
    expect(h.editAccount.product_titles).toEqual(['Game A', 'PS Plus до 09/04/27'])
  })

  it('loadAccountProducts preserves known products on endpoint error', async () => {
    const h = createHarness()
    h.apiGet.mockRejectedValueOnce(new Error('404'))
    h.editAccount.product_ids = [55]

    expect(await h.loadAccountProducts(5)).toBe(false)

    expect(h.apiGet).toHaveBeenCalledTimes(1)
    expect(h.apiGet).toHaveBeenCalledWith('/accounts/5/products', { token: 'token-1' })
    expect(h.editAccount.product_ids).toEqual([55])
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
      if (url.endsWith('/authenticator-image')) return { image: '', version: '' }
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

  it('toggleAccountEditMode reverts unsaved changes on second click', async () => {
    const h = createHarness()
    await h.startEditAccount({
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
    h.editAccount.expected_reserves = { reserve1: 'r1', reserve2: 'r2' }
    h.apiPut.mockResolvedValue({ ok: true })
    h.suppressUnsavedConfirm.value = true

    await h.updateAccount()

    expect(h.apiPut).toHaveBeenCalledWith(
      '/accounts/5/secrets',
      {
        upserts: [
          { secret_key: 'account_password', secret_value: 'acc-pass' },
          { secret_key: 'auth_code', secret_value: 'auth-pass' },
        ],
        delete_keys: ['email_password'],
        reserve_values: ['r1'],
        expected_reserves: { reserve1: 'r1', reserve2: 'r2' },
      },
      { token: 'token-1' }
    )
  })

  it('sends replaced and reordered values with the original identity snapshot', async () => {
    // Новый код нельзя отправлять как перезапись старой занятой ячейки.
    const h = createHarness()
    Object.assign(h.editAccount, {
      login_name: 'user', domain_code: 'mail.com', region_code: 'RU',
      reserve_text: 'B NEW', existing_reserve_keys: ['reserve1', 'reserve2'],
      expected_reserves: { reserve1: 'OLD', reserve2: 'B' },
    })
    h.apiPut.mockResolvedValue({ ok: true })
    h.suppressUnsavedConfirm.value = true
    await h.updateAccount()
    expect(h.apiPut).toHaveBeenCalledWith('/accounts/5/secrets', expect.objectContaining({
      reserve_values: ['B', 'NEW'], expected_reserves: { reserve1: 'OLD', reserve2: 'B' },
    }), { token: 'token-1' })
    const payload = h.apiPut.mock.calls.find(([url]) => url.endsWith('/secrets'))[1]
    expect(payload.upserts.some((item) => item.secret_key.startsWith('reserve'))).toBe(false)
  })

  it('updateAccount refreshes account secrets cache after save', async () => {
    const h = createHarness()
    h.editAccount.login_name = 'user'
    h.editAccount.domain_code = 'mail.com'
    h.editAccount.region_code = 'RU'
    h.editAccount.reserve_text = ''
    h.editAccount.existing_reserve_keys = ['reserve1']
    h.editAccount.expected_reserves = { reserve1: 'old' }
    h.editAccount.has_account = false
    h.editAccount.has_email = false
    h.editAccount.has_auth = false
    h.accountSecrets.value = {
      5: [{ secret_key: 'reserve1', secret_value_b64: 'b2xk' }],
    }
    h.apiPut.mockResolvedValue({ ok: true })
    h.apiGet.mockImplementation(async (url) => {
      if (url.endsWith('/authenticator-image')) return { image: '', version: '' }
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
  it('saves only deactivation when a completed deal removed a reserve after opening', async () => {
    // Устаревшие резервы, пароли и товары не мешают изменить только деактивацию.
    const h = createHarness()
    h.accountSecrets.value[5] = [{ secret_key: 'reserve1', secret_value_b64: btoa('OLD') }]
    h.apiGet.mockImplementation(async (url) => {
      if (url.endsWith('/authenticator-image')) return { image: '', version: '' }
      if (url.endsWith('/secrets')) return [
        { secret_key: 'reserve2', secret_value_b64: btoa('LIVE') },
        { secret_key: 'account_password', secret_value_b64: btoa('password') },
      ]
      if (url.endsWith('/products')) return [{ product_id: 7 }]
      return { items: [], total: 0 }
    })
    await h.startEditAccount({ account_id: 5, login_name: 'user', domain_code: 'mail.com' })
    expect(h.editAccount.expected_reserves).toEqual({ reserve2: 'LIVE' })
    h.toggleAccountEditMode()
    h.editAccount.is_deactivated = true
    h.apiPut.mockImplementation(async (url) => {
      if (url.endsWith('/authenticator-image')) return { image: '', version: '' }
      if (url.endsWith('/secrets')) throw new Error('Резервы изменились. Откройте аккаунт заново.')
      return { ok: true }
    })
    await h.updateAccount()
    expect(h.apiPut.mock.calls).toEqual([['/accounts/5', { is_deactivated: true }, { token: 'token-1' }]])
    expect(h.accountsError.value).toBeNull()
    expect(h.editAccount.open).toBe(false)
  })

  it('does not replace reserves for whitespace or order changes', async () => {
    // Постоянные ID не зависят от порядка строк, пробелы не требуют записи списка.
    const h = createHarness()
    h.apiGet.mockImplementation(async (url) => url.endsWith('/authenticator-image') ? { image: '', version: '' } : [
      { secret_key: 'reserve1', secret_value_b64: btoa('A') },
      { secret_key: 'reserve2', secret_value_b64: btoa('B') },
    ])
    await h.startEditAccount({ account_id: 5, login_name: 'user', domain_code: 'mail.com' })
    h.toggleAccountEditMode()
    h.editAccount.reserve_text = ' B\n A  '
    await h.updateAccount()
    expect(h.apiPut).not.toHaveBeenCalled()
  })

  it.each(['new-password', ''])('writes only the edited password, value=%s', async (password) => {
    // Изменение или удаление пароля не отправляет соседние секреты и резервы.
    const h = createHarness()
    h.apiGet.mockImplementation(async (url) => url.endsWith('/authenticator-image') ? { image: '', version: '' } : url.endsWith('/secrets') ? [
      { secret_key: 'account_password', secret_value_b64: btoa('old-password') },
      { secret_key: 'email_password', secret_value_b64: btoa('email-password') },
      { secret_key: 'reserve1', secret_value_b64: btoa('A') },
    ] : [])
    await h.startEditAccount({ account_id: 5, login_name: 'user', domain_code: 'mail.com' })
    h.toggleAccountEditMode()
    h.editAccount.account_password = password
    await h.updateAccount()
    expect(h.apiPut.mock.calls).toEqual([['/accounts/5/secrets', {
      upserts: password ? [{ secret_key: 'account_password', secret_value: password }] : [],
      delete_keys: password ? [] : ['account_password'],
    }, { token: 'token-1' }]])
  })

  it.each(['NEW', ''])('keeps conflict protection for a real reserve edit, value=%s', async (value) => {
    // Замена и очистка требуют исходного снимка; конфликт не повторяется автоматически.
    const h = createHarness()
    h.apiGet.mockImplementation(async (url) => url.endsWith('/authenticator-image') ? { image: '', version: '' } : url.endsWith('/secrets')
      ? [{ secret_key: 'reserve9', secret_value_b64: btoa('OLD') }] : [])
    await h.startEditAccount({ account_id: 5, login_name: 'user', domain_code: 'mail.com' })
    h.toggleAccountEditMode()
    h.editAccount.reserve_text = value
    h.apiPut.mockRejectedValue(new Error('Резервы изменились. Откройте аккаунт заново.'))
    await h.updateAccount()
    expect(h.apiPut).toHaveBeenCalledExactlyOnceWith('/accounts/5/secrets', {
      upserts: [], delete_keys: [], reserve_values: value ? [value] : [], expected_reserves: { reserve9: 'OLD' },
    }, { token: 'token-1' })
    expect(h.editAccount.reserve_text).toBe(value)
    expect(h.editAccount.open).toBe(true)
    expect(h.accountsError.value).toContain('Резервы изменились')
  })

  it('preserves cache on a failed reload and retries an initially failed request', async () => {
    // Ошибка сети не становится пустым списком, блокирующим следующие загрузки.
    const h = createHarness()
    const known = [{ secret_key: 'reserve1', secret_value_b64: btoa('A') }]
    h.accountSecrets.value[5] = known
    h.apiGet.mockRejectedValue(new Error('offline'))
    expect(await h.ensureAccountSecretsLoaded(5, true)).toBe(false)
    expect(h.accountSecrets.value[5]).toEqual(known)
    expect(await h.ensureAccountSecretsLoaded(9)).toBe(false)
    expect(h.accountSecrets.value).not.toHaveProperty('9')
    h.apiGet.mockResolvedValue([])
    expect(await h.ensureAccountSecretsLoaded(9)).toBe(true)
    expect(h.accountSecrets.value[9]).toEqual([])
  })

  it('ignores an old secret response that arrives after a newer reload', async () => {
    // Медленный старый запрос не возвращает уже удалённый код в общий кеш.
    const h = createHarness()
    const older = createDeferred()
    const newer = createDeferred()
    h.apiGet.mockReturnValueOnce(older.promise).mockReturnValueOnce(newer.promise)
    const first = h.ensureAccountSecretsLoaded(5, true)
    const second = h.ensureAccountSecretsLoaded(5, true)
    newer.resolve([])
    await second
    older.resolve([{ secret_key: 'reserve1', secret_value_b64: btoa('DELETED') }])
    expect(await first).toBe(true)
    expect(h.accountSecrets.value[5]).toEqual([])
  })

  it('blocks editing and saving until fresh account details have loaded', async () => {
    // Быстрый клик не отправляет пустые поля до ответа сервера.
    const h = createHarness()
    const pending = createDeferred()
    h.apiGet.mockImplementation(async (url) => url.endsWith('/authenticator-image') ? { image: '', version: '' } : url.endsWith('/secrets') ? pending.promise : [])
    const opening = h.startEditAccount({ account_id: 5, login_name: 'user', domain_code: 'mail.com' })
    h.toggleAccountEditMode()
    await h.updateAccount()
    expect(h.accountEditMode.value).toBe('view')
    expect(h.apiPut).not.toHaveBeenCalled()
    pending.resolve([])
    await opening
    h.toggleAccountEditMode()
    expect(h.accountEditMode.value).toBe('edit')
  })

  it.each(['secrets', 'products'])('blocks saving after failed %s loading and recovers on refresh', async (endpoint) => {
    // Неизвестный список секретов или товаров нельзя отправлять как намеренную очистку.
    const h = createHarness()
    h.apiGet.mockImplementation(async (url) => {
      if (url.endsWith('/authenticator-image')) return { image: '', version: '' }
      if (url.endsWith(`/${endpoint}`)) throw new Error('offline')
      return []
    })
    await h.startEditAccount({ account_id: 5, login_name: 'user', domain_code: 'mail.com' })
    expect(h.editAccount.details_load_failed).toBe(true)
    await h.updateAccount()
    expect(h.apiPut).not.toHaveBeenCalled()
    h.apiGet.mockImplementation(async (url) => {
      if (url.endsWith('/authenticator-image')) return { image: '', version: '' }
      if (url.startsWith('/accounts?')) return { items: [{ account_id: 5, login_name: 'user', domain_code: 'mail.com' }] }
      return []
    })
    await h.refreshOpenAccountFromDb()
    expect(h.editAccount.details_load_failed).toBe(false)
    h.toggleAccountEditMode()
    expect(h.accountEditMode.value).toBe('edit')
  })

  it('does not apply a response from a previous opening of the same account', async () => {
    // Закрытие и повторное открытие одного ID не дают старому ответу сбросить правки.
    const h = createHarness()
    const pending = createDeferred()
    let secretReads = 0
    h.apiGet.mockImplementation(async (url) => {
      if (url.endsWith('/authenticator-image')) return { image: '', version: '' }
      if (url.endsWith('/secrets')) return ++secretReads === 1 ? pending.promise : []
      return []
    })
    const first = h.startEditAccount({ account_id: 5, login_name: 'user', domain_code: 'mail.com' })
    await h.cancelEditAccount()
    await h.startEditAccount({ account_id: 5, login_name: 'user', domain_code: 'mail.com' })
    h.toggleAccountEditMode()
    h.editAccount.reserve_text = 'MY-EDIT'
    pending.resolve([{ secret_key: 'reserve1', secret_value_b64: btoa('OLD') }])
    await first
    expect(h.editAccount.reserve_text).toBe('MY-EDIT')
    expect(h.editAccount.expected_reserves).toEqual({})
  })

  it('does not refresh over unsaved edits even if the handler is called directly', async () => {
    // Защита работает и вне кнопки, которая недоступна при редактировании.
    const h = createHarness()
    await h.startEditAccount({ account_id: 5, login_name: 'user', domain_code: 'mail.com' })
    h.toggleAccountEditMode()
    h.editAccount.reserve_text = 'MY-EDIT'
    h.apiGet.mockClear()
    await h.refreshOpenAccountFromDb()
    expect(h.apiGet).not.toHaveBeenCalled()
    expect(h.editAccount.reserve_text).toBe('MY-EDIT')
  })

  it('rebases saved reserves before retrying a failed products update', async () => {
    // Повтор сохранения после частичного сбоя не отправляет собственный устаревший снимок.
    const h = createHarness()
    let secrets = [{ secret_key: 'reserve1', secret_value_b64: btoa('OLD') }]
    h.apiGet.mockImplementation(async (url) => url.endsWith('/authenticator-image') ? { image: '', version: '' } : url.endsWith('/secrets') ? secrets : [])
    await h.startEditAccount({ account_id: 5, login_name: 'user', domain_code: 'mail.com' })
    h.toggleAccountEditMode()
    h.editAccount.reserve_text = 'NEW'
    h.editAccount.product_ids = [7]
    h.apiPut.mockImplementation(async (url) => {
      if (url.endsWith('/authenticator-image')) return { image: '', version: '' }
      if (url.endsWith('/secrets')) {
        secrets = [{ secret_key: 'reserve2', secret_value_b64: btoa('NEW') }]
        return {}
      }
      throw new Error('products unavailable')
    })
    await h.updateAccount()
    expect(h.accountsError.value).toContain('Часть изменений уже сохранена')
    expect(h.editAccount.expected_reserves).toEqual({ reserve2: 'NEW' })
    h.apiPut.mockReset().mockResolvedValue({})
    await h.updateAccount()
    expect(h.apiPut).toHaveBeenCalledExactlyOnceWith('/accounts/5/products', { product_ids: [7] }, { token: 'token-1' })
    expect(h.editAccount.open).toBe(false)
  })

  it('stops a save chain when another account replaces its editor', async () => {
    // После смены карточки оставшиеся запросы не отправляются с новым account_id.
    const h = createHarness()
    await h.startEditAccount({ account_id: 5, login_name: 'user', domain_code: 'mail.com' })
    h.toggleAccountEditMode()
    h.editAccount.notes = 'changed'
    h.editAccount.reserve_text = 'NEW'
    const pending = createDeferred()
    h.apiPut.mockReturnValue(pending.promise)
    const saving = h.updateAccount()
    await h.startEditAccount({ account_id: 9, login_name: 'another', domain_code: 'mail.com' })
    pending.resolve({})
    await saving
    expect(h.apiPut).toHaveBeenCalledExactlyOnceWith('/accounts/5', { notes: 'changed' }, { token: 'token-1' })
    expect(h.editAccount.account_id).toBe(9)
    expect(h.editAccount.open).toBe(true)
  })

  it('loads account navigation through the shared fresh secrets cache', async () => {
    // Открытие из сделки не обходит защиту общего кеша отдельной записью.
    const h = createHarness()
    h.accountSecrets.value[5] = [{ secret_key: 'reserve1', secret_value_b64: btoa('OLD') }]
    h.apiGet.mockImplementation(async (url) => url.endsWith('/authenticator-image') ? { image: '', version: '' } : url.endsWith('/secrets') ? [] : { account_id: 5 })
    expect(await h.loadAccountForDealNavigation(5)).toEqual({ account_id: 5 })
    expect(h.accountSecrets.value[5]).toEqual([])
  })

  it('rejects navigation when fresh secrets cannot be loaded', async () => {
    // Ошибка оставляет исходную сделку открытой через существующий обработчик перехода.
    const h = createHarness()
    h.apiGet.mockImplementation(async (url) => {
      if (url.endsWith('/authenticator-image')) return { image: '', version: '' }
      if (url.endsWith('/secrets')) throw new Error('offline')
      return { account_id: 5 }
    })
    await expect(h.loadAccountForDealNavigation(5)).rejects.toThrow('Не удалось загрузить данные аккаунта')
  })

  it.each(['data:image/png;base64,NEW', ''])('saves an image edit with its original version: %s', async (image) => {
    // Замена и удаление QR не требуют перезаписи резервов или других секретов.
    const h = createHarness()
    let server = { image: 'data:image/png;base64,OLD', version: 'v1' }
    h.apiGet.mockImplementation(async (url) => url.endsWith('/authenticator-image') ? server : [])
    await h.startEditAccount({ account_id: 5, login_name: 'user', domain_code: 'mail.com' })
    expect(h.editAccount.authenticator_image).toBe(server.image)
    h.toggleAccountEditMode()
    h.editAccount.authenticator_image = image
    h.apiPut.mockImplementation(async () => { server = { image, version: 'v2' } })
    await h.updateAccount()
    expect(h.apiPut).toHaveBeenCalledExactlyOnceWith('/accounts/5/secrets', {
      upserts: [], delete_keys: [], authenticator_image: image, expected_authenticator_image_version: 'v1',
    }, { token: 'token-1' })
  })

  it('does not resend an unchanged image while saving a comment', async () => {
    // Картинка другого сотрудника не может быть затёрта обычным сохранением заметки.
    const h = createHarness()
    h.apiGet.mockImplementation(async (url) => url.endsWith('/authenticator-image') ? { image: 'data:image/png;base64,OLD', version: 'v1' } : [])
    await h.startEditAccount({ account_id: 5, login_name: 'user', domain_code: 'mail.com' })
    h.toggleAccountEditMode()
    h.editAccount.notes = 'comment'
    await h.updateAccount()
    expect(h.apiPut).toHaveBeenCalledExactlyOnceWith('/accounts/5', { notes: 'comment' }, { token: 'token-1' })
  })

  it('reverts image edits and confirms closing a changed image', async () => {
    // QR участвует в обычной отмене редактирования и защите несохранённых изменений.
    const h = createHarness()
    await h.startEditAccount({ account_id: 5, login_name: 'user', domain_code: 'mail.com' })
    h.toggleAccountEditMode()
    h.editAccount.authenticator_image = 'data:image/png;base64,NEW'
    h.requestUnsavedConfirm.mockResolvedValue(false)
    expect(await h.cancelEditAccount()).toBe(false)
    h.toggleAccountEditMode()
    expect(h.editAccount.authenticator_image).toBe('')
  })

  it('blocks saving when the image has not loaded or its file is still being read', async () => {
    // Сетевая ошибка не превращает сохранённый QR в намеренное удаление.
    const h = createHarness()
    h.apiGet.mockImplementation(async (url) => {
      if (url.endsWith('/authenticator-image')) throw new Error('offline')
      return []
    })
    await h.startEditAccount({ account_id: 5, login_name: 'user', domain_code: 'mail.com' })
    await h.updateAccount()
    expect(h.editAccount.details_load_failed).toBe(true)
    expect(h.apiPut).not.toHaveBeenCalled()
    h.editAccount.details_load_failed = false
    h.editAccount.authenticator_image_loading = true
    await h.updateAccount()
    expect(h.apiPut).not.toHaveBeenCalled()
  })

  it('creates an account with a QR instead of a text authenticator code', async () => {
    // Изображение может заменить ручной код, остальные обязательные поля остаются прежними.
    const h = createHarness()
    h.openCreateAccountModal()
    Object.assign(h.newAccount, { login_name: 'user', domain_code: 'mail.com', region_code: 'RU', account_date: '2026-10-28', email_password: 'email', account_password: 'password', authenticator_image: 'data:image/png;base64,QR' })
    h.apiPost.mockResolvedValue({ account_id: 9 })
    await h.createAccount()
    expect(h.apiPut).toHaveBeenCalledWith('/accounts/9/secrets', expect.objectContaining({ authenticator_image: 'data:image/png;base64,QR', expected_authenticator_image_version: '' }), { token: 'token-1' })
    expect(h.newAccount.authenticator_image).toBe('')
  })

  it('does not warn about unsaved changes in an untouched new account form', async () => {
    // Служебный флаг чтения файла не делает пустую форму изменённой.
    const h = createHarness()
    h.openCreateAccountModal()
    expect(await h.cancelEditAccount()).toBe(true)
    expect(h.requestUnsavedConfirm).not.toHaveBeenCalled()
  })

})
