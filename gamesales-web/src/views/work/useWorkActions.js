export function useWorkActions({
  auth,
  apiGet,
  apiPost,
  mapApiError,
  requestDealConfirm,
  loadDeals,
  loadAccounts,
  loadProducts,
  accountsPage,
  accountsPageInput,
  productsPage,
  productsPageInput,
  newDeal,
  editDeal,
  newDealProductSearch,
  editDealProductSearch,
  quickNewProduct,
  quickEditProduct,
  quickNewProductError,
  quickEditProductError,
  accountSlotAssignments,
  accountSlotAssignmentsLoading,
  accountSlotAssignmentsError,
  productSlotAssignments,
  productSlotAssignmentsLoading,
  productSlotAssignmentsError,
  accountSlotReleaseLoading,
  editAccount,
  showDealForm,
  dealError,
  loadAccountSlotStatus,
  loadDealAccountAssignments,
  loadDealAccountsForProduct,
  loadDealProductAssignments,
  productAccountsSort,
  productAccountsPage,
  productAccountsTotalPages,
  closeProductModal,
  goToAccount,
}) {
  let accountSlotAssignmentsRequestSeq = 0

  // Распознает кратковременный сетевой сбой браузера, который стоит тихо повторить.
  function isTransientFetchError(error) {
    const text = String(error?.message || '').toLowerCase()
    return text.includes('failed to fetch') || text.includes('networkerror')
  }

  // Небольшая пауза перед повтором, чтобы сгладить редкие скачки сети/прокси.
  async function sleep(ms) {
    await new Promise((resolve) => setTimeout(resolve, ms))
  }
  // Переход из карточки товара прямо к аккаунту.
  function openAccountFromProduct(login) {
    if (!login) return
    closeProductModal()
    goToAccount(login)
  }

  // Применяет поиск по сделкам.
  function applyDealSearch() {
    loadDeals(1)
  }

  // Применяет поиск по аккаунтам.
  function applyAccountSearch() {
    accountsPage.value = 1
    accountsPageInput.value = 1
    loadAccounts()
  }

  // Применяет поиск по товарам.
  function applyProductSearch() {
    productsPage.value = 1
    productsPageInput.value = 1
    loadProducts()
  }

  function syncNewDealProductSearch() {
    newDealProductSearch.value = ''
  }

  function syncEditDealProductSearch() {
    editDealProductSearch.value = ''
  }

  function onNewDealProductSearch() {
    if (newDeal.product_id) newDeal.product_id = ''
    quickNewProductError.value = ''
    if (newDealProductSearch.value) quickNewProduct.title = newDealProductSearch.value
  }

  function onEditDealProductSearch() {
    if (editDeal.product_id) editDeal.product_id = ''
    quickEditProductError.value = ''
    if (editDealProductSearch.value) quickEditProduct.title = editDealProductSearch.value
  }

  // Подгружает назначения слотов у аккаунта для модалки аккаунта.
  async function loadAccountSlotAssignments(accountId) {
    const requestId = ++accountSlotAssignmentsRequestSeq
    if (!accountId) {
      accountSlotAssignments.value = []
      return
    }
    accountSlotAssignmentsLoading.value = true
    accountSlotAssignmentsError.value = null
    try {
      let data
      try {
        data = await apiGet(`/accounts/${accountId}/slot-assignments`, { token: auth.state.token })
      } catch (e) {
        if (!isTransientFetchError(e)) throw e
        await sleep(250)
        data = await apiGet(`/accounts/${accountId}/slot-assignments`, { token: auth.state.token })
      }
      // Если пользователь уже переключился на другую карточку, старый ответ игнорируем.
      if (requestId !== accountSlotAssignmentsRequestSeq || Number(editAccount?.account_id || 0) !== Number(accountId || 0)) return
      accountSlotAssignments.value = data || []
    } catch (e) {
      if (requestId !== accountSlotAssignmentsRequestSeq || Number(editAccount?.account_id || 0) !== Number(accountId || 0)) return
      accountSlotAssignmentsError.value = mapApiError(e?.message)
      accountSlotAssignments.value = []
    } finally {
      if (requestId === accountSlotAssignmentsRequestSeq) {
        accountSlotAssignmentsLoading.value = false
      }
    }
  }

  // Подгружает назначения слотов у товара по product-маршруту.
  async function loadProductSlotAssignments(productId) {
    if (!productId) {
      productSlotAssignments.value = []
      return
    }
    productSlotAssignmentsLoading.value = true
    productSlotAssignmentsError.value = null
    try {
      // Используем только product-маршрут назначений слотов.
      const data = await apiGet(`/products/${productId}/slot-assignments`, { token: auth.state.token })
      productSlotAssignments.value = data || []
    } catch (e) {
      productSlotAssignmentsError.value = mapApiError(e?.message)
      productSlotAssignments.value = []
    } finally {
      productSlotAssignmentsLoading.value = false
    }
  }

  // Снимает слот у покупателя и обновляет связанные данные на форме.
  async function releaseSlotAssignment(assignmentId) {
    if (!assignmentId) return
    // Показываем единое оформление подтверждения для операций со слотами.
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
      await apiPost(`/slot-assignments/${assignmentId}/release`, {}, { token: auth.state.token })
      if (editAccount.open && editAccount.account_id) {
        await loadAccountSlotAssignments(editAccount.account_id)
      }
      if (editDeal.open && editDeal.account_id) {
        await loadAccountSlotStatus('edit')
        await loadDealAccountAssignments('edit')
        await loadDealAccountsForProduct('edit')
      }
      if (showDealForm.value && newDeal.account_id) {
        await loadAccountSlotStatus('new')
        await loadDealAccountAssignments('new')
        await loadDealAccountsForProduct('new')
      }
      if (editDeal.open) {
        await loadDealProductAssignments('edit')
      }
      if (showDealForm.value) {
        await loadDealProductAssignments('new')
      }
    } catch (e) {
      dealError.value = mapApiError(e?.message)
    } finally {
      accountSlotReleaseLoading.value = false
    }
  }

  // Возвращает ранее снятый слот и синхронизирует зависимые блоки интерфейса.
  async function restoreSlotAssignment(assignmentId) {
    if (!assignmentId) return
    const accepted = typeof requestDealConfirm === 'function'
      ? await requestDealConfirm({
        title: 'Подтверждение',
        message: 'Вернуть снятый слот?',
        confirmText: 'Вернуть',
        cancelText: 'Отмена',
      })
      : window.confirm('Вернуть снятый слот?')
    if (!accepted) return
    accountSlotReleaseLoading.value = true
    try {
      await apiPost(`/slot-assignments/${assignmentId}/restore`, {}, { token: auth.state.token })
      if (editAccount.open && editAccount.account_id) {
        await loadAccountSlotAssignments(editAccount.account_id)
      }
      if (editDeal.open && editDeal.account_id) {
        await loadAccountSlotStatus('edit')
        await loadDealAccountAssignments('edit')
        await loadDealAccountsForProduct('edit')
      }
      if (showDealForm.value && newDeal.account_id) {
        await loadAccountSlotStatus('new')
        await loadDealAccountAssignments('new')
        await loadDealAccountsForProduct('new')
      }
      if (editDeal.open) {
        await loadDealProductAssignments('edit')
      }
      if (showDealForm.value) {
        await loadDealProductAssignments('new')
      }
    } catch (e) {
      dealError.value = mapApiError(e?.message)
    } finally {
      accountSlotReleaseLoading.value = false
    }
  }

  // Переключает сортировку таблицы аккаунтов внутри модалки товара.
  function sortProductAccounts(key) {
    const current = productAccountsSort.value
    if (current.key === key) {
      current.dir = current.dir === 'asc' ? 'desc' : 'asc'
    } else {
      productAccountsSort.value = { key, dir: 'asc' }
    }
    productAccountsPage.value = 1
  }

  function nextProductAccountsPage() {
    if (productAccountsPage.value < productAccountsTotalPages.value) {
      productAccountsPage.value += 1
    }
  }

  function prevProductAccountsPage() {
    if (productAccountsPage.value > 1) {
      productAccountsPage.value -= 1
    }
  }

  return {
    openAccountFromProduct,
    applyProductSearch,
    loadProductSlotAssignments,
    sortProductAccounts,
    nextProductAccountsPage,
    prevProductAccountsPage,
    applyDealSearch,
    applyAccountSearch,
    syncNewDealProductSearch,
    syncEditDealProductSearch,
    onNewDealProductSearch,
    onEditDealProductSearch,
    loadAccountSlotAssignments,
    releaseSlotAssignment,
    restoreSlotAssignment,
  }
}
