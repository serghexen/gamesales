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

  // Возвращает true, если товар относится к типу игры.
  function isGameType(item) {
    return String(item?.type_code || '').toLowerCase() === PRODUCT_TYPE_PRIMARY
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

  // Открывает форму создания новой игры.
  function openCreateProductModal() {
    closeAllModals()
    resetModalPos()
    showProductForm.value = true
    productEditMode.value = 'edit'
    cancelEditProduct()
    productError.value = null
    productOk.value = null
  }

  // Закрывает модалку игры и очищает все временные поля.
  async function closeProductModal() {
    const guardEnabled = !suppressUnsavedConfirm?.value
    const createDirty = showProductForm.value && !isSameNormalized(newProduct, {
      title: '',
      type_code: PRODUCT_TYPE_PRIMARY,
      short_title: '',
      link: '',
      text_lang: '',
      audio_lang: '',
      vr_support: '',
      platform_codes: [],
      region_code: '',
      provider: '',
      billing_period: '',
      subscription_notes: '',
    })
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
    return true
  }

  // Открывает модалку игры и грузит связанные аккаунты/слоты.
  function openProductAccounts(product) {
    const normalized = normalizeProduct(product || {})
    resetModalPos()
    startEditProduct(normalized)
    productAccounts.value = []
    productAccountsPage.value = 1
    // Для карточки игры используем только product_id.
    if (isGameType(normalized) && normalized.product_id) {
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
      params.set('type_code', PRODUCT_TYPE_PRIMARY)
      params.set('sort_key', 'title')
      params.set('sort_dir', 'asc')
      const res = await apiGet(`/products?${params.toString()}`, { token: auth.state.token })
      // В этом списке оставляем только товары типа "Игра".
      productsAll.value = (res?.items || []).map(normalizeProduct).filter(isGameType)
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
      await apiPost(
        '/products',
        {
          type_code: newProduct.type_code || PRODUCT_TYPE_PRIMARY,
          title: newProduct.title,
          short_title: newProduct.short_title || null,
          link: isGameType(newProduct) ? (newProduct.link || null) : null,
          text_lang: isGameType(newProduct) ? (newProduct.text_lang || null) : null,
          audio_lang: isGameType(newProduct) ? (newProduct.audio_lang || null) : null,
          vr_support: isGameType(newProduct) ? (newProduct.vr_support || null) : null,
          platform_codes: isGameType(newProduct) ? (newProduct.platform_codes || []) : [],
          provider: !isGameType(newProduct) ? (newProduct.provider || null) : null,
          billing_period: !isGameType(newProduct) ? (newProduct.billing_period || null) : null,
          subscription_notes: !isGameType(newProduct) ? (newProduct.subscription_notes || null) : null,
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
      await apiPut(
        `/products/${editProduct.product_id}`,
        {
          type_code: editProduct.type_code,
          title: editProduct.title,
          short_title: editProduct.short_title || null,
          link: isGameType(editProduct) ? (editProduct.link || null) : null,
          text_lang: isGameType(editProduct) ? (editProduct.text_lang || null) : null,
          audio_lang: isGameType(editProduct) ? (editProduct.audio_lang || null) : null,
          vr_support: isGameType(editProduct) ? (editProduct.vr_support || null) : null,
          platform_codes: isGameType(editProduct) ? (editProduct.platform_codes || []) : [],
          provider: !isGameType(editProduct) ? (editProduct.provider || null) : null,
          billing_period: !isGameType(editProduct) ? (editProduct.billing_period || null) : null,
          subscription_notes: !isGameType(editProduct) ? (editProduct.subscription_notes || null) : null,
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
    productFilters.type_code = PRODUCT_TYPE_PRIMARY
    productFilters.platform_code = ''
    productFilters.region_code = ''
    productFilterDraft.title = productFilters.q
    productFilterDraft.type = PRODUCT_TYPE_PRIMARY
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
