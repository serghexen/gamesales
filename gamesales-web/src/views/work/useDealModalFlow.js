import { confirmDiscardIfNeeded, isSameNormalized } from './unsavedChanges'

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
  editDealResponsible,
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
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
  currentResponsibleName,
}) {
  let initialEditDealSnapshot = null
  let initialCreateDealSnapshot = null

  // Возвращает имя ответственного по умолчанию из текущей сессии.
  function getDefaultResponsibleName() {
    const raw = typeof currentResponsibleName === 'object' && currentResponsibleName
      ? currentResponsibleName.value
      : currentResponsibleName
    return String(raw || '').trim()
  }

  // Снимает "снимок" формы создания, чтобы сравнивать изменения относительно фактического стартового режима.
  function syncCreateDealSnapshot() {
    initialCreateDealSnapshot = {
      deal_type_code: newDeal.deal_type_code,
      account_id: newDeal.account_id,
      game_id: newDeal.game_id,
      customer_nickname: newDeal.customer_nickname,
      order_number: newDeal.order_number,
      source_id: newDeal.source_id,
      region_code: newDeal.region_code,
      slot_type_code: newDeal.slot_type_code,
      price: newDeal.price,
      purchase_cost: newDeal.purchase_cost,
      login: newDeal.login,
      password: newDeal.password,
      game_link: newDeal.game_link,
      purchase_at: newDeal.purchase_at,
      slots_used: newDeal.slots_used,
      notes: newDeal.notes,
      responsible: newDealResponsible.value,
    }
  }

  function applyDealToEditState(deal) {
    if (!deal) return
    editDeal.deal_id = deal.deal_id
    editDeal.created_at = deal.created_at || ''
    // Берем дату завершения из API, чтобы показать ее рядом со статусом.
    editDeal.completed_at = deal.completed_at || ''
    editDeal.deal_type_code = deal.deal_type_code || (deal.deal_type === 'Шеринг' ? 'rental' : 'sale')
    editDeal.account_id = deal.account_id
    editDeal.game_id = deal.game_id
    editDeal.customer_nickname = deal.customer_nickname || ''
    editDeal.order_number = deal.order_number || ''
    editDeal.source_id = deal.source_id || ''
    editDeal.region_code = deal.region_code || ''
    editDeal.slot_type_code = deal.slot_type_code || ''
    editDeal.price = Number(deal.price || 0)
    editDeal.purchase_cost = Number(deal.purchase_cost || 0)
    editDeal.login = deal.login || ''
    editDeal.password = deal.password || ''
    editDeal.game_link = deal.game_link || ''
    editDeal.purchase_at = deal.purchase_at ? String(deal.purchase_at).slice(0, 10) : ''
    editDeal.slots_used = deal.slots_used || (deal.deal_type_code === 'rental' ? 1 : 0)
    editDeal.notes = deal.notes || ''
    editDeal.flow_status_code = deal.flow_status_code || ''
    editDeal.is_refund = Boolean(deal.is_refund)
    // Для существующей сделки показываем сохраненное значение как есть, без подмены на текущего пользователя.
    editDealResponsible.value = deal.responsible_username || ''
  }

  function cancelEditDeal() {
    editDeal.open = false
    editDeal.deal_id = null
    editDeal.created_at = ''
    // Дата завершения нужна для показа в форме только у завершенных сделок.
    editDeal.completed_at = ''
    editDeal.deal_type_code = 'sale'
    editDeal.account_id = ''
    editDeal.game_id = ''
    editDeal.customer_nickname = ''
    editDeal.order_number = ''
    editDeal.source_id = ''
    editDeal.region_code = ''
    editDeal.slot_type_code = ''
    editDeal.price = 0
    editDeal.purchase_cost = 0
    editDeal.login = ''
    editDeal.password = ''
    editDeal.game_link = ''
    editDeal.purchase_at = ''
    editDeal.slots_used = 1
    editDeal.notes = ''
    editDeal.flow_status_code = ''
    editDeal.is_refund = false
    editDealResponsible.value = ''
    dealEditMode.value = 'view'
    initialEditDealSnapshot = null
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
    // Для новых сделок сразу подставляем ответственного из текущей сессии.
    newDealResponsible.value = getDefaultResponsibleName()
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
    syncCreateDealSnapshot()
  }

  function openCreateSaleModal() {
    setActiveTab('deals')
    openCreateDealModal()
    newDeal.deal_type_code = 'sale'
    syncCreateDealSnapshot()
  }

  function openCreateSharingModal() {
    setActiveTab('deals')
    openCreateDealModal()
    newDeal.deal_type_code = 'rental'
    syncCreateDealSnapshot()
  }

  async function closeDealModal() {
    const guardEnabled = !suppressUnsavedConfirm?.value
    const createBaseline = initialCreateDealSnapshot || {
      deal_type_code: 'sale',
      account_id: '',
      game_id: '',
      customer_nickname: '',
      order_number: '',
      source_id: '',
      region_code: '',
      slot_type_code: '',
      price: 0,
      purchase_cost: 0,
      login: '',
      password: '',
      game_link: '',
      purchase_at: '',
      slots_used: 1,
      notes: '',
      responsible: getDefaultResponsibleName(),
    }
    const createCurrent = {
      deal_type_code: newDeal.deal_type_code,
      account_id: newDeal.account_id,
      game_id: newDeal.game_id,
      customer_nickname: newDeal.customer_nickname,
      order_number: newDeal.order_number,
      source_id: newDeal.source_id,
      region_code: newDeal.region_code,
      slot_type_code: newDeal.slot_type_code,
      price: newDeal.price,
      purchase_cost: newDeal.purchase_cost,
      login: newDeal.login,
      password: newDeal.password,
      game_link: newDeal.game_link,
      purchase_at: newDeal.purchase_at,
      slots_used: newDeal.slots_used,
      notes: newDeal.notes,
      responsible: newDealResponsible.value,
    }
    const editCurrent = {
      deal_type_code: editDeal.deal_type_code,
      account_id: editDeal.account_id,
      game_id: editDeal.game_id,
      customer_nickname: editDeal.customer_nickname,
      order_number: editDeal.order_number,
      source_id: editDeal.source_id,
      region_code: editDeal.region_code,
      slot_type_code: editDeal.slot_type_code,
      price: editDeal.price,
      purchase_cost: editDeal.purchase_cost,
      login: editDeal.login,
      password: editDeal.password,
      game_link: editDeal.game_link,
      purchase_at: editDeal.purchase_at,
      slots_used: editDeal.slots_used,
      notes: editDeal.notes,
      flow_status_code: editDeal.flow_status_code,
      is_refund: editDeal.is_refund,
      responsible_username: editDealResponsible.value,
    }
    const createDirty = showDealForm.value && !isSameNormalized(createCurrent, createBaseline)
    const editDirty = editDeal.open && dealEditMode.value === 'edit' && !isSameNormalized(editCurrent, initialEditDealSnapshot || {})
    if (guardEnabled && !(await confirmDiscardIfNeeded(createDirty || editDirty, { requestConfirm: requestUnsavedConfirm }))) return false

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
    newDeal.login = ''
    newDeal.password = ''
    newDeal.game_link = ''
    newDeal.purchase_at = ''
    newDeal.slots_used = 1
    newDeal.notes = ''
    // После закрытия возвращаем дефолт для следующего открытия формы.
    newDealResponsible.value = getDefaultResponsibleName()
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
    initialCreateDealSnapshot = null
    return true
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
    // Сохраняем исходные данные в том же формате, что и форма, чтобы корректно сравнивать "грязные" изменения.
    initialEditDealSnapshot = {
      created_at: deal.created_at || '',
      completed_at: deal.completed_at || '',
      deal_type_code: deal.deal_type_code || (deal.deal_type === 'Шеринг' ? 'rental' : 'sale'),
      account_id: deal.account_id,
      game_id: deal.game_id,
      customer_nickname: deal.customer_nickname || '',
      order_number: deal.order_number || '',
      source_id: deal.source_id || '',
      region_code: deal.region_code || '',
      slot_type_code: deal.slot_type_code || '',
      price: Number(deal.price || 0),
      purchase_cost: Number(deal.purchase_cost || 0),
      login: deal.login || '',
      password: deal.password || '',
      game_link: deal.game_link || '',
      purchase_at: deal.purchase_at ? String(deal.purchase_at).slice(0, 10) : '',
      slots_used: deal.slots_used || (deal.deal_type_code === 'rental' ? 1 : 0),
      notes: deal.notes || '',
      flow_status_code: deal.flow_status_code || '',
      // Для снимка фиксируем и признак возврата, чтобы корректно откатывать изменения формы.
      is_refund: Boolean(deal.is_refund),
      // Снимок редактирования должен хранить фактическое значение сделки, чтобы не было ложной подстановки.
      responsible_username: deal.responsible_username || '',
    }
    applyDealToEditState(deal)
    nextTick(() => {
      setTimeout(() => {
        dealInitLock.value = false
        if (editDeal.game_id) loadDealSlotAvailability('edit')
      }, 0)
    })
  }

  function toggleDealEditMode() {
    // Второй клик по кнопке "редактировать" возвращает в просмотр и сбрасывает несохраненные правки.
    if (dealEditMode.value === 'edit') {
      dealInitLock.value = true
      applyDealToEditState(initialEditDealSnapshot)
      dealEditMode.value = 'view'
      nextTick(() => {
        setTimeout(() => {
          dealInitLock.value = false
          if (editDeal.game_id) loadDealSlotAvailability('edit')
        }, 0)
      })
      return
    }
    dealEditMode.value = 'edit'
  }

  return {
    openCreateDealModal,
    openCreateSaleModal,
    openCreateSharingModal,
    closeDealModal,
    startEditDeal,
    cancelEditDeal,
    toggleDealEditMode,
  }
}
