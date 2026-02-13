import { PRODUCT_TYPE_PRIMARY } from './domainUtils'

export function useDealsFlow({
  auth,
  apiGet,
  apiPost,
  apiPut,
  mapApiError,
  isSlotTypeSupportedForProduct,
  slotTypes,
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
  loadProductsAll,
  loadAccountsAll,
}) {
  // Используем единый product-first загрузчик справочника.
  const reloadProductsAll = loadProductsAll

  // Возвращает выбранный товар в форме сделки.
  function resolveSelectedDealRefs(target) {
    const isEdit = target === 'edit'
    const deal = isEdit ? editDeal : newDeal
    const directProductId = Number(deal?.product_id || 0) || null
    return { productId: directProductId }
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
          logo_url: null,
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
    if (!window.confirm('Снять слот у покупателя?')) return
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
    loading.value = true
    try {
      const created = await apiPost(
        '/accounts',
        {
          login_name: state.login_name,
          domain_code: state.domain_code,
          region_code: isEdit ? editDeal.region_code || null : newDeal.region_code || null,
          account_date: null,
          notes: null,
        },
        { token: auth.state.token }
      )
      await loadAccountsAll()
      const selectedRefs = resolveSelectedDealRefs(target)
      const selectedProductId = selectedRefs.productId
      if (created?.account_id && selectedProductId) {
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
    } catch (e) {
      error.value = mapApiError(e?.message)
    } finally {
      loading.value = false
    }
  }

  function clearNewDealProduct() {
    newDeal.product_id = ''
    newDealProductSearch.value = ''
    dealAccountsForProductNew.value = []
  }

  function clearEditDealProduct() {
    editDeal.product_id = ''
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
    releaseSlotFromDeal,
  }
}
