export function isDealMutationRealtimeEvent(payload) {
  // Отбирает только события, после которых расчетные виджеты по сделкам могут измениться.
  const eventType = String(payload?.event || '').trim().toLowerCase()
  return eventType === 'deal_created' || eventType === 'deal_updated' || eventType === 'deal_deleted'
}

export function createRealtimeRefreshScheduler(runRefresh, minIntervalMs = 1000) {
  let refreshTimer = null
  let refreshQueued = false
  let refreshLastAt = 0
  const safeMinIntervalMs = Math.max(0, Number(minIntervalMs) || 0)

  function runNow() {
    // Выполняет отложенное обновление и запоминает время, чтобы сжать частые события.
    refreshQueued = false
    refreshTimer = null
    refreshLastAt = Date.now()
    runRefresh?.()
  }

  function schedule() {
    // Ставит обновление в очередь, но не чаще заданного интервала.
    refreshQueued = true
    const elapsed = Date.now() - refreshLastAt
    if (!refreshTimer && elapsed >= safeMinIntervalMs) {
      runNow()
      return
    }
    if (refreshTimer) return
    const waitMs = Math.max(50, safeMinIntervalMs - elapsed)
    refreshTimer = setTimeout(() => {
      if (!refreshQueued) {
        refreshTimer = null
        return
      }
      runNow()
    }, waitMs)
  }

  function cleanup() {
    // Очищает таймер при размонтировании экрана, чтобы не было поздних запросов.
    if (refreshTimer) {
      clearTimeout(refreshTimer)
      refreshTimer = null
    }
    refreshQueued = false
  }

  return {
    schedule,
    cleanup,
  }
}
