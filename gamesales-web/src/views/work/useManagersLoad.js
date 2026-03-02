import { ref } from 'vue'

const MANAGERS_LOAD_POLL_MS = 5_000
const MANAGERS_LOAD_POLL_BG_MS = 20_000
const PRESENCE_HEARTBEAT_POLL_MS = 5_000
const PRESENCE_HEARTBEAT_POLL_BG_MS = 20_000

export function useManagersLoad({ auth, apiGet, apiPost, mapApiError }) {
  const managersLoadItems = ref([])
  const managersLoadOnlineCount = ref(0)
  const managersLoadDate = ref('')
  const managersLoadTimezone = ref('Europe/Moscow')
  const managersLoadLoading = ref(false)
  const managersLoadError = ref('')

  let pollingTimer = null
  let requestInFlight = false
  let heartbeatTimer = null
  let heartbeatInFlight = false
  let visibilityBound = false

  // Возвращает интервал опроса для активной/фоновой вкладки.
  function resolvePollInterval(activeMs, backgroundMs) {
    if (typeof document === 'undefined') return activeMs
    return document.hidden ? backgroundMs : activeMs
  }

  // Перезапускает интервалы при смене видимости вкладки, чтобы снизить фоновую нагрузку.
  function handleVisibilityChange() {
    if (pollingTimer) {
      clearInterval(pollingTimer)
      pollingTimer = setInterval(() => {
        refreshManagersWorkload()
      }, resolvePollInterval(MANAGERS_LOAD_POLL_MS, MANAGERS_LOAD_POLL_BG_MS))
    }
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = setInterval(() => {
        sendManagersHeartbeat()
      }, resolvePollInterval(PRESENCE_HEARTBEAT_POLL_MS, PRESENCE_HEARTBEAT_POLL_BG_MS))
    }
  }

  // Подписывает на visibilitychange только когда есть хотя бы один активный таймер.
  function ensureVisibilitySubscription() {
    if (visibilityBound || typeof document === 'undefined') return
    document.addEventListener('visibilitychange', handleVisibilityChange)
    visibilityBound = true
  }

  // Снимает подписку, когда polling и heartbeat остановлены.
  function releaseVisibilitySubscription() {
    if (!visibilityBound || typeof document === 'undefined') return
    if (pollingTimer || heartbeatTimer) return
    document.removeEventListener('visibilitychange', handleVisibilityChange)
    visibilityBound = false
  }

  // Отправляет heartbeat в backend, чтобы текущий пользователь оставался в списке онлайн.
  async function sendManagersHeartbeat() {
    if (heartbeatInFlight) return
    heartbeatInFlight = true
    try {
      await apiPost('/presence/heartbeat', {}, { token: auth.state.token })
    } catch {
      // Ошибку heartbeat не показываем отдельно, ее отразит основной запрос нагрузки.
    } finally {
      heartbeatInFlight = false
    }
  }

  // Загружает список онлайн-менеджеров и их количество заявок "в ожидании" за текущий день.
  async function loadManagersWorkload() {
    if (requestInFlight) return
    requestInFlight = true
    managersLoadLoading.value = true
    managersLoadError.value = ''
    try {
      const data = await apiGet('/dashboard/managers-load', { token: auth.state.token })
      managersLoadItems.value = Array.isArray(data?.items) ? data.items : []
      managersLoadOnlineCount.value = Number(data?.online_count || 0)
      managersLoadDate.value = String(data?.date || '')
      managersLoadTimezone.value = String(data?.timezone || 'Europe/Moscow')
    } catch (e) {
      managersLoadItems.value = []
      managersLoadOnlineCount.value = 0
      managersLoadError.value = mapApiError(e?.message)
    } finally {
      managersLoadLoading.value = false
      requestInFlight = false
    }
  }

  // Обновляет heartbeat и сразу перезапрашивает агрегаты по менеджерам.
  async function refreshManagersWorkload() {
    await sendManagersHeartbeat()
    await loadManagersWorkload()
  }

  // Запускает регулярное обновление виджета нагрузки менеджеров на дашборде.
  function startManagersWorkloadPolling() {
    if (pollingTimer) return
    ensureVisibilitySubscription()
    refreshManagersWorkload()
    pollingTimer = setInterval(() => {
      refreshManagersWorkload()
    }, resolvePollInterval(MANAGERS_LOAD_POLL_MS, MANAGERS_LOAD_POLL_BG_MS))
  }

  // Останавливает polling при уходе с дашборда или размонтировании экрана.
  function stopManagersWorkloadPolling() {
    if (!pollingTimer) return
    clearInterval(pollingTimer)
    pollingTimer = null
    releaseVisibilitySubscription()
  }

  // Держит online-присутствие активным на любой вкладке рабочего экрана.
  function startPresenceHeartbeatPolling() {
    if (heartbeatTimer) return
    ensureVisibilitySubscription()
    sendManagersHeartbeat()
    heartbeatTimer = setInterval(() => {
      sendManagersHeartbeat()
    }, resolvePollInterval(PRESENCE_HEARTBEAT_POLL_MS, PRESENCE_HEARTBEAT_POLL_BG_MS))
  }

  // Останавливает heartbeat при выходе со страницы/разлогине.
  function stopPresenceHeartbeatPolling() {
    if (!heartbeatTimer) return
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
    releaseVisibilitySubscription()
  }

  return {
    managersLoadItems,
    managersLoadOnlineCount,
    managersLoadDate,
    managersLoadTimezone,
    managersLoadLoading,
    managersLoadError,
    refreshManagersWorkload,
    startManagersWorkloadPolling,
    stopManagersWorkloadPolling,
    startPresenceHeartbeatPolling,
    stopPresenceHeartbeatPolling,
  }
}
