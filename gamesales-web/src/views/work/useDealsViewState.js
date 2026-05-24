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

  // Возвращает дату назначения слота или null, если значение невалидно.
  function getAssignmentDate(assignment) {
    const assignedAtRaw = String(assignment?.assigned_at || '').trim()
    if (!assignedAtRaw) return null
    const assignedAt = new Date(assignedAtRaw)
    if (Number.isNaN(assignedAt.getTime())) return null
    return assignedAt
  }

  // Возвращает дату снятия слота или null, если слот еще активен/дата невалидна.
  function getReleasedDate(assignment) {
    const releasedAtRaw = String(assignment?.released_at || '').trim()
    if (!releasedAtRaw) return null
    const releasedAt = new Date(releasedAtRaw)
    if (Number.isNaN(releasedAt.getTime())) return null
    return releasedAt
  }

  // Проверяет, можно ли показывать слот в списке дублей (не раньше 2 месяцев с момента назначения).
  function canUseAssignmentForDuplicateFlow(assignment) {
    const assignedAt = getAssignmentDate(assignment)
    if (!assignedAt) return false
    const threshold = new Date()
    threshold.setMonth(threshold.getMonth() - 2)
    return assignedAt.getTime() <= threshold.getTime()
  }

  // Возвращает аккаунты, где за последние 2 месяца уже был дубль по выбранному методу.
  function getRecentDuplicateLockedAccountIds(assignments, slotTypeCode) {
    const selectedSlotType = normalizeSlotTypeCode(slotTypeCode)
    if (!selectedSlotType) return new Set()
    const threshold = new Date()
    threshold.setMonth(threshold.getMonth() - 2)

    const assignmentsByMethod = (assignments || [])
      .map((assignment) => {
        return {
          accountId: Number(assignment?.account_id || 0),
          slotTypeCode: normalizeSlotTypeCode(assignment?.slot_type_code),
          assignedAt: getAssignmentDate(assignment),
          releasedAt: getReleasedDate(assignment),
        }
      })
      .filter((item) => item.accountId > 0 && item.slotTypeCode === selectedSlotType && item.assignedAt)

    const lockedAccountIds = new Set()
    const assignmentsByAccount = new Map()
    for (const assignment of assignmentsByMethod) {
      if (!assignmentsByAccount.has(assignment.accountId)) {
        assignmentsByAccount.set(assignment.accountId, [])
      }
      assignmentsByAccount.get(assignment.accountId).push(assignment)
    }

    for (const [accountId, accountAssignments] of assignmentsByAccount.entries()) {
      const hasRecentDuplicate = accountAssignments.some((current) => {
        if (current.assignedAt.getTime() <= threshold.getTime()) return false
        return accountAssignments.some((prev) => {
          if (prev === current) return false
          // Если более раннее назначение перекрывало момент текущего, значит это дубль.
          if (prev.assignedAt.getTime() >= current.assignedAt.getTime()) return false
          const releasedAtTime = prev.releasedAt ? prev.releasedAt.getTime() : Number.POSITIVE_INFINITY
          return releasedAtTime > current.assignedAt.getTime()
        })
      })
      if (hasRecentDuplicate) lockedAccountIds.add(accountId)
    }
    return lockedAccountIds
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
    const lockedAccountIds = getRecentDuplicateLockedAccountIds(dealProductAssignmentsNew.value, selectedSlotType)
    return (dealProductAssignmentsNew.value || [])
      .filter((s) => {
        const accountId = Number(s?.account_id || 0)
        return !s.released_at
          && accountId > 0
          && !lockedAccountIds.has(accountId)
          && normalizeSlotTypeCode(s.slot_type_code) === selectedSlotType
          && canUseAssignmentForDuplicateFlow(s)
      })
      // В списке дублей сверху показываем самое старое назначение, чтобы переиспользование было предсказуемым.
      .sort((left, right) => {
        const leftTime = getAssignmentDate(left)?.getTime() || 0
        const rightTime = getAssignmentDate(right)?.getTime() || 0
        return leftTime - rightTime
      })
  })

  // Назначения по выбранному типу слота для редактируемой сделки.
  const dealProductAssignmentsForSelectedSlotEdit = computed(() => {
    if (!editDeal.slot_type_code) return []
    const selectedSlotType = normalizeSlotTypeCode(editDeal.slot_type_code)
    const lockedAccountIds = getRecentDuplicateLockedAccountIds(dealProductAssignmentsEdit.value, selectedSlotType)
    return (dealProductAssignmentsEdit.value || [])
      .filter((s) => {
        const accountId = Number(s?.account_id || 0)
        // Для edit используем тот же порог 2 месяца, чтобы сценарий дубля был одинаковым с create.
        return !s.released_at
          && accountId > 0
          && !lockedAccountIds.has(accountId)
          && normalizeSlotTypeCode(s.slot_type_code) === selectedSlotType
          && canUseAssignmentForDuplicateFlow(s)
      })
      .sort((left, right) => {
        const leftTime = getAssignmentDate(left)?.getTime() || 0
        const rightTime = getAssignmentDate(right)?.getTime() || 0
        return leftTime - rightTime
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
