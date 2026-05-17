import { computed } from 'vue'

export function useDealsViewState({
  productsAll,
  newDeal,
  editDeal,
  newDealProductSearch: newDealProductSearch,
  editDealProductSearch: editDealProductSearch,
  dealAccountsForProductNew: dealAccountsForProductNew,
  dealAccountsForProductEdit: dealAccountsForProductEdit,
  dealGameAssignmentsNew: dealProductAssignmentsNew,
  dealGameAssignmentsEdit: dealProductAssignmentsEdit,
}) {
  // Нормализует код слота для корректного сравнения данных из API и формы.
  function normalizeSlotTypeCode(value) {
    return String(value || '').trim().toLowerCase()
  }

  // Проверяет, можно ли показывать слот в списке "снять и занять" (не раньше 3 месяцев с момента занятия).
  function canUseAssignmentForDuplicateFlow(assignment) {
    const assignedAtRaw = String(assignment?.assigned_at || '').trim()
    if (!assignedAtRaw) return false
    const assignedAt = new Date(assignedAtRaw)
    if (Number.isNaN(assignedAt.getTime())) return false
    const threshold = new Date()
    threshold.setMonth(threshold.getMonth() - 3)
    return assignedAt.getTime() <= threshold.getTime()
  }

  // Поиск товаров для формы создания сделки.
  const filteredNewDealProducts = computed(() => {
    const list = productsAll.value || []
    const q = newDealProductSearch.value.trim().toLowerCase()
    if (q) return list.filter((g) => String(g.title || '').toLowerCase().includes(q))
    if (newDeal.product_id) return list.filter((g) => g.product_id === newDeal.product_id)
    return list
  })

  // Поиск товаров для формы редактирования сделки.
  const filteredEditDealProducts = computed(() => {
    const list = productsAll.value || []
    const q = editDealProductSearch.value.trim().toLowerCase()
    if (q) return list.filter((g) => String(g.title || '').toLowerCase().includes(q))
    if (editDeal.product_id) return list.filter((g) => g.product_id === editDeal.product_id)
    return list
  })

  // Нужен ли блок "ничего не найдено" в создании сделки.
  const newDealProductNoMatches = computed(() => {
    return newDealProductSearch.value.trim().length > 0 && filteredNewDealProducts.value.length === 0
  })

  // Нужен ли блок "ничего не найдено" в редактировании сделки.
  const editDealProductNoMatches = computed(() => {
    return editDealProductSearch.value.trim().length > 0 && filteredEditDealProducts.value.length === 0
  })

  // Аккаунты, доступные для новой сделки по текущему товару/слоту.
  const dealAccountsForNew = computed(() => {
    if (!newDeal.product_id || !newDeal.slot_type_code) return []
    return [...dealAccountsForProductNew.value]
  })

  // Аккаунты, доступные для редактируемой сделки по текущему товару/слоту.
  const dealAccountsForEdit = computed(() => {
    if (!editDeal.product_id || !editDeal.slot_type_code) return []
    return [...dealAccountsForProductEdit.value]
  })

  // Назначения по выбранному типу слота для новой сделки.
  const dealProductAssignmentsForSelectedSlotNew = computed(() => {
    if (!newDeal.slot_type_code) return []
    const selectedSlotType = normalizeSlotTypeCode(newDeal.slot_type_code)
    return (dealProductAssignmentsNew.value || []).filter((s) => {
      return !s.released_at
        && normalizeSlotTypeCode(s.slot_type_code) === selectedSlotType
        && canUseAssignmentForDuplicateFlow(s)
    })
  })

  // Назначения по выбранному типу слота для редактируемой сделки.
  const dealProductAssignmentsForSelectedSlotEdit = computed(() => {
    if (!editDeal.slot_type_code) return []
    const selectedSlotType = normalizeSlotTypeCode(editDeal.slot_type_code)
    return (dealProductAssignmentsEdit.value || []).filter((s) => {
      // Для edit используем тот же порог 3 месяца, чтобы сценарий дубля был одинаковым с create.
      return !s.released_at
        && normalizeSlotTypeCode(s.slot_type_code) === selectedSlotType
        && canUseAssignmentForDuplicateFlow(s)
    })
  })

  const hasAnyProductAssignmentsNew = computed(() => (dealProductAssignmentsNew.value || []).some((s) => !s.released_at))
  const hasAnyProductAssignmentsEdit = computed(() => (dealProductAssignmentsEdit.value || []).some((s) => !s.released_at))

  return {
    filteredNewDealProducts,
    filteredEditDealProducts,
    newDealProductNoMatches,
    editDealProductNoMatches,
    dealAccountsForNew,
    dealAccountsForEdit,
    dealProductAssignmentsForSelectedSlotNew,
    dealProductAssignmentsForSelectedSlotEdit,
    hasAnyProductAssignmentsNew,
    hasAnyProductAssignmentsEdit,
  }
}
