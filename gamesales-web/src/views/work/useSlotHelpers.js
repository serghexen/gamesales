import { computed } from 'vue'

export function useSlotHelpers({
  slotTypes,
  productsAll,
  newDeal,
  editDeal,
  dealAccountsForProductNew,
  dealAccountsForProductEdit,
  dealSlotAvailabilityNew,
  dealSlotAvailabilityEdit,
  hasAnyProductAssignmentsNew,
  hasAnyProductAssignmentsEdit,
  accountSlotAssignments,
  accountSlotAssignmentsSort,
}) {
  // Используем только product-first входы в расчетах слотов сделки.
  const dealAccountsNew = dealAccountsForProductNew
  const dealAccountsEdit = dealAccountsForProductEdit
  const hasAssignmentsNew = hasAnyProductAssignmentsNew
  const hasAssignmentsEdit = hasAnyProductAssignmentsEdit
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

  const getProductById = (productId) => (productsAll.value || []).find((item) => item.product_id === productId)

  const getProductLabelById = (idValue) => {
    // Для формы сделок используем только product_id.
    const product = getProductById(idValue)
    return product?.title || (idValue ? String(idValue) : '—')
  }

  const getProductPlatformCodes = (productId) => {
    const product = getProductById(productId)
    const codes = Array.isArray(product?.platform_codes) ? product.platform_codes : []
    return codes.map((c) => String(c).toLowerCase())
  }

  const isSlotTypeSupportedForProduct = (slotTypeCode, productId) => {
    if (!slotTypeCode || !productId) return false
    const type = slotTypes.value.find((t) => t.code === slotTypeCode)
    if (!type?.platform_code) return true
    const platforms = getProductPlatformCodes(productId)
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
    const list = isEdit ? dealAccountsEdit.value : dealAccountsNew.value
    const account = (list || []).find((a) => a.account_id === accountId)
    const codes = Array.isArray(account?.platform_codes) ? account.platform_codes : []
    return codes.map((c) => String(c).toLowerCase())
  }

  const isSlotTypeSupportedForDeal = (slotTypeCode, target) => {
    if (!slotTypeCode) return false
    const isEdit = target === 'edit'
    const productId = isEdit ? editDeal.product_id : newDeal.product_id
    const type = slotTypes.value.find((t) => t.code === slotTypeCode)
    if (!type?.platform_code) return true
    const accountPlatforms = getAccountPlatformCodesForDeal(target)
    if (accountPlatforms.length) {
      const hasPs4 = accountPlatforms.includes('ps4')
      if (hasPs4) return true
      return String(type.platform_code).toLowerCase() === 'ps5'
    }
    return isSlotTypeSupportedForProduct(slotTypeCode, productId)
  }

  // Формирует варианты типов слотов для формы сделки.
  const getDealSlotTypeOptions = (target) => {
    const isEdit = target === 'edit'
    const availability = isEdit ? dealSlotAvailabilityEdit.value : dealSlotAvailabilityNew.value
    const hasAssignments = isEdit ? hasAssignmentsEdit.value : hasAssignmentsNew.value
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
    const productId = isEdit ? editDeal.product_id : newDeal.product_id
    const slotTypeCode = isEdit ? editDeal.slot_type_code : newDeal.slot_type_code
    if (!productId || !slotTypeCode) return false
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
    const list = isEdit ? dealAccountsEdit.value : dealAccountsNew.value
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
    getProductLabelById,
    isSlotTypeSupportedForProduct,
    getDealSlotTypeOptions,
    getDealSlotTypeLabel,
    isDealSlotTypeUnsupported,
    hasFreeDealSlots,
  }
}
