import { ref } from 'vue'

const MANAGERS_LOAD_POLL_MS = 30_000
const PRESENCE_HEARTBEAT_POLL_MS = 25_000

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
    refreshManagersWorkload()
    pollingTimer = setInterval(() => {
      refreshManagersWorkload()
    }, MANAGERS_LOAD_POLL_MS)
  }

  // Останавливает polling при уходе с дашборда или размонтировании экрана.
  function stopManagersWorkloadPolling() {
    if (!pollingTimer) return
    clearInterval(pollingTimer)
    pollingTimer = null
  }

  // Держит online-присутствие активным на любой вкладке рабочего экрана.
  function startPresenceHeartbeatPolling() {
    if (heartbeatTimer) return
    sendManagersHeartbeat()
    heartbeatTimer = setInterval(() => {
      sendManagersHeartbeat()
    }, PRESENCE_HEARTBEAT_POLL_MS)
  }

  // Останавливает heartbeat при выходе со страницы/разлогине.
  function stopPresenceHeartbeatPolling() {
    if (!heartbeatTimer) return
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
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
