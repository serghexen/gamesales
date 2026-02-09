import { watch } from 'vue'

export function useDealsWatchers({
  newDeal,
  editDeal,
  dealInitLock,
  dealSlotAutoAssign,
  accountSlotStatusNew,
  accountSlotStatusEdit,
  dealAccountAssignmentsNew,
  dealAccountAssignmentsEdit,
  dealSlotAvailabilityNew,
  dealSlotAvailabilityEdit,
  loadDealAccountsForGame,
  loadDealGameAssignments,
  loadAccountSlotStatus,
  loadDealAccountAssignments,
  loadDealSlotAvailability,
}) {
  watch(
    () => [newDeal.game_id, newDeal.slot_type_code],
    () => {
      loadDealAccountsForGame('new')
      if (newDeal.game_id) loadDealGameAssignments('new')
    }
  )

  watch(
    () => [editDeal.game_id, editDeal.slot_type_code],
    () => {
      if (editDeal.open) loadDealAccountsForGame('edit')
      if (editDeal.open && editDeal.game_id) loadDealGameAssignments('edit')
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
    () => newDeal.game_id,
    (val, prev) => {
      if (val === prev) return
      newDeal.account_id = ''
      newDeal.slot_type_code = ''
      accountSlotStatusNew.value = []
      dealAccountAssignmentsNew.value = []
      dealSlotAvailabilityNew.value = {}
      loadDealSlotAvailability('new')
    }
  )

  watch(
    () => editDeal.game_id,
    (val, prev) => {
      if (!editDeal.open || dealInitLock.value) return
      if (val === prev) return
      editDeal.account_id = ''
      editDeal.slot_type_code = ''
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
        accountSlotStatusNew.value = []
        dealAccountAssignmentsNew.value = []
        return
      }
      newDeal.account_id = ''
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
        accountSlotStatusEdit.value = []
        dealAccountAssignmentsEdit.value = []
        return
      }
      editDeal.account_id = ''
      accountSlotStatusEdit.value = []
      dealAccountAssignmentsEdit.value = []
    }
  )
}
