import { computed } from 'vue'

export function useSlotHelpers({
  slotTypes,
  gamesAll,
  newDeal,
  editDeal,
  dealAccountsForGameNew,
  dealAccountsForGameEdit,
  dealSlotAvailabilityNew,
  dealSlotAvailabilityEdit,
  hasAnyGameAssignmentsNew,
  hasAnyGameAssignmentsEdit,
  accountSlotAssignments,
  accountSlotAssignmentsSort,
}) {
  // Читаем человеко-понятное имя типа слота.
  const getSlotTypeLabel = (code) => {
    if (!code) return '—'
    return slotTypes.value.find((t) => t.code === code)?.name || code
  }

  // Ищем слоты аккаунта по конкретной платформе.
  const getAccountPlatformSlots = (account, platformCode) => {
    if (!account?.platform_slots || !platformCode) return null
    const code = String(platformCode).toLowerCase()
    return account.platform_slots.find((s) => String(s.platform_code || '').toLowerCase() === code) || null
  }

  // Короткая строка занято/всего для аккаунта.
  const getAccountSlotsText = (account) => {
    const list = Array.isArray(account?.slot_status) ? account.slot_status : []
    if (list.length) {
      return list.map((s) => `${getSlotTypeLabel(s.slot_type_code)} ${s.occupied || 0}/${s.capacity || 0}`).join(' · ')
    }
    const ps4 = getAccountPlatformSlots(account, 'ps4')
    const ps5 = getAccountPlatformSlots(account, 'ps5')
    const ps4Text = `PS4 ${ps4?.occupied_slots || 0}/${ps4?.slot_capacity || 0}`
    const ps5Text = `PS5 ${ps5?.occupied_slots || 0}/${ps5?.slot_capacity || 0}`
    return `${ps4Text} · ${ps5Text}`
  }

  // Строка статуса для одного типа слота.
  const formatAccountSlotStatusLine = (slot) => {
    if (!slot) return '—'
    return `${getSlotTypeLabel(slot.slot_type_code)} - ${slot.occupied || 0}/${slot.capacity || 0}`
  }

  // Сортировка слотов в стабильном порядке: режим -> платформа -> код.
  const getSortedSlotStatus = (list) => {
    const items = Array.isArray(list) ? [...list] : []
    const typeMap = new Map((slotTypes.value || []).map((t) => [t.code, t]))
    const modeOrder = new Map([['activate', 0], ['play', 1]])
    items.sort((a, b) => {
      const at = typeMap.get(a.slot_type_code)
      const bt = typeMap.get(b.slot_type_code)
      const am = modeOrder.has(at?.mode) ? modeOrder.get(at?.mode) : 9
      const bm = modeOrder.has(bt?.mode) ? modeOrder.get(bt?.mode) : 9
      if (am !== bm) return am - bm
      const ap = String(at?.platform_code || '').localeCompare(String(bt?.platform_code || ''))
      if (ap !== 0) return ap
      return String(a.slot_type_code || '').localeCompare(String(b.slot_type_code || ''))
    })
    return items
  }

  const compareSlotTypeCodes = (aCode, bCode) => {
    const typeMap = new Map((slotTypes.value || []).map((t) => [t.code, t]))
    const modeOrder = new Map([['activate', 0], ['play', 1]])
    const at = typeMap.get(aCode)
    const bt = typeMap.get(bCode)
    const am = modeOrder.has(at?.mode) ? modeOrder.get(at?.mode) : 9
    const bm = modeOrder.has(bt?.mode) ? modeOrder.get(bt?.mode) : 9
    if (am !== bm) return am - bm
    const ap = String(at?.platform_code || '').localeCompare(String(bt?.platform_code || ''))
    if (ap !== 0) return ap
    return String(aCode || '').localeCompare(String(bCode || ''))
  }

  // Сортировка строк назначений в таблице слотов аккаунта.
  const sortedAccountSlotAssignments = computed(() => {
    const list = Array.isArray(accountSlotAssignments.value) ? [...accountSlotAssignments.value] : []
    const { key, dir } = accountSlotAssignmentsSort.value || { key: 'slot', dir: 'asc' }
    if (key === 'slot') {
      list.sort((a, b) => {
        const base = compareSlotTypeCodes(a.slot_type_code, b.slot_type_code)
        return dir === 'desc' ? -base : base
      })
    }
    return list
  })

  // Список статусов слотов аккаунта с учетом платформы.
  const getAccountSlotStatusList = (account) => {
    const list = Array.isArray(account?.slot_status) ? account.slot_status : []
    if (list.length) {
      const codes = Array.isArray(account?.platform_codes) ? account.platform_codes.map((c) => String(c).toLowerCase()) : []
      if (codes.length && !codes.includes('ps4')) {
        return getSortedSlotStatus(list.filter((s) => String(s?.platform_code || '').toLowerCase() === 'ps5'))
      }
      return getSortedSlotStatus(list)
    }
    return []
  }

  const getAccountFreeTotal = (account) => {
    const list = Array.isArray(account?.slot_status) ? account.slot_status : null
    if (list) return list.reduce((sum, s) => sum + Number(s?.free || 0), 0)
    return (account?.platform_slots || []).reduce((sum, s) => sum + Number(s?.free_slots || 0), 0)
  }

  const formatAccountSlots = (account) => getAccountSlotsText(account)

  const getAccountFreeSlots = (account, platformCode) => {
    const slot = getAccountPlatformSlots(account, platformCode)
    return Number(slot?.free_slots || 0)
  }

  const getGameById = (gameId) => (gamesAll.value || []).find((g) => g.game_id === gameId)

  const getGameLabelById = (gameId) => {
    const game = getGameById(gameId)
    return game?.title || (gameId ? String(gameId) : '—')
  }

  const getGamePlatformCodes = (gameId) => {
    const game = getGameById(gameId)
    const codes = Array.isArray(game?.platform_codes) ? game.platform_codes : []
    return codes.map((c) => String(c).toLowerCase())
  }

  // Можно ли использовать тип слота для выбранной игры.
  const isSlotTypeSupportedForGame = (slotTypeCode, gameId) => {
    if (!slotTypeCode || !gameId) return false
    const type = slotTypes.value.find((t) => t.code === slotTypeCode)
    if (!type?.platform_code) return true
    const platforms = getGamePlatformCodes(gameId)
    if (!platforms.length) return true
    const hasPs4 = platforms.includes('ps4')
    const hasPs5 = platforms.includes('ps5')
    if (hasPs4) return true
    if (hasPs5) return String(type.platform_code).toLowerCase() === 'ps5'
    return true
  }

  const getAccountPlatformCodesForDeal = (target) => {
    const isEdit = target === 'edit'
    const accountId = isEdit ? editDeal.account_id : newDeal.account_id
    if (!accountId) return []
    const list = isEdit ? dealAccountsForGameEdit.value : dealAccountsForGameNew.value
    const account = (list || []).find((a) => a.account_id === accountId)
    const codes = Array.isArray(account?.platform_codes) ? account.platform_codes : []
    return codes.map((c) => String(c).toLowerCase())
  }

  const isSlotTypeSupportedForDeal = (slotTypeCode, target) => {
    if (!slotTypeCode) return false
    const isEdit = target === 'edit'
    const gameId = isEdit ? editDeal.game_id : newDeal.game_id
    const type = slotTypes.value.find((t) => t.code === slotTypeCode)
    if (!type?.platform_code) return true
    const accountPlatforms = getAccountPlatformCodesForDeal(target)
    if (accountPlatforms.length) {
      const hasPs4 = accountPlatforms.includes('ps4')
      if (hasPs4) return true
      return String(type.platform_code).toLowerCase() === 'ps5'
    }
    return isSlotTypeSupportedForGame(slotTypeCode, gameId)
  }

  // Формирует варианты типов слотов для формы сделки.
  const getDealSlotTypeOptions = (target) => {
    const isEdit = target === 'edit'
    const availability = isEdit ? dealSlotAvailabilityEdit.value : dealSlotAvailabilityNew.value
    const hasAssignments = isEdit ? hasAnyGameAssignmentsEdit.value : hasAnyGameAssignmentsNew.value
    return (slotTypes.value || []).map((t) => {
      const supported = isSlotTypeSupportedForDeal(t.code, target)
      const hasFree = availability?.[t.code]?.hasFree
      const noAccounts = supported && hasFree === false && !hasAssignments
      return { code: t.code, name: t.name, platform_code: t.platform_code, supported, hasFree, noAccounts }
    })
  }

  // Подпись для опции типа слота в форме сделки.
  const getDealSlotTypeLabel = (slot) => {
    if (!slot) return '—'
    if (!slot.supported) return `${slot.name} — недоступно`
    if (slot.noAccounts) return slot.name
    if (slot.hasFree === false) return `${slot.name} — заняты`
    return slot.name
  }

  // Проверка: выбранный тип слота сейчас недоступен для сделки.
  const isDealSlotTypeUnsupported = (target) => {
    const isEdit = target === 'edit'
    const gameId = isEdit ? editDeal.game_id : newDeal.game_id
    const slotTypeCode = isEdit ? editDeal.slot_type_code : newDeal.slot_type_code
    if (!gameId || !slotTypeCode) return false
    return !isSlotTypeSupportedForDeal(slotTypeCode, target)
  }

  // Проверка: есть ли свободные слоты под текущий тип.
  const hasFreeDealSlots = (target) => {
    const isEdit = target === 'edit'
    const slotTypeCode = isEdit ? editDeal.slot_type_code : newDeal.slot_type_code
    if (!slotTypeCode) return false
    const availability = isEdit ? dealSlotAvailabilityEdit.value : dealSlotAvailabilityNew.value
    if (availability && Object.prototype.hasOwnProperty.call(availability, slotTypeCode)) {
      return Boolean(availability[slotTypeCode]?.hasFree)
    }
    const list = isEdit ? dealAccountsForGameEdit.value : dealAccountsForGameNew.value
    return Array.isArray(list) && list.length > 0
  }

  return {
    getSlotTypeLabel,
    getAccountSlotsText,
    formatAccountSlotStatusLine,
    getSortedSlotStatus,
    sortedAccountSlotAssignments,
    getAccountSlotStatusList,
    getAccountFreeTotal,
    formatAccountSlots,
    getAccountFreeSlots,
    getGameLabelById,
    isSlotTypeSupportedForGame,
    getDealSlotTypeOptions,
    getDealSlotTypeLabel,
    isDealSlotTypeUnsupported,
    hasFreeDealSlots,
  }
}
