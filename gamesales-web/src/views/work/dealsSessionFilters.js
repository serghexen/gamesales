export const DEAL_FILTERS_SESSION_KEY_PREFIX = 'gamesales:deal-filters:'

// Строит ключ хранения фильтров по пользователю, чтобы сессии не смешивались.
export function buildDealFiltersSessionKey(username) {
  const normalized = String(username || '').trim().toLowerCase()
  if (!normalized) return ''
  return `${DEAL_FILTERS_SESSION_KEY_PREFIX}${normalized}`
}

// Читает фильтры сделок из sessionStorage и валидирует базовую структуру.
export function readDealFiltersSession(username, storage = sessionStorage) {
  const key = buildDealFiltersSessionKey(username)
  if (!key) return null
  try {
    const raw = storage.getItem(key)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return null
    if (!parsed.filters || typeof parsed.filters !== 'object') return null
    return {
      filters: parsed.filters,
      showCompleted: Boolean(parsed.showCompleted),
    }
  } catch {
    return null
  }
}

// Сохраняет текущие фильтры сделки в рамках сессии браузера.
export function writeDealFiltersSession(username, filters, showCompleted, storage = sessionStorage) {
  const key = buildDealFiltersSessionKey(username)
  if (!key) return
  const payload = {
    filters: {
      search_q: String(filters?.search_q || ''),
      customer_q: String(filters?.customer_q || ''),
      responsible_q: String(filters?.responsible_q || ''),
      region_q: String(filters?.region_q || ''),
      status_q: String(filters?.status_q || ''),
      purchase_from: String(filters?.purchase_from || ''),
      purchase_to: String(filters?.purchase_to || ''),
      type_q: String(filters?.type_q || ''),
    },
    showCompleted: Boolean(showCompleted),
  }
  try {
    storage.setItem(key, JSON.stringify(payload))
  } catch {
    // Игнорируем ошибки quota/private mode: фильтры просто не сохранятся.
  }
}

// Очищает все сессионные фильтры сделок (используется при logout).
export function clearDealFiltersSessionByPrefix(storage = sessionStorage) {
  try {
    const keys = []
    for (let i = 0; i < storage.length; i += 1) {
      const key = storage.key(i)
      if (key && key.startsWith(DEAL_FILTERS_SESSION_KEY_PREFIX)) keys.push(key)
    }
    for (const key of keys) storage.removeItem(key)
  } catch {
    // Если storage недоступен, пропускаем очистку без падения.
  }
}
