export function useDealModalFlow({
  closeAllModals,
  resetModalPos,
  setActiveTab,
  showDealForm,
  dealError,
  dealOk,
  newDeal,
  editDeal,
  dealEditMode,
  dealInitLock,
  newDealResponsible,
  newDealCommentOpen,
  newDealGameSearch,
  editDealGameSearch,
  quickNewGame,
  quickEditGame,
  quickNewGameError,
  quickEditGameError,
  quickNewAccount,
  quickEditAccount,
  quickNewAccountError,
  quickEditAccountError,
  dealAccountsForGameNew,
  dealAccountsForGameEdit,
  dealAccountAssignmentsNew,
  dealAccountAssignmentsEdit,
  dealSlotAvailabilityNew,
  dealSlotAvailabilityEdit,
  nextTick,
  loadDealSlotAvailability,
}) {
  function cancelEditDeal() {
    editDeal.open = false
    editDeal.deal_id = null
    editDeal.created_at = ''
    editDeal.deal_type_code = 'sale'
    editDeal.account_id = ''
    editDeal.game_id = ''
    editDeal.customer_nickname = ''
    editDeal.source_id = ''
    editDeal.region_code = ''
    editDeal.slot_type_code = ''
    editDeal.price = 0
    editDeal.purchase_cost = 0
    editDeal.game_link = ''
    editDeal.purchase_at = ''
    editDeal.slots_used = 1
    editDeal.notes = ''
    editDeal.flow_status_code = ''
    dealEditMode.value = 'view'
    dealAccountAssignmentsEdit.value = []
    dealSlotAvailabilityEdit.value = {}
  }

  function openCreateDealModal() {
    closeAllModals()
    resetModalPos()
    showDealForm.value = true
    cancelEditDeal()
    dealError.value = null
    dealOk.value = null
    newDealCommentOpen.value = false
    newDealGameSearch.value = ''
    editDealGameSearch.value = ''
    quickNewGame.title = ''
    quickNewGame.platform_codes = []
    quickNewGameError.value = ''
    quickNewAccount.login_name = ''
    quickNewAccount.domain_code = ''
    quickNewAccount.platform_codes = []
    quickNewAccountError.value = ''
    dealAccountsForGameNew.value = []
    dealSlotAvailabilityNew.value = {}
  }

  function openCreateSaleModal() {
    setActiveTab('deals')
    openCreateDealModal()
    newDeal.deal_type_code = 'sale'
  }

  function openCreateSharingModal() {
    setActiveTab('deals')
    openCreateDealModal()
    newDeal.deal_type_code = 'rental'
  }

  function closeDealModal() {
    showDealForm.value = false
    cancelEditDeal()
    dealError.value = null
    dealOk.value = null
    newDeal.deal_type_code = 'sale'
    newDeal.account_id = ''
    newDeal.game_id = ''
    newDeal.customer_nickname = ''
    // Очищаем номер заказа, чтобы старое значение не переносилось в новую сделку.
    newDeal.order_number = ''
    newDeal.source_id = ''
    newDeal.region_code = ''
    newDeal.slot_type_code = ''
    newDeal.price = 0
    newDeal.purchase_cost = 0
    newDeal.game_link = ''
    newDeal.purchase_at = ''
    newDeal.slots_used = 1
    newDeal.notes = ''
    newDealResponsible.value = ''
    newDealCommentOpen.value = false
    newDealGameSearch.value = ''
    editDealGameSearch.value = ''
    quickNewGame.title = ''
    quickNewGame.platform_codes = []
    quickNewGameError.value = ''
    quickEditGame.title = ''
    quickEditGame.platform_codes = []
    quickEditGameError.value = ''
    quickNewAccount.login_name = ''
    quickNewAccount.domain_code = ''
    quickNewAccount.platform_codes = []
    quickNewAccountError.value = ''
    quickEditAccount.login_name = ''
    quickEditAccount.domain_code = ''
    quickEditAccount.platform_codes = []
    quickEditAccountError.value = ''
    dealAccountsForGameNew.value = []
    dealAccountsForGameEdit.value = []
    dealAccountAssignmentsNew.value = []
    dealAccountAssignmentsEdit.value = []
    dealSlotAvailabilityNew.value = {}
    dealSlotAvailabilityEdit.value = {}
  }

  function startEditDeal(deal) {
    closeAllModals()
    resetModalPos()
    showDealForm.value = false
    editDeal.open = true
    dealInitLock.value = true
    dealEditMode.value = 'view'
    editDealGameSearch.value = ''
    quickEditGame.title = ''
    quickEditGame.platform_codes = []
    quickEditGameError.value = ''
    quickEditAccount.login_name = ''
    quickEditAccount.domain_code = ''
    quickEditAccount.platform_codes = []
    quickEditAccountError.value = ''
    dealAccountsForGameEdit.value = []
    editDeal.deal_id = deal.deal_id
    editDeal.created_at = deal.created_at || ''
    editDeal.deal_type_code = deal.deal_type_code || (deal.deal_type === 'Шеринг' ? 'rental' : 'sale')
    editDeal.account_id = deal.account_id
    editDeal.game_id = deal.game_id
    editDeal.customer_nickname = deal.customer_nickname || ''
    editDeal.source_id = deal.source_id || ''
    editDeal.region_code = deal.region_code || ''
    editDeal.slot_type_code = deal.slot_type_code || ''
    editDeal.price = Number(deal.price || 0)
    editDeal.purchase_cost = Number(deal.purchase_cost || 0)
    editDeal.game_link = deal.game_link || ''
    editDeal.purchase_at = deal.purchase_at ? String(deal.purchase_at).slice(0, 10) : ''
    editDeal.slots_used = deal.slots_used || (deal.deal_type_code === 'rental' ? 1 : 0)
    editDeal.notes = deal.notes || ''
    editDeal.flow_status_code = deal.flow_status_code || ''
    nextTick(() => {
      setTimeout(() => {
        dealInitLock.value = false
        if (editDeal.game_id) loadDealSlotAvailability('edit')
      }, 0)
    })
  }

  return {
    openCreateDealModal,
    openCreateSaleModal,
    openCreateSharingModal,
    closeDealModal,
    startEditDeal,
    cancelEditDeal,
  }
}
