export function createInterhubAgentTransactionId(now = Date.now, random = Math.random) {
  // Формируем числовой ID операции без букв, сохраняя уникальность при близких запросах.
  const timestamp = String(Math.max(0, Math.trunc(Number(now()) || 0)))
  const suffix = String(Math.floor(Math.max(0, Math.min(0.999, Number(random()) || 0)) * 1000)).padStart(3, '0')
  return `${timestamp}${suffix}`
}
