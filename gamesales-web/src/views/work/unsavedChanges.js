function normalizeValue(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value.trim()
  if (Array.isArray(value)) return value.map(normalizeValue)
  if (typeof value === 'object') {
    const out = {}
    for (const key of Object.keys(value).sort()) {
      out[key] = normalizeValue(value[key])
    }
    return out
  }
  return value
}

// Сравнивает два значения после нормализации (строки, null/undefined, порядок ключей).
export function isSameNormalized(left, right) {
  return JSON.stringify(normalizeValue(left)) === JSON.stringify(normalizeValue(right))
}

// Показывает единое подтверждение, если пользователь закрывает форму с несохраненными изменениями.
export async function confirmDiscardIfNeeded(
  isDirty,
  {
    message = 'Закрыть без сохранения?',
    requestConfirm = null,
  } = {},
) {
  if (!isDirty) return true
  if (typeof requestConfirm === 'function') {
    return await requestConfirm(message)
  }
  return window.confirm(message)
}
