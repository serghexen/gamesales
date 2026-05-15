import { PRODUCT_TYPE_PRIMARY } from './domainUtils'

export function useDealsFlow({
  auth,
  apiGet,
  apiPost,
  apiPut,
  mapApiError,
  requestDealConfirm,
  isSlotTypeSupportedForProduct,
  slotTypes,
  productsAll,
  accountsAll,
  editDeal,
  newDeal,
  accountSlotStatusNew,
  accountSlotStatusEdit,
  dealAccountAssignmentsNew,
  dealAccountAssignmentsEdit,
  dealAccountAssignmentsLoadingNew,
  dealAccountAssignmentsLoadingEdit,
  dealGameAssignmentsNew,
  dealGameAssignmentsEdit,
  dealGameAssignmentsLoadingNew,
  dealGameAssignmentsLoadingEdit,
  dealSlotAvailabilityNew,
  dealSlotAvailabilityEdit,
  dealSlotAvailabilityLoadingNew,
  dealSlotAvailabilityLoadingEdit,
  dealAccountsForProductNew,
  dealAccountsForProductEdit,
  dealAccountsForProductLoading,
  accountSlotReleaseLoading,
  dealSlotAutoAssign,
  dealError,
  quickNewProduct,
  quickEditProduct,
  quickNewProductLoading,
  quickEditProductLoading,
  quickNewProductError,
  quickEditProductError,
  quickNewAccount,
  quickEditAccount,
  quickNewAccountLoading,
  quickEditAccountLoading,
  quickNewAccountError,
  quickEditAccountError,
  newDealProductSearch,
  editDealProductSearch,
  subscriptionFreeProductIdsNew,
  subscriptionFreeProductIdsEdit,
  subscriptionFreeProductIdsLoadingNew,
  subscriptionFreeProductIdsLoadingEdit,
  subscriptionTermsNew,
  subscriptionTermsEdit,
  subscriptionTermsLoadingNew,
  subscriptionTermsLoadingEdit,
  subscriptionAvailableItemsNew,
  subscriptionAvailableItemsEdit,
  subscriptionAvailableItemsLoadingNew,
  subscriptionAvailableItemsLoadingEdit,
  quickNewSubscriptionTerm,
  quickEditSubscriptionTerm,
  quickNewSubscriptionTermLoading,
  quickEditSubscriptionTermLoading,
  quickNewSubscriptionTermError,
  quickEditSubscriptionTermError,
  loadProductsAll,
  loadAccountsAll,
}) {
  // Возвращает дату для quick-срока: текущая дата плюс один год.
  const getDefaultSubscriptionTermDate = () => {
    const nextYearDate = new Date()
    nextYearDate.setFullYear(nextYearDate.getFullYear() + 1)
    const year = nextYearDate.getFullYear()
    const month = String(nextYearDate.getMonth() + 1).padStart(2, '0')
    const day = String(nextYearDate.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  const subscriptionTermsNewRef = subscriptionTermsNew || { value: [] }
  const subscriptionTermsEditRef = subscriptionTermsEdit || { value: [] }
  const subscriptionTermsLoadingNewRef = subscriptionTermsLoadingNew || { value: false }
  const subscriptionTermsLoadingEditRef = subscriptionTermsLoadingEdit || { value: false }
  const quickNewSubscriptionTermRef = quickNewSubscriptionTerm || { account_id: '', valid_until: getDefaultSubscriptionTermDate(), notes: '' }
  const quickEditSubscriptionTermRef = quickEditSubscriptionTerm || { account_id: '', valid_until: getDefaultSubscriptionTermDate(), notes: '' }

  // Возвращает сегодняшнюю дату в формате YYYY-MM-DD для обязательного поля account_date.
  function getTodayAccountDate() {
    const now = new Date()
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  }

  // Подбирает регион для быстрого аккаунта: сначала из сделки, затем из выбранного товара.
  function resolveQuickAccountRegionCode(target, selectedProductId = 0, fallbackSubscriptionProductId = 0) {
    const isEdit = target === 'edit'
    const dealRegion = String((isEdit ? editDeal.region_code : newDeal.region_code) || '').trim()
    if (dealRegion) return dealRegion
    const productId = Number(selectedProductId || fallbackSubscriptionProductId || 0)
    if (!productId) return ''
    const list = Array.isArray(productsAll.value) ? productsAll.value : []
    const product = list.find((item) => Number(item?.product_id || 0) === productId)
    return String(product?.region_code || '').trim()
  }
  const quickNewSubscriptionTermLoadingRef = quickNewSubscriptionTermLoading || { value: false }
  const quickEditSubscriptionTermLoadingRef = quickEditSubscriptionTermLoading || { value: false }
  const quickNewSubscriptionTermErrorRef = quickNewSubscriptionTermError || { value: '' }
  const quickEditSubscriptionTermErrorRef = quickEditSubscriptionTermError || { value: '' }
  const subscriptionAvailableItemsNewRef = subscriptionAvailableItemsNew || { value: [] }
  const subscriptionAvailableItemsEditRef = subscriptionAvailableItemsEdit || { value: [] }
  const subscriptionAvailableItemsLoadingNewRef = subscriptionAvailableItemsLoadingNew || { value: false }
  const subscriptionAvailableItemsLoadingEditRef = subscriptionAvailableItemsLoadingEdit || { value: false }

  // Используем единый product-first загрузчик справочника.
  const reloadProductsAll = loadProductsAll

  // Возвращает выбранный товар в форме сделки.
  function resolveSelectedDealRefs(target) {
    const isEdit = target === 'edit'
    const deal = isEdit ? editDeal : newDeal
    const directProductId = Number(deal?.product_id || 0) || null
    return { productId: directProductId }
  }

  // Определяет, относится ли выбранный товар к подпискам.
  function isSubscriptionProduct(productId) {
    if (!productId) return false
    const list = Array.isArray(productsAll?.value) ? productsAll.value : []
    const found = list.find((item) => Number(item?.product_id || 0) === Number(productId))
    return String(found?.type_code || '').trim().toLowerCase() === 'subscription'
  }

  // Собирает id подписок, где выбранный слот действительно свободен.
  async function loadSubscriptionFreeProductIds(target, slotTypeCode) {
    const isEdit = target === 'edit'
    const listRef = isEdit ? subscriptionFreeProductIdsEdit : subscriptionFreeProductIdsNew
    const loadingRef = isEdit ? subscriptionFreeProductIdsLoadingEdit : subscriptionFreeProductIdsLoadingNew
    const normalizedSlotTypeCode = String(slotTypeCode || '').trim()
    if (!normalizedSlotTypeCode) {
      listRef.value = []
      loadingRef.value = false
      return
    }
    const subscriptionProducts = (productsAll.value || []).filter((item) => String(item?.type_code || '').trim().toLowerCase() === 'subscription')
    if (!subscriptionProducts.length) {
      listRef.value = []
      loadingRef.value = false
      return
    }
    loadingRef.value = true
    try {
      // Берем с backend готовый список id, чтобы не слать запрос на каждую подписку.
      const data = await apiGet(
        `/products/subscriptions/free-by-slot?slot_type_code=${encodeURIComponent(normalizedSlotTypeCode)}`,
        { token: auth.state.token }
      )
      const ids = Array.isArray(data) ? data.map((item) => Number(item || 0)).filter(Boolean) : []
      listRef.value = ids
    } catch {
      listRef.value = []
    } finally {
      loadingRef.value = false
    }
  }

  // Загружает доступные сроки подписки под выбранные товар+слот.
  async function loadSubscriptionTerms(target) {
    const isEdit = target === 'edit'
    const deal = isEdit ? editDeal : newDeal
    const listRef = isEdit ? subscriptionTermsEditRef : subscriptionTermsNewRef
    const loadingRef = isEdit ? subscriptionTermsLoadingEditRef : subscriptionTermsLoadingNewRef
    const productId = Number(deal?.product_id || 0)
    const slotTypeCode = String(deal?.slot_type_code || '').trim()
    if (!productId || !slotTypeCode || !isSubscriptionProduct(productId)) {
      listRef.value = []
      loadingRef.value = false
      return
    }
    loadingRef.value = true
    try {
      const available = await apiGet(
        `/products/subscriptions/${encodeURIComponent(productId)}/terms/available?slot_type_code=${encodeURIComponent(slotTypeCode)}`,
        { token: auth.state.token }
      )
      let list = Array.isArray(available) ? available : []
      // Для редактирования сохраняем отображение уже выбранного срока, даже если он занят текущей сделкой.
      const selectedTermId = Number(deal?.subscription_term_id || 0)
      const hasSelected = selectedTermId && list.some((item) => Number(item?.term_id || 0) === selectedTermId)
      if (isEdit && selectedTermId && !hasSelected) {
        try {
          const allTerms = await apiGet(`/products/subscriptions/${encodeURIComponent(productId)}/terms`, { token: auth.state.token })
          const selected = (Array.isArray(allTerms) ? allTerms : []).find((item) => Number(item?.term_id || 0) === selectedTermId)
          if (selected) list = [selected, ...list]
        } catch {
          // Ошибка фоновой догрузки не должна ломать форму.
        }
      }
      listRef.value = list
      if (selectedTermId && !list.some((item) => Number(item?.term_id || 0) === selectedTermId)) {
        deal.subscription_term_id = ''
      }
      // Если срок выбран, синхронизируем аккаунт по сроку.
      const selected = list.find((item) => Number(item?.term_id || 0) === Number(deal?.subscription_term_id || 0))
      if (selected?.account_id) {
        deal.account_id = Number(selected.account_id)
      }
    } catch {
      listRef.value = []
    } finally {
      loadingRef.value = false
    }
  }

  // Загружает плоский список доступных подписок (товар + срок) для выбранного слота.
  async function loadAvailableSubscriptionItems(target, slotTypeCode) {
    const isEdit = target === 'edit'
    const listRef = isEdit ? subscriptionAvailableItemsEditRef : subscriptionAvailableItemsNewRef
    const loadingRef = isEdit ? subscriptionAvailableItemsLoadingEditRef : subscriptionAvailableItemsLoadingNewRef
    const normalizedSlotTypeCode = String(slotTypeCode || '').trim()
    if (!normalizedSlotTypeCode) {
      listRef.value = []
      loadingRef.value = false
      return
    }
    loadingRef.value = true
    try {
      const data = await apiGet(
        `/products/subscriptions/terms/available-for-deal?slot_type_code=${encodeURIComponent(normalizedSlotTypeCode)}`,
        { token: auth.state.token }
      )
      listRef.value = Array.isArray(data) ? data : []
    } catch {
      listRef.value = []
    } finally {
      loadingRef.value = false
    }
  }

  // Быстро создает срок подписки из модалки сделки.
  async function createQuickSubscriptionTerm(target) {
    const isEdit = target === 'edit'
    const deal = isEdit ? editDeal : newDeal
    const state = isEdit ? quickEditSubscriptionTermRef : quickNewSubscriptionTermRef
    const loadingRef = isEdit ? quickEditSubscriptionTermLoadingRef : quickNewSubscriptionTermLoadingRef
    const errorRef = isEdit ? quickEditSubscriptionTermErrorRef : quickNewSubscriptionTermErrorRef
    errorRef.value = ''
    const productId = Number(deal?.product_id || 0)
    if (!productId || !isSubscriptionProduct(productId)) {
      errorRef.value = 'Сначала выберите товар типа подписка'
      return
    }
    const accountId = Number(state?.account_id || deal?.account_id || 0)
    const validUntil = String(state?.valid_until || '').trim()
    if (!accountId) {
      errorRef.value = 'Выберите аккаунт для срока'
      return
    }
    if (!validUntil) {
      errorRef.value = 'Укажите дату окончания'
      return
    }
    loadingRef.value = true
    try {
      const created = await apiPost(
        `/products/subscriptions/${encodeURIComponent(productId)}/terms`,
        {
          account_id: accountId,
          valid_until: validUntil,
          notes: state?.notes ? String(state.notes).trim() : null,
        },
        { token: auth.state.token }
      )
      await loadSubscriptionTerms(target)
      if (created?.term_id) deal.subscription_term_id = Number(created.term_id)
      if (created?.account_id) deal.account_id = Number(created.account_id)
      state.account_id = ''
      state.valid_until = getDefaultSubscriptionTermDate()
      state.notes = ''
    } catch (e) {
      errorRef.value = mapApiError(e?.message)
    } finally {
      loadingRef.value = false
    }
  }

  // Быстрое создание товара типа "игра" прямо из формы сделки.
  async function createQuickProduct(target) {
    const isEdit = target === 'edit'
    const state = isEdit ? quickEditProduct : quickNewProduct
    const loading = isEdit ? quickEditProductLoading : quickNewProductLoading
    const error = isEdit ? quickEditProductError : quickNewProductError
    error.value = ''
    if (!state.title) {
      error.value = 'Укажите название товара'
      return
    }
    if (!state.platform_codes.length) {
      error.value = 'Выберите платформу'
      return
    }
    loading.value = true
    try {
      const created = await apiPost(
        '/products',
        {
          type_code: PRODUCT_TYPE_PRIMARY,
          title: state.title,
          platform_codes: state.platform_codes,
          short_title: null,
          link: null,
          text_lang: null,
          audio_lang: null,
          vr_support: null,
          region_code: null,
        },
        { token: auth.state.token }
      )
      await reloadProductsAll()
      if (created?.product_id) {
        if (isEdit) {
          editDeal.product_id = created.product_id
          editDealProductSearch.value = ''
        } else {
          newDeal.product_id = created.product_id
          newDealProductSearch.value = ''
        }
      }
      state.title = ''
      state.platform_codes = []
    } catch (e) {
      error.value = mapApiError(e?.message)
    } finally {
      loading.value = false
    }
  }

  // Загружает подходящие аккаунты для выбранного товара и типа слота.
  async function loadDealAccountsForProduct(target) {
    const isEdit = target === 'edit'
    const refs = resolveSelectedDealRefs(target)
    const productId = refs.productId
    const slotTypeCode = isEdit ? editDeal.slot_type_code : newDeal.slot_type_code
    const slotSupported = productId ? isSlotTypeSupportedForProduct(slotTypeCode, productId) : true
    if (!productId || !slotTypeCode || !slotSupported) {
      if (isEdit) dealAccountsForProductEdit.value = []
      else dealAccountsForProductNew.value = []
      return
    }
    dealAccountsForProductLoading.value = true
    try {
      // Список аккаунтов всегда берем из общего for-deal, чтобы учитывались реальные привязки товара к аккаунту.
      const params = new URLSearchParams()
      params.set('product_id', String(productId))
      if (slotTypeCode) params.set('slot_type_code', slotTypeCode)
      const data = await apiGet(`/accounts/for-deal?${params.toString()}`, { token: auth.state.token })
      if (isEdit) {
        let list = data || []
        const currentId = editDeal.account_id
        if (currentId && !list.find((a) => a.account_id === currentId)) {
          const fallback = (accountsAll.value || []).find((a) => a.account_id === currentId)
          if (fallback) list = [fallback, ...list]
        }
        dealAccountsForProductEdit.value = list
      } else {
        dealAccountsForProductNew.value = data || []
      }
    } catch {
      if (isEdit) dealAccountsForProductEdit.value = []
      else dealAccountsForProductNew.value = []
    } finally {
      dealAccountsForProductLoading.value = false
    }
  }

  // Загружает состояние слотов выбранного аккаунта.
  async function loadAccountSlotStatus(target) {
    const isEdit = target === 'edit'
    const accountId = isEdit ? editDeal.account_id : newDeal.account_id
    if (!accountId) {
      if (isEdit) accountSlotStatusEdit.value = []
      else accountSlotStatusNew.value = []
      return
    }
    try {
      const data = await apiGet(`/accounts/${accountId}/slot-status`, { token: auth.state.token })
      if (isEdit) accountSlotStatusEdit.value = data || []
      else accountSlotStatusNew.value = data || []
    } catch {
      if (isEdit) accountSlotStatusEdit.value = []
      else accountSlotStatusNew.value = []
    }
  }

  // Загружает назначения слотов по выбранному аккаунту.
  async function loadDealAccountAssignments(target) {
    const isEdit = target === 'edit'
    const accountId = isEdit ? editDeal.account_id : newDeal.account_id
    if (!accountId) {
      if (isEdit) dealAccountAssignmentsEdit.value = []
      else dealAccountAssignmentsNew.value = []
      return
    }
    const loading = isEdit ? dealAccountAssignmentsLoadingEdit : dealAccountAssignmentsLoadingNew
    loading.value = true
    try {
      const data = await apiGet(`/accounts/${accountId}/slot-assignments`, { token: auth.state.token })
      if (isEdit) dealAccountAssignmentsEdit.value = data || []
      else dealAccountAssignmentsNew.value = data || []
    } catch {
      if (isEdit) dealAccountAssignmentsEdit.value = []
      else dealAccountAssignmentsNew.value = []
    } finally {
      loading.value = false
    }
  }

  // Загружает назначения слотов по выбранному товару.
  async function loadDealProductAssignments(target) {
    const isEdit = target === 'edit'
    const refs = resolveSelectedDealRefs(target)
    const productId = refs.productId
    if (!productId) {
      if (isEdit) dealGameAssignmentsEdit.value = []
      else dealGameAssignmentsNew.value = []
      return
    }
    const loading = isEdit ? dealGameAssignmentsLoadingEdit : dealGameAssignmentsLoadingNew
    loading.value = true
    try {
      // Загружаем назначения только по product-маршруту.
      const data = await apiGet(`/products/${productId}/slot-assignments`, { token: auth.state.token })
      if (isEdit) dealGameAssignmentsEdit.value = data || []
      else dealGameAssignmentsNew.value = data || []
    } catch {
      if (isEdit) dealGameAssignmentsEdit.value = []
      else dealGameAssignmentsNew.value = []
    } finally {
      loading.value = false
    }
  }

  // Загружает доступность слотов для выбранного товара.
  async function loadDealSlotAvailability(target) {
    const isEdit = target === 'edit'
    const refs = resolveSelectedDealRefs(target)
    const productId = refs.productId
    if (!productId) {
      if (isEdit) dealSlotAvailabilityEdit.value = {}
      else dealSlotAvailabilityNew.value = {}
      return
    }
    if (isSubscriptionProduct(productId)) {
      // Для подписок считаем слоты доступными по умолчанию и не дергаем game-only эндпоинт.
      const availabilityMap = Object.fromEntries(
        (slotTypes.value || []).map((item) => [item.code, { hasFree: true }])
      )
      if (isEdit) dealSlotAvailabilityEdit.value = availabilityMap
      else dealSlotAvailabilityNew.value = availabilityMap
      return
    }
    const loading = isEdit ? dealSlotAvailabilityLoadingEdit : dealSlotAvailabilityLoadingNew
    loading.value = true
    try {
      const list = slotTypes.value || []
      let availabilityMap = {}
      let availabilityLoaded = false
      try {
        const qs = `product_id=${encodeURIComponent(productId)}`
        const data = await apiGet(`/accounts/for-deal/availability?${qs}`, { token: auth.state.token })
        availabilityMap = Object.fromEntries((data || []).map((i) => [i.slot_type_code, { hasFree: Boolean(i.has_free) }]))
        availabilityLoaded = true
      } catch {
        availabilityMap = {}
      }
      if (!availabilityLoaded) {
        const results = await Promise.all(
          list.map(async (t) => {
            const supported = isSlotTypeSupportedForProduct(t.code, productId)
            if (!supported) {
              return [t.code, { hasFree: false }]
            }
            try {
              const params = new URLSearchParams()
              params.set('product_id', String(productId))
              params.set('slot_type_code', t.code)
              const data = await apiGet(`/accounts/for-deal?${params.toString()}`, { token: auth.state.token })
              return [t.code, { hasFree: Array.isArray(data) && data.length > 0 }]
            } catch {
              return [t.code, { hasFree: false }]
            }
          })
        )
        availabilityMap = Object.fromEntries(results)
      }
      if (availabilityLoaded) {
        const normalized = {}
        for (const t of list) {
          const supported = isSlotTypeSupportedForProduct(t.code, productId)
          normalized[t.code] = supported ? (availabilityMap[t.code] || { hasFree: false }) : { hasFree: false }
        }
        availabilityMap = normalized
      }
      if (isEdit) dealSlotAvailabilityEdit.value = availabilityMap
      else dealSlotAvailabilityNew.value = availabilityMap
    } finally {
      loading.value = false
    }
  }

  async function releaseSlotFromDeal(item, target) {
    if (!item?.assignment_id) return
    // Для снятия слота используем фирменное подтверждение вместо системного confirm.
    const accepted = typeof requestDealConfirm === 'function'
      ? await requestDealConfirm({
        title: 'Подтверждение',
        message: 'Снять слот у покупателя?',
        confirmText: 'Снять',
        cancelText: 'Отмена',
      })
      : window.confirm('Снять слот у покупателя?')
    if (!accepted) return
    accountSlotReleaseLoading.value = true
    try {
      await apiPost(`/slot-assignments/${item.assignment_id}/release`, {}, { token: auth.state.token })
      const accountId = item.account_id
      const slotTypeCode = item.slot_type_code
      dealSlotAutoAssign.value = true
      if (target === 'edit') {
        editDeal.account_id = accountId || ''
        editDeal.slot_type_code = slotTypeCode || ''
        await loadAccountSlotStatus('edit')
        await loadDealAccountAssignments('edit')
        await loadDealAccountsForProduct('edit')
        await loadDealProductAssignments('edit')
        await loadDealSlotAvailability('edit')
      } else {
        newDeal.account_id = accountId || ''
        newDeal.slot_type_code = slotTypeCode || ''
        await loadAccountSlotStatus('new')
        await loadDealAccountAssignments('new')
        await loadDealAccountsForProduct('new')
        await loadDealProductAssignments('new')
        await loadDealSlotAvailability('new')
      }
    } catch (e) {
      dealError.value = mapApiError(e?.message)
    } finally {
      dealSlotAutoAssign.value = false
      accountSlotReleaseLoading.value = false
    }
  }

  async function createQuickAccount(target) {
    const isEdit = target === 'edit'
    const state = isEdit ? quickEditAccount : quickNewAccount
    const loading = isEdit ? quickEditAccountLoading : quickNewAccountLoading
    const error = isEdit ? quickEditAccountError : quickNewAccountError
    const deal = isEdit ? editDeal : newDeal
    error.value = ''
    if (!state.login_name) {
      error.value = 'Укажите логин'
      return
    }
    if (!state.domain_code) {
      error.value = 'Выберите домен'
      return
    }
    if (!state.platform_codes.length) {
      error.value = 'Выберите платформу'
      return
    }
    if (!String(state.password || '').trim()) {
      error.value = 'Укажите пароль аккаунта'
      return
    }
    const selectedRefs = resolveSelectedDealRefs(target)
    const selectedProductId = Number(selectedRefs.productId || 0)
    const selectedProductIsSubscription = selectedProductId && isSubscriptionProduct(selectedProductId)
    const requestedSubscriptionProductId = Number(state.subscription_product_id || 0)
    const fallbackSubscriptionProductId = requestedSubscriptionProductId && isSubscriptionProduct(requestedSubscriptionProductId)
      ? requestedSubscriptionProductId
      : 0
    // Для сценария "нет свободных" даем выбрать подписку прямо в quick-форме.
    const quickSubscriptionProductId = selectedProductIsSubscription ? selectedProductId : fallbackSubscriptionProductId
    if (
      String(deal?.deal_type_code || '').toLowerCase() === 'rental'
      && String(deal?.slot_type_code || '').trim()
      && !selectedProductId
      && !quickSubscriptionProductId
    ) {
      error.value = 'Выберите подписку'
      return
    }
    const regionCode = resolveQuickAccountRegionCode(target, selectedProductId, quickSubscriptionProductId)
    loading.value = true
    try {
      const created = await apiPost(
        '/accounts',
        {
          login_name: state.login_name,
          domain_code: state.domain_code,
          region_code: regionCode || null,
          account_date: getTodayAccountDate(),
          notes: state.notes ? String(state.notes).trim() : null,
        },
        { token: auth.state.token }
      )
      if (created?.account_id && state.password) {
        try {
          await apiPost(
            `/accounts/${created.account_id}/secrets`,
            { secret_key: 'password', secret_value: state.password },
            { token: auth.state.token }
          )
        } catch {
          // Ошибка сохранения пароля не должна блокировать создание аккаунта.
        }
      }
      await loadAccountsAll()
      // Для подписок не используем game-only привязки account_assets, чтобы не получать 400 от API.
      if (created?.account_id && selectedProductId && !isSubscriptionProduct(selectedProductId)) {
        try {
          // Работаем только с product-привязками аккаунта.
          const existingProducts = await apiGet(`/accounts/${created.account_id}/products`, { token: auth.state.token })
          const ids = new Set((existingProducts || []).map((p) => Number(p?.product_id || 0)).filter(Boolean))
          ids.add(selectedProductId)
          await apiPut(
            `/accounts/${created.account_id}/products`,
            { product_ids: Array.from(ids) },
            { token: auth.state.token }
          )
        } catch {
          // Ошибка привязки не должна мешать созданию аккаунта.
        }
      }
      if (created?.account_id && quickSubscriptionProductId) {
        try {
          // После быстрого создания аккаунта сразу добавляем срок подписки на +1 год.
          const createdTerm = await apiPost(
            `/products/subscriptions/${encodeURIComponent(quickSubscriptionProductId)}/terms`,
            {
              account_id: created.account_id,
              valid_until: getDefaultSubscriptionTermDate(),
              notes: String(state.notes || '').trim() || null,
            },
            { token: auth.state.token }
          )
          deal.product_id = quickSubscriptionProductId
          deal.subscription_term_id = Number(createdTerm?.term_id || 0) || ''
        } catch {
          // Ошибка создания срока не должна откатывать уже созданный аккаунт.
        }
      }
      if (created?.account_id) {
        if (isEdit) {
          editDeal.account_id = created.account_id
        } else {
          newDeal.account_id = created.account_id
        }
      }
      if (created?.account_id) {
        const targetList = isEdit ? dealAccountsForProductEdit : dealAccountsForProductNew
        const exists = (targetList.value || []).some((a) => a.account_id === created.account_id)
        if (!exists) {
          const fallback = (accountsAll.value || []).find((a) => a.account_id === created.account_id) || created
          targetList.value = [fallback, ...(targetList.value || [])]
        }
        if (isEdit) {
          dealGameAssignmentsEdit.value = []
        } else {
          dealGameAssignmentsNew.value = []
        }
      }
      if (isEdit) {
        await loadDealSlotAvailability('edit')
        await loadDealAccountsForProduct('edit')
      } else {
        await loadDealSlotAvailability('new')
        await loadDealAccountsForProduct('new')
      }
      state.login_name = ''
      state.domain_code = ''
      state.platform_codes = []
      state.password = ''
      state.notes = ''
      state.subscription_product_id = ''
    } catch (e) {
      error.value = mapApiError(e?.message)
    } finally {
      loading.value = false
    }
  }

  function clearNewDealProduct() {
    // Для подписок на крестик сбрасываем связку товар+срок+аккаунт, чтобы выбрать заново.
    const resetSubscriptionChain = isSubscriptionProduct(Number(newDeal.product_id || 0))
    newDeal.product_id = ''
    if (resetSubscriptionChain) {
      newDeal.subscription_term_id = ''
      newDeal.account_id = ''
    }
    newDealProductSearch.value = ''
    dealAccountsForProductNew.value = []
  }

  function clearEditDealProduct() {
    // В редактировании подписки крестик также очищает выбранный срок и аккаунт.
    const resetSubscriptionChain = isSubscriptionProduct(Number(editDeal.product_id || 0))
    editDeal.product_id = ''
    if (resetSubscriptionChain) {
      editDeal.subscription_term_id = ''
      editDeal.account_id = ''
    }
    editDealProductSearch.value = ''
    dealAccountsForProductEdit.value = []
  }

  return {
    createQuickProduct,
    createQuickAccount,
    clearNewDealProduct,
    clearEditDealProduct,
    loadDealAccountsForProduct,
    loadAccountSlotStatus,
    loadDealAccountAssignments,
    loadDealProductAssignments,
    loadDealSlotAvailability,
    loadSubscriptionFreeProductIds,
    loadAvailableSubscriptionItems,
    loadSubscriptionTerms,
    createQuickSubscriptionTerm,
    releaseSlotFromDeal,
  }
}
