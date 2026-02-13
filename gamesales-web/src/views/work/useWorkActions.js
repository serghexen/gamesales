export function useWorkActions({
  auth,
  apiGet,
  apiPost,
  mapApiError,
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
    if (!accountId) {
      accountSlotAssignments.value = []
      return
    }
    accountSlotAssignmentsLoading.value = true
    accountSlotAssignmentsError.value = null
    try {
      const data = await apiGet(`/accounts/${accountId}/slot-assignments`, { token: auth.state.token })
      accountSlotAssignments.value = data || []
    } catch (e) {
      accountSlotAssignmentsError.value = mapApiError(e?.message)
      accountSlotAssignments.value = []
    } finally {
      accountSlotAssignmentsLoading.value = false
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
    if (!window.confirm('Снять слот у покупателя?')) return
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
  }
}
