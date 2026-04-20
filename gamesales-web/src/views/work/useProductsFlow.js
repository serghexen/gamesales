import { confirmDiscardIfNeeded, isSameNormalized } from './unsavedChanges'
import { PRODUCT_TYPE_PRIMARY } from './domainUtils'

export function useProductsFlow({
  auth,
  apiGet,
  apiPost,
  apiPut,
  apiDelete,
  mapApiError,
  closeAllModals,
  resetModalPos,
  setActiveTab,
  showProductForm,
  productEditMode,
  editProduct,
  newProduct,
  productError,
  productOk,
  productsLoading,
  productLoading,
  productSaving,
  products,
  productsAll,
  productsTotal,
  productsSort,
  productsPage,
  productsPageSize,
  productFilters,
  productFilterDraft,
  accountFilters,
  productAccounts,
  productAccountsLoading,
  productAccountsError,
  productAccountOptions,
  productAccountsPage,
  productSlotAssignments,
  productSlotAssignmentsError,
  productSlotAssignmentsLoading,
  productSubscriptionTerms,
  productSubscriptionTermsLoading,
  productSubscriptionTermsError,
  loadProductSlotAssignments,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
  requestDealConfirm,
  loadAccountsAll,
  quickNewProductAccount,
  quickNewProductAccountLoading,
  quickNewProductAccountError,
  quickEditProductAccount,
  quickEditProductAccountLoading,
  quickEditProductAccountError,
}) {
  let initialEditProductSnapshot = null
  let initialCreateProductSnapshot = null
  const productSubscriptionTermsRef = productSubscriptionTerms || { value: [] }
  const productSubscriptionTermsLoadingRef = productSubscriptionTermsLoading || { value: false }
  const productSubscriptionTermsErrorRef = productSubscriptionTermsError || { value: null }

  // Возвращает сегодняшнюю дату в формате YYYY-MM-DD для создания нового аккаунта.
  function getTodayAccountDate() {
    const now = new Date()
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  }
  // Нормализует список аккаунтов к массиву уникальных числовых id.
  function normalizeAccountIds(value) {
    const source = Array.isArray(value) ? value : (value ? [value] : [])
    return Array.from(new Set(source.map((item) => Number(item || 0)).filter(Boolean)))
  }

  // Нормализует товар из API в формат, совместимый с текущим UI вкладки.
  function normalizeProduct(product) {
    return {
      ...product,
      product_id: Number(product?.product_id || 0) || null,
      account_ids: normalizeAccountIds(product?.account_ids || product?.account_id),
      type_code: product?.type_code || PRODUCT_TYPE_PRIMARY,
      platform_codes: Array.isArray(product?.platform_codes) ? [...product.platform_codes] : [],
      provider: product?.provider || '',
      billing_period: product?.billing_period || '',
      subscription_notes: product?.subscription_notes || '',
    }
  }

  // Открывает игру в режиме просмотра и подгружает логотип.
  function startEditProduct(product) {
    const normalized = normalizeProduct(product || {})
    closeAllModals()
    resetModalPos()
    showProductForm.value = false
    editProduct.open = true
    productEditMode.value = 'view'
    editProduct.product_id = normalized.product_id
    editProduct.account_ids = [...normalizeAccountIds(normalized.account_ids)]
    editProduct.type_code = normalized.type_code
    editProduct.title = normalized.title || ''
    editProduct.short_title = normalized.short_title || ''
    editProduct.link = normalized.link || ''
    editProduct.text_lang = normalized.text_lang || ''
    editProduct.audio_lang = normalized.audio_lang || ''
    editProduct.vr_support = normalized.vr_support || ''
    editProduct.platform_codes = [...normalized.platform_codes]
    editProduct.region_code = normalized.region_code || ''
    editProduct.provider = normalized.provider || ''
    editProduct.billing_period = normalized.billing_period || ''
    editProduct.subscription_notes = normalized.subscription_notes || ''
    // Сохраняем исходные данные для проверки несохраненных правок.
    initialEditProductSnapshot = {
      type_code: editProduct.type_code,
      title: editProduct.title,
      short_title: editProduct.short_title,
      link: editProduct.link,
      text_lang: editProduct.text_lang,
      audio_lang: editProduct.audio_lang,
      vr_support: editProduct.vr_support,
      platform_codes: [...(editProduct.platform_codes || [])],
      region_code: editProduct.region_code,
      provider: editProduct.provider,
      billing_period: editProduct.billing_period,
      subscription_notes: editProduct.subscription_notes,
      account_ids: [...normalizeAccountIds(editProduct.account_ids)],
    }
  }

  // Очищает состояние редактирования игры.
  function cancelEditProduct() {
    editProduct.open = false
    editProduct.product_id = null
    editProduct.account_ids = []
    editProduct.type_code = PRODUCT_TYPE_PRIMARY
    productEditMode.value = 'view'
    editProduct.title = ''
    editProduct.short_title = ''
    editProduct.link = ''
    editProduct.text_lang = ''
    editProduct.audio_lang = ''
    editProduct.vr_support = ''
    editProduct.platform_codes = []
    editProduct.region_code = ''
    editProduct.provider = ''
    editProduct.billing_period = ''
    editProduct.subscription_notes = ''
    productSlotAssignments.value = []
    productSlotAssignmentsError.value = null
    productSlotAssignmentsLoading.value = false
    productSubscriptionTermsRef.value = []
    productSubscriptionTermsErrorRef.value = null
    productSubscriptionTermsLoadingRef.value = false
    initialEditProductSnapshot = null
  }

  // Загружает сроки подписки для карточки товара типа "subscription".
  async function loadProductSubscriptionTerms(productId, typeCode) {
    const normalizedType = String(typeCode || '').trim().toLowerCase()
    if (!productId || normalizedType !== 'subscription') {
      productSubscriptionTermsRef.value = []
      productSubscriptionTermsErrorRef.value = null
      productSubscriptionTermsLoadingRef.value = false
      return
    }
    productSubscriptionTermsLoadingRef.value = true
    productSubscriptionTermsErrorRef.value = null
    try {
      const data = await apiGet(`/products/subscriptions/${encodeURIComponent(productId)}/terms`, { token: auth.state.token })
      productSubscriptionTermsRef.value = Array.isArray(data) ? data : []
    } catch (e) {
      productSubscriptionTermsRef.value = []
      productSubscriptionTermsErrorRef.value = mapApiError(e?.message)
    } finally {
      productSubscriptionTermsLoadingRef.value = false
    }
  }

  // Подготавливает форму создания товара с выбранным типом.
  function openCreateProductModalByType(typeCode) {
    closeAllModals()
    resetModalPos()
    showProductForm.value = true
    productEditMode.value = 'edit'
    cancelEditProduct()
    // Фиксируем тип, чтобы кнопки "Игра" и "Подписка" открывали нужный сценарий.
    newProduct.type_code = typeCode || PRODUCT_TYPE_PRIMARY
    newProduct.account_ids = []
    // Запоминаем стартовое состояние формы создания для корректной проверки "грязных" правок.
    initialCreateProductSnapshot = {
      type_code: newProduct.type_code,
      title: newProduct.title,
      short_title: newProduct.short_title,
      link: newProduct.link,
      text_lang: newProduct.text_lang,
      audio_lang: newProduct.audio_lang,
      vr_support: newProduct.vr_support,
      platform_codes: [...(newProduct.platform_codes || [])],
      region_code: newProduct.region_code,
      provider: newProduct.provider,
      billing_period: newProduct.billing_period,
      subscription_notes: newProduct.subscription_notes,
      account_ids: [...normalizeAccountIds(newProduct.account_ids)],
    }
    quickNewProductAccount.login_name = ''
    quickNewProductAccount.domain_code = ''
    quickNewProductAccount.platform_codes = []
    quickNewProductAccountError.value = ''
    productError.value = null
    productOk.value = null
    // Для формы товара загружаем доступные аккаунты под выбранный тип.
    loadAvailableProductAccounts(newProduct.type_code, null)
  }

  // Открывает форму создания игры.
  function openCreateGameProductModal() {
    openCreateProductModalByType(PRODUCT_TYPE_PRIMARY)
  }

  // Открывает форму создания подписки.
  function openCreateSubscriptionProductModal() {
    openCreateProductModalByType('subscription')
  }

  // Оставляем совместимость для старых вызовов.
  function openCreateProductModal() {
    openCreateGameProductModal()
  }

  // Закрывает модалку игры и очищает все временные поля.
  async function closeProductModal() {
    const guardEnabled = !suppressUnsavedConfirm?.value
    const createCurrent = {
      type_code: newProduct.type_code,
      title: newProduct.title,
      short_title: newProduct.short_title,
      link: newProduct.link,
      text_lang: newProduct.text_lang,
      audio_lang: newProduct.audio_lang,
      vr_support: newProduct.vr_support,
      platform_codes: [...(newProduct.platform_codes || [])],
      region_code: newProduct.region_code,
      provider: newProduct.provider,
      billing_period: newProduct.billing_period,
      subscription_notes: newProduct.subscription_notes,
      account_ids: [...normalizeAccountIds(newProduct.account_ids)],
    }
    const createDirty = showProductForm.value && !isSameNormalized(createCurrent, initialCreateProductSnapshot || {})
    const editCurrent = {
      title: editProduct.title,
      short_title: editProduct.short_title,
      link: editProduct.link,
      text_lang: editProduct.text_lang,
      audio_lang: editProduct.audio_lang,
      vr_support: editProduct.vr_support,
      platform_codes: [...(editProduct.platform_codes || [])],
      region_code: editProduct.region_code,
      account_ids: [...normalizeAccountIds(editProduct.account_ids)],
    }
    const editDirty = editProduct.open && productEditMode.value === 'edit' && !isSameNormalized(editCurrent, initialEditProductSnapshot || {})
    if (guardEnabled && !(await confirmDiscardIfNeeded(createDirty || editDirty, { requestConfirm: requestUnsavedConfirm }))) return false

    showProductForm.value = false
    cancelEditProduct()
    productError.value = null
    productOk.value = null
    productAccounts.value = []
    productAccountsError.value = null
    productAccountsLoading.value = false
    productSlotAssignments.value = []
    productSlotAssignmentsError.value = null
    productSlotAssignmentsLoading.value = false
    productSubscriptionTermsRef.value = []
    productSubscriptionTermsErrorRef.value = null
    productSubscriptionTermsLoadingRef.value = false
    newProduct.title = ''
    newProduct.type_code = PRODUCT_TYPE_PRIMARY
    newProduct.account_ids = []
    newProduct.short_title = ''
    newProduct.link = ''
    newProduct.text_lang = ''
    newProduct.audio_lang = ''
    newProduct.vr_support = ''
    newProduct.platform_codes = []
    newProduct.region_code = ''
    newProduct.provider = ''
    newProduct.billing_period = ''
    newProduct.subscription_notes = ''
    quickNewProductAccount.login_name = ''
    quickNewProductAccount.domain_code = ''
    quickNewProductAccount.platform_codes = []
    quickNewProductAccountError.value = ''
    quickEditProductAccount.login_name = ''
    quickEditProductAccount.domain_code = ''
    quickEditProductAccount.platform_codes = []
    quickEditProductAccountError.value = ''
    initialCreateProductSnapshot = null
    return true
  }

  // Открывает карточку товара и грузит связанные аккаунты/слоты по product_id.
  function openProductAccounts(product) {
    const normalized = normalizeProduct(product || {})
    resetModalPos()
    startEditProduct(normalized)
    productAccounts.value = []
    productAccountsPage.value = 1
    // Для обоих типов товара (игра/подписка) используем единый сценарий загрузки.
    if (normalized.product_id) {
      loadProductAccounts(normalized.product_id)
      loadProductLinkedAccounts(normalized.product_id)
      loadProductSlotAssignments(normalized.product_id)
      loadProductSubscriptionTerms(normalized.product_id, normalized.type_code)
    }
    // Подгружаем доступные аккаунты с учетом типа и текущего товара.
    loadAvailableProductAccounts(normalized.type_code, normalized.product_id)
  }

  // Переключает режим карточки товара и при возврате в просмотр откатывает несохраненные изменения.
  function toggleProductEditMode() {
    if (!editProduct.open) return
    if (productEditMode.value === 'edit') {
      const snapshot = initialEditProductSnapshot || {}
      editProduct.type_code = snapshot.type_code || PRODUCT_TYPE_PRIMARY
      editProduct.title = snapshot.title || ''
      editProduct.short_title = snapshot.short_title || ''
      editProduct.link = snapshot.link || ''
      editProduct.text_lang = snapshot.text_lang || ''
      editProduct.audio_lang = snapshot.audio_lang || ''
      editProduct.vr_support = snapshot.vr_support || ''
      editProduct.platform_codes = [...(snapshot.platform_codes || [])]
      editProduct.region_code = snapshot.region_code || ''
      editProduct.account_ids = [...normalizeAccountIds(snapshot.account_ids)]
      editProduct.provider = snapshot.provider || ''
      editProduct.billing_period = snapshot.billing_period || ''
      editProduct.subscription_notes = snapshot.subscription_notes || ''
      productEditMode.value = 'view'
      return
    }
    productEditMode.value = 'edit'
    // При входе в редактирование обновляем фильтр доступных аккаунтов по текущему типу товара.
    loadAvailableProductAccounts(editProduct.type_code, editProduct.product_id)
  }

  function refreshProductAccounts() {
    // Обновляем список связанных аккаунтов по product_id.
    if (editProduct.product_id) {
      productAccountsPage.value = 1
      loadProductAccounts(editProduct.product_id)
    }
  }

  // Загружает список игр для таблицы.
  async function loadProducts() {
    productsLoading.value = true
    try {
      const params = new URLSearchParams()
      if (productFilters.q) params.set('q', productFilters.q)
      if (productFilters.type_code) params.set('type_code', productFilters.type_code)
      if (productFilters.platform_code) params.set('platform_code', productFilters.platform_code)
      if (productFilters.region_code) params.set('region_code', productFilters.region_code)
      params.set('sort_key', productsSort.value.key)
      params.set('sort_dir', productsSort.value.dir)
      params.set('page', String(productsPage.value))
      params.set('page_size', String(productsPageSize.value))
      const res = await apiGet(`/products?${params.toString()}`, { token: auth.state.token })
      products.value = (res?.items || []).map(normalizeProduct)
      productsTotal.value = Number(res?.total || 0)
    } catch {
      products.value = []
      productsTotal.value = 0
    } finally {
      productsLoading.value = false
    }
  }

  async function loadProductsAll() {
    try {
      const params = new URLSearchParams()
      params.set('all', 'true')
      params.set('sort_key', 'title')
      params.set('sort_dir', 'asc')
      const res = await apiGet(`/products?${params.toString()}`, { token: auth.state.token })
      // Для переходов из сделок держим все типы товаров, чтобы корректно открывать игру и подписку.
      productsAll.value = (res?.items || []).map(normalizeProduct)
    } catch {
      productsAll.value = []
    }
  }

  async function loadProductAccounts(productId) {
    if (!productId) {
      productAccounts.value = []
      return
    }
    productAccountsLoading.value = true
    productAccountsError.value = null
    try {
      // Используем только product-маршрут для связанных аккаунтов товара.
      const data = await apiGet(`/products/${productId}/accounts`, { token: auth.state.token })
      productAccounts.value = data || []
    } catch (e) {
      productAccountsError.value = mapApiError(e?.message)
      productAccounts.value = []
    } finally {
      productAccountsLoading.value = false
    }
  }

  async function loadAvailableProductAccounts(typeCode, productId = null) {
    const normalizedType = String(typeCode || PRODUCT_TYPE_PRIMARY).trim().toLowerCase() === 'subscription'
      ? 'subscription'
      : PRODUCT_TYPE_PRIMARY
    try {
      const params = new URLSearchParams()
      params.set('type_code', normalizedType)
      if (productId) params.set('product_id', String(productId))
      const data = await apiGet(`/accounts/available-for-product?${params.toString()}`, { token: auth.state.token })
      productAccountOptions.value = Array.isArray(data) ? data : []
    } catch {
      productAccountOptions.value = []
    }
  }

  async function getProductLinkedAccountIds(productId) {
    if (!productId) return []
    try {
      const data = await apiGet(`/products/${productId}/linked-accounts`, { token: auth.state.token })
      return normalizeAccountIds((data || []).map((item) => item?.account_id))
    } catch {
      return []
    }
  }

  async function loadProductLinkedAccounts(productId) {
    const ids = await getProductLinkedAccountIds(productId)
    if (editProduct.open && Number(editProduct.product_id) === Number(productId)) {
      // Подставляем фактические привязки товара из account_assets.
      editProduct.account_ids = ids
    }
  }

  // Привязывает товар к выбранному аккаунту через account_assets, не трогая существующие связи.
  async function bindProductToAccount(accountId, productId) {
    const normalizedAccountId = Number(accountId || 0)
    const normalizedProductId = Number(productId || 0)
    if (!normalizedAccountId || !normalizedProductId) return
    const existingProducts = await apiGet(`/accounts/${normalizedAccountId}/products`, { token: auth.state.token })
    const ids = new Set((existingProducts || []).map((item) => Number(item?.product_id || 0)).filter(Boolean))
    ids.add(normalizedProductId)
    await apiPut(
      `/accounts/${normalizedAccountId}/products`,
      { product_ids: Array.from(ids) },
      { token: auth.state.token },
    )
  }

  // Привязывает товар к нескольким аккаунтам из формы.
  async function bindProductToAccounts(accountIds, productId) {
    const ids = normalizeAccountIds(accountIds)
    for (const accountId of ids) {
      await bindProductToAccount(accountId, productId)
    }
  }

  // Удаляет привязку товара у аккаунта, оставляя остальные товары аккаунта без изменений.
  async function unbindProductFromAccount(accountId, productId) {
    const normalizedAccountId = Number(accountId || 0)
    const normalizedProductId = Number(productId || 0)
    if (!normalizedAccountId || !normalizedProductId) return
    const existingProducts = await apiGet(`/accounts/${normalizedAccountId}/products`, { token: auth.state.token })
    const ids = (existingProducts || [])
      .map((item) => Number(item?.product_id || 0))
      .filter((idValue) => idValue && idValue !== normalizedProductId)
    await apiPut(
      `/accounts/${normalizedAccountId}/products`,
      { product_ids: Array.from(new Set(ids)) },
      { token: auth.state.token },
    )
  }

  // Синхронизирует привязки товара "как в форме": добавляет новые и удаляет снятые.
  async function syncProductAccountBindings(productId, targetAccountIds) {
    const targetIds = normalizeAccountIds(targetAccountIds)
    const currentIds = await getProductLinkedAccountIds(productId)
    const targetSet = new Set(targetIds)
    const currentSet = new Set(currentIds)
    const toAdd = targetIds.filter((idValue) => !currentSet.has(idValue))
    const toRemove = currentIds.filter((idValue) => !targetSet.has(idValue))
    if (toAdd.length) {
      await bindProductToAccounts(toAdd, productId)
    }
    if (toRemove.length) {
      for (const accountId of toRemove) {
        await unbindProductFromAccount(accountId, productId)
      }
    }
  }

  async function createProduct() {
    productError.value = null
    productOk.value = null
    if (!newProduct.title) {
      productError.value = 'Укажите название товара'
      return
    }
    productLoading.value = true
    productSaving.value = true
    try {
      // Нормализуем тип перед отправкой, чтобы кнопка "Игра" всегда создавала game.
      const typeCode = String(newProduct.type_code || '').toLowerCase() === 'subscription'
        ? 'subscription'
        : PRODUCT_TYPE_PRIMARY
      const created = await apiPost(
        '/products',
        {
          type_code: typeCode,
          title: newProduct.title,
          short_title: newProduct.short_title || null,
          link: typeCode === PRODUCT_TYPE_PRIMARY ? (newProduct.link || null) : null,
          text_lang: typeCode === PRODUCT_TYPE_PRIMARY ? (newProduct.text_lang || null) : null,
          audio_lang: typeCode === PRODUCT_TYPE_PRIMARY ? (newProduct.audio_lang || null) : null,
          vr_support: typeCode === PRODUCT_TYPE_PRIMARY ? (newProduct.vr_support || null) : null,
          // Платформы сохраняем для обоих типов товаров (игра и подписка).
          platform_codes: newProduct.platform_codes || [],
          provider: typeCode !== PRODUCT_TYPE_PRIMARY ? (newProduct.provider || null) : null,
          billing_period: typeCode !== PRODUCT_TYPE_PRIMARY ? (newProduct.billing_period || null) : null,
          // Поле используем как универсальный комментарий для игры и подписки.
          subscription_notes: newProduct.subscription_notes || null,
          region_code: newProduct.region_code || null,
        },
        { token: auth.state.token }
      )
      // Для игры дополнительно сохраняем выбранные привязки к аккаунтам.
      const createdProductId = Number(created?.product_id || 0)
      if (typeCode === PRODUCT_TYPE_PRIMARY && createdProductId) {
        await syncProductAccountBindings(createdProductId, newProduct.account_ids)
      }
      const createdTitle = newProduct.title
      // Сначала закрываем модалку, чтобы во время перезагрузки списков не переключать форму на "игру".
      suppressUnsavedConfirm.value = true
      const closed = await closeProductModal()
      suppressUnsavedConfirm.value = false
      if (!closed) return
      productOk.value = `Товар “${createdTitle}” добавлен`
      await loadProducts()
      await loadProductsAll()
      if (createdProductId) {
        await loadProductLinkedAccounts(createdProductId)
      }
    } catch (e) {
      productError.value = mapApiError(e?.message)
    } finally {
      productLoading.value = false
      productSaving.value = false
    }
  }

  async function updateProduct() {
    productError.value = null
    productOk.value = null
    if (!editProduct.product_id) return
    if (!editProduct.title) {
      productError.value = 'Укажите название товара'
      return
    }
    productLoading.value = true
    productSaving.value = true
    try {
      // Для редактирования тоже нормализуем тип в допустимые значения.
      const typeCode = String(editProduct.type_code || '').toLowerCase() === 'subscription'
        ? 'subscription'
        : PRODUCT_TYPE_PRIMARY
      await apiPut(
        `/products/${editProduct.product_id}`,
        {
          type_code: typeCode,
          title: editProduct.title,
          short_title: editProduct.short_title || null,
          link: typeCode === PRODUCT_TYPE_PRIMARY ? (editProduct.link || null) : null,
          text_lang: typeCode === PRODUCT_TYPE_PRIMARY ? (editProduct.text_lang || null) : null,
          audio_lang: typeCode === PRODUCT_TYPE_PRIMARY ? (editProduct.audio_lang || null) : null,
          vr_support: typeCode === PRODUCT_TYPE_PRIMARY ? (editProduct.vr_support || null) : null,
          // Платформы сохраняем для обоих типов товаров (игра и подписка).
          platform_codes: editProduct.platform_codes || [],
          provider: typeCode !== PRODUCT_TYPE_PRIMARY ? (editProduct.provider || null) : null,
          billing_period: typeCode !== PRODUCT_TYPE_PRIMARY ? (editProduct.billing_period || null) : null,
          // Поле используем как универсальный комментарий для игры и подписки.
          subscription_notes: editProduct.subscription_notes || null,
          region_code: editProduct.region_code || null,
        },
        { token: auth.state.token }
      )
      // При редактировании игры добавляем связи с выбранными аккаунтами.
      if (typeCode === PRODUCT_TYPE_PRIMARY) {
        await syncProductAccountBindings(editProduct.product_id, editProduct.account_ids)
      }
      productOk.value = 'Товар обновлен'
      await loadProducts()
      await loadProductsAll()
      if (editProduct.product_id) {
        await loadProductAccounts(editProduct.product_id)
        await loadProductLinkedAccounts(editProduct.product_id)
      }
      cancelEditProduct()
    } catch (e) {
      productError.value = mapApiError(e?.message)
    } finally {
      productLoading.value = false
      productSaving.value = false
    }
  }

  async function archiveProduct() {
    productError.value = null
    productOk.value = null
    if (!editProduct.product_id) return
    // Для удаления товара используем фирменное модальное подтверждение, как в сделках.
    const isConfirmed = typeof requestDealConfirm === 'function'
      ? await requestDealConfirm({
        title: 'Предупреждение',
        message: 'Удалить товар?',
        confirmText: 'Удалить',
        cancelText: 'Отмена',
      })
      : window.confirm('Удалить товар?')
    if (!isConfirmed) return
    productLoading.value = true
    productSaving.value = true
    try {
      await apiDelete(`/products/${editProduct.product_id}`, { token: auth.state.token })
      await loadProducts()
      await loadProductsAll()
      closeProductModal()
    } catch (e) {
      productError.value = mapApiError(e?.message)
    } finally {
      productLoading.value = false
      productSaving.value = false
    }
  }

  function goToAccount(login) {
    setActiveTab('accounts')
    accountFilters.login_q = login || ''
  }

  async function openDealProduct(deal) {
    if (!deal || !deal.product_id) return
    setActiveTab('products')
    productFilters.q = deal.product_title || ''
    // Не ограничиваем тип, чтобы из сделки открывался любой товар.
    productFilters.type_code = ''
    productFilters.platform_code = ''
    productFilters.region_code = ''
    productFilterDraft.title = productFilters.q
    productFilterDraft.type = ''
    productFilterDraft.platform = ''
    productFilterDraft.region = ''
    productsPage.value = 1
    await loadProducts()
    if (!productsAll.value.length) {
      await loadProductsAll()
    }
    const product = productsAll.value.find((g) => g.product_id === deal.product_id) || products.value.find((g) => g.product_id === deal.product_id)
    if (product) {
      openProductAccounts(product)
    }
  }

  async function createQuickProductAccount(target) {
    const isEdit = target === 'edit'
    const state = isEdit ? quickEditProductAccount : quickNewProductAccount
    const loading = isEdit ? quickEditProductAccountLoading : quickNewProductAccountLoading
    const error = isEdit ? quickEditProductAccountError : quickNewProductAccountError
    error.value = ''
    if (!String(state.login_name || '').trim()) {
      error.value = 'Укажите логин'
      return
    }
    if (!String(state.domain_code || '').trim()) {
      error.value = 'Выберите домен'
      return
    }
    if (!Array.isArray(state.platform_codes) || !state.platform_codes.length) {
      error.value = 'Выберите платформу'
      return
    }
    const regionCode = String(isEdit ? editProduct.region_code || '' : newProduct.region_code || '').trim()
    if (!regionCode) {
      error.value = 'Укажите регион товара'
      return
    }
    loading.value = true
    try {
      // Быстро создаем аккаунт в потоке товара и сразу добавляем его в выбранные привязки.
      const created = await apiPost(
        '/accounts',
        {
          login_name: state.login_name,
          domain_code: state.domain_code,
          region_code: regionCode,
          account_date: getTodayAccountDate(),
          notes: null,
        },
        { token: auth.state.token },
      )
      await loadAccountsAll?.()
      const createdId = Number(created?.account_id || 0) || null
      if (createdId) {
        if (isEdit) editProduct.account_ids = normalizeAccountIds([...(editProduct.account_ids || []), createdId])
        else newProduct.account_ids = normalizeAccountIds([...(newProduct.account_ids || []), createdId])
      }
      await loadAvailableProductAccounts(
        isEdit ? editProduct.type_code : newProduct.type_code,
        isEdit ? editProduct.product_id : null,
      )
      state.login_name = ''
      state.domain_code = ''
      state.platform_codes = []
    } catch (e) {
      error.value = mapApiError(e?.message)
    } finally {
      loading.value = false
    }
  }

  // Быстро добавляет новый срок подписки в открытой карточке товара.
  async function createQuickProductSubscriptionTerm(payload) {
    const productId = Number(editProduct.product_id || 0)
    const typeCode = String(editProduct.type_code || '').trim().toLowerCase()
    const accountId = Number(payload?.account_id || 0)
    const validUntil = String(payload?.valid_until || '').trim()
    if (!productId || typeCode !== 'subscription') throw new Error('Откройте карточку подписки')
    if (!accountId) throw new Error('Выберите аккаунт')
    if (!validUntil) throw new Error('Укажите дату окончания')
    await apiPost(
      `/products/subscriptions/${encodeURIComponent(productId)}/terms`,
      { account_id: accountId, valid_until: validUntil, notes: null },
      { token: auth.state.token },
    )
    await loadProductSubscriptionTerms(productId, 'subscription')
  }

  return {
    openProductAccounts,
    openCreateGameProductModal,
    openCreateSubscriptionProductModal,
    openCreateProductModal,
    closeProductModal,
    loadProducts,
    loadProductsAll,
    loadProductAccounts,
    loadAvailableProductAccounts,
    createProduct,
    updateProduct,
    archiveProduct,
    createQuickProductAccount,
    createQuickProductSubscriptionTerm,
    goToAccount,
    openDealProduct,
    startEditProduct,
    toggleProductEditMode,
    cancelEditProduct,
    refreshProductAccounts,
  }
}
