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
  editDealCommentOpen,
  newDealProductSearch,
  editDealProductSearch,
  quickNewProduct,
  quickEditProduct,
  quickNewProductError,
  quickEditProductError,
  quickNewAccount,
  quickEditAccount,
  quickNewAccountError,
  quickEditAccountError,
  quickNewSubscriptionTerm,
  quickEditSubscriptionTerm,
  quickNewSubscriptionTermError,
  quickEditSubscriptionTermError,
  dealAccountsForProductNew,
  dealAccountsForProductEdit,
  dealAccountAssignmentsNew,
  dealAccountAssignmentsEdit,
  dealSlotAvailabilityNew,
  dealSlotAvailabilityEdit,
  nextTick,
  loadDealSlotAvailability,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
  currentResponsibleName,
  canEditCompletedDeal,
  showDealWarning,
}) {
  // Возвращает дефолтную дату срока: сегодня плюс один год.
  function getDefaultSubscriptionTermDate() {
    const nextYearDate = new Date()
    nextYearDate.setFullYear(nextYearDate.getFullYear() + 1)
    const year = nextYearDate.getFullYear()
    const month = String(nextYearDate.getMonth() + 1).padStart(2, '0')
    const day = String(nextYearDate.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  const safeQuickNewSubscriptionTerm = quickNewSubscriptionTerm || { account_id: '', valid_until: getDefaultSubscriptionTermDate(), notes: '' }
  const safeQuickEditSubscriptionTerm = quickEditSubscriptionTerm || { account_id: '', valid_until: getDefaultSubscriptionTermDate(), notes: '' }
  const safeQuickNewSubscriptionTermError = quickNewSubscriptionTermError || { value: '' }
  const safeQuickEditSubscriptionTermError = quickEditSubscriptionTermError || { value: '' }

  let initialEditDealSnapshot = null
  let initialCreateDealSnapshot = null

  // Приводит дату к формату datetime-local, чтобы поле в форме было редактируемым.
  function toDateTimeLocalValue(value) {
    if (!value) return ''
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return ''
    const pad = (n) => String(n).padStart(2, '0')
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
  }

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
      product_id: newDeal.product_id,
      customer_nickname: newDeal.customer_nickname,
      order_number: newDeal.order_number,
      source_id: newDeal.source_id,
      messenger_id: newDeal.messenger_id,
      region_code: newDeal.region_code,
      slot_type_code: newDeal.slot_type_code,
      subscription_term_id: newDeal.subscription_term_id,
      reserve_key: newDeal.reserve_key,
      price: newDeal.price,
      purchase_cost: newDeal.purchase_cost,
      login: newDeal.login,
      password: newDeal.password,
      product_link: newDeal.product_link,
      purchase_at: newDeal.purchase_at,
      slots_used: newDeal.slots_used,
      notes: newDeal.notes,
      is_refund: newDeal.is_refund,
      responsible: newDealResponsible.value,
    }
  }

  function applyDealToEditState(deal) {
    if (!deal) return
    editDeal.deal_id = deal.deal_id
    // Храним версию записи, чтобы backend мог отследить конфликт параллельного редактирования.
    editDeal.lock_version = Number(deal.lock_version || 1)
    editDeal.created_at = toDateTimeLocalValue(deal.created_at)
    // Берем дату завершения из API, чтобы показать ее рядом со статусом.
    editDeal.completed_at = toDateTimeLocalValue(deal.completed_at)
    editDeal.deal_type_code = deal.deal_type_code || (deal.deal_type === 'Шеринг' ? 'rental' : 'sale')
    editDeal.account_id = deal.account_id
    editDeal.product_id = deal.product_id || deal.game_id || ''
    editDeal.customer_nickname = deal.customer_nickname || ''
    editDeal.order_number = deal.order_number || ''
    editDeal.source_id = deal.source_id || ''
    editDeal.messenger_id = deal.messenger_id || ''
    editDeal.region_code = deal.region_code || ''
    editDeal.slot_type_code = deal.slot_type_code || ''
    editDeal.subscription_term_id = deal.subscription_term_id || ''
    editDeal.reserve_key = deal.reserve_key || ''
    editDeal.price = Number(deal.price || 0)
    editDeal.purchase_cost = Number(deal.purchase_cost || 0)
    editDeal.login = deal.login || ''
    editDeal.password = deal.password || ''
    editDeal.product_link = deal.product_link || ''
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
    editDeal.lock_version = 1
    editDeal.created_at = ''
    // Дата завершения нужна для показа в форме только у завершенных сделок.
    editDeal.completed_at = ''
    editDeal.deal_type_code = 'sale'
    editDeal.account_id = ''
    editDeal.product_id = ''
    editDeal.customer_nickname = ''
    editDeal.order_number = ''
    editDeal.source_id = ''
    editDeal.messenger_id = ''
    editDeal.region_code = ''
    editDeal.slot_type_code = ''
    editDeal.subscription_term_id = ''
    editDeal.reserve_key = ''
    editDeal.price = 0
    editDeal.purchase_cost = 0
    editDeal.login = ''
    editDeal.password = ''
    editDeal.product_link = ''
    editDeal.purchase_at = ''
    editDeal.slots_used = 1
    editDeal.notes = ''
    editDeal.flow_status_code = ''
    editDeal.is_refund = false
    editDealResponsible.value = ''
    // Закрываем комментарий при сбросе формы редактирования, чтобы не тянуть старое состояние.
    if (editDealCommentOpen?.value !== undefined) editDealCommentOpen.value = false
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
    if (editDealCommentOpen?.value !== undefined) editDealCommentOpen.value = false
    newDeal.is_refund = false
    // Для новых сделок сразу подставляем ответственного из текущей сессии.
    newDealResponsible.value = getDefaultResponsibleName()
    newDealProductSearch.value = ''
    editDealProductSearch.value = ''
    quickNewProduct.title = ''
    quickNewProduct.platform_codes = []
    quickNewProductError.value = ''
    quickNewAccount.login_name = ''
    quickNewAccount.domain_code = ''
    quickNewAccount.platform_codes = []
    quickNewAccount.password = ''
    quickNewAccount.notes = ''
    quickNewAccount.subscription_product_id = ''
    quickNewAccountError.value = ''
    safeQuickNewSubscriptionTerm.account_id = ''
    safeQuickNewSubscriptionTerm.valid_until = getDefaultSubscriptionTermDate()
    safeQuickNewSubscriptionTerm.notes = ''
    safeQuickNewSubscriptionTermError.value = ''
    dealAccountsForProductNew.value = []
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
      product_id: '',
      customer_nickname: '',
      order_number: '',
      source_id: '',
      messenger_id: '',
      region_code: '',
      slot_type_code: '',
      subscription_term_id: '',
      reserve_key: '',
      price: 0,
      purchase_cost: 0,
      login: '',
      password: '',
      product_link: '',
      purchase_at: '',
      slots_used: 1,
      notes: '',
      is_refund: false,
      responsible: getDefaultResponsibleName(),
    }
    const createCurrent = {
      deal_type_code: newDeal.deal_type_code,
      account_id: newDeal.account_id,
      product_id: newDeal.product_id,
      customer_nickname: newDeal.customer_nickname,
      order_number: newDeal.order_number,
      source_id: newDeal.source_id,
      messenger_id: newDeal.messenger_id,
      region_code: newDeal.region_code,
      slot_type_code: newDeal.slot_type_code,
      subscription_term_id: newDeal.subscription_term_id,
      reserve_key: newDeal.reserve_key,
      price: newDeal.price,
      purchase_cost: newDeal.purchase_cost,
      login: newDeal.login,
      password: newDeal.password,
      product_link: newDeal.product_link,
      purchase_at: newDeal.purchase_at,
      slots_used: newDeal.slots_used,
      notes: newDeal.notes,
      is_refund: newDeal.is_refund,
      responsible: newDealResponsible.value,
    }
    const editCurrent = {
      lock_version: editDeal.lock_version,
      deal_type_code: editDeal.deal_type_code,
      account_id: editDeal.account_id,
      product_id: editDeal.product_id,
      customer_nickname: editDeal.customer_nickname,
      order_number: editDeal.order_number,
      source_id: editDeal.source_id,
      messenger_id: editDeal.messenger_id,
      region_code: editDeal.region_code,
      slot_type_code: editDeal.slot_type_code,
      subscription_term_id: editDeal.subscription_term_id,
      reserve_key: editDeal.reserve_key,
      price: editDeal.price,
      purchase_cost: editDeal.purchase_cost,
      login: editDeal.login,
      password: editDeal.password,
      product_link: editDeal.product_link,
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
    newDeal.product_id = ''
    newDeal.customer_nickname = ''
    // Очищаем номер заказа, чтобы старое значение не переносилось в новую сделку.
    newDeal.order_number = ''
    newDeal.source_id = ''
    newDeal.messenger_id = ''
    newDeal.region_code = ''
    newDeal.slot_type_code = ''
    newDeal.subscription_term_id = ''
    newDeal.reserve_key = ''
    newDeal.price = 0
    newDeal.purchase_cost = 0
    newDeal.login = ''
    newDeal.password = ''
    newDeal.product_link = ''
    newDeal.purchase_at = ''
    newDeal.slots_used = 1
    newDeal.notes = ''
    newDeal.is_refund = false
    // После закрытия возвращаем дефолт для следующего открытия формы.
    newDealResponsible.value = getDefaultResponsibleName()
    newDealCommentOpen.value = false
    newDealProductSearch.value = ''
    editDealProductSearch.value = ''
    quickNewProduct.title = ''
    quickNewProduct.platform_codes = []
    quickNewProductError.value = ''
    quickEditProduct.title = ''
    quickEditProduct.platform_codes = []
    quickEditProductError.value = ''
    quickNewAccount.login_name = ''
    quickNewAccount.domain_code = ''
    quickNewAccount.platform_codes = []
    quickNewAccount.password = ''
    quickNewAccount.notes = ''
    quickNewAccount.subscription_product_id = ''
    quickNewAccountError.value = ''
    safeQuickNewSubscriptionTerm.account_id = ''
    safeQuickNewSubscriptionTerm.valid_until = getDefaultSubscriptionTermDate()
    safeQuickNewSubscriptionTerm.notes = ''
    safeQuickNewSubscriptionTermError.value = ''
    quickEditAccount.login_name = ''
    quickEditAccount.domain_code = ''
    quickEditAccount.platform_codes = []
    quickEditAccount.password = ''
    quickEditAccount.notes = ''
    quickEditAccount.subscription_product_id = ''
    quickEditAccountError.value = ''
    safeQuickEditSubscriptionTerm.account_id = ''
    safeQuickEditSubscriptionTerm.valid_until = getDefaultSubscriptionTermDate()
    safeQuickEditSubscriptionTerm.notes = ''
    safeQuickEditSubscriptionTermError.value = ''
    dealAccountsForProductNew.value = []
    dealAccountsForProductEdit.value = []
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
    if (editDealCommentOpen?.value !== undefined) editDealCommentOpen.value = false
    editDealProductSearch.value = ''
    quickEditProduct.title = ''
    quickEditProduct.platform_codes = []
    quickEditProductError.value = ''
    quickEditAccount.login_name = ''
    quickEditAccount.domain_code = ''
    quickEditAccount.platform_codes = []
    quickEditAccount.password = ''
    quickEditAccount.notes = ''
    quickEditAccount.subscription_product_id = ''
    quickEditAccountError.value = ''
    safeQuickEditSubscriptionTerm.account_id = ''
    safeQuickEditSubscriptionTerm.valid_until = getDefaultSubscriptionTermDate()
    safeQuickEditSubscriptionTerm.notes = ''
    safeQuickEditSubscriptionTermError.value = ''
    dealAccountsForProductEdit.value = []
    // Сохраняем исходные данные в том же формате, что и форма, чтобы корректно сравнивать "грязные" изменения.
    initialEditDealSnapshot = {
      lock_version: Number(deal.lock_version || 1),
      created_at: toDateTimeLocalValue(deal.created_at),
      completed_at: toDateTimeLocalValue(deal.completed_at),
      deal_type_code: deal.deal_type_code || (deal.deal_type === 'Шеринг' ? 'rental' : 'sale'),
      account_id: deal.account_id,
      product_id: deal.product_id || deal.game_id || '',
      customer_nickname: deal.customer_nickname || '',
      order_number: deal.order_number || '',
      source_id: deal.source_id || '',
      messenger_id: deal.messenger_id || '',
      region_code: deal.region_code || '',
      slot_type_code: deal.slot_type_code || '',
      subscription_term_id: deal.subscription_term_id || '',
      reserve_key: deal.reserve_key || '',
      price: Number(deal.price || 0),
      purchase_cost: Number(deal.purchase_cost || 0),
      login: deal.login || '',
      password: deal.password || '',
      product_link: deal.product_link || '',
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
        if (editDeal.product_id) loadDealSlotAvailability('edit')
      }, 0)
    })
  }

  function toggleDealEditMode() {
    const allowCompletedEdit = typeof canEditCompletedDeal === 'object' && canEditCompletedDeal
      ? Boolean(canEditCompletedDeal.value)
      : Boolean(canEditCompletedDeal)
    // Завершенные сделки оставляем только в режиме просмотра для обычных ролей.
    if (dealEditMode.value === 'view' && editDeal.flow_status_code === 'completed' && !allowCompletedEdit) {
      if (typeof showDealWarning === 'function') {
        showDealWarning('Редактирование завершенных сделок доступно только администратору и владельцу')
      }
      return
    }
    // Второй клик по кнопке "редактировать" возвращает в просмотр и сбрасывает несохраненные правки.
    if (dealEditMode.value === 'edit') {
      dealInitLock.value = true
      applyDealToEditState(initialEditDealSnapshot)
      dealEditMode.value = 'view'
      nextTick(() => {
        setTimeout(() => {
          dealInitLock.value = false
          if (editDeal.product_id) loadDealSlotAvailability('edit')
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
