export function useWorkFormatters({
  accountsAll,
  regions,
  domains,
  sources,
  messengers,
  dealFlowStatusOptions,
  maxProductTitleLength,
}) {
  // Лимит нужен для показа короткого названия в таблице сделок.
  const maxTitleLength = Number(maxProductTitleLength ?? 0)

  // Сравнивает id как число (когда возможно), чтобы строковые и числовые id считались одинаковыми.
  function isSameEntityId(leftId, rightId) {
    const leftNum = Number(leftId)
    const rightNum = Number(rightId)
    if (Number.isFinite(leftNum) && Number.isFinite(rightNum)) {
      return leftNum === rightNum
    }
    return String(leftId || '').trim() === String(rightId || '').trim()
  }

  // Подпись аккаунта по id для таблиц и форм.
  const getAccountLabelById = (accountId) => {
    if (!accountId) return '—'
    const found = (accountsAll.value || []).find((a) => isSameEntityId(a?.account_id, accountId))
    return found?.login_full || found?.login_name || String(accountId)
  }

  // Подпись региона в виде "Название (код)".
  const getRegionLabel = (code) => {
    if (!code) return '—'
    const region = (regions.value || []).find((r) => r.code === code)
    return region ? `${region.name} (${region.code})` : code
  }

  // Подпись домена.
  const getDomainLabel = (code) => {
    if (!code) return '—'
    const domain = (domains.value || []).find((d) => d.name === code)
    return domain?.name || code
  }

  // Подпись статуса аккаунта.
  const getAccountStatusLabel = (code) => {
    if (!code) return '—'
    return code
  }

  // Подпись источника по id.
  const getSourceLabelById = (sourceId) => {
    if (!sourceId) return '—'
    const source = (sources.value || []).find((s) => s.source_id === sourceId)
    return source ? `${source.name} (${source.code})` : String(sourceId)
  }

  // Подпись мессенджера по id.
  const getMessengerLabelById = (messengerId) => {
    if (!messengerId) return '—'
    const messenger = (messengers.value || []).find((m) => m.messenger_id === messengerId)
    return messenger ? `${messenger.name} (${messenger.code})` : String(messengerId)
  }

  // Подпись статуса сделки по коду.
  const getFlowStatusLabel = (code) => {
    if (!code) return '—'
    const status = dealFlowStatusOptions.find((s) => s.code === code)
    return status?.name || code
  }

  // Короткий заголовок товара в таблице сделок.
  const getDealProductTitleDisplay = (deal) => {
    if (!deal) return '—'
    const title = String(deal.product_title || '')
    const shortTitle = String(deal.product_short_title || '')
    if (title.length > maxTitleLength && shortTitle) {
      return shortTitle
    }
    return title || '—'
  }

  // Полный заголовок товара (для tooltip, если текст обрезан).
  const getDealProductTitleTooltip = (deal) => {
    if (!deal) return ''
    const title = String(deal.product_title || '')
    const shortTitle = String(deal.product_short_title || '')
    if (title.length > maxTitleLength && shortTitle) {
      return title
    }
    return ''
  }

  const formatProductPlatforms = (codes) => {
    const list = Array.isArray(codes) ? codes : []
    if (!list.length) return '—'
    return list.join(', ')
  }

  function formatSecret(value) {
    if (!value) return '—'
    return value
  }

  // Универсальный формат даты.
  function formatDateOnly(value) {
    if (!value) return '—'
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return '—'
    return d.toLocaleDateString()
  }

  // Формат дата + время до минут.
  function formatDateTimeMinutes(value) {
    if (!value) return '—'
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return '—'
    const date = d.toLocaleDateString()
    const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    return `${date} ${time}`
  }

  return {
    getAccountLabelById,
    getRegionLabel,
    getDomainLabel,
    getAccountStatusLabel,
    getSourceLabelById,
    getMessengerLabelById,
    getFlowStatusLabel,
    getDealProductTitleDisplay,
    getDealProductTitleTooltip,
    formatProductPlatforms,
    formatSecret,
    formatDateOnly,
    formatDateTimeMinutes,
  }
}
