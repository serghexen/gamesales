import { onBeforeUnmount, ref, watch } from 'vue'

import { API_BASE } from '../../api/http'

const RECONNECT_DELAYS_MS = [1000, 2000, 5000, 10000]
const DEAL_EDIT_HEARTBEAT_MS = 15000

// Применяет событие редактирования к локальной карте блокировок по сделкам.
export function applyDealEditingRealtimeEvent(editingByDealId, payload) {
  const current = editingByDealId && typeof editingByDealId === 'object' ? editingByDealId : {}
  const eventType = String(payload?.event || '').trim().toLowerCase()
  if (eventType === 'connected') {
    const list = Array.isArray(payload?.editing) ? payload.editing : []
    const next = {}
    for (const item of list) {
      const dealId = Number(item?.deal_id || 0)
      const actor = String(item?.actor || '').trim()
      if (!dealId || !actor) continue
      next[dealId] = {
        actor,
        changedAt: String(item?.changed_at || ''),
      }
    }
    return next
  }
  const dealId = Number(payload?.deal_id || 0)
  if (!dealId) return current
  if (eventType === 'deal_edit_started') {
    return {
      ...current,
      [dealId]: {
        actor: String(payload?.actor || '').trim(),
        changedAt: String(payload?.changed_at || ''),
      },
    }
  }
  if (eventType === 'deal_edit_stopped') {
    const next = { ...current }
    delete next[dealId]
    return next
  }
  return current
}

// Определяет, нужно ли держать lock для сделки: только в режиме реального редактирования.
export function shouldHoldDealEditLock({ activeTab, editDealOpen, dealEditMode, dealId }) {
  const tab = String(activeTab || '').trim().toLowerCase()
  const mode = String(dealEditMode || '').trim().toLowerCase()
  const normalizedDealId = Number(dealId || 0)
  return tab === 'deals' && Boolean(editDealOpen) && mode === 'edit' && normalizedDealId > 0
}

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
  dealEditMode,
  showDealForm,
  loadDeals,
  onDealEvent = null,
  wsState: externalWsState = null,
  editingByDealId: externalEditingByDealId = null,
  realtimeAnimationTick: externalRealtimeAnimationTick = null,
}) {
  const wsState = externalWsState || ref('offline')
  const editingByDealId = externalEditingByDealId || ref({})
  const realtimeAnimationTick = externalRealtimeAnimationTick || ref(0)
  let ws = null
  let reconnectTimer = null
  let reloadTimer = null
  let reconnectAttempt = 0
  let pendingRefresh = false
  let editingDealId = null
  let editHeartbeatTimer = null
  const hasExternalDealEventHook = typeof onDealEvent === 'function'

  // Определяет, нужно ли держать websocket активным в текущем состоянии экрана.
  const shouldKeepSocket = () => {
    const token = auth?.state?.token
    if (!token) return false
    return activeTab.value === 'deals' || hasExternalDealEventHook
  }

  const canApplyReloadNow = () => activeTab.value === 'deals' && !showDealForm.value && !editDeal.open

  // Помечает следующее обновление списка как websocket-обновление для анимации строк.
  const markRealtimeAnimation = () => {
    realtimeAnimationTick.value += 1
  }

  // Отправляет событие редактирования сделки на backend по активному websocket.
  const sendEditingEvent = (eventType, dealId) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    const normalizedId = Number(dealId || 0)
    if (!normalizedId) return
    try {
      ws.send(JSON.stringify({ event: eventType, deal_id: normalizedId }))
    } catch {
      // Ошибку отправки проглатываем: состояние синхронизируется при следующем соединении.
    }
  }

  // Запускает периодическое продление lock во время редактирования сделки.
  const startEditHeartbeat = () => {
    if (editHeartbeatTimer || !editingDealId) return
    editHeartbeatTimer = setInterval(() => {
      sendEditingEvent('deal_edit_heartbeat', editingDealId)
    }, DEAL_EDIT_HEARTBEAT_MS)
  }

  // Останавливает heartbeat, когда редактирование завершено или сокет отключен.
  const stopEditHeartbeat = () => {
    if (!editHeartbeatTimer) return
    clearInterval(editHeartbeatTimer)
    editHeartbeatTimer = null
  }

  // Синхронизирует "мягкий lock" текущего пользователя по состоянию модалки редактирования.
  const syncEditingState = () => {
    const nextDealId = shouldHoldDealEditLock({
      activeTab: activeTab.value,
      editDealOpen: editDeal.open,
      dealEditMode: dealEditMode?.value,
      dealId: editDeal.deal_id,
    })
      ? Number(editDeal.deal_id || 0)
      : 0
    if (editingDealId && editingDealId !== nextDealId) {
      sendEditingEvent('deal_edit_stopped', editingDealId)
      editingDealId = null
      stopEditHeartbeat()
    }
    if (nextDealId && editingDealId !== nextDealId) {
      sendEditingEvent('deal_edit_started', nextDealId)
      editingDealId = nextDealId
      startEditHeartbeat()
    }
    if (!nextDealId) stopEditHeartbeat()
  }

  // Обновляет список сделок с коротким debounce, чтобы не дергать API на каждое событие отдельно.
  const scheduleReload = () => {
    if (reloadTimer) clearTimeout(reloadTimer)
    reloadTimer = setTimeout(() => {
      reloadTimer = null
      // Перед перезагрузкой отмечаем, что изменения пришли из realtime-канала.
      markRealtimeAnimation()
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
      if (editingDealId) {
        sendEditingEvent('deal_edit_stopped', editingDealId)
        editingDealId = null
      }
      stopEditHeartbeat()
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
    if (!shouldKeepSocket()) return
    const token = auth?.state?.token
    const url = buildDealsWsUrl(API_BASE, token)
    if (!url || ws) return

    wsState.value = reconnectAttempt > 0 ? 'reconnecting' : 'connecting'
    ws = new WebSocket(url)
    ws.onopen = () => {
      reconnectAttempt = 0
      wsState.value = 'online'
      // После переподключения повторно заявляем, что текущая сделка открыта на редактирование.
      syncEditingState()
      startEditHeartbeat()
    }
    ws.onmessage = (event) => {
      let payload = null
      try {
        payload = JSON.parse(String(event?.data || '{}'))
      } catch {
        return
      }
      if (!payload?.event) return
      // Пробрасываем событие наружу, чтобы другие виджеты могли обновляться по этому же WS-каналу.
      if (typeof onDealEvent === 'function') {
        try {
          onDealEvent(payload)
        } catch {
          // Ошибка внешнего обработчика не должна ломать основной realtime-поток.
        }
      }
      editingByDealId.value = applyDealEditingRealtimeEvent(editingByDealId.value, payload)
      if (payload.event === 'connected') return
      if (canApplyReloadNow()) {
        scheduleReload()
        return
      }
      pendingRefresh = true
    }
    ws.onclose = () => {
      ws = null
      if (!shouldKeepSocket()) return
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
      if (token && (tab === 'deals' || hasExternalDealEventHook)) {
        connect()
        return
      }
      cleanupSocket()
    },
    { immediate: true },
  )

  watch(
    [activeTab, () => editDeal.open, () => editDeal.deal_id, () => dealEditMode?.value],
    () => {
      syncEditingState()
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
    if (editingDealId) {
      sendEditingEvent('deal_edit_stopped', editingDealId)
      editingDealId = null
    }
    stopEditHeartbeat()
    cleanupSocket()
  })

  return {
    wsState,
    editingByDealId,
    realtimeAnimationTick,
  }
}
