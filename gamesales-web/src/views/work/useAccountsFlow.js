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
    if (!String(newAccount.auth_code || '').trim()) missing.push('Код аутентификатора')
    return missing
  }

  let initialEditAccountSnapshot = null
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
    const list = accountSecrets.value[accountId] || []
    const reserves = list
      .filter((s) => s.secret_key?.startsWith('reserve'))
      .map((s) => (s.secret_value_b64 ? decodeSecret(s.secret_value_b64) : ''))
      .filter(Boolean)
    return reserves.join(' ')
  }

  // Возвращает резервы аккаунта как список пар key/value, отсортированных по номеру reserveN.
  function getReserveSecretEntries(accountId) {
    const list = accountSecrets.value[accountId] || []
    return list
      .filter((s) => /^reserve\d+$/i.test(String(s.secret_key || '').trim()))
      .map((s) => ({
        key: String(s.secret_key || '').trim().toLowerCase(),
        value: s.secret_value_b64 ? decodeSecret(s.secret_value_b64).trim() : '',
      }))
      .filter((item) => item.value)
      .sort((a, b) => {
        const aNum = Number(String(a.key).replace('reserve', '')) || 0
        const bNum = Number(String(b.key).replace('reserve', '')) || 0
        return aNum - bNum
      })
  }

  // Достает код/секрет для входа (2FA/код).
  function getAuthSecret(accountId) {
    const list = accountSecrets.value[accountId] || []
    const item = list.find((s) => s.secret_key === 'auth_code')
    return item?.secret_value_b64 ? decodeSecret(item.secret_value_b64) : ''
  }

  // Загружает секреты пачкой, с запасным вариантом по одному аккаунту.
  async function loadAccountSecrets(list) {
    accountSecrets.value = {}
    if (!list.length) return
    const ids = list.map((a) => a.account_id).filter(Boolean)
    if (!ids.length) return
    try {
      const batch = await apiPost('/accounts/secrets/batch', { account_ids: ids }, { token: auth.state.token })
      const map = {}
      for (const item of batch || []) {
        map[item.account_id] = item.secrets || []
      }
      accountSecrets.value = map
    } catch {
      await Promise.all(
        ids.map(async (accountId) => {
          try {
            const s = await apiGet(`/accounts/${accountId}/secrets`, { token: auth.state.token })
            accountSecrets.value[accountId] = s || []
          } catch {
            accountSecrets.value[accountId] = []
          }
        })
      )
    }
  }

  // Догружает секреты для одного аккаунта, если их еще нет в локальном кеше.
  async function ensureAccountSecretsLoaded(accountId) {
    const targetId = Number(accountId || 0)
    if (!targetId) return
    if (Object.prototype.hasOwnProperty.call(accountSecrets.value || {}, targetId)) return
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

  // Загружает товары, привязанные к аккаунту.
  async function loadAccountProducts(accountId) {
    accountProductsLoading.value = true
    try {
      // Используем только новый product endpoint для привязок аккаунта.
      const items = await apiGet(`/accounts/${accountId}/products`, { token: auth.state.token })
      editAccount.product_ids = [...new Set((items || []).map((p) => Number(p?.product_id || 0)).filter(Boolean))]
      // Храним названия из ответа API; для подписок при необходимости дособираем даты сроков.
      const baseTitles = [...new Set((items || []).map((p) => String(p?.title || '').trim()).filter(Boolean))]
      const needsSubscriptionEnrich = (items || []).some((p) => {
        const typeCode = String(p?.type_code || '').trim().toLowerCase()
        const title = String(p?.title || '').trim().toLowerCase()
        return typeCode === 'subscription' && title && !title.includes(' до ')
      })
      if (!needsSubscriptionEnrich) {
        editAccount.product_titles = baseTitles
      } else {
        const enrichedTitles = []
        for (const item of (items || [])) {
          const typeCode = String(item?.type_code || '').trim().toLowerCase()
          const title = String(item?.title || '').trim()
          const productId = Number(item?.product_id || 0)
          if (typeCode !== 'subscription' || !title || !productId) {
            if (title) enrichedTitles.push(title)
            continue
          }
          if (title.toLowerCase().includes(' до ')) {
            enrichedTitles.push(title)
            continue
          }
          try {
            // Подтягиваем сроки подписки товара и оставляем только сроки текущего аккаунта.
            const terms = await apiGet(`/products/subscriptions/${productId}/terms`, { token: auth.state.token })
            const ownTerms = (Array.isArray(terms) ? terms : []).filter(
              (term) => Number(term?.account_id || 0) === Number(accountId || 0) && !term?.is_archived
            )
            if (!ownTerms.length) {
              enrichedTitles.push(title)
              continue
            }
            for (const term of ownTerms) {
              const rawDate = String(term?.valid_until || '').trim()
              if (!rawDate) {
                enrichedTitles.push(title)
                continue
              }
              const parsed = new Date(rawDate)
              if (Number.isNaN(parsed.getTime())) {
                enrichedTitles.push(`${title} до ${rawDate}`)
                continue
              }
              const day = String(parsed.getDate()).padStart(2, '0')
              const month = String(parsed.getMonth() + 1).padStart(2, '0')
              const year = String(parsed.getFullYear())
              enrichedTitles.push(`${title} до ${day}.${month}.${year}`)
            }
          } catch {
            // Если сроки не удалось загрузить, не ломаем карточку аккаунта.
            enrichedTitles.push(title)
          }
        }
        editAccount.product_titles = [...new Set(enrichedTitles.filter(Boolean))]
      }
    } catch {
      editAccount.product_ids = []
      editAccount.product_titles = []
    } finally {
      accountProductsLoading.value = false
    }
  }

  // Загружает список аккаунтов с фильтрами/сортировкой/пагинацией.
  async function loadAccounts() {
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
      accounts.value = data?.items || []
      accountsTotal.value = Number(data?.total || 0)
      await loadAccountSecrets(accounts.value)
    } catch (e) {
      accountsError.value = mapApiError(e?.message)
      accountsTotal.value = 0
    } finally {
      accountsLoading.value = false
    }
  }

  // Загружает все аккаунты целиком для выпадающих списков.
  async function loadAccountsAll() {
    try {
      const params = new URLSearchParams()
      params.set('all', 'true')
      params.set('sort_key', 'login')
      params.set('sort_dir', 'asc')
      const data = await apiGet(`/accounts?${params.toString()}`, { token: auth.state.token })
      accountsAll.value = data?.items || []
    } catch {
      accountsAll.value = []
    }
  }

  // Загружает сделки по конкретному аккаунту.
  async function loadAccountDeals(accountId) {
    accountDealsLoading.value = true
    accountDealsError.value = null
    try {
      const params = new URLSearchParams()
      params.set('account_id', String(accountId))
      params.set('page', '1')
      params.set('page_size', '200')
      const res = await apiGet(`/deals?${params.toString()}`, { token: auth.state.token })
      accountDeals.value = res?.items || []
    } catch (e) {
      accountDealsError.value = mapApiError(e?.message)
      accountDeals.value = []
    } finally {
      accountDealsLoading.value = false
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

    const secrets = accountSecrets.value[a.account_id] || []
    const email = secrets.find((s) => s.secret_key === 'email_password')
    const account = secrets.find((s) => s.secret_key === 'account_password' || s.secret_key === 'primary' || s.secret_key === 'password')
    const authSecret = secrets.find((s) => s.secret_key === 'auth_code')
    const reserves = secrets.filter((s) => s.secret_key?.startsWith('reserve'))
    editAccount.email_password = email?.secret_value_b64 ? decodeSecret(email.secret_value_b64) : ''
    editAccount.email_key = email?.secret_key || 'email_password'
    editAccount.account_password = account?.secret_value_b64 ? decodeSecret(account.secret_value_b64) : ''
    editAccount.account_key = account?.secret_key || 'account_password'
    editAccount.auth_code = authSecret?.secret_value_b64 ? decodeSecret(authSecret.secret_value_b64) : ''
    editAccount.auth_key = authSecret?.secret_key || 'auth_code'
    editAccount.reserve_text = reserves
      .sort((a1, a2) => a1.secret_key.localeCompare(a2.secret_key))
      .map((s) => (s.secret_value_b64 ? decodeSecret(s.secret_value_b64) : ''))
      .filter(Boolean)
      .join(' ')
    editAccount.existing_reserve_keys = reserves.map((s) => s.secret_key)
    editAccount.has_account = Boolean(account)
    editAccount.has_email = Boolean(email)
    editAccount.has_auth = Boolean(authSecret)
    editAccountProductType.value = 'game'
    quickEditAccountProduct.title = ''
    quickEditAccountProduct.platform_codes = []
    quickEditAccountProductError.value = ''
    // Фиксируем исходное состояние, чтобы уметь определять несохраненные изменения.
    const syncInitialAccountSnapshot = () => {
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
    syncInitialAccountSnapshot()
    loadAccountProducts(a.account_id).finally(() => {
      if (editAccount.open && accountEditMode.value === 'view') syncInitialAccountSnapshot()
    })
    loadAccountDeals(a.account_id)
    loadAccountSlotAssignments(a.account_id)
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

      const secretTasks = []
      if (newAccount.email_password) {
        secretTasks.push(
          apiPost(
            `/accounts/${created.account_id}/secrets`,
            { secret_key: 'email_password', secret_value: newAccount.email_password },
            { token: auth.state.token }
          )
        )
      }
      if (newAccount.account_password) {
        secretTasks.push(
          apiPost(
            `/accounts/${created.account_id}/secrets`,
            { secret_key: 'account_password', secret_value: newAccount.account_password },
            { token: auth.state.token }
          )
        )
      }
      if (newAccount.auth_code) {
        secretTasks.push(
          apiPost(
            `/accounts/${created.account_id}/secrets`,
            { secret_key: 'auth_code', secret_value: newAccount.auth_code },
            { token: auth.state.token }
          )
        )
      }
      const reserveValues = (newAccount.reserve_text || '')
        .split(/\s+/)
        .map((v) => v.trim())
        .filter(Boolean)
      reserveValues.forEach((val, idx) => {
        secretTasks.push(
          apiPost(
            `/accounts/${created.account_id}/secrets`,
            { secret_key: `reserve${idx + 1}`, secret_value: val },
            { token: auth.state.token }
          )
        )
      })
      if (secretTasks.length) {
        await Promise.all(secretTasks)
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

      const secretTasks = []
      if (editAccount.email_password) {
        secretTasks.push(
          apiPost(
            `/accounts/${editAccount.account_id}/secrets`,
            { secret_key: editAccount.email_key || 'email_password', secret_value: editAccount.email_password },
            { token: auth.state.token }
          )
        )
      } else if (editAccount.has_email) {
        secretTasks.push(
          apiDelete(`/accounts/${editAccount.account_id}/secrets/${editAccount.email_key || 'email_password'}`, {
            token: auth.state.token,
          })
        )
      }

      if (editAccount.account_password) {
        secretTasks.push(
          apiPost(
            `/accounts/${editAccount.account_id}/secrets`,
            { secret_key: editAccount.account_key || 'account_password', secret_value: editAccount.account_password },
            { token: auth.state.token }
          )
        )
      } else if (editAccount.has_account) {
        secretTasks.push(
          apiDelete(`/accounts/${editAccount.account_id}/secrets/${editAccount.account_key || 'account_password'}`, {
            token: auth.state.token,
          })
        )
      }

      if (editAccount.auth_code) {
        secretTasks.push(
          apiPost(
            `/accounts/${editAccount.account_id}/secrets`,
            { secret_key: editAccount.auth_key || 'auth_code', secret_value: editAccount.auth_code },
            { token: auth.state.token }
          )
        )
      } else if (editAccount.has_auth) {
        secretTasks.push(
          apiDelete(`/accounts/${editAccount.account_id}/secrets/${editAccount.auth_key || 'auth_code'}`, {
            token: auth.state.token,
          })
        )
      }

      const reserveValues = (editAccount.reserve_text || '')
        .split(/\s+/)
        .map((v) => v.trim())
        .filter(Boolean)
      const keepKeys = []
      reserveValues.forEach((val, idx) => {
        const key = `reserve${idx + 1}`
        keepKeys.push(key)
        secretTasks.push(
          apiPost(
            `/accounts/${editAccount.account_id}/secrets`,
            { secret_key: key, secret_value: val },
            { token: auth.state.token }
          )
        )
      })
      editAccount.existing_reserve_keys
        .filter((k) => !keepKeys.includes(k))
        .forEach((k) => {
          secretTasks.push(apiDelete(`/accounts/${editAccount.account_id}/secrets/${k}`, { token: auth.state.token }))
        })

      if (secretTasks.length) {
        await Promise.all(secretTasks)
      }

      await apiPut(
        `/accounts/${editAccount.account_id}/products`,
        { product_ids: editAccount.product_ids || [] },
        { token: auth.state.token }
      )

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
    loadAccountSecrets,
    ensureAccountSecretsLoaded,
    loadAccountProducts,
    loadAccounts,
    loadAccountsAll,
    loadAccountDeals,
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
