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
}) {
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
      if (newDeal.product_id) loadDealProductAssignments('new')
    }
  )

  watch(
    () => [editDeal.product_id, editDeal.slot_type_code],
    () => {
      if (editDeal.open) loadDealAccountsForProduct('edit')
      if (editDeal.open && editDeal.product_id) loadDealProductAssignments('edit')
    }
  )

  watch(
    () => newDeal.account_id,
    () => {
      loadAccountSlotStatus('new')
      loadDealAccountAssignments('new')
    }
  )

  watch(
    () => editDeal.account_id,
    () => {
      if (editDeal.open) loadAccountSlotStatus('edit')
      if (editDeal.open) loadDealAccountAssignments('edit')
    }
  )

  watch(
    () => newDeal.product_id,
    (val, prev) => {
      if (val === prev) return
      const productType = getProductTypeCode(val)
      newDeal.account_id = ''
      newDeal.reserve_key = ''
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
      const productType = getProductTypeCode(val)
      editDeal.account_id = ''
      editDeal.reserve_key = ''
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
      if (!val) {
        newDeal.account_id = ''
        newDeal.reserve_key = ''
        accountSlotStatusNew.value = []
        dealAccountAssignmentsNew.value = []
        return
      }
      newDeal.account_id = ''
      newDeal.reserve_key = ''
      accountSlotStatusNew.value = []
      dealAccountAssignmentsNew.value = []
    }
  )

  watch(
    () => editDeal.slot_type_code,
    (val, prev) => {
      if (!editDeal.open || dealInitLock.value) return
      if (dealSlotAutoAssign.value || val === prev) return
      if (!val) {
        editDeal.account_id = ''
        editDeal.reserve_key = ''
        accountSlotStatusEdit.value = []
        dealAccountAssignmentsEdit.value = []
        return
      }
      editDeal.account_id = ''
      editDeal.reserve_key = ''
      accountSlotStatusEdit.value = []
      dealAccountAssignmentsEdit.value = []
    }
  )
}
