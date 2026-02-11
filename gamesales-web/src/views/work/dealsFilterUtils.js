// Превращает строку фильтра в массив значений для мультивыбора.
export function parseMultiValueFilterQuery(query) {
  return String(query || '')
    .split(',')
    .map((item) => String(item || '').trim())
    .filter(Boolean)
}

// Собирает строку фильтра из выбранных значений для отправки в API.
export function stringifyMultiValueFilterQuery(values) {
  if (!Array.isArray(values)) return ''
  const normalized = values
    .map((item) => String(item || '').trim())
    .filter(Boolean)
  return Array.from(new Set(normalized)).join(',')
}

// Совместимость со старым API названий для фильтра ответственных.
export const parseResponsibleFilterQuery = parseMultiValueFilterQuery
// Совместимость со старым API названий для фильтра ответственных.
export const stringifyResponsibleFilterQuery = stringifyMultiValueFilterQuery
