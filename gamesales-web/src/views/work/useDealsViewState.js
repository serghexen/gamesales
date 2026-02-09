import { computed } from 'vue'

export function useDealsViewState({
  gamesAll,
  newDeal,
  editDeal,
  newDealGameSearch,
  editDealGameSearch,
  dealAccountsForGameNew,
  dealAccountsForGameEdit,
  dealGameAssignmentsNew,
  dealGameAssignmentsEdit,
}) {
  // Поиск игр для формы создания сделки.
  const filteredNewDealGames = computed(() => {
    const list = gamesAll.value || []
    const q = newDealGameSearch.value.trim().toLowerCase()
    if (q) return list.filter((g) => String(g.title || '').toLowerCase().includes(q))
    if (newDeal.game_id) return list.filter((g) => g.game_id === newDeal.game_id)
    return list
  })

  // Поиск игр для формы редактирования сделки.
  const filteredEditDealGames = computed(() => {
    const list = gamesAll.value || []
    const q = editDealGameSearch.value.trim().toLowerCase()
    if (q) return list.filter((g) => String(g.title || '').toLowerCase().includes(q))
    if (editDeal.game_id) return list.filter((g) => g.game_id === editDeal.game_id)
    return list
  })

  // Нужен ли блок "ничего не найдено" в создании сделки.
  const newDealGameNoMatches = computed(() => {
    return newDealGameSearch.value.trim().length > 0 && filteredNewDealGames.value.length === 0
  })

  // Нужен ли блок "ничего не найдено" в редактировании сделки.
  const editDealGameNoMatches = computed(() => {
    return editDealGameSearch.value.trim().length > 0 && filteredEditDealGames.value.length === 0
  })

  // Аккаунты, доступные для новой сделки по текущей игре/слоту.
  const dealAccountsForNew = computed(() => {
    if (!newDeal.game_id || !newDeal.slot_type_code) return []
    return [...dealAccountsForGameNew.value]
  })

  // Аккаунты, доступные для редактируемой сделки по текущей игре/слоту.
  const dealAccountsForEdit = computed(() => {
    if (!editDeal.game_id || !editDeal.slot_type_code) return []
    return [...dealAccountsForGameEdit.value]
  })

  // Назначения по выбранному типу слота для новой сделки.
  const dealGameAssignmentsForSelectedSlotNew = computed(() => {
    if (!newDeal.slot_type_code) return []
    return (dealGameAssignmentsNew.value || []).filter((s) => !s.released_at && s.slot_type_code === newDeal.slot_type_code)
  })

  // Назначения по выбранному типу слота для редактируемой сделки.
  const dealGameAssignmentsForSelectedSlotEdit = computed(() => {
    if (!editDeal.slot_type_code) return []
    return (dealGameAssignmentsEdit.value || []).filter((s) => !s.released_at && s.slot_type_code === editDeal.slot_type_code)
  })

  const hasAnyGameAssignmentsNew = computed(() => (dealGameAssignmentsNew.value || []).some((s) => !s.released_at))
  const hasAnyGameAssignmentsEdit = computed(() => (dealGameAssignmentsEdit.value || []).some((s) => !s.released_at))

  return {
    filteredNewDealGames,
    filteredEditDealGames,
    newDealGameNoMatches,
    editDealGameNoMatches,
    dealAccountsForNew,
    dealAccountsForEdit,
    dealGameAssignmentsForSelectedSlotNew,
    dealGameAssignmentsForSelectedSlotEdit,
    hasAnyGameAssignmentsNew,
    hasAnyGameAssignmentsEdit,
  }
}
