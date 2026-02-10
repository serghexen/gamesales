import { onBeforeUnmount, ref, watch } from 'vue'

import { API_BASE } from '../../api/http'

const RECONNECT_DELAYS_MS = [1000, 2000, 5000, 10000]

// Собирает URL websocket для событий сделок на основе API_BASE и токена.
export function buildDealsWsUrl(apiBase, token, locationLike = null) {
  const safeToken = String(token || '').trim()
  if (!safeToken) return ''
  const base = String(apiBase || '').trim().replace(/\/+$/, '')
  if (!base) return ''

  if (base.startsWith('http://') || base.startsWith('https://')) {
    const wsBase = base.replace(/^http/i, 'ws')
    return `${wsBase}/ws/deals?token=${encodeURIComponent(safeToken)}`
  }

  if (base.startsWith('/')) {
    const loc = locationLike || (typeof window !== 'undefined' ? window.location : null)
    if (!loc?.protocol || !loc?.host) return ''
    const wsProto = loc.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${wsProto}//${loc.host}${base}/ws/deals?token=${encodeURIComponent(safeToken)}`
  }

  return ''
}

export function useDealsRealtime({
  activeTab,
  auth,
  dealPage,
  editDeal,
  showDealForm,
  loadDeals,
  wsState: externalWsState = null,
}) {
  const wsState = externalWsState || ref('offline')
  let ws = null
  let reconnectTimer = null
  let reloadTimer = null
  let reconnectAttempt = 0
  let pendingRefresh = false

  const canApplyReloadNow = () => activeTab.value === 'deals' && !showDealForm.value && !editDeal.open

  // Обновляет список сделок с коротким debounce, чтобы не дергать API на каждое событие отдельно.
  const scheduleReload = () => {
    if (reloadTimer) clearTimeout(reloadTimer)
    reloadTimer = setTimeout(() => {
      reloadTimer = null
      loadDeals(dealPage.value)
    }, 250)
  }

  // Закрывает текущее websocket-подключение и очищает таймеры переподключения.
  const cleanupSocket = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.onopen = null
      ws.onmessage = null
      ws.onclose = null
      ws.onerror = null
      try {
        ws.close()
      } catch {
        // ignore close errors
      }
      ws = null
    }
    wsState.value = 'offline'
  }

  // Поднимает websocket для вкладки сделок и поддерживает reconnect при обрывах.
  const connect = () => {
    if (activeTab.value !== 'deals') return
    const token = auth?.state?.token
    const url = buildDealsWsUrl(API_BASE, token)
    if (!url || ws) return

    wsState.value = reconnectAttempt > 0 ? 'reconnecting' : 'connecting'
    ws = new WebSocket(url)
    ws.onopen = () => {
      reconnectAttempt = 0
      wsState.value = 'online'
    }
    ws.onmessage = (event) => {
      let payload = null
      try {
        payload = JSON.parse(String(event?.data || '{}'))
      } catch {
        return
      }
      if (!payload?.event || payload.event === 'connected') return
      if (canApplyReloadNow()) {
        scheduleReload()
        return
      }
      pendingRefresh = true
    }
    ws.onclose = () => {
      ws = null
      if (activeTab.value !== 'deals') return
      wsState.value = 'reconnecting'
      const delay = RECONNECT_DELAYS_MS[Math.min(reconnectAttempt, RECONNECT_DELAYS_MS.length - 1)]
      reconnectAttempt += 1
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null
        connect()
      }, delay)
    }
    ws.onerror = () => {
      // Ошибка сокета приводит к close, там уже сработает reconnect.
    }
  }

  // Следит за вкладкой и токеном: подключаемся только на вкладке сделок.
  watch(
    [activeTab, () => auth?.state?.token],
    ([tab, token]) => {
      if (tab === 'deals' && token) {
        connect()
        return
      }
      cleanupSocket()
    },
    { immediate: true },
  )

  // Если были отложенные события во время редактирования, применяем обновление после закрытия формы.
  watch(
    [activeTab, showDealForm, () => editDeal.open],
    ([tab, showCreate, showEdit]) => {
      if (!pendingRefresh) return
      if (tab !== 'deals' || showCreate || showEdit) return
      pendingRefresh = false
      scheduleReload()
    },
  )

  onBeforeUnmount(() => {
    pendingRefresh = false
    if (reloadTimer) clearTimeout(reloadTimer)
    cleanupSocket()
  })

  return {
    wsState,
  }
}
