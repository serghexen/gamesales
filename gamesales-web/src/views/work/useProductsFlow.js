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
  productAccountsPage,
  productSlotAssignments,
  productSlotAssignmentsError,
  productSlotAssignmentsLoading,
  loadProductSlotAssignments,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
}) {
  let initialEditProductSnapshot = null
  let initialCreateProductSnapshot = null
  // Нормализует товар из API в формат, совместимый с текущим UI вкладки.
  function normalizeProduct(product) {
    return {
      ...product,
      product_id: Number(product?.product_id || 0) || null,
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
    }
  }

  // Очищает состояние редактирования игры.
  function cancelEditProduct() {
    editProduct.open = false
    editProduct.product_id = null
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
    initialEditProductSnapshot = null
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
    }
    productError.value = null
    productOk.value = null
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
    newProduct.title = ''
    newProduct.type_code = PRODUCT_TYPE_PRIMARY
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
      loadProductSlotAssignments(normalized.product_id)
    }
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
      await apiPost(
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
      productOk.value = `Товар “${newProduct.title}” добавлен`
      newProduct.type_code = PRODUCT_TYPE_PRIMARY
      newProduct.title = ''
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
      productOk.value = 'Товар обновлен'
      await loadProducts()
      await loadProductsAll()
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
    if (!window.confirm('Архивировать товар?')) return
    productLoading.value = true
    productSaving.value = true
    try {
      await apiDelete(`/products/${editProduct.product_id}`, { token: auth.state.token })
      productOk.value = 'Товар архивирован'
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

  return {
    openProductAccounts,
    openCreateGameProductModal,
    openCreateSubscriptionProductModal,
    openCreateProductModal,
    closeProductModal,
    loadProducts,
    loadProductsAll,
    loadProductAccounts,
    createProduct,
    updateProduct,
    archiveProduct,
    goToAccount,
    openDealProduct,
    startEditProduct,
    cancelEditProduct,
    refreshProductAccounts,
  }
}
