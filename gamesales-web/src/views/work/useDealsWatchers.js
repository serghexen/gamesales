import { watch } from 'vue'

export function useDealsWatchers({
  newDeal,
  editDeal,
  productsAll,
  dealInitLock,
  dealSlotAutoAssign,
  accountSlotStatusNew,
  accountSlotStatusEdit,
  dealAccountAssignmentsNew,
  dealAccountAssignmentsEdit,
  dealSlotAvailabilityNew,
  dealSlotAvailabilityEdit,
  loadDealAccountsForProduct,
  loadDealProductAssignments,
  loadAccountSlotStatus,
  loadDealAccountAssignments,
  loadDealSlotAvailability,
  loadSubscriptionFreeProductIds,
  loadAvailableSubscriptionItems,
  loadSubscriptionTerms,
  ensureAccountSecretsLoaded,
}) {
  const safeLoadSubscriptionTerms = typeof loadSubscriptionTerms === 'function'
    ? loadSubscriptionTerms
    : () => {}

  // Возвращает тип товара по id, чтобы ветвить поведение для игр и подписок.
  function getProductTypeCode(productId) {
    if (!productId) return ''
    const list = Array.isArray(productsAll?.value) ? productsAll.value : []
    const found = list.find((item) => Number(item?.product_id || 0) === Number(productId))
    return String(found?.type_code || '').trim().toLowerCase()
  }

  watch(
    () => [newDeal.product_id, newDeal.slot_type_code],
    () => {
      loadDealAccountsForProduct('new')
      safeLoadSubscriptionTerms('new')
      if (newDeal.product_id) loadDealProductAssignments('new')
    }
  )

  watch(
    () => [editDeal.product_id, editDeal.slot_type_code],
    () => {
      if (editDeal.open) loadDealAccountsForProduct('edit')
      if (editDeal.open) safeLoadSubscriptionTerms('edit')
      if (editDeal.open && editDeal.product_id) loadDealProductAssignments('edit')
    }
  )

  watch(
    () => newDeal.account_id,
    (val, prev) => {
      // Если аккаунт меняют руками, снимаем признак дубля.
      if (!dealSlotAutoAssign.value && val !== prev) {
        newDeal.is_duplicate_flow = false
        newDeal.duplicate_assignment_id = ''
      }
      // При выборе аккаунта догружаем его секреты для блока "Данные аккаунта".
      ensureAccountSecretsLoaded(newDeal.account_id)
      loadAccountSlotStatus('new')
      loadDealAccountAssignments('new')
    }
  )

  watch(
    () => editDeal.account_id,
    (val, prev) => {
      // Для edit при ручной смене аккаунта снимаем метку дубля, чтобы не тащить старый сценарий.
      if (!dealSlotAutoAssign.value && val !== prev) {
        editDeal.is_duplicate_flow = false
        editDeal.duplicate_assignment_id = ''
      }
      // Для редактирования сделки подтягиваем секреты выбранного аккаунта тем же способом.
      ensureAccountSecretsLoaded(editDeal.account_id)
      if (editDeal.open) loadAccountSlotStatus('edit')
      if (editDeal.open) loadDealAccountAssignments('edit')
    }
  )

  watch(
    () => newDeal.product_id,
    (val, prev) => {
      if (val === prev) return
      // Смена товара означает новый сценарий, метка дубля больше не актуальна.
      newDeal.is_duplicate_flow = false
      newDeal.duplicate_assignment_id = ''
      const productType = getProductTypeCode(val)
      // Если товар пришел из выбора "срок подписки", не сбрасываем уже выбранный срок и аккаунт.
      const keepSubscriptionChain = (
        productType === 'subscription'
        && Number(newDeal.subscription_term_id || 0) > 0
      )
      if (!keepSubscriptionChain) {
        newDeal.account_id = ''
        newDeal.subscription_term_id = ''
      }
      newDeal.reserve_key = ''
      newDeal.reserve_claim_token = ''
      // Для подписок оставляем выбранный тип слота, потому что там сценарий slot -> product.
      if (productType !== 'subscription') newDeal.slot_type_code = ''
      accountSlotStatusNew.value = []
      dealAccountAssignmentsNew.value = []
      dealSlotAvailabilityNew.value = {}
      loadDealSlotAvailability('new')
    }
  )

  watch(
    () => editDeal.product_id,
    (val, prev) => {
      if (!editDeal.open || dealInitLock.value) return
      if (val === prev) return
      // Смена товара в edit сбрасывает маркер дубля.
      editDeal.is_duplicate_flow = false
      editDeal.duplicate_assignment_id = ''
      const productType = getProductTypeCode(val)
      // Не трогаем цепочку срока при выборе подписки по term_id в режиме редактирования.
      const keepSubscriptionChain = (
        productType === 'subscription'
        && Number(editDeal.subscription_term_id || 0) > 0
      )
      if (!keepSubscriptionChain) {
        editDeal.account_id = ''
        editDeal.subscription_term_id = ''
      }
      editDeal.reserve_key = ''
      editDeal.reserve_claim_token = ''
      // Для подписок сохраняем слот, чтобы не ломать порядок выбора в форме.
      if (productType !== 'subscription') editDeal.slot_type_code = ''
      accountSlotStatusEdit.value = []
      dealAccountAssignmentsEdit.value = []
      dealSlotAvailabilityEdit.value = {}
      loadDealSlotAvailability('edit')
    }
  )

  watch(
    () => newDeal.account_id,
    (val) => {
      if (!val) {
        newDeal.reserve_key = ''
        newDeal.reserve_claim_token = ''
        newDeal.duplicate_assignment_id = ''
        accountSlotStatusNew.value = []
        dealAccountAssignmentsNew.value = []
      }
    }
  )

  watch(
    () => editDeal.account_id,
    (val, prev) => {
      if (!editDeal.open || dealInitLock.value) return
      if (!val) {
        editDeal.reserve_key = ''
        editDeal.reserve_claim_token = ''
        editDeal.duplicate_assignment_id = ''
        accountSlotStatusEdit.value = []
        dealAccountAssignmentsEdit.value = []
        return
      }
      if (!prev) return
      accountSlotStatusEdit.value = []
      dealAccountAssignmentsEdit.value = []
    }
  )

  watch(
    () => newDeal.slot_type_code,
    (val, prev) => {
      if (dealSlotAutoAssign.value || val === prev) return
      // Любая ручная смена слота сбрасывает признак дубля.
      newDeal.is_duplicate_flow = false
      newDeal.duplicate_assignment_id = ''
      // При смене слота пересчитываем только подписки с реально свободным слотом.
      loadSubscriptionFreeProductIds('new', val)
      if (typeof loadAvailableSubscriptionItems === 'function') loadAvailableSubscriptionItems('new', val)
      safeLoadSubscriptionTerms('new')
      if (!val) {
        newDeal.account_id = ''
        newDeal.subscription_term_id = ''
        newDeal.reserve_key = ''
        newDeal.reserve_claim_token = ''
        accountSlotStatusNew.value = []
        dealAccountAssignmentsNew.value = []
        return
      }
      newDeal.account_id = ''
      newDeal.subscription_term_id = ''
      newDeal.reserve_key = ''
      newDeal.reserve_claim_token = ''
      accountSlotStatusNew.value = []
      dealAccountAssignmentsNew.value = []
    }
  )

  watch(
    () => editDeal.slot_type_code,
    (val, prev) => {
      if (!editDeal.open || dealInitLock.value) return
      if (dealSlotAutoAssign.value || val === prev) return
      // В edit ручная смена типа слота тоже обнуляет сценарий дубля.
      editDeal.is_duplicate_flow = false
      editDeal.duplicate_assignment_id = ''
      // Для редактирования обновляем тот же список подписок под выбранный слот.
      loadSubscriptionFreeProductIds('edit', val)
      if (typeof loadAvailableSubscriptionItems === 'function') loadAvailableSubscriptionItems('edit', val)
      safeLoadSubscriptionTerms('edit')
      if (!val) {
        editDeal.account_id = ''
        editDeal.subscription_term_id = ''
        editDeal.reserve_key = ''
        editDeal.reserve_claim_token = ''
        accountSlotStatusEdit.value = []
        dealAccountAssignmentsEdit.value = []
        return
      }
      editDeal.account_id = ''
      editDeal.subscription_term_id = ''
      editDeal.reserve_key = ''
      editDeal.reserve_claim_token = ''
      accountSlotStatusEdit.value = []
      dealAccountAssignmentsEdit.value = []
    }
  )

  watch(
    () => productsAll.value?.length || 0,
    () => {
      // Когда справочник товаров догрузился, пересобираем фильтр подписок под текущие слоты.
      loadSubscriptionFreeProductIds('new', newDeal.slot_type_code)
      if (typeof loadAvailableSubscriptionItems === 'function') loadAvailableSubscriptionItems('new', newDeal.slot_type_code)
      safeLoadSubscriptionTerms('new')
      if (editDeal.open) loadSubscriptionFreeProductIds('edit', editDeal.slot_type_code)
      if (editDeal.open && typeof loadAvailableSubscriptionItems === 'function') loadAvailableSubscriptionItems('edit', editDeal.slot_type_code)
      if (editDeal.open) safeLoadSubscriptionTerms('edit')
    }
  )
}
