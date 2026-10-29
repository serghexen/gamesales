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
  quickNewAccountProduct,
  quickNewAccountProductLoading,
  quickNewAccountProductError,
  quickEditAccountProduct,
  quickEditAccountProductLoading,
  quickEditAccountProductError,
  loadProductsAll,
}) {
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
    if (!String(newAccount.account_password || '').trim()) missing.push('Пароль аккаунта')
    if (!String(newAccount.email_password || '').trim()) missing.push('Пароль почты')
    if (!String(newAccount.auth_code || '').trim() && !newAccount.authenticator_image) missing.push('Код аутентификатора')
    return missing
  }

  let initialEditAccountSnapshot = null
  let pendingAccountReturn = null
  let accountDealsRequestSeq = 0
  let accountsRequestSeq = 0
  let accountsAllRequestSeq = 0
  let accountProductsRequestSeq = 0
  let accountEditorRequestSeq = 0
  const accountSecretsRequests = new Map()

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
  function getReserveSecretEntries(accountId, includeUnlisted = false) {
    const list = accountSecrets.value[accountId] || []
    return list
      .filter((s) => /^reserve\d+$/i.test(String(s.secret_key || '').trim()) && (includeUnlisted || s.reserve_listed !== false))
      .map((s) => ({
        key: normalizeReserveKey(s.secret_key),
        listed: s.reserve_listed !== false,
        reserve_id: s.reserve_id,
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

  // Обновляет кеш только последним ответом; ошибка загрузки не означает пустой список секретов.
  async function ensureAccountSecretsLoaded(accountId, forceReload = false) {
    const targetId = Number(accountId || 0)
    if (!targetId) return false
    if (!forceReload && Object.prototype.hasOwnProperty.call(accountSecrets.value || {}, targetId)) return true
    const request = {}
    accountSecretsRequests.set(targetId, request)
    request.promise = (async () => {
      try {
        const secrets = await apiGet(`/accounts/${targetId}/secrets`, { token: auth.state.token })
        if (accountSecretsRequests.get(targetId) !== request) return accountSecretsRequests.get(targetId).promise
        if (!Array.isArray(secrets)) return false
        accountSecrets.value = { ...(accountSecrets.value || {}), [targetId]: secrets }
        return true
      } catch {
        if (accountSecretsRequests.get(targetId) !== request) return accountSecretsRequests.get(targetId).promise
        return false
      }
    })()
    return request.promise
  }

  async function fetchAuthenticatorImage(accountId) {
    // QR загружается только для карточки аккаунта и не занимает общий кеш секретов.
    try {
      const result = await apiGet(`/accounts/${accountId}/authenticator-image`, { token: auth.state.token })
      return result && typeof result.image === 'string' && typeof result.version === 'string' ? result : null
    } catch {
      return null
    }
  }

  function applyAuthenticatorImage(result) {
    // Снимок версии остаётся рядом с изображением для проверки параллельного редактирования.
    editAccount.authenticator_image = result.image
    editAccount.expected_authenticator_image_version = result.version
  }

  async function loadAccountForDealNavigation(accountId) {
    // Переход из сделки использует тот же кеш с защитой от запоздалых ответов.
    const [account, secretsLoaded] = await Promise.all([
      apiGet(`/accounts/${Number(accountId)}`, { token: auth.state.token }),
      ensureAccountSecretsLoaded(accountId, true),
    ])
    if (!secretsLoaded) throw new Error('Не удалось загрузить данные аккаунта. Повторите открытие.')
    return account
  }

  // Разбирает поле резервов без пустых строк, сохраняя дубли для серверной проверки.
  function reserveValuesFromText(text) {
    return String(text || '').split(/\s+/).filter(Boolean)
  }

  function sameListValues(left, right) {
    // Порядок кодов и привязок не меняет их принадлежность аккаунту.
    return JSON.stringify([...left].sort()) === JSON.stringify([...right].sort())
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
      authenticator_image: editAccount.authenticator_image || '',
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
    editAccount.expected_reserves = Object.fromEntries(reserveEntries.map((item) => [item.key, item.value]))
    editAccount.has_account = Boolean(account)
    editAccount.has_email = Boolean(email)
    editAccount.has_auth = Boolean(authSecret)
  }

  // Загружает товары, привязанные к аккаунту.
  async function loadAccountProducts(accountId) {
    const requestId = ++accountProductsRequestSeq
    const editorRequestId = accountEditorRequestSeq
    accountProductsLoading.value = true
    try {
      // Используем только новый product endpoint для привязок аккаунта.
      const items = await apiGet(`/accounts/${accountId}/products`, { token: auth.state.token })
      if (!Array.isArray(items)) throw new Error('Invalid products response')
      // Применяем ответ только если это последний запрос и карточка все еще открыта на тот же аккаунт.
      if (editorRequestId !== accountEditorRequestSeq || requestId !== accountProductsRequestSeq || Number(editAccount?.account_id || 0) !== Number(accountId || 0)) return
      editAccount.product_ids = [...new Set((items || []).map((p) => Number(p?.product_id || 0)).filter(Boolean))]
      // Доверяем API: backend уже возвращает подписки с датами, если они есть.
      editAccount.product_titles = [...new Set((items || []).map((p) => String(p?.title || '').trim()).filter(Boolean))]
      return true
    } catch {
      if (editorRequestId !== accountEditorRequestSeq || requestId !== accountProductsRequestSeq || Number(editAccount?.account_id || 0) !== Number(accountId || 0)) return
      // Не превращаем сетевую ошибку в команду удалить все привязки при сохранении.
      return false
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
      if (accountFilters.without_products) params.set('without_products', 'true')
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
  function startEditAccount(a, { onClose } = {}) {
    // Возврат привязан только к этой карточке и задаётся после закрытия прежних модалок.
    closeAllModals()
    pendingAccountReturn = typeof onClose === 'function' ? onClose : null
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

    const requestId = ++accountEditorRequestSeq
    editAccount.details_loading = true
    editAccount.details_load_failed = false
    editAccount.authenticator_image = ''
    editAccount.expected_authenticator_image_version = ''
    editAccount.authenticator_image_loading = false
    accountsError.value = null
    accountsOk.value = null
    editAccount.product_ids = []
    editAccount.product_titles = []
    // Кеш служит только для показа: редактирование доступно после свежего снимка с сервера.
    applyCachedSecretsToEditAccount(a.account_id)
    editAccountProductType.value = 'game'
    quickEditAccountProduct.title = ''
    quickEditAccountProduct.platform_codes = []
    quickEditAccountProductError.value = ''
    syncInitialEditAccountSnapshot()
    loadAccountDeals(a.account_id)
    loadAccountSlotAssignments(a.account_id)
    return Promise.all([
      ensureAccountSecretsLoaded(a.account_id, true),
      loadAccountProducts(a.account_id),
      fetchAuthenticatorImage(a.account_id),
    ]).then(([secretsLoaded, productsLoaded, image]) => {
      // Повторное открытие того же аккаунта тоже считается другой формой.
      if (requestId !== accountEditorRequestSeq || !editAccount.open || !isSameAccountId(editAccount.account_id, a.account_id)) return
      editAccount.details_loading = false
      editAccount.details_load_failed = !secretsLoaded || !productsLoaded || !image
      if (editAccount.details_load_failed) {
        accountsError.value = 'Не удалось загрузить данные аккаунта. Нажмите «Обновить из базы» перед редактированием.'
        return
      }
      applyCachedSecretsToEditAccount(a.account_id)
      applyAuthenticatorImage(image)
      syncInitialEditAccountSnapshot()
    })
  }

  // Перезагружает текущую карточку аккаунта с сервера, чтобы подтянуть изменения из других вкладок.
  async function refreshOpenAccountFromDb() {
    const targetId = Number(editAccount.account_id || 0)
    if (!targetId || accountModalMode.value !== 'edit' || accountEditMode.value === 'edit' || accountSaving.value || editAccount.details_loading || editAccount.authenticator_image_loading) return
    const requestId = ++accountEditorRequestSeq
    const isSameOpenedAccount = () => requestId === accountEditorRequestSeq && editAccount.open && Number(editAccount.account_id || 0) === targetId
    editAccount.details_loading = true
    accountsError.value = null
    accountsOk.value = null
    try {
      const [accountsData, , secretsLoaded, productsLoaded, image] = await Promise.all([
        apiGet('/accounts?all=true&sort_key=login&sort_dir=asc', { token: auth.state.token }),
        loadAccountsAll([targetId]),
        ensureAccountSecretsLoaded(targetId, true),
        loadAccountProducts(targetId),
        fetchAuthenticatorImage(targetId),
        loadAccountDeals(targetId),
        loadAccountSlotAssignments(targetId),
      ])
      if (!isSameOpenedAccount()) return
      if (!secretsLoaded || !productsLoaded || !image) throw new Error('Не удалось загрузить данные аккаунта. Повторите обновление.')
      const list = Array.isArray(accountsData?.items) ? accountsData.items : []
      const freshAccount = list.find((item) => isSameAccountId(item?.account_id, targetId))
      if (!freshAccount) throw new Error('Не удалось загрузить карточку аккаунта. Повторите обновление.')
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
      applyAuthenticatorImage(image)
      if (accountEditMode.value === 'view') {
        syncInitialEditAccountSnapshot()
      }
      editAccount.details_load_failed = false
      accountsOk.value = 'Данные аккаунта обновлены'
    } catch (e) {
      if (!isSameOpenedAccount()) return
      editAccount.details_load_failed = true
      accountsError.value = mapApiError(e?.message)
    } finally {
      if (isSameOpenedAccount()) {
        editAccount.details_loading = false
      }
    }
  }

  // Открывает модалку создания нового аккаунта.
  function openCreateAccountModal() {
    // Создание нового аккаунта не наследует возврат из ранее открытой карточки.
    accountEditorRequestSeq += 1
    editAccount.details_loading = false
    editAccount.details_load_failed = false
    closeAllModals()
    pendingAccountReturn = null
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
    newAccount.authenticator_image = ''
    newAccount.authenticator_image_loading = false
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
    if (accountModalMode.value !== 'edit' || accountSaving.value || accountsLoading.value || editAccount.details_loading || editAccount.authenticator_image_loading) return
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
      editAccount.authenticator_image = snapshot.authenticator_image || ''
      editAccount.reserve_text = snapshot.reserve_text || ''
      editAccount.product_ids = [...(snapshot.product_ids || [])]
      accountEditMode.value = 'view'
      editAccountProductSearch.value = ''
      editAccountProductType.value = 'game'
      return
    }
    if (editAccount.details_load_failed) return
    accountEditMode.value = 'edit'
  }

  async function cancelEditAccount({ returnToSource = true } = {}) {
    // Смена сценария закрывает карточку без возврата; крестик и сохранение возвращают в сделку.
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
      authenticator_image: '',
      authenticator_image_loading: false,
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
      authenticator_image: editAccount.authenticator_image || '',
      reserve_text: editAccount.reserve_text,
      product_ids: [...(editAccount.product_ids || [])],
    }
    const editDirty = accountModalMode.value === 'edit' && accountEditMode.value === 'edit' && !isSameNormalized(editCurrent, initialEditAccountSnapshot || {})
    if (guardEnabled && !(await confirmDiscardIfNeeded(createDirty || editDirty, { requestConfirm: requestUnsavedConfirm }))) return false

    const onClose = returnToSource ? pendingAccountReturn : null
    pendingAccountReturn = null
    accountEditorRequestSeq += 1
    editAccount.details_loading = false
    editAccount.details_load_failed = false
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
    editAccount.authenticator_image = ''
    editAccount.expected_authenticator_image_version = ''
    editAccount.authenticator_image_loading = false
    editAccount.auth_key = 'auth_code'
    editAccount.reserve_text = ''
    editAccount.existing_reserve_keys = []
    editAccount.expected_reserves = {}
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
    newAccount.authenticator_image = ''
    newAccount.authenticator_image_loading = false
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
    // Сначала сбрасываем карточку и одноразовый возврат, чтобы открытие сделки не вызвало цикл.
    if (onClose) await onClose()
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
    // Дожидаемся чтения файла, чтобы QR не потерялся при быстром сохранении.
    if (newAccount.authenticator_image_loading || accountsLoading.value) return
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
      if (newAccount.email_password) {
        secretUpserts.push({ secret_key: 'email_password', secret_value: newAccount.email_password })
      }
      if (newAccount.account_password) {
        secretUpserts.push({ secret_key: 'account_password', secret_value: newAccount.account_password })
      }
      if (newAccount.auth_code) {
        secretUpserts.push({ secret_key: 'auth_code', secret_value: newAccount.auth_code })
      }
      const reserveValues = (newAccount.reserve_text || '')
        .split(/\s+/)
        .map((v) => v.trim())
        .filter(Boolean)
      if (secretUpserts.length || reserveValues.length || newAccount.authenticator_image) {
        await apiPut(
          `/accounts/${created.account_id}/secrets`,
          { upserts: secretUpserts, delete_keys: [], reserve_values: reserveValues, expected_reserves: {},
            ...(newAccount.authenticator_image ? { authenticator_image: newAccount.authenticator_image, expected_authenticator_image_version: '' } : {}),
          },
          { token: auth.state.token }
        )
      }

      if (newAccount.product_ids.length) {
        await apiPut(
          `/accounts/${created.account_id}/products`,
          { product_ids: newAccount.product_ids },
          { token: auth.state.token }
        )
      }
      if (isCreateSubscriptionMode && subscriptionProductId && subscriptionValidUntil) {
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
      newAccount.authenticator_image = ''
      newAccount.authenticator_image_loading = false
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
    // Нельзя сохранять неполный снимок или запускать второе сохранение параллельно первому.
    if (accountSaving.value || editAccount.details_loading || editAccount.authenticator_image_loading) return
    accountsError.value = null
    accountsOk.value = null
    if (!editAccount.account_id) return
    if (editAccount.details_load_failed) {
      accountsError.value = 'Данные аккаунта не загружены. Обновите карточку перед сохранением.'
      return
    }
    if (!editAccount.login_name || !editAccount.domain_code) {
      accountsError.value = 'Укажите логин и домен'
      return
    }
    const targetId = editAccount.account_id
    const editorRequestId = accountEditorRequestSeq
    const isCurrentEditor = () => editorRequestId === accountEditorRequestSeq && isSameAccountId(editAccount.account_id, targetId)
    const original = initialEditAccountSnapshot
    const current = { ...editAccount, product_ids: [...(editAccount.product_ids || [])] }
    const accountPatch = {
      region_code: current.region_code || null,
      login_name: current.login_name || null,
      domain_code: current.domain_code || null,
      notes: current.notes || null,
      account_date: current.account_date || null,
      status_code: current.status_code || 'active',
      is_deactivated: Boolean(current.is_deactivated),
    }
    // Не отправляем неизменённые поля: старый снимок не должен отменять правки другого сотрудника.
    if (original) {
      for (const key of Object.keys(accountPatch)) {
        const previous = key === 'is_deactivated' ? Boolean(original[key])
          : (original[key] || (key === 'status_code' ? 'active' : null))
        if (accountPatch[key] === previous) delete accountPatch[key]
      }
    }
    const secretUpserts = []
    const secretDeleteKeys = []
    for (const [field, keyField, hasField] of [
      ['email_password', 'email_key', 'has_email'],
      ['account_password', 'account_key', 'has_account'],
      ['auth_code', 'auth_key', 'has_auth'],
    ]) {
      if (original && (current[field] || '') === (original[field] || '')) continue
      if (current[field]) secretUpserts.push({ secret_key: current[keyField] || field, secret_value: current[field] })
      else if (current[hasField]) secretDeleteKeys.push(current[keyField] || field)
    }
    const reserveValues = reserveValuesFromText(current.reserve_text)
    const expectedReserves = { ...(current.expected_reserves || {}) }
    const reservesChanged = !sameListValues(reserveValues, Object.values(expectedReserves))
    const secretsPatch = { upserts: secretUpserts, delete_keys: secretDeleteKeys }
    // Проверка устаревшего списка нужна только при реальном изменении резервов.
    if (reservesChanged) Object.assign(secretsPatch, { reserve_values: reserveValues, expected_reserves: expectedReserves })
    const imageChanged = (current.authenticator_image || '') !== (original?.authenticator_image || '')
    if (imageChanged) Object.assign(secretsPatch, { authenticator_image: current.authenticator_image || '', expected_authenticator_image_version: current.expected_authenticator_image_version || '' })
    const secretsChanged = imageChanged || reservesChanged || secretUpserts.length > 0 || secretDeleteKeys.length > 0
    const productsChanged = !original || !sameListValues(current.product_ids, original.product_ids || [])
    let savedParts = false
    accountSaving.value = true
    try {
      if (Object.keys(accountPatch).length) {
        await apiPut(`/accounts/${targetId}`, accountPatch, { token: auth.state.token })
        savedParts = true
        if (!isCurrentEditor()) return
        if (original) {
          for (const key of Object.keys(accountPatch)) original[key] = current[key]
        }
      }
      if (secretsChanged) {
        await apiPut(`/accounts/${targetId}/secrets`, secretsPatch, { token: auth.state.token })
        savedParts = true
        if (!isCurrentEditor()) return
        // После успешной записи обновляем исходный снимок, чтобы повтор после сбоя следующего запроса не конфликтовал сам с собой.
        const [loaded, image] = await Promise.all([ensureAccountSecretsLoaded(targetId, true), fetchAuthenticatorImage(targetId)])
        if (!isCurrentEditor()) return
        if (!loaded || !image) {
          editAccount.details_load_failed = true
          throw new Error('Секреты сохранены, но не удалось загрузить их актуальное состояние. Откройте аккаунт заново.')
        }
        applyCachedSecretsToEditAccount(targetId)
        applyAuthenticatorImage(image)
        if (original) {
          for (const field of ['email_password', 'account_password', 'auth_code', 'reserve_text', 'authenticator_image']) original[field] = editAccount[field]
        }
      }
      if (productsChanged) {
        await apiPut(`/accounts/${targetId}/products`, { product_ids: current.product_ids }, { token: auth.state.token })
        savedParts = true
        if (!isCurrentEditor()) return
        if (original) original.product_ids = [...current.product_ids]
      }
      accountsOk.value = 'Аккаунт обновлён'
      // После успешного сохранения закрываем модалку без повторного confirm о несохраненных правках.
      if (suppressUnsavedConfirm) suppressUnsavedConfirm.value = true
      try {
        await cancelEditAccount()
      } finally {
        if (suppressUnsavedConfirm) suppressUnsavedConfirm.value = false
      }
      await Promise.allSettled([loadAccounts(), loadAccountsAll()])
    } catch (e) {
      if (!isCurrentEditor()) return
      // API сохраняет блоки отдельными запросами; честно сообщаем о возможном частичном результате.
      const message = mapApiError(e?.message)
      accountsError.value = savedParts ? `Часть изменений уже сохранена. ${message}` : message
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
    loadAccountForDealNavigation,
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
