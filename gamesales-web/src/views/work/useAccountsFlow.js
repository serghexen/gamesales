import { confirmDiscardIfNeeded, isSameNormalized } from './unsavedChanges'

export function useAccountsFlow({
  auth,
  apiGet,
  apiPost,
  apiPut,
  apiDelete,
  mapApiError,
  resolveAccountSort,
  closeAllModals,
  resetModalPos,
  accountModalMode,
  accountEditMode,
  editAccount,
  newAccount,
  accountProductSearch,
  editAccountProductSearch,
  accountProductType,
  editAccountProductType,
  accountProductsLoading,
  accountDeals,
  accountDealsError,
  accountDealsLoading,
  accountSlotAssignments,
  accountSlotAssignmentsError,
  accountSlotAssignmentsLoading,
  accounts,
  accountsAll,
  accountsTotal,
  accountsPage,
  accountsPageSize,
  accountFilters,
  accountSort,
  accountSecrets,
  accountsError,
  accountsOk,
  accountsLoading,
  accountSaving,
  loadAccountSlotAssignments,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
  requestDealConfirm,
  showDealWarning,
  canDoAction,
  quickNewAccountProduct,
  quickNewAccountProductLoading,
  quickNewAccountProductError,
  quickEditAccountProduct,
  quickEditAccountProductLoading,
  quickEditAccountProductError,
  loadProductsAll,
}) {
  // Проверяет action-право для аккаунтов; в старых тестах без функции считаем действие разрешенным.
  const canUseAccountAction = (actionCode) => {
    if (typeof canDoAction !== 'function') return true
    return canDoAction(actionCode)
  }

  // Возвращает дефолтную дату срока подписки: сегодня + 1 год.
  function getDefaultSubscriptionTermDate() {
    const nextYearDate = new Date()
    nextYearDate.setFullYear(nextYearDate.getFullYear() + 1)
    const year = nextYearDate.getFullYear()
    const month = String(nextYearDate.getMonth() + 1).padStart(2, '0')
    const day = String(nextYearDate.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  // Проверяет обязательные поля при создании аккаунта и возвращает их человекочитаемые названия.
  function getMissingCreateAccountFields() {
    const missing = []
    if (!String(newAccount.login_name || '').trim()) missing.push('Логин')
    if (!String(newAccount.domain_code || '').trim()) missing.push('Домен')
    if (!String(newAccount.region_code || '').trim()) missing.push('Регион')
    if (!String(newAccount.account_date || '').trim()) missing.push('Дата')
    if (canUseAccountAction('accounts.reflect_account_password') && !String(newAccount.account_password || '').trim()) missing.push('Пароль аккаунта')
    if (canUseAccountAction('accounts.reflect_email_password') && !String(newAccount.email_password || '').trim()) missing.push('Пароль почты')
    if (canUseAccountAction('accounts.reflect_auth_code') && !String(newAccount.auth_code || '').trim()) missing.push('Код аутентификатора')
    return missing
  }

  let initialEditAccountSnapshot = null
  let accountDealsRequestSeq = 0
  let accountsRequestSeq = 0
  let accountsAllRequestSeq = 0
  let accountProductsRequestSeq = 0

  // Сравнивает account_id как число, чтобы корректно мержить строки и числа.
  function isSameAccountId(leftId, rightId) {
    const leftNum = Number(leftId)
    const rightNum = Number(rightId)
    if (Number.isFinite(leftNum) && Number.isFinite(rightNum)) return leftNum === rightNum
    return String(leftId || '').trim() === String(rightId || '').trim()
  }

  // Определяет кратковременный сетевой сбой, который можно безопасно повторить.
  function isTransientFetchError(error) {
    const text = String(error?.message || '').toLowerCase()
    return text.includes('failed to fetch') || text.includes('networkerror')
  }

  // Делает короткую паузу перед повтором запроса, чтобы снизить шанс ложной ошибки.
  async function sleep(ms) {
    await new Promise((resolve) => setTimeout(resolve, ms))
  }

  // Раскодирует base64-строку с учетом UTF-8.
  function decodeSecret(value) {
    try {
      const binary = atob(value)
      const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0))
      return new TextDecoder().decode(bytes)
    } catch {
      return ''
    }
  }

  // Нормализует ключ резерва к формату reserveN для единой обработки во всех блоках UI.
  function normalizeReserveKey(value) {
    const raw = String(value || '').trim().toLowerCase()
    if (!/^reserve\d+$/.test(raw)) return ''
    return `reserve${Number(raw.replace('reserve', ''))}`
  }

  // Сравнивает ключи reserveN по числовому номеру, чтобы порядок был предсказуемым.
  function compareReserveKeys(leftKey, rightKey) {
    const leftNum = Number(String(leftKey || '').replace('reserve', '')) || 0
    const rightNum = Number(String(rightKey || '').replace('reserve', '')) || 0
    return leftNum - rightNum
  }

  // Достает пароль почты для аккаунта.
  function getEmailSecret(accountId) {
    const list = accountSecrets.value[accountId] || []
    const item = list.find((s) => s.secret_key === 'email_password')
    return item?.secret_value_b64 ? decodeSecret(item.secret_value_b64) : ''
  }

  // Достает основной пароль аккаунта.
  function getAccountSecret(accountId) {
    const list = accountSecrets.value[accountId] || []
    const item = list.find((s) => s.secret_key === 'account_password' || s.secret_key === 'primary' || s.secret_key === 'password')
    return item?.secret_value_b64 ? decodeSecret(item.secret_value_b64) : ''
  }

  // Склеивает резервные пароли в одну строку для отображения.
  function getReserveSecrets(accountId) {
    const reserves = getReserveSecretEntries(accountId)
    return reserves.map((item) => item.value).filter(Boolean).join(' ')
  }

  // Возвращает резервы аккаунта как список пар key/value, отсортированных по номеру reserveN.
  function getReserveSecretEntries(accountId) {
    const list = accountSecrets.value[accountId] || []
    return list
      .filter((s) => /^reserve\d+$/i.test(String(s.secret_key || '').trim()))
      .map((s) => ({
        key: normalizeReserveKey(s.secret_key),
        value: s.secret_value_b64 ? decodeSecret(s.secret_value_b64).trim() : '',
      }))
      .filter((item) => item.key && item.value)
      .sort((a, b) => compareReserveKeys(a.key, b.key))
  }

  // Достает код/секрет для входа (2FA/код).
  function getAuthSecret(accountId) {
    const list = accountSecrets.value[accountId] || []
    const item = list.find((s) => s.secret_key === 'auth_code')
    return item?.secret_value_b64 ? decodeSecret(item.secret_value_b64) : ''
  }

  // Догружает секреты для одного аккаунта, если их еще нет в локальном кеше.
  async function ensureAccountSecretsLoaded(accountId, forceReload = false) {
    const targetId = Number(accountId || 0)
    if (!targetId) return
    if (!forceReload && Object.prototype.hasOwnProperty.call(accountSecrets.value || {}, targetId)) return
    try {
      const secrets = await apiGet(`/accounts/${targetId}/secrets`, { token: auth.state.token })
      accountSecrets.value = {
        ...(accountSecrets.value || {}),
        [targetId]: secrets || [],
      }
    } catch {
      // Даже при ошибке фиксируем пустой список, чтобы не спамить повторными запросами.
      accountSecrets.value = {
        ...(accountSecrets.value || {}),
        [targetId]: [],
      }
    }
  }

  // Фиксирует текущее состояние карточки как эталон "без изменений" для режима просмотра.
  function syncInitialEditAccountSnapshot() {
    initialEditAccountSnapshot = {
      login_name: editAccount.login_name,
      domain_code: editAccount.domain_code,
      region_code: editAccount.region_code,
      status_code: editAccount.status_code,
      is_deactivated: editAccount.is_deactivated,
      deactivated_at: editAccount.deactivated_at,
      next_activation_at: editAccount.next_activation_at,
      notes: editAccount.notes,
      account_date: editAccount.account_date,
      email_password: editAccount.email_password,
      account_password: editAccount.account_password,
      auth_code: editAccount.auth_code,
      reserve_text: editAccount.reserve_text,
      product_ids: [...(editAccount.product_ids || [])],
    }
  }

  // Подставляет секреты из кеша в открытую карточку аккаунта.
  function applyCachedSecretsToEditAccount(accountId) {
    const targetId = Number(accountId || 0)
    if (!targetId || Number(editAccount.account_id || 0) !== targetId) return
    const secrets = accountSecrets.value[targetId] || []
    const email = secrets.find((s) => s.secret_key === 'email_password')
    const account = secrets.find((s) => s.secret_key === 'account_password' || s.secret_key === 'primary' || s.secret_key === 'password')
    const authSecret = secrets.find((s) => s.secret_key === 'auth_code')
    const reserveEntries = getReserveSecretEntries(targetId)
    editAccount.email_password = email?.secret_value_b64 ? decodeSecret(email.secret_value_b64) : ''
    editAccount.email_key = email?.secret_key || 'email_password'
    editAccount.account_password = account?.secret_value_b64 ? decodeSecret(account.secret_value_b64) : ''
    editAccount.account_key = account?.secret_key || 'account_password'
    editAccount.auth_code = authSecret?.secret_value_b64 ? decodeSecret(authSecret.secret_value_b64) : ''
    editAccount.auth_key = authSecret?.secret_key || 'auth_code'
    // Держим текст и список ключей в одном и том же порядке, чтобы не переименовывать резервы при сохранении.
    editAccount.reserve_text = reserveEntries.map((item) => item.value).join(' ')
    editAccount.existing_reserve_keys = reserveEntries.map((item) => item.key)
    editAccount.has_account = Boolean(account)
    editAccount.has_email = Boolean(email)
    editAccount.has_auth = Boolean(authSecret)
  }

  // Загружает товары, привязанные к аккаунту.
  async function loadAccountProducts(accountId) {
    const requestId = ++accountProductsRequestSeq
    accountProductsLoading.value = true
    try {
      // Используем только новый product endpoint для привязок аккаунта.
      const items = await apiGet(`/accounts/${accountId}/products`, { token: auth.state.token })
      // Применяем ответ только если это последний запрос и карточка все еще открыта на тот же аккаунт.
      if (requestId !== accountProductsRequestSeq || Number(editAccount?.account_id || 0) !== Number(accountId || 0)) return
      editAccount.product_ids = [...new Set((items || []).map((p) => Number(p?.product_id || 0)).filter(Boolean))]
      // Доверяем API: backend уже возвращает подписки с датами, если они есть.
      editAccount.product_titles = [...new Set((items || []).map((p) => String(p?.title || '').trim()).filter(Boolean))]
    } catch {
      if (requestId !== accountProductsRequestSeq || Number(editAccount?.account_id || 0) !== Number(accountId || 0)) return
      editAccount.product_ids = []
      editAccount.product_titles = []
    } finally {
      if (requestId === accountProductsRequestSeq) {
        accountProductsLoading.value = false
      }
    }
  }

  // Загружает список аккаунтов с фильтрами/сортировкой/пагинацией.
  async function loadAccounts() {
    const requestId = ++accountsRequestSeq
    accountsLoading.value = true
    accountsError.value = null
    accountsOk.value = null
    try {
      const params = new URLSearchParams()
      if (accountFilters.search_q) params.set('q', accountFilters.search_q)
      if (accountFilters.login_q) params.set('login_q', accountFilters.login_q)
      // Передаем фильтр товара через product_q.
      if (accountFilters.product_q) params.set('product_q', accountFilters.product_q)
      if (accountFilters.region_q) params.set('region_q', accountFilters.region_q)
      if (accountFilters.status_q) params.set('status_q', accountFilters.status_q)
      if (accountFilters.date_from) params.set('date_from', accountFilters.date_from)
      if (accountFilters.date_to) params.set('date_to', accountFilters.date_to)
      const sort = resolveAccountSort(accountSort.value)
      params.set('sort_key', sort.key)
      params.set('sort_dir', sort.dir)
      params.set('page', String(accountsPage.value))
      params.set('page_size', String(accountsPageSize.value))
      const data = await apiGet(`/accounts?${params.toString()}`, { token: auth.state.token })
      if (requestId !== accountsRequestSeq) return
      const items = data?.items || []
      accounts.value = items
      accountsTotal.value = Number(data?.total || 0)
    } catch (e) {
      if (requestId !== accountsRequestSeq) return
      accountsError.value = mapApiError(e?.message)
      accountsTotal.value = 0
    } finally {
      if (requestId === accountsRequestSeq) {
        accountsLoading.value = false
      }
    }
  }

  // Загружает справочник аккаунтов: полный список или легкий lookup по account_id.
  async function loadAccountsAll(accountIds = null) {
    const normalizedIds = Array.isArray(accountIds)
      ? [...new Set(accountIds.map((id) => Number(id || 0)).filter((id) => id > 0))]
      : []
    if (normalizedIds.length) {
      try {
        const params = new URLSearchParams()
        normalizedIds.forEach((id) => params.append('account_id', String(id)))
        const labels = await apiGet(`/accounts/labels?${params.toString()}`, { token: auth.state.token })
        const current = Array.isArray(accountsAll.value) ? [...accountsAll.value] : []
        for (const item of (Array.isArray(labels) ? labels : [])) {
          const targetId = Number(item?.account_id || 0)
          if (!targetId) continue
          const foundIndex = current.findIndex((row) => isSameAccountId(row?.account_id, targetId))
          const merged = {
            ...(foundIndex >= 0 ? current[foundIndex] : {}),
            account_id: targetId,
            login_name: String(item?.login_name || '').trim() || null,
            domain_code: String(item?.domain_code || '').trim() || null,
            login_full: String(item?.login_full || '').trim() || String(targetId),
          }
          if (foundIndex >= 0) current[foundIndex] = merged
          else current.push(merged)
        }
        accountsAll.value = current
      } catch {
        // На сетевом сбое сохраняем прошлый кеш подписей аккаунтов.
      }
      return
    }
    const requestId = ++accountsAllRequestSeq
    try {
      const params = new URLSearchParams()
      params.set('all', 'true')
      params.set('sort_key', 'login')
      params.set('sort_dir', 'asc')
      const data = await apiGet(`/accounts?${params.toString()}`, { token: auth.state.token })
      if (requestId !== accountsAllRequestSeq) return
      accountsAll.value = data?.items || []
    } catch {
      if (requestId !== accountsAllRequestSeq) return
      // На сетевом сбое сохраняем прошлый список, чтобы UI не скатывался к показу account_id.
    }
  }

  // Загружает сделки по конкретному аккаунту.
  async function loadAccountDeals(accountId) {
    const requestId = ++accountDealsRequestSeq
    accountDealsLoading.value = true
    accountDealsError.value = null
    try {
      const params = new URLSearchParams()
      params.set('account_id', String(accountId))
      params.set('page', '1')
      params.set('page_size', '200')
      let res
      try {
        res = await apiGet(`/deals?${params.toString()}`, { token: auth.state.token })
      } catch (e) {
        if (!isTransientFetchError(e)) throw e
        await sleep(250)
        res = await apiGet(`/deals?${params.toString()}`, { token: auth.state.token })
      }
      // Не затираем карточку данными от старого запроса, если пользователь уже переключился.
      if (requestId !== accountDealsRequestSeq || Number(editAccount?.account_id || 0) !== Number(accountId || 0)) return
      accountDeals.value = res?.items || []
    } catch (e) {
      if (requestId !== accountDealsRequestSeq || Number(editAccount?.account_id || 0) !== Number(accountId || 0)) return
      accountDealsError.value = mapApiError(e?.message)
      accountDeals.value = []
    } finally {
      if (requestId === accountDealsRequestSeq) {
        accountDealsLoading.value = false
      }
    }
  }

  // Открывает модалку аккаунта в режиме просмотра.
  function startEditAccount(a) {
    closeAllModals()
    resetModalPos()
    accountModalMode.value = 'edit'
    accountEditMode.value = 'view'
    editAccount.open = true
    editAccount.account_id = a.account_id
    editAccount.login_name = a.login_name || ''
    editAccount.domain_code = a.domain_code || ''
    editAccount.region_code = a.region_code || ''
    editAccount.status_code = a.status || 'active'
    // Сохраняем даты деактивации из API, чтобы модалка могла показать таймер до активации.
    editAccount.is_deactivated = Boolean(a.is_deactivated)
    editAccount.deactivated_at = a.deactivated_at || ''
    editAccount.next_activation_at = a.next_activation_at || ''
    editAccount.notes = a.notes || ''
    editAccount.account_date = a.account_date || ''

    // Сначала показываем то, что уже есть в локальном кеше.
    applyCachedSecretsToEditAccount(a.account_id)
    // Если кеша нет, тихо догружаем и обновляем поля без повторного открытия карточки.
    ensureAccountSecretsLoaded(a.account_id).then(() => {
      if (editAccount.open && Number(editAccount.account_id || 0) === Number(a.account_id || 0)) {
        applyCachedSecretsToEditAccount(a.account_id)
      }
    })
    editAccountProductType.value = 'game'
    quickEditAccountProduct.title = ''
    quickEditAccountProduct.platform_codes = []
    quickEditAccountProductError.value = ''
    syncInitialEditAccountSnapshot()
    loadAccountProducts(a.account_id).finally(() => {
      if (editAccount.open && accountEditMode.value === 'view') syncInitialEditAccountSnapshot()
    })
    loadAccountDeals(a.account_id)
    loadAccountSlotAssignments(a.account_id)
  }

  // Перезагружает текущую карточку аккаунта с сервера, чтобы подтянуть изменения из других вкладок.
  async function refreshOpenAccountFromDb() {
    const targetId = Number(editAccount.account_id || 0)
    if (!targetId || accountModalMode.value !== 'edit') return
    const isSameOpenedAccount = () => editAccount.open && Number(editAccount.account_id || 0) === targetId
    accountsError.value = null
    accountsOk.value = null
    accountsLoading.value = true
    try {
      const [accountsData] = await Promise.all([
        apiGet('/accounts?all=true&sort_key=login&sort_dir=asc', { token: auth.state.token }),
        loadAccountsAll([targetId]),
        ensureAccountSecretsLoaded(targetId, true),
        loadAccountProducts(targetId),
        loadAccountDeals(targetId),
        loadAccountSlotAssignments(targetId),
      ])
      if (!isSameOpenedAccount()) return
      const list = Array.isArray(accountsData?.items) ? accountsData.items : []
      const freshAccount = list.find((item) => isSameAccountId(item?.account_id, targetId))
      if (freshAccount) {
        editAccount.login_name = freshAccount.login_name || ''
        editAccount.domain_code = freshAccount.domain_code || ''
        editAccount.region_code = freshAccount.region_code || ''
        editAccount.status_code = freshAccount.status || 'active'
        editAccount.is_deactivated = Boolean(freshAccount.is_deactivated)
        editAccount.deactivated_at = freshAccount.deactivated_at || ''
        editAccount.next_activation_at = freshAccount.next_activation_at || ''
        editAccount.notes = freshAccount.notes || ''
        editAccount.account_date = freshAccount.account_date || ''
      }
      applyCachedSecretsToEditAccount(targetId)
      if (accountEditMode.value === 'view') {
        syncInitialEditAccountSnapshot()
      }
      accountsOk.value = 'Данные аккаунта обновлены'
    } catch (e) {
      if (!isSameOpenedAccount()) return
      accountsError.value = mapApiError(e?.message)
    } finally {
      accountsLoading.value = false
    }
  }

  // Открывает модалку создания нового аккаунта.
  function openCreateAccountModal() {
    closeAllModals()
    resetModalPos()
    accountModalMode.value = 'create'
    accountEditMode.value = 'edit'
    editAccount.open = true
    accountProductsLoading.value = false
    accountsError.value = null
    accountsOk.value = null
    newAccount.login_name = ''
    newAccount.domain_code = ''
    newAccount.region_code = ''
    newAccount.notes = ''
    newAccount.account_date = ''
    newAccount.email_password = ''
    newAccount.account_password = ''
    newAccount.reserve_text = ''
    newAccount.auth_code = ''
    newAccount.product_ids = []
    newAccount.subscription_valid_until = getDefaultSubscriptionTermDate()
    accountProductSearch.value = ''
    // Тип товара в форме создания всегда начинаем с игр.
    accountProductType.value = 'game'
    quickNewAccountProduct.title = ''
    quickNewAccountProduct.platform_codes = []
    quickNewAccountProductError.value = ''
    quickEditAccountProduct.title = ''
    quickEditAccountProduct.platform_codes = []
    quickEditAccountProductError.value = ''
    initialEditAccountSnapshot = null
  }

  // Переключает режим просмотра/редактирования и при возврате в просмотр откатывает несохраненные поля.
  function toggleAccountEditMode() {
    if (accountModalMode.value !== 'edit') return
    if (accountEditMode.value === 'edit') {
      const snapshot = initialEditAccountSnapshot || {}
      editAccount.login_name = snapshot.login_name || ''
      editAccount.domain_code = snapshot.domain_code || ''
      editAccount.region_code = snapshot.region_code || ''
      editAccount.status_code = snapshot.status_code || 'active'
      editAccount.is_deactivated = Boolean(snapshot.is_deactivated)
      editAccount.deactivated_at = snapshot.deactivated_at || ''
      editAccount.next_activation_at = snapshot.next_activation_at || ''
      editAccount.notes = snapshot.notes || ''
      editAccount.account_date = snapshot.account_date || ''
      editAccount.email_password = snapshot.email_password || ''
      editAccount.account_password = snapshot.account_password || ''
      editAccount.auth_code = snapshot.auth_code || ''
      editAccount.reserve_text = snapshot.reserve_text || ''
      editAccount.product_ids = [...(snapshot.product_ids || [])]
      accountEditMode.value = 'view'
      editAccountProductSearch.value = ''
      editAccountProductType.value = 'game'
      return
    }
    accountEditMode.value = 'edit'
  }

  async function cancelEditAccount() {
    const guardEnabled = !suppressUnsavedConfirm?.value
    const createDirty = accountModalMode.value === 'create' && isSameNormalized(newAccount, {
      login_name: '',
      domain_code: '',
      region_code: '',
      notes: '',
      account_date: '',
      email_password: '',
      account_password: '',
      reserve_text: '',
      auth_code: '',
      product_ids: [],
      subscription_valid_until: getDefaultSubscriptionTermDate(),
    }) === false
    const editCurrent = {
      login_name: editAccount.login_name,
      domain_code: editAccount.domain_code,
      region_code: editAccount.region_code,
      status_code: editAccount.status_code,
      is_deactivated: editAccount.is_deactivated,
      deactivated_at: editAccount.deactivated_at,
      next_activation_at: editAccount.next_activation_at,
      notes: editAccount.notes,
      account_date: editAccount.account_date,
      email_password: editAccount.email_password,
      account_password: editAccount.account_password,
      auth_code: editAccount.auth_code,
      reserve_text: editAccount.reserve_text,
      product_ids: [...(editAccount.product_ids || [])],
    }
    const editDirty = accountModalMode.value === 'edit' && accountEditMode.value === 'edit' && !isSameNormalized(editCurrent, initialEditAccountSnapshot || {})
    if (guardEnabled && !(await confirmDiscardIfNeeded(createDirty || editDirty, { requestConfirm: requestUnsavedConfirm }))) return false

    editAccount.open = false
    accountModalMode.value = 'edit'
    editAccount.account_id = null
    editAccount.login_name = ''
    editAccount.domain_code = ''
    editAccount.region_code = ''
    editAccount.status_code = 'active'
    editAccount.is_deactivated = false
    editAccount.deactivated_at = ''
    editAccount.next_activation_at = ''
    editAccount.notes = ''
    editAccount.account_date = ''
    editAccount.email_password = ''
    editAccount.email_key = 'email_password'
    editAccount.account_password = ''
    editAccount.account_key = 'account_password'
    editAccount.auth_code = ''
    editAccount.auth_key = 'auth_code'
    editAccount.reserve_text = ''
    editAccount.existing_reserve_keys = []
    editAccount.has_account = false
    editAccount.has_email = false
    editAccount.has_auth = false
    editAccount.product_ids = []
    editAccount.product_titles = []
    editAccountProductSearch.value = ''
    editAccountProductType.value = 'game'
    accountDeals.value = []
    accountDealsError.value = null
    accountDealsLoading.value = false
    accountSlotAssignments.value = []
    accountSlotAssignmentsError.value = null
    accountSlotAssignmentsLoading.value = false
    accountEditMode.value = 'view'
    newAccount.login_name = ''
    newAccount.domain_code = ''
    newAccount.region_code = ''
    newAccount.notes = ''
    newAccount.account_date = ''
    newAccount.email_password = ''
    newAccount.account_password = ''
    newAccount.reserve_text = ''
    newAccount.auth_code = ''
    newAccount.product_ids = []
    newAccount.subscription_valid_until = getDefaultSubscriptionTermDate()
    accountProductSearch.value = ''
    accountProductType.value = 'game'
    quickNewAccountProduct.title = ''
    quickNewAccountProduct.platform_codes = []
    quickNewAccountProductError.value = ''
    quickEditAccountProduct.title = ''
    quickEditAccountProduct.platform_codes = []
    quickEditAccountProductError.value = ''
    initialEditAccountSnapshot = null
    return true
  }

  // Возвращает refs нужной формы (создание/редактирование) для быстрого создания товара.
  function resolveQuickAccountProductRefs(target = 'new') {
    if (target === 'edit') {
      return {
        state: quickEditAccountProduct,
        loading: quickEditAccountProductLoading,
        error: quickEditAccountProductError,
        selectedIds: editAccount.product_ids || [],
        setSelectedIds: (ids) => { editAccount.product_ids = ids },
      }
    }
    return {
      state: quickNewAccountProduct,
      loading: quickNewAccountProductLoading,
      error: quickNewAccountProductError,
      selectedIds: newAccount.product_ids || [],
      setSelectedIds: (ids) => { newAccount.product_ids = ids },
    }
  }

  // Быстро создает товар из формы создания аккаунта и сразу подставляет его в выбранные.
  async function createQuickAccountProduct(typeCode = 'game', target = 'new') {
    const refs = resolveQuickAccountProductRefs(target)
    refs.error.value = ''
    const normalizedType = String(typeCode || '').trim().toLowerCase() === 'subscription' ? 'subscription' : 'game'
    if (!String(refs.state.title || '').trim()) {
      refs.error.value = 'Укажите название товара'
      return
    }
    if (!Array.isArray(refs.state.platform_codes) || !refs.state.platform_codes.length) {
      refs.error.value = 'Выберите платформу'
      return
    }
    refs.loading.value = true
    try {
      const created = await apiPost(
        '/products',
        {
          type_code: normalizedType,
          title: String(refs.state.title || '').trim(),
          platform_codes: refs.state.platform_codes,
          short_title: null,
          link: null,
          text_lang: null,
          audio_lang: null,
          vr_support: null,
          region_code: null,
        },
        { token: auth.state.token }
      )
      await loadProductsAll()
      const createdId = Number(created?.product_id || 0)
      if (createdId) {
        // Для подписки в создании аккаунта держим один выбранный товар, чтобы срок создавался однозначно.
        if (normalizedType === 'subscription' && target === 'new') {
          refs.setSelectedIds([createdId])
        } else {
          refs.setSelectedIds([...new Set([...(refs.selectedIds || []), createdId])])
        }
      }
      accountProductSearch.value = ''
      editAccountProductSearch.value = ''
      refs.state.title = ''
      refs.state.platform_codes = []
    } catch (e) {
      refs.error.value = mapApiError(e?.message)
    } finally {
      refs.loading.value = false
    }
  }

  async function createAccount() {
    accountsError.value = null
    accountsOk.value = null
    // На форме создания требуем заполнение всех основных полей карточки аккаунта.
    const missingFields = getMissingCreateAccountFields()
    if (missingFields.length) {
      accountsError.value = `Заполните обязательные поля: ${missingFields.join(', ')}`
      return
    }
    const isCreateSubscriptionMode = String(accountProductType.value || '').trim().toLowerCase() === 'subscription'
    const subscriptionProductId = Number((newAccount.product_ids || [])[0] || 0)
    const subscriptionValidUntil = String(newAccount.subscription_valid_until || '').trim()
    if (isCreateSubscriptionMode && !subscriptionProductId) {
      accountsError.value = 'Для подписки сначала создайте товар'
      return
    }
    if (isCreateSubscriptionMode && !subscriptionValidUntil) {
      accountsError.value = 'Для подписки укажите дату срока'
      return
    }
    accountsLoading.value = true
    try {
      const created = await apiPost(
        '/accounts',
        {
          region_code: newAccount.region_code || null,
          login_name: newAccount.login_name || null,
          domain_code: newAccount.domain_code || null,
          notes: newAccount.notes || null,
          account_date: newAccount.account_date || null,
        },
        { token: auth.state.token }
      )

      // Готовим пачку секретов и сохраняем ее атомарно одним запросом.
      const secretUpserts = []
      if (canUseAccountAction('accounts.reflect_email_password') && newAccount.email_password) {
        secretUpserts.push({ secret_key: 'email_password', secret_value: newAccount.email_password })
      }
      if (canUseAccountAction('accounts.reflect_account_password') && newAccount.account_password) {
        secretUpserts.push({ secret_key: 'account_password', secret_value: newAccount.account_password })
      }
      if (canUseAccountAction('accounts.reflect_auth_code') && newAccount.auth_code) {
        secretUpserts.push({ secret_key: 'auth_code', secret_value: newAccount.auth_code })
      }
      if (canUseAccountAction('accounts.reflect_reserves')) {
        const reserveValues = (newAccount.reserve_text || '')
          .split(/\s+/)
          .map((v) => v.trim())
          .filter(Boolean)
        reserveValues.forEach((val, idx) => {
          secretUpserts.push({ secret_key: `reserve${idx + 1}`, secret_value: val })
        })
      }
      if (secretUpserts.length) {
        await apiPut(
          `/accounts/${created.account_id}/secrets`,
          { upserts: secretUpserts, delete_keys: [] },
          { token: auth.state.token }
        )
      }

      if (canUseAccountAction('accounts.reflect_slots') && newAccount.product_ids.length) {
        await apiPut(
          `/accounts/${created.account_id}/products`,
          { product_ids: newAccount.product_ids },
          { token: auth.state.token }
        )
      }
      if (canUseAccountAction('accounts.reflect_slots') && isCreateSubscriptionMode && subscriptionProductId && subscriptionValidUntil) {
        try {
          await apiPost(
            `/products/subscriptions/${encodeURIComponent(subscriptionProductId)}/terms`,
            { account_id: created.account_id, valid_until: subscriptionValidUntil, notes: null },
            { token: auth.state.token }
          )
        } catch (e) {
          // Не откатываем создание аккаунта: показываем, что срок подписки не добавился.
          if (typeof showDealWarning === 'function') {
            showDealWarning(`Аккаунт создан, но срок подписки не добавлен: ${mapApiError(e?.message)}`)
          }
        }
      }

      accountsOk.value = `Аккаунт ${newAccount.login_name}@${newAccount.domain_code} создан`
      newAccount.login_name = ''
      newAccount.domain_code = ''
      newAccount.region_code = ''
      newAccount.notes = ''
      newAccount.account_date = ''
      newAccount.email_password = ''
      newAccount.account_password = ''
      newAccount.reserve_text = ''
      newAccount.auth_code = ''
      newAccount.product_ids = []
      newAccount.subscription_valid_until = getDefaultSubscriptionTermDate()
      accountProductSearch.value = ''
      accountProductType.value = 'game'
      quickNewAccountProduct.title = ''
      quickNewAccountProduct.platform_codes = []
      quickNewAccountProductError.value = ''
      quickEditAccountProduct.title = ''
      quickEditAccountProduct.platform_codes = []
      quickEditAccountProductError.value = ''
      // После успешного сохранения закрываем модалку без повторного confirm о несохраненных правках.
      if (suppressUnsavedConfirm) suppressUnsavedConfirm.value = true
      try {
        await cancelEditAccount()
      } finally {
        if (suppressUnsavedConfirm) suppressUnsavedConfirm.value = false
      }
      // Обновляем списки уже после закрытия модалки, чтобы сетевые задержки не мешали UX.
      await Promise.allSettled([loadAccounts(), loadAccountsAll()])
    } catch (e) {
      const mappedError = mapApiError(e?.message)
      // Для дубликата логина показываем фирменное предупреждение, а не inline-ошибку.
      if (mappedError === 'Данный аккаунт уже есть в базе данных' && typeof showDealWarning === 'function') {
        showDealWarning(mappedError)
        accountsError.value = null
      } else {
        accountsError.value = mappedError
      }
    } finally {
      accountsLoading.value = false
    }
  }

  async function updateAccount() {
    accountsError.value = null
    accountsOk.value = null
    if (!editAccount.account_id) return
    if (!editAccount.login_name || !editAccount.domain_code) {
      accountsError.value = 'Укажите логин и домен'
      return
    }
    accountSaving.value = true
    try {
      await apiPut(
        `/accounts/${editAccount.account_id}`,
        {
          region_code: editAccount.region_code || null,
          login_name: editAccount.login_name || null,
          domain_code: editAccount.domain_code || null,
          notes: editAccount.notes || null,
          account_date: editAccount.account_date || null,
          status_code: editAccount.status_code || 'active',
          // Передаем флаг деактивации отдельным полем: backend сам валидирует правило 183 дней.
          is_deactivated: Boolean(editAccount.is_deactivated),
        },
        { token: auth.state.token }
      )

      // Секреты сохраняем одной операцией, чтобы исключить частичное обновление при сетевой ошибке.
      const secretUpserts = []
      const secretDeleteKeys = []
      if (canUseAccountAction('accounts.reflect_email_password') && editAccount.email_password) {
        secretUpserts.push({
          secret_key: editAccount.email_key || 'email_password',
          secret_value: editAccount.email_password,
        })
      } else if (canUseAccountAction('accounts.reflect_email_password') && editAccount.has_email) {
        secretDeleteKeys.push(editAccount.email_key || 'email_password')
      }

      if (canUseAccountAction('accounts.reflect_account_password') && editAccount.account_password) {
        secretUpserts.push({
          secret_key: editAccount.account_key || 'account_password',
          secret_value: editAccount.account_password,
        })
      } else if (canUseAccountAction('accounts.reflect_account_password') && editAccount.has_account) {
        secretDeleteKeys.push(editAccount.account_key || 'account_password')
      }

      if (canUseAccountAction('accounts.reflect_auth_code') && editAccount.auth_code) {
        secretUpserts.push({
          secret_key: editAccount.auth_key || 'auth_code',
          secret_value: editAccount.auth_code,
        })
      } else if (canUseAccountAction('accounts.reflect_auth_code') && editAccount.has_auth) {
        secretDeleteKeys.push(editAccount.auth_key || 'auth_code')
      }

      if (canUseAccountAction('accounts.reflect_reserves')) {
        const reserveValues = (editAccount.reserve_text || '')
          .split(/\s+/)
          .map((v) => v.trim())
          .filter(Boolean)

        // Сохраняем существующие ключи резервов, чтобы редактирование не сбивало их нумерацию.
        const existingReserveKeys = Array.from(
          new Set(
            (Array.isArray(editAccount.existing_reserve_keys) ? editAccount.existing_reserve_keys : [])
              .map((key) => normalizeReserveKey(key))
              .filter(Boolean)
          )
        ).sort(compareReserveKeys)

        // Для новых значений подбираем ближайший свободный reserveN без конфликтов.
        const takeNextFreeReserveKey = (usedKeys) => {
          for (let idx = 1; idx <= 50; idx += 1) {
            const key = `reserve${idx}`
            if (!usedKeys.has(key)) return key
          }
          return `reserve${usedKeys.size + 1}`
        }

        const keepKeys = []
        const usedKeys = new Set(existingReserveKeys)
        reserveValues.forEach((val, idx) => {
          const key = existingReserveKeys[idx] || takeNextFreeReserveKey(usedKeys)
          usedKeys.add(key)
          keepKeys.push(key)
          secretUpserts.push({ secret_key: key, secret_value: val })
        })
        existingReserveKeys
          .filter((k) => !keepKeys.includes(k))
          .forEach((k) => {
            secretDeleteKeys.push(k)
          })
      }

      if (secretUpserts.length || secretDeleteKeys.length) {
        await apiPut(
          `/accounts/${editAccount.account_id}/secrets`,
          { upserts: secretUpserts, delete_keys: secretDeleteKeys },
          { token: auth.state.token }
        )
      }
      // Принудительно обновляем кеш секретов, чтобы сразу показать актуальные резервы без ручного refresh.
      await ensureAccountSecretsLoaded(editAccount.account_id, true)

      if (canUseAccountAction('accounts.reflect_slots')) {
        await apiPut(
          `/accounts/${editAccount.account_id}/products`,
          { product_ids: editAccount.product_ids || [] },
          { token: auth.state.token }
        )
      }

      accountsOk.value = 'Аккаунт обновлён'
      // После успешного сохранения закрываем модалку без повторного confirm о несохраненных правках.
      if (suppressUnsavedConfirm) suppressUnsavedConfirm.value = true
      try {
        await cancelEditAccount()
      } finally {
        if (suppressUnsavedConfirm) suppressUnsavedConfirm.value = false
      }
      // Обновляем список после закрытия, чтобы модалка не зависела от времени ответа API.
      await Promise.allSettled([loadAccounts(), loadAccountsAll()])
    } catch (e) {
      accountsError.value = mapApiError(e?.message)
    } finally {
      accountSaving.value = false
    }
  }

  async function deleteAccount() {
    accountsError.value = null
    accountsOk.value = null
    if (!editAccount.account_id) return
    // Подтверждение удаления показываем в фирменном модальном стиле.
    const isConfirmed = typeof requestDealConfirm === 'function'
      ? await requestDealConfirm({
        title: 'Предупреждение',
        message: 'Удалить аккаунт?',
        confirmText: 'Удалить',
        cancelText: 'Отмена',
      })
      : window.confirm('Удалить аккаунт?')
    if (!isConfirmed) return
    accountsLoading.value = true
    try {
      await apiDelete(`/accounts/${editAccount.account_id}`, { token: auth.state.token })
      // После успешного удаления закрываем модалку без повторного confirm о несохраненных правках.
      if (suppressUnsavedConfirm) suppressUnsavedConfirm.value = true
      try {
        await cancelEditAccount()
      } finally {
        if (suppressUnsavedConfirm) suppressUnsavedConfirm.value = false
      }
      // Обновляем таблицы после закрытия модалки.
      await Promise.allSettled([loadAccounts(), loadAccountsAll()])
    } catch (e) {
      accountsError.value = mapApiError(e?.message)
    } finally {
      accountsLoading.value = false
    }
  }

  return {
    getEmailSecret,
    getAccountSecret,
    getReserveSecrets,
    getReserveSecretEntries,
    getAuthSecret,
    ensureAccountSecretsLoaded,
    loadAccountProducts,
    loadAccounts,
    loadAccountsAll,
    loadAccountDeals,
    refreshOpenAccountFromDb,
    startEditAccount,
    toggleAccountEditMode,
    openCreateAccountModal,
    cancelEditAccount,
    createAccount,
    createQuickAccountProduct,
    updateAccount,
    deleteAccount,
  }
}
