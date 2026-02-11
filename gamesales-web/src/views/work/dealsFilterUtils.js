// Превращает строку фильтра ответственных в массив значений для мультивыбора.
export function parseResponsibleFilterQuery(query) {
  return String(query || '')
    .split(',')
    .map((item) => String(item || '').trim())
    .filter(Boolean)
}

// Собирает строку фильтра из выбранных ответственных для отправки в API.
export function stringifyResponsibleFilterQuery(values) {
  if (!Array.isArray(values)) return ''
  const normalized = values
    .map((item) => String(item || '').trim())
    .filter(Boolean)
  return Array.from(new Set(normalized)).join(',')
}
