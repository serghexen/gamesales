export function useTelegram({
  auth,
  telegram,
  activeTab,
  tgMessagesList,
  apiGet,
  apiPost,
  apiPut,
  apiGetFile,
  mapApiError,
  nextTick,
  showTelegramChannelLabelForList,
  TELEGRAM_DIALOGS_POLL_MS,
  TELEGRAM_MESSAGES_POLL_MS,
  TELEGRAM_DIALOGS_POLL_ERROR_MS,
  TELEGRAM_MESSAGES_POLL_ERROR_MS,
}) {
  // Таймеры и флаги, чтобы опрос Telegram не запускался параллельно.
  let telegramDialogsPollTimer = null
  let telegramMessagesPollTimer = null
  let telegramDialogsPollBusy = false
  let telegramMessagesPollBusy = false

  // Загружает текущий статус подключения Telegram.
  async function loadTelegramStatus() {
    telegram.loading = true
    telegram.error = ''
    telegram.info = ''
    try {
      const data = await apiGet('/tg/status', { token: auth.state.token })
      telegram.status = data?.status || 'not_connected'
      telegram.phone = data?.phone || ''
      if (telegram.status === 'ready') {
        await loadTelegramDialogs()
      }
    } catch (e) {
      telegram.error = mapApiError(e?.message)
    } finally {
      telegram.loading = false
    }
  }

  // Шаг 1 авторизации: отправка кода на телефон.
  async function tgAuthStart() {
    if (!telegram.phone) {
      telegram.error = 'Введите телефон'
      return
    }
    telegram.loading = true
    telegram.error = ''
    telegram.info = ''
    try {
      await apiPost('/tg/auth/start', { phone: telegram.phone }, { token: auth.state.token })
      telegram.status = 'pending'
      telegram.info = 'Код отправлен'
    } catch (e) {
      telegram.error = mapApiError(e?.message)
    } finally {
      telegram.loading = false
    }
  }

  // Шаг 2 авторизации: подтверждение кода из Telegram.
  async function tgAuthConfirm() {
    if (!telegram.code) {
      telegram.error = 'Введите код'
      return
    }
    telegram.loading = true
    telegram.error = ''
    telegram.info = ''
    try {
      const res = await apiPost('/tg/auth/confirm', { code: telegram.code }, { token: auth.state.token })
      if (res?.status === 'password_required') {
        telegram.status = 'password_required'
        telegram.info = 'Нужен пароль 2FA'
      } else {
        telegram.status = 'ready'
        telegram.code = ''
        await loadTelegramDialogs()
      }
    } catch (e) {
      telegram.error = mapApiError(e?.message)
    } finally {
      telegram.loading = false
    }
  }

  // Шаг 3 авторизации при 2FA: проверка пароля.
  async function tgAuthPassword() {
    if (!telegram.password) {
      telegram.error = 'Введите пароль'
      return
    }
    telegram.loading = true
    telegram.error = ''
    telegram.info = ''
    try {
      await apiPost('/tg/auth/password', { password: telegram.password }, { token: auth.state.token })
      telegram.status = 'ready'
      telegram.password = ''
      await loadTelegramDialogs()
    } catch (e) {
      telegram.error = mapApiError(e?.message)
    } finally {
      telegram.loading = false
    }
  }

  // Полностью отвязывает Telegram и чистит локальное состояние вкладки.
  async function tgAuthDisconnect() {
    telegram.loading = true
    telegram.error = ''
    telegram.info = ''
    try {
      await apiPost('/tg/auth/disconnect', {}, { token: auth.state.token })
      telegram.status = 'not_connected'
      stopTelegramPolling()
      telegram.phone = ''
      telegram.code = ''
      telegram.password = ''
      telegram.dialogs = []
      telegram.messages = []
      telegram.loadingMessages = false
      telegram.loadingOlderMessages = false
      telegram.hasMoreOlderMessages = true
      telegram.dialogsSyncLoaded = 0
      telegram.dialogsSyncBatches = 0
      telegram.activeChatId = null
      telegram.activeDialog = null
      telegram.activeContactId = null
      telegram.contact = { title: '', info: '' }
      telegram.contactEdit = { title: '', info: '' }
      telegram.contactMeta = { name: '', username: '' }
      telegram.contactEditing = false
      telegram.info = 'Telegram отключен'
    } catch (e) {
      telegram.error = mapApiError(e?.message)
    } finally {
      telegram.loading = false
    }
  }

  // Загружает список диалогов и счетчики.
  async function loadTelegramDialogs() {
    telegram.loading = true
    telegram.error = ''
    try {
      const params = new URLSearchParams()
      if (telegram.dialogStatusFilter && telegram.dialogStatusFilter !== 'all') {
        params.set('status', telegram.dialogStatusFilter)
      }
      const data = await apiGet(`/tg/dialogs?${params.toString()}`, { token: auth.state.token })
      telegram.dialogs = data?.items || []
      telegram.dialogCounts = data?.counts || { new: 0, accepted: 0, archived: 0, all: 0 }
      telegram.dialogsSyncRunning = Boolean(data?.sync_running)
      telegram.dialogsLastSyncAt = data?.last_sync_at || ''
      telegram.dialogsSyncLoaded = Number(data?.sync_loaded || 0)
      telegram.dialogsSyncBatches = Number(data?.sync_batches || 0)
      if (telegram.activeChatId) {
        telegram.activeDialog = telegram.dialogs.find((d) => d.id === telegram.activeChatId) || null
        if (!telegram.activeDialog) {
          revokeTelegramMediaUrls()
          telegram.activeChatId = null
          telegram.messages = []
          telegram.loadingOlderMessages = false
          telegram.hasMoreOlderMessages = true
          telegram.activeContactId = null
          telegram.contactEditing = false
          telegram.contact = { title: '', info: '' }
          telegram.contactEdit = { title: '', info: '' }
          telegram.contactMeta = { name: '', username: '' }
        }
      }
    } catch (e) {
      telegram.error = mapApiError(e?.message)
      telegram.dialogs = []
      telegram.dialogCounts = { new: 0, accepted: 0, archived: 0, all: 0 }
      telegram.dialogsSyncRunning = false
      telegram.dialogsLastSyncAt = ''
      telegram.dialogsSyncLoaded = 0
      telegram.dialogsSyncBatches = 0
    } finally {
      telegram.loading = false
    }
  }

  async function loadTelegramDialogsQuiet() {
    const params = new URLSearchParams()
    if (telegram.dialogStatusFilter && telegram.dialogStatusFilter !== 'all') {
      params.set('status', telegram.dialogStatusFilter)
    }
    const data = await apiGet(`/tg/dialogs?${params.toString()}`, { token: auth.state.token })
    telegram.dialogs = data?.items || []
    telegram.dialogCounts = data?.counts || { new: 0, accepted: 0, archived: 0, all: 0 }
    telegram.dialogsSyncRunning = Boolean(data?.sync_running)
    telegram.dialogsLastSyncAt = data?.last_sync_at || ''
    telegram.dialogsSyncLoaded = Number(data?.sync_loaded || 0)
    telegram.dialogsSyncBatches = Number(data?.sync_batches || 0)
    if (telegram.activeChatId) {
      telegram.activeDialog = telegram.dialogs.find((d) => d.id === telegram.activeChatId) || null
      if (!telegram.activeDialog) {
        revokeTelegramMediaUrls()
        telegram.activeChatId = null
        telegram.messages = []
        telegram.loadingOlderMessages = false
        telegram.hasMoreOlderMessages = true
        telegram.activeContactId = null
        telegram.contactEditing = false
        telegram.contact = { title: '', info: '' }
        telegram.contactEdit = { title: '', info: '' }
        telegram.contactMeta = { name: '', username: '' }
      }
    }
  }

  // Переключает фильтр списка диалогов (новые/принятые/архив).
  async function setTelegramDialogFilter(status) {
    if (!['all', 'new', 'accepted', 'archived'].includes(status)) return
    if (telegram.dialogStatusFilter === status) return
    telegram.dialogStatusFilter = status
    await loadTelegramDialogs()
  }

  // Открывает выбранный диалог и загружает сообщения.
  async function selectTelegramDialog(dialogId) {
    revokeTelegramMediaUrls()
    telegram.activeChatId = dialogId
    telegram.activeDialog = telegram.dialogs.find((d) => d.id === dialogId) || null
    telegram.messages = []
    telegram.activeContactId = null
    telegram.loadingOlderMessages = false
    telegram.hasMoreOlderMessages = true
    telegram.autoStickBottom = true
    telegram.contactEditing = false
    telegram.contact = { title: '', info: '' }
    telegram.contactMeta = { name: '', username: '' }
    telegram.loadingMessages = true
    telegram.error = ''
    try {
      const data = await apiGet(`/tg/messages?chat_id=${dialogId}&limit=100`, { token: auth.state.token })
      const initialItems = (data?.items || []).slice().reverse()
      telegram.messages = initialItems
      telegram.hasMoreOlderMessages = initialItems.length >= 100
      setTelegramDefaultContact()
      await loadTelegramContact()
      await nextTick()
      scrollTelegramToBottom(true)
      telegram.loadingMessages = false
      loadTelegramMessageMedia()
      scheduleTelegramMessagesPoll(200)
    } catch (e) {
      telegram.error = mapApiError(e?.message)
      telegram.loadingMessages = false
    }
  }

  function revokeTelegramMediaUrls() {
    telegram.messages.forEach((m) => {
      if (m?.media_url && String(m.media_url).startsWith('blob:')) {
        URL.revokeObjectURL(m.media_url)
      }
    })
  }

  async function loadTelegramMessageMedia() {
    const chatId = telegram.activeChatId
    if (!chatId) return
    const batch = []
    const BATCH_SIZE = 4
    const BATCH_DELAY_MS = 120
    let lastFlushAt = Date.now()

    const flushBatch = async (force = false) => {
      if (!batch.length) return
      const now = Date.now()
      if (!force && batch.length < BATCH_SIZE && now - lastFlushAt < BATCH_DELAY_MS) return
      const keepBottom = isTelegramNearBottom(140) || telegram.autoStickBottom
      while (batch.length) {
        const item = batch.shift()
        if (!item) break
        if (telegram.activeChatId !== chatId) return
        item.msg.media_url = item.url
      }
      await nextTick()
      if (keepBottom) scrollTelegramToBottom(true)
      lastFlushAt = now
    }

    for (const msg of telegram.messages) {
      if (!msg?.has_media || msg?.media_url) continue
      if (telegram.activeChatId !== chatId) return
      try {
        const blob = await apiGetFile(`/tg/media?chat_id=${chatId}&message_id=${msg.id}`, { token: auth.state.token })
        batch.push({ msg, url: URL.createObjectURL(blob) })
        await flushBatch(false)
      } catch {
        // ignore media load failures
      }
    }
    await flushBatch(true)
  }

  async function refreshActiveTelegramMessagesQuiet() {
    const chatId = telegram.activeChatId
    if (!chatId) return
    const keepBottom = isTelegramNearBottom(140) || telegram.autoStickBottom
    const current = telegram.messages || []
    const newestId = current.length ? Number(current[current.length - 1]?.id || 0) : 0
    const prevById = new Map(current.map((m) => [m.id, m]))
    const url = newestId
      ? `/tg/messages?chat_id=${chatId}&min_id=${newestId}&limit=50`
      : `/tg/messages?chat_id=${chatId}&limit=50`
    const data = await apiGet(url, { token: auth.state.token })
    const incoming = (data?.items || []).slice().reverse()
    if (!incoming.length) return
    const appended = []
    for (const msg of incoming) {
      if (prevById.has(msg.id)) continue
      appended.push(msg)
    }
    if (!appended.length) return
    telegram.messages = [...current, ...appended]
    setTelegramDefaultContact()
    await nextTick()
    if (keepBottom) scrollTelegramToBottom(true)
    loadTelegramMessageMedia()
  }

  async function loadOlderTelegramMessages() {
    if (!telegram.activeChatId || telegram.loadingOlderMessages || !telegram.hasMoreOlderMessages) return
    const listEl = resolveTelegramMessagesEl()
    if (!listEl) return
    const oldestId = Number(telegram.messages?.[0]?.id || 0)
    if (!oldestId) {
      telegram.hasMoreOlderMessages = false
      return
    }

    telegram.loadingOlderMessages = true
    const prevHeight = listEl.scrollHeight
    const prevTop = listEl.scrollTop
    try {
      const data = await apiGet(`/tg/messages?chat_id=${telegram.activeChatId}&max_id=${oldestId}&limit=50`, {
        token: auth.state.token,
      })
      const incomingRaw = data?.items || []
      const incoming = incomingRaw.slice().reverse()
      if (!incoming.length) {
        telegram.hasMoreOlderMessages = false
        return
      }
      const knownIds = new Set((telegram.messages || []).map((m) => m.id))
      const older = incoming.filter((m) => !knownIds.has(m.id))
      if (!older.length) {
        telegram.hasMoreOlderMessages = false
        return
      }
      telegram.messages = [...older, ...(telegram.messages || [])]
      telegram.hasMoreOlderMessages = incomingRaw.length >= 50
      await nextTick()
      const nextHeight = listEl.scrollHeight
      listEl.scrollTop = prevTop + (nextHeight - prevHeight)
      loadTelegramMessageMedia()
    } finally {
      telegram.loadingOlderMessages = false
    }
  }

  function isTelegramNearBottom(threshold = 100) {
    const el = resolveTelegramMessagesEl()
    if (!el) return true
    const distance = el.scrollHeight - el.clientHeight - el.scrollTop
    return distance <= threshold
  }

  function updateTelegramAutoStick() {
    telegram.autoStickBottom = isTelegramNearBottom(120)
  }

  function onTelegramMessagesScroll() {
    updateTelegramAutoStick()
    const el = resolveTelegramMessagesEl()
    if (!el) return
    if (el.scrollTop <= 80) {
      loadOlderTelegramMessages()
    }
  }

  function scrollTelegramToBottom(force = false) {
    const el = resolveTelegramMessagesEl()
    if (!el) return
    if (!force && !telegram.autoStickBottom) return
    el.scrollTop = el.scrollHeight
  }

  function resolveTelegramMessagesEl() {
    const target = tgMessagesList.value
    if (!target) return null
    return target?.$el || target
  }

  function onTelegramMediaRendered() {
    if (telegram.autoStickBottom || isTelegramNearBottom(140)) {
      requestAnimationFrame(() => scrollTelegramToBottom(true))
    }
  }

  function setTelegramDefaultContact() {
    const messages = telegram.messages || []
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const senderId = messages[i]?.sender_id
      if (senderId && !messages[i]?.out) {
        telegram.activeContactId = senderId
        telegram.contactMeta = getTelegramContactMeta(senderId)
        return
      }
    }
    telegram.activeContactId = null
    telegram.contactMeta = { name: '', username: '' }
  }

  async function loadTelegramContact() {
    if (!telegram.activeContactId) return
    try {
      const data = await apiGet(`/tg/contact?sender_id=${telegram.activeContactId}`, { token: auth.state.token })
      telegram.contact = {
        title: data?.title || '',
        info: data?.info || '',
      }
    } catch {
      telegram.contact = { title: '', info: '' }
    }
  }

  function setTelegramActiveContact(senderId) {
    if (!senderId || senderId === telegram.activeContactId) return
    telegram.activeContactId = senderId
    telegram.contactEditing = false
    telegram.contact = { title: '', info: '' }
    telegram.contactMeta = getTelegramContactMeta(senderId)
    loadTelegramContact()
  }

  function toggleTelegramContactEdit() {
    if (!telegram.activeContactId) return
    if (!telegram.contactEditing) {
      telegram.contactEdit = {
        title: telegram.contact.title || '',
        info: telegram.contact.info || '',
      }
    }
    telegram.contactEditing = !telegram.contactEditing
  }

  function cancelTelegramContactEdit() {
    telegram.contactEditing = false
  }

  async function saveTelegramContact() {
    if (!telegram.activeContactId) return
    telegram.loading = true
    telegram.error = ''
    try {
      await apiPut(
        '/tg/contact',
        {
          sender_id: telegram.activeContactId,
          title: telegram.contactEdit.title || '',
          info: telegram.contactEdit.info || '',
        },
        { token: auth.state.token }
      )
      telegram.contact = {
        title: telegram.contactEdit.title || '',
        info: telegram.contactEdit.info || '',
      }
      telegram.contactEditing = false
    } catch (e) {
      telegram.error = mapApiError(e?.message)
    } finally {
      telegram.loading = false
    }
  }

  function getTelegramContactMeta(senderId) {
    const messages = telegram.messages || []
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const msg = messages[i]
      if (msg?.sender_id === senderId) {
        return {
          name: msg?.sender_name || '',
          username: msg?.sender_username || '',
        }
      }
    }
    return { name: '', username: '' }
  }

  function showTelegramChannelLabel(index) {
    return showTelegramChannelLabelForList(telegram.messages, index)
  }

  function shouldTelegramPoll() {
    return activeTab.value === 'telegram' && telegram.status === 'ready' && auth.isAuthed()
  }

  function stopTelegramPolling() {
    if (telegramDialogsPollTimer) clearTimeout(telegramDialogsPollTimer)
    if (telegramMessagesPollTimer) clearTimeout(telegramMessagesPollTimer)
    telegramDialogsPollTimer = null
    telegramMessagesPollTimer = null
  }

  function scheduleTelegramDialogsPoll(delayMs = TELEGRAM_DIALOGS_POLL_MS) {
    if (!shouldTelegramPoll()) return
    if (telegramDialogsPollTimer) clearTimeout(telegramDialogsPollTimer)
    telegramDialogsPollTimer = setTimeout(async () => {
      if (!shouldTelegramPoll()) return
      if (telegramDialogsPollBusy) {
        scheduleTelegramDialogsPoll(TELEGRAM_DIALOGS_POLL_MS)
        return
      }
      telegramDialogsPollBusy = true
      try {
        await loadTelegramDialogsQuiet()
        scheduleTelegramDialogsPoll(TELEGRAM_DIALOGS_POLL_MS)
      } catch {
        scheduleTelegramDialogsPoll(TELEGRAM_DIALOGS_POLL_ERROR_MS)
      } finally {
        telegramDialogsPollBusy = false
      }
    }, delayMs)
  }

  function scheduleTelegramMessagesPoll(delayMs = TELEGRAM_MESSAGES_POLL_MS) {
    if (!shouldTelegramPoll()) return
    if (!telegram.activeChatId) return
    if (telegramMessagesPollTimer) clearTimeout(telegramMessagesPollTimer)
    telegramMessagesPollTimer = setTimeout(async () => {
      if (!shouldTelegramPoll() || !telegram.activeChatId) return
      if (telegramMessagesPollBusy) {
        scheduleTelegramMessagesPoll(TELEGRAM_MESSAGES_POLL_MS)
        return
      }
      telegramMessagesPollBusy = true
      try {
        await refreshActiveTelegramMessagesQuiet()
        scheduleTelegramMessagesPoll(TELEGRAM_MESSAGES_POLL_MS)
      } catch {
        scheduleTelegramMessagesPoll(TELEGRAM_MESSAGES_POLL_ERROR_MS)
      } finally {
        telegramMessagesPollBusy = false
      }
    }, delayMs)
  }

  function handleTelegramActiveChatChange() {
    if (!shouldTelegramPoll()) return
    if (!telegram.activeChatId) {
      if (telegramMessagesPollTimer) clearTimeout(telegramMessagesPollTimer)
      telegramMessagesPollTimer = null
      return
    }
    scheduleTelegramMessagesPoll(800)
  }

  function startTelegramPolling() {
    stopTelegramPolling()
    if (!shouldTelegramPoll()) return
    scheduleTelegramDialogsPoll(2000)
    if (telegram.activeChatId) scheduleTelegramMessagesPoll(1500)
  }

  async function sendTelegramMessage() {
    if (!telegram.activeChatId || !telegram.messageText) return
    telegram.loading = true
    telegram.error = ''
    try {
      await apiPost('/tg/messages', { chat_id: telegram.activeChatId, text: telegram.messageText }, { token: auth.state.token })
      telegram.messageText = ''
      if (telegram.activeDialog) {
        telegram.activeDialog.status = 'accepted'
      }
      await loadTelegramDialogs()
      if (telegram.activeChatId) {
        telegram.activeDialog = telegram.dialogs.find((d) => d.id === telegram.activeChatId) || telegram.activeDialog
      }
      await selectTelegramDialog(telegram.activeChatId)
      scheduleTelegramMessagesPoll(500)
    } catch (e) {
      telegram.error = mapApiError(e?.message)
    } finally {
      telegram.loading = false
    }
  }

  async function setTelegramDialogStatus(status) {
    if (!telegram.activeChatId) return
    if (!['new', 'accepted', 'archived'].includes(status)) return
    telegram.loading = true
    telegram.error = ''
    try {
      await apiPut(`/tg/dialogs/${telegram.activeChatId}/status`, { status }, { token: auth.state.token })
      await loadTelegramDialogs()
      if (telegram.activeChatId) {
        telegram.activeDialog = telegram.dialogs.find((d) => d.id === telegram.activeChatId) || telegram.activeDialog
      }
    } catch (e) {
      telegram.error = mapApiError(e?.message)
    } finally {
      telegram.loading = false
    }
  }

  return {
    loadTelegramStatus,
    tgAuthStart,
    tgAuthConfirm,
    tgAuthPassword,
    tgAuthDisconnect,
    setTelegramDialogFilter,
    selectTelegramDialog,
    onTelegramMessagesScroll,
    onTelegramMediaRendered,
    setTelegramActiveContact,
    toggleTelegramContactEdit,
    cancelTelegramContactEdit,
    saveTelegramContact,
    showTelegramChannelLabel,
    shouldTelegramPoll,
    stopTelegramPolling,
    startTelegramPolling,
    handleTelegramActiveChatChange,
    sendTelegramMessage,
    setTelegramDialogStatus,
    revokeTelegramMediaUrls,
  }
}
