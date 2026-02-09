export function useWorkFormatters({
  accountsAll,
  regions,
  domains,
  sources,
  dealFlowStatusOptions,
  maxGameTitleLength,
}) {
  // Подпись аккаунта по id для таблиц и форм.
  const getAccountLabelById = (accountId) => {
    if (!accountId) return '—'
    const found = (accountsAll.value || []).find((a) => a.account_id === accountId)
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

  // Подпись статуса сделки по коду.
  const getFlowStatusLabel = (code) => {
    if (!code) return '—'
    const status = dealFlowStatusOptions.find((s) => s.code === code)
    return status?.name || code
  }

  // Короткий заголовок игры в таблице сделок.
  const getDealGameTitleDisplay = (deal) => {
    if (!deal) return '—'
    const title = String(deal.game_title || '')
    const shortTitle = String(deal.game_short_title || '')
    if (title.length > maxGameTitleLength && shortTitle) {
      return shortTitle
    }
    return title || '—'
  }

  // Полный заголовок игры (для tooltip, если текст обрезан).
  const getDealGameTitleTooltip = (deal) => {
    if (!deal) return ''
    const title = String(deal.game_title || '')
    const shortTitle = String(deal.game_short_title || '')
    if (title.length > maxGameTitleLength && shortTitle) {
      return title
    }
    return ''
  }

  const formatGamePlatforms = (codes) => {
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
    getFlowStatusLabel,
    getDealGameTitleDisplay,
    getDealGameTitleTooltip,
    formatGamePlatforms,
    formatSecret,
    formatDateOnly,
    formatDateTimeMinutes,
  }
}
