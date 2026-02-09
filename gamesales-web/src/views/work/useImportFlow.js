export function useImportFlow({
  auth,
  API_BASE,
  apiGet,
  apiPost,
  apiPostForm,
  apiGetFile,
  mapApiError,
  GAME_IMPORT_JOB_KEY,
  ACCOUNT_IMPORT_JOB_KEY,
  SLOT_VALIDATE_JOB_KEY,
  SLOT_IMPORT_JOB_KEY,
  closeAllModals,
  resetModalPos,
  showGameImport,
  showAccountImport,
  showSlotImport,
  gameImportFile,
  accountImportFile,
  slotImportFile,
  slotImportLimit,
  gameImportValidated,
  accountImportValidated,
  slotImportValidated,
  gameImportErrors,
  accountImportErrors,
  slotImportErrors,
  gameImportWarnings,
  accountImportWarnings,
  slotImportWarnings,
  gameImportTotal,
  accountImportTotal,
  slotImportTotal,
  gameImportLoading,
  accountImportLoading,
  slotImportLoading,
  gameImportMessage,
  accountImportMessage,
  slotImportMessage,
  slotImportError,
  slotImportAction,
  slotImportProgress,
  slotImportJobId,
  slotImportStats,
  gameImportAction,
  accountImportAction,
  gameImportStats,
  accountImportStats,
  gameImportProgress,
  accountImportProgress,
  gameImportJobId,
  accountImportJobId,
  importDetailsRef,
  accountImportDetailsRef,
  loadGames,
  loadGamesAll,
  loadAccounts,
  loadAccountsAll,
}) {
  // Таймеры опроса фоновых задач импорта.
  let gameImportStatusTimer = null
  let accountImportStatusTimer = null
  let slotImportStatusTimer = null

  // Открывает окно импорта игр и сбрасывает прошлое состояние.
  function openGameImport() {
    closeAllModals()
    resetModalPos()
    showGameImport.value = true
    gameImportFile.value = null
    gameImportValidated.value = false
    gameImportErrors.value = []
    gameImportWarnings.value = []
    gameImportTotal.value = 0
    gameImportLoading.value = false
    gameImportMessage.value = ''
    gameImportAction.value = ''
    gameImportStats.value = null
    gameImportProgress.current = 0
    gameImportProgress.total = 0
    gameImportProgress.phase = ''
    gameImportJobId.value = ''
    stopGameImportStatusPolling()
    const stored = localStorage.getItem(GAME_IMPORT_JOB_KEY)
    if (stored) {
      gameImportJobId.value = stored
      gameImportAction.value = 'upload'
      gameImportLoading.value = true
      startGameImportStatusPolling()
    }
  }

  // Открывает окно импорта аккаунтов и сбрасывает прошлое состояние.
  function openAccountImport() {
    closeAllModals()
    resetModalPos()
    showAccountImport.value = true
    accountImportFile.value = null
    accountImportValidated.value = false
    accountImportErrors.value = []
    accountImportWarnings.value = []
    accountImportTotal.value = 0
    accountImportLoading.value = false
    accountImportMessage.value = ''
    accountImportAction.value = ''
    accountImportStats.value = null
    accountImportProgress.current = 0
    accountImportProgress.total = 0
    accountImportProgress.phase = ''
    accountImportJobId.value = ''
    stopAccountImportStatusPolling()
    const stored = localStorage.getItem(ACCOUNT_IMPORT_JOB_KEY)
    if (stored) {
      accountImportJobId.value = stored
      accountImportAction.value = 'upload'
      accountImportLoading.value = true
      startAccountImportStatusPolling()
    }
  }

  // Открывает окно импорта слотов и подхватывает незавершенную задачу.
  function openSlotImport() {
    closeAllModals()
    resetModalPos()
    showSlotImport.value = true
    slotImportFile.value = null
    slotImportMessage.value = ''
    slotImportError.value = ''
    slotImportValidated.value = false
    slotImportErrors.value = []
    slotImportWarnings.value = []
    slotImportTotal.value = 0
    slotImportLoading.value = false
    slotImportLimit.value = 10
    slotImportAction.value = ''
    slotImportProgress.current = 0
    slotImportProgress.total = 0
    slotImportProgress.phase = ''
    slotImportJobId.value = ''
    slotImportStats.value = null
    stopSlotImportStatusPolling()
    const storedImport = localStorage.getItem(SLOT_IMPORT_JOB_KEY)
    const storedValidate = localStorage.getItem(SLOT_VALIDATE_JOB_KEY)
    if (storedImport) {
      slotImportJobId.value = storedImport
      slotImportAction.value = 'upload'
      slotImportLoading.value = true
      startSlotImportStatusPolling()
    } else if (storedValidate) {
      slotImportJobId.value = storedValidate
      slotImportAction.value = 'validate'
      slotImportLoading.value = true
      startSlotImportStatusPolling()
    }
  }

  // Полностью очищает состояние импорта слотов и останавливает опрос.
  function closeSlotImport() {
    showSlotImport.value = false
    slotImportFile.value = null
    slotImportMessage.value = ''
    slotImportError.value = ''
    slotImportValidated.value = false
    slotImportErrors.value = []
    slotImportWarnings.value = []
    slotImportTotal.value = 0
    slotImportLoading.value = false
    slotImportLimit.value = 10
    slotImportAction.value = ''
    slotImportProgress.current = 0
    slotImportProgress.total = 0
    slotImportProgress.phase = ''
    slotImportJobId.value = ''
    slotImportStats.value = null
    stopSlotImportStatusPolling()
    localStorage.removeItem(SLOT_VALIDATE_JOB_KEY)
    localStorage.removeItem(SLOT_IMPORT_JOB_KEY)
  }

  // Закрывает импорт игр и очищает временные данные.
  function closeGameImport() {
    showGameImport.value = false
    gameImportFile.value = null
    gameImportValidated.value = false
    gameImportErrors.value = []
    gameImportWarnings.value = []
    gameImportTotal.value = 0
    gameImportLoading.value = false
    gameImportMessage.value = ''
    gameImportAction.value = ''
    gameImportStats.value = null
    gameImportProgress.current = 0
    gameImportProgress.total = 0
    gameImportProgress.phase = ''
    gameImportJobId.value = ''
    stopGameImportStatusPolling()
  }

  // Закрывает импорт аккаунтов и очищает временные данные.
  function closeAccountImport() {
    showAccountImport.value = false
    accountImportFile.value = null
    accountImportValidated.value = false
    accountImportErrors.value = []
    accountImportWarnings.value = []
    accountImportTotal.value = 0
    accountImportLoading.value = false
    accountImportMessage.value = ''
    accountImportAction.value = ''
    accountImportStats.value = null
    accountImportProgress.current = 0
    accountImportProgress.total = 0
    accountImportProgress.phase = ''
    accountImportJobId.value = ''
    stopAccountImportStatusPolling()
  }

  // Один шаг опроса статуса импорта игр.
  async function pollGameImportStatusOnce() {
    if (!gameImportJobId.value) return
    try {
      const status = await apiGet(`/games/import/status?job_id=${encodeURIComponent(gameImportJobId.value)}`, { token: auth.state.token })
      if (!status) return
      gameImportProgress.current = Number(status.current || 0)
      gameImportProgress.total = Number(status.total || 0)
      gameImportProgress.phase = status.phase || ''
      if (status.done && status.result) {
        applyGameImportResult(status.result)
        return
      }
      if (status.done) {
        gameImportMessage.value = 'Импорт завершен'
        gameImportLoading.value = false
        gameImportAction.value = ''
        gameImportJobId.value = ''
        localStorage.removeItem(GAME_IMPORT_JOB_KEY)
        stopGameImportStatusPolling()
      }
    } catch {
      // ignore polling errors
    }
  }

  async function pollAccountImportStatusOnce() {
    if (!accountImportJobId.value) return
    try {
      const status = await apiGet(`/accounts/import/status?job_id=${encodeURIComponent(accountImportJobId.value)}`, { token: auth.state.token })
      if (!status) return
      accountImportProgress.current = Number(status.current || 0)
      accountImportProgress.total = Number(status.total || 0)
      accountImportProgress.phase = status.phase || ''
      if (status.done && status.result) {
        applyAccountImportResult(status.result)
        return
      }
      if (status.done) {
        accountImportMessage.value = 'Импорт завершен'
        accountImportLoading.value = false
        accountImportAction.value = ''
        accountImportJobId.value = ''
        localStorage.removeItem(ACCOUNT_IMPORT_JOB_KEY)
        stopAccountImportStatusPolling()
      }
    } catch {
      // ignore polling errors
    }
  }

  function startGameImportStatusPolling() {
    stopGameImportStatusPolling()
    pollGameImportStatusOnce()
    gameImportStatusTimer = setInterval(async () => {
      try {
        if (!gameImportJobId.value) return
        const status = await apiGet(`/games/import/status?job_id=${encodeURIComponent(gameImportJobId.value)}`, { token: auth.state.token })
        if (!status) return
        gameImportProgress.current = Number(status.current || 0)
        gameImportProgress.total = Number(status.total || 0)
        gameImportProgress.phase = status.phase || ''
        if (status.done && status.result) {
          applyGameImportResult(status.result)
        }
        if (status.done && !status.result) {
          gameImportMessage.value = 'Импорт завершен'
          gameImportLoading.value = false
          gameImportAction.value = ''
          gameImportJobId.value = ''
          localStorage.removeItem(GAME_IMPORT_JOB_KEY)
          stopGameImportStatusPolling()
        }
        if (status.done && !gameImportLoading.value) stopGameImportStatusPolling()
      } catch {
        // ignore polling errors
      }
    }, 600)
  }

  function startAccountImportStatusPolling() {
    stopAccountImportStatusPolling()
    pollAccountImportStatusOnce()
    accountImportStatusTimer = setInterval(async () => {
      try {
        if (!accountImportJobId.value) return
        const status = await apiGet(`/accounts/import/status?job_id=${encodeURIComponent(accountImportJobId.value)}`, { token: auth.state.token })
        if (!status) return
        accountImportProgress.current = Number(status.current || 0)
        accountImportProgress.total = Number(status.total || 0)
        accountImportProgress.phase = status.phase || ''
        if (status.done && status.result) {
          applyAccountImportResult(status.result)
        }
        if (status.done && !status.result) {
          accountImportMessage.value = 'Импорт завершен'
          accountImportLoading.value = false
          accountImportAction.value = ''
          accountImportJobId.value = ''
          localStorage.removeItem(ACCOUNT_IMPORT_JOB_KEY)
          stopAccountImportStatusPolling()
        }
        if (status.done && !accountImportLoading.value) stopAccountImportStatusPolling()
      } catch {
        // ignore polling errors
      }
    }, 600)
  }

  async function pollSlotImportStatusOnce() {
    if (!slotImportJobId.value) return
    try {
      const endpoint = slotImportAction.value === 'upload'
        ? `/accounts/slots/import/status?job_id=${encodeURIComponent(slotImportJobId.value)}`
        : `/accounts/slots/validate/status?job_id=${encodeURIComponent(slotImportJobId.value)}`
      const status = await apiGet(endpoint, { token: auth.state.token })
      if (!status) return
      slotImportProgress.current = Number(status.current || 0)
      slotImportProgress.total = Number(status.total || 0)
      slotImportProgress.phase = status.phase || ''
      if (status.done && status.result) {
        applySlotImportResult(status.result, slotImportAction.value)
        return
      }
      if (status.done) {
        slotImportMessage.value = slotImportAction.value === 'upload' ? 'Загрузка завершена' : 'Проверка завершена'
        slotImportLoading.value = false
        slotImportAction.value = ''
        slotImportJobId.value = ''
        localStorage.removeItem(SLOT_VALIDATE_JOB_KEY)
        localStorage.removeItem(SLOT_IMPORT_JOB_KEY)
        stopSlotImportStatusPolling()
      }
    } catch {
      // ignore polling errors
    }
  }

  function startSlotImportStatusPolling() {
    stopSlotImportStatusPolling()
    pollSlotImportStatusOnce()
    slotImportStatusTimer = setInterval(async () => {
      try {
        if (!slotImportJobId.value) return
        const endpoint = slotImportAction.value === 'upload'
          ? `/accounts/slots/import/status?job_id=${encodeURIComponent(slotImportJobId.value)}`
          : `/accounts/slots/validate/status?job_id=${encodeURIComponent(slotImportJobId.value)}`
        const status = await apiGet(endpoint, { token: auth.state.token })
        if (!status) return
        slotImportProgress.current = Number(status.current || 0)
        slotImportProgress.total = Number(status.total || 0)
        slotImportProgress.phase = status.phase || ''
        if (status.done && status.result) {
          applySlotImportResult(status.result, slotImportAction.value)
        }
        if (status.done && !status.result) {
          slotImportMessage.value = slotImportAction.value === 'upload' ? 'Загрузка завершена' : 'Проверка завершена'
          slotImportLoading.value = false
          slotImportAction.value = ''
          slotImportJobId.value = ''
          localStorage.removeItem(SLOT_VALIDATE_JOB_KEY)
          localStorage.removeItem(SLOT_IMPORT_JOB_KEY)
          stopSlotImportStatusPolling()
        }
        if (status.done && !slotImportLoading.value) stopSlotImportStatusPolling()
      } catch {
        // ignore polling errors
      }
    }, 600)
  }

  function stopGameImportStatusPolling() {
    if (!gameImportStatusTimer) return
    clearInterval(gameImportStatusTimer)
    gameImportStatusTimer = null
  }

  function stopAccountImportStatusPolling() {
    if (!accountImportStatusTimer) return
    clearInterval(accountImportStatusTimer)
    accountImportStatusTimer = null
  }

  function stopSlotImportStatusPolling() {
    if (!slotImportStatusTimer) return
    clearInterval(slotImportStatusTimer)
    slotImportStatusTimer = null
  }

  function scrollToImportDetails() {
    if (!importDetailsRef.value) return
    importDetailsRef.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  function scrollToAccountImportDetails() {
    if (!accountImportDetailsRef.value) return
    accountImportDetailsRef.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  async function applyGameImportResult(res) {
    if (!res) return
    if (res?.cancelled) {
      gameImportMessage.value = 'Импорт отменен'
      gameImportErrors.value = []
      gameImportWarnings.value = []
      gameImportStats.value = null
      gameImportLoading.value = false
      gameImportAction.value = ''
      gameImportJobId.value = ''
      localStorage.removeItem(GAME_IMPORT_JOB_KEY)
      stopGameImportStatusPolling()
      return
    }
    const created = res?.created || 0
    const updated = res?.updated || 0
    const skipped = res?.skipped || 0
    const failed = res?.failed || 0
    gameImportErrors.value = res?.errors || []
    gameImportWarnings.value = res?.warnings || []
    if (res?.ok) {
      gameImportMessage.value = `Загружено. Создано: ${created}, обновлено: ${updated}, пропущено: ${skipped}`
    } else {
      const until = res?.success_until_row ? `до строки ${res.success_until_row}` : 'до строки —'
      gameImportMessage.value = `Загрузка с ошибками, успешно ${until}. Ошибок: ${failed}`
    }
    gameImportStats.value = { created, updated, skipped, failed, total: res?.total || 0 }
    gameImportLoading.value = false
    gameImportAction.value = ''
    gameImportJobId.value = ''
    localStorage.removeItem(GAME_IMPORT_JOB_KEY)
    stopGameImportStatusPolling()
    await loadGames()
    await loadGamesAll()
  }

  async function applyAccountImportResult(res) {
    if (!res) return
    if (res?.cancelled) {
      accountImportMessage.value = 'Импорт отменен'
      accountImportErrors.value = []
      accountImportWarnings.value = []
      accountImportStats.value = null
      accountImportLoading.value = false
      accountImportAction.value = ''
      accountImportJobId.value = ''
      localStorage.removeItem(ACCOUNT_IMPORT_JOB_KEY)
      stopAccountImportStatusPolling()
      return
    }
    const created = res?.created || 0
    const updated = res?.updated || 0
    const skipped = res?.skipped || 0
    const failed = res?.failed || 0
    accountImportErrors.value = res?.errors || []
    accountImportWarnings.value = res?.warnings || []
    if (res?.ok) {
      accountImportMessage.value = `Загружено. Создано: ${created}, обновлено: ${updated}, пропущено: ${skipped}`
    } else {
      accountImportMessage.value = `Загрузка с ошибками. Ошибок: ${failed}`
    }
    accountImportStats.value = { created, updated, skipped, failed, total: res?.total || 0 }
    accountImportLoading.value = false
    accountImportAction.value = ''
    accountImportJobId.value = ''
    localStorage.removeItem(ACCOUNT_IMPORT_JOB_KEY)
    stopAccountImportStatusPolling()
    await loadAccounts()
    await loadAccountsAll()
  }

  async function applySlotImportResult(res, action) {
    if (!res) return
    if (res?.cancelled) {
      slotImportMessage.value = action === 'upload' ? 'Загрузка отменена' : 'Проверка отменена'
      slotImportErrors.value = []
      slotImportWarnings.value = []
      slotImportValidated.value = false
      slotImportLoading.value = false
      slotImportAction.value = ''
      slotImportJobId.value = ''
      localStorage.removeItem(SLOT_VALIDATE_JOB_KEY)
      localStorage.removeItem(SLOT_IMPORT_JOB_KEY)
      stopSlotImportStatusPolling()
      return
    }
    slotImportErrors.value = res?.errors || []
    slotImportWarnings.value = res?.warnings || []
    slotImportTotal.value = Number(res?.total || 0)
    slotImportValidated.value = Boolean(res?.ok)
    if (action === 'upload') {
      const created = res?.created || 0
      const released = res?.released || 0
      const skipped = res?.skipped || 0
      const failed = res?.failed || 0
      slotImportStats.value = { created, released, skipped, failed, total: res?.total || 0 }
      if (res?.ok) {
        slotImportMessage.value = `Загружено. Создано: ${created}, снято: ${released}, пропущено: ${skipped}`
      } else {
        slotImportMessage.value = `Загрузка с ошибками. Ошибок: ${failed}`
      }
    } else if (res?.ok) {
      slotImportMessage.value = slotImportWarnings.value.length
        ? `Проверка завершена. Некоторые строки будут пропущены: ${slotImportWarnings.value.length}.`
        : `Проверка завершена. Строк к загрузке: ${slotImportTotal.value}.`
    } else {
      slotImportMessage.value = 'Файл не корректен. Исправьте ошибки ниже.'
    }
    slotImportLoading.value = false
    slotImportAction.value = ''
    slotImportJobId.value = ''
    localStorage.removeItem(SLOT_VALIDATE_JOB_KEY)
    localStorage.removeItem(SLOT_IMPORT_JOB_KEY)
    stopSlotImportStatusPolling()
  }

  function onGameImportFile(event) {
    const file = event?.target?.files?.[0]
    gameImportFile.value = file || null
    gameImportValidated.value = false
    gameImportErrors.value = []
    gameImportWarnings.value = []
    gameImportTotal.value = 0
    gameImportMessage.value = ''
    gameImportAction.value = ''
    gameImportStats.value = null
    gameImportProgress.current = 0
    gameImportProgress.total = 0
    gameImportProgress.phase = ''
    gameImportJobId.value = ''
    stopGameImportStatusPolling()
  }

  function onAccountImportFile(event) {
    const file = event?.target?.files?.[0]
    accountImportFile.value = file || null
    accountImportValidated.value = false
    accountImportErrors.value = []
    accountImportWarnings.value = []
    accountImportTotal.value = 0
    accountImportMessage.value = ''
    accountImportAction.value = ''
    accountImportStats.value = null
    accountImportProgress.current = 0
    accountImportProgress.total = 0
    accountImportProgress.phase = ''
    accountImportJobId.value = ''
    stopAccountImportStatusPolling()
  }

  function onSlotImportFile(event) {
    const file = event?.target?.files?.[0]
    slotImportFile.value = file || null
    slotImportMessage.value = ''
    slotImportError.value = ''
    slotImportValidated.value = false
    slotImportErrors.value = []
    slotImportWarnings.value = []
    slotImportTotal.value = 0
    slotImportLimit.value = slotImportLimit.value || 10
    slotImportAction.value = ''
    slotImportProgress.current = 0
    slotImportProgress.total = 0
    slotImportProgress.phase = ''
    slotImportJobId.value = ''
    slotImportStats.value = null
    stopSlotImportStatusPolling()
    localStorage.removeItem(SLOT_VALIDATE_JOB_KEY)
    localStorage.removeItem(SLOT_IMPORT_JOB_KEY)
  }

  async function downloadGameTemplate() {
    try {
      const blob = await apiGetFile('/games/import/template', { token: auth.state.token })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'games_import_template.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      gameImportMessage.value = mapApiError(e?.message)
    }
  }

  async function downloadAccountTemplate() {
    try {
      const blob = await apiGetFile('/accounts/import/template', { token: auth.state.token })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'accounts_import_template.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      accountImportMessage.value = mapApiError(e?.message)
    }
  }

  async function downloadGameImportReport() {
    try {
      const payload = { errors: gameImportErrors.value || [], warnings: gameImportWarnings.value || [] }
      const res = await fetch(`${API_BASE}/games/import/report`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${auth.state.token}`,
        },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        throw new Error(`report failed: ${res.status}`)
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'games_import_report.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      gameImportMessage.value = mapApiError(e?.message)
    }
  }

  async function validateGameImport() {
    if (!gameImportFile.value) return
    const form = new FormData()
    form.append('file', gameImportFile.value)
    gameImportValidated.value = false
    gameImportAction.value = 'validate'
    gameImportLoading.value = true
    gameImportProgress.current = 0
    gameImportProgress.total = gameImportTotal.value || 0
    gameImportProgress.phase = ''
    try {
      const res = await apiPostForm('/games/import/validate', form, { token: auth.state.token })
      gameImportErrors.value = res?.errors || []
      gameImportWarnings.value = res?.warnings || []
      gameImportTotal.value = res?.total || 0
      gameImportValidated.value = Boolean(res?.ok)
      if (res?.ok) {
        gameImportMessage.value = gameImportWarnings.value.length
          ? `Файл корректный. Некоторые строки будут пропущены: ${gameImportWarnings.value.length}.`
          : `Файл корректный. Строк: ${gameImportTotal.value}. Можно загружать.`
      } else {
        gameImportMessage.value = 'Файл не корректен. Исправьте ошибки ниже.'
      }
    } catch (e) {
      gameImportValidated.value = false
      gameImportErrors.value = []
      gameImportWarnings.value = []
      gameImportMessage.value = mapApiError(e?.message)
    } finally {
      gameImportLoading.value = false
      gameImportAction.value = ''
      stopGameImportStatusPolling()
    }
  }

  async function downloadAccountImportReport() {
    try {
      const payload = { errors: accountImportErrors.value || [], warnings: accountImportWarnings.value || [] }
      const res = await fetch(`${API_BASE}/accounts/import/report`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${auth.state.token}`,
        },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        throw new Error(`report failed: ${res.status}`)
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'accounts_import_report.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      accountImportMessage.value = mapApiError(e?.message)
    }
  }

  async function validateAccountImport() {
    if (!accountImportFile.value) return
    const form = new FormData()
    form.append('file', accountImportFile.value)
    accountImportValidated.value = false
    accountImportAction.value = 'validate'
    accountImportLoading.value = true
    accountImportProgress.current = 0
    accountImportProgress.total = accountImportTotal.value || 0
    accountImportProgress.phase = ''
    try {
      const res = await apiPostForm('/accounts/import/validate', form, { token: auth.state.token })
      accountImportErrors.value = res?.errors || []
      accountImportWarnings.value = res?.warnings || []
      accountImportTotal.value = res?.total || 0
      accountImportValidated.value = Boolean(res?.ok)
      if (res?.ok) {
        accountImportMessage.value = accountImportWarnings.value.length
          ? `Файл корректный. Некоторые строки будут пропущены: ${accountImportWarnings.value.length}.`
          : `Файл корректный. Строк: ${accountImportTotal.value}. Можно загружать.`
      } else {
        accountImportMessage.value = 'Файл не корректен. Исправьте ошибки ниже.'
      }
    } catch (e) {
      accountImportValidated.value = false
      accountImportErrors.value = []
      accountImportWarnings.value = []
      accountImportMessage.value = mapApiError(e?.message)
    } finally {
      accountImportLoading.value = false
      accountImportAction.value = ''
      stopAccountImportStatusPolling()
    }
  }

  async function cleanSlotImport() {
    if (!slotImportFile.value) return
    slotImportLoading.value = true
    slotImportMessage.value = ''
    slotImportError.value = ''
    try {
      const form = new FormData()
      form.append('file', slotImportFile.value)
      const res = await fetch(`${API_BASE}/accounts/slots/clean`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${auth.state.token}`,
        },
        body: form,
      })
      if (!res.ok) {
        let msg = ''
        try {
          const data = await res.json()
          msg = data?.detail || JSON.stringify(data)
        } catch {
          msg = await res.text()
        }
        throw new Error(msg || `Ошибка: ${res.status}`)
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      const base = slotImportFile.value?.name ? slotImportFile.value.name.replace(/\.(xlsx|xls)$/i, '') : 'slots_import'
      a.href = url
      a.download = `${base}_cleaned.xlsx`
      a.click()
      URL.revokeObjectURL(url)
      slotImportMessage.value = 'Файл сформирован.'
    } catch (e) {
      slotImportError.value = mapApiError(e?.message)
    } finally {
      slotImportLoading.value = false
    }
  }

  async function validateSlotImport() {
    if (!slotImportFile.value) return
    slotImportLoading.value = true
    slotImportMessage.value = ''
    slotImportError.value = ''
    slotImportValidated.value = false
    slotImportErrors.value = []
    slotImportWarnings.value = []
    slotImportTotal.value = 0
    slotImportAction.value = 'validate'
    slotImportProgress.current = 0
    slotImportProgress.total = slotImportTotal.value || 0
    slotImportProgress.phase = ''
    try {
      const form = new FormData()
      form.append('file', slotImportFile.value)
      if (slotImportLimit.value) form.append('limit', String(slotImportLimit.value))
      const res = await apiPostForm('/accounts/slots/validate', form, { token: auth.state.token })
      if (res?.job_id) {
        slotImportJobId.value = res.job_id
        localStorage.setItem(SLOT_VALIDATE_JOB_KEY, res.job_id)
        startSlotImportStatusPolling()
      } else {
        slotImportMessage.value = 'Не удалось запустить проверку'
        slotImportLoading.value = false
        slotImportAction.value = ''
      }
    } catch (e) {
      slotImportValidated.value = false
      slotImportErrors.value = []
      slotImportWarnings.value = []
      slotImportTotal.value = 0
      slotImportError.value = mapApiError(e?.message)
      slotImportLoading.value = false
      slotImportAction.value = ''
    }
  }

  async function uploadSlotImport() {
    if (!slotImportFile.value || !slotImportValidated.value) return
    slotImportAction.value = 'upload'
    slotImportLoading.value = true
    slotImportProgress.current = 0
    slotImportProgress.total = slotImportTotal.value || 0
    slotImportProgress.phase = ''
    slotImportStats.value = null
    try {
      const form = new FormData()
      form.append('file', slotImportFile.value)
      const res = await apiPostForm('/accounts/slots/import', form, { token: auth.state.token })
      if (res?.job_id) {
        slotImportJobId.value = res.job_id
        localStorage.setItem(SLOT_IMPORT_JOB_KEY, res.job_id)
        startSlotImportStatusPolling()
      } else {
        slotImportMessage.value = 'Не удалось запустить загрузку'
        slotImportLoading.value = false
        slotImportAction.value = ''
      }
    } catch (e) {
      slotImportError.value = mapApiError(e?.message)
      slotImportLoading.value = false
      slotImportAction.value = ''
    }
  }

  async function downloadSlotImportReport() {
    try {
      const payload = { errors: slotImportErrors.value || [], warnings: slotImportWarnings.value || [] }
      const res = await fetch(`${API_BASE}/accounts/slots/report`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${auth.state.token}`,
        },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        throw new Error(`report failed: ${res.status}`)
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'slots_import_report.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      slotImportError.value = mapApiError(e?.message)
    }
  }

  async function cancelSlotImport() {
    if (!slotImportJobId.value) return
    const action = slotImportAction.value
    slotImportAction.value = 'cancel'
    slotImportLoading.value = true
    try {
      const endpoint = action === 'upload'
        ? `/accounts/slots/import/cancel?job_id=${encodeURIComponent(slotImportJobId.value)}`
        : `/accounts/slots/validate/cancel?job_id=${encodeURIComponent(slotImportJobId.value)}`
      await apiPost(endpoint, {}, { token: auth.state.token })
      startSlotImportStatusPolling()
    } catch (e) {
      slotImportError.value = mapApiError(e?.message)
      slotImportLoading.value = false
      slotImportAction.value = ''
    }
  }

  async function uploadGameImport() {
    if (!gameImportFile.value || !gameImportValidated.value) return
    const form = new FormData()
    form.append('file', gameImportFile.value)
    gameImportAction.value = 'upload'
    gameImportLoading.value = true
    gameImportProgress.current = 0
    gameImportProgress.total = gameImportTotal.value || 0
    gameImportProgress.phase = ''
    try {
      const res = await apiPostForm('/games/import', form, { token: auth.state.token })
      if (res?.job_id) {
        gameImportJobId.value = res.job_id
        localStorage.setItem(GAME_IMPORT_JOB_KEY, res.job_id)
        startGameImportStatusPolling()
      } else {
        gameImportMessage.value = 'Не удалось запустить импорт'
        gameImportLoading.value = false
        gameImportAction.value = ''
      }
    } catch (e) {
      gameImportMessage.value = mapApiError(e?.message)
      gameImportLoading.value = false
      gameImportAction.value = ''
    }
  }

  async function uploadAccountImport() {
    if (!accountImportFile.value || !accountImportValidated.value) return
    const form = new FormData()
    form.append('file', accountImportFile.value)
    accountImportAction.value = 'upload'
    accountImportLoading.value = true
    accountImportProgress.current = 0
    accountImportProgress.total = accountImportTotal.value || 0
    accountImportProgress.phase = ''
    try {
      const res = await apiPostForm('/accounts/import', form, { token: auth.state.token })
      if (res?.job_id) {
        accountImportJobId.value = res.job_id
        localStorage.setItem(ACCOUNT_IMPORT_JOB_KEY, res.job_id)
        startAccountImportStatusPolling()
      } else {
        accountImportMessage.value = 'Не удалось запустить импорт'
        accountImportLoading.value = false
        accountImportAction.value = ''
      }
    } catch (e) {
      accountImportMessage.value = mapApiError(e?.message)
      accountImportLoading.value = false
      accountImportAction.value = ''
    }
  }

  async function cancelGameImport() {
    if (!gameImportJobId.value) return
    gameImportAction.value = 'cancel'
    gameImportLoading.value = true
    try {
      await apiPost(`/games/import/cancel?job_id=${encodeURIComponent(gameImportJobId.value)}`, {}, { token: auth.state.token })
      startGameImportStatusPolling()
    } catch (e) {
      gameImportMessage.value = mapApiError(e?.message)
      gameImportLoading.value = false
      gameImportAction.value = ''
    }
  }

  async function cancelAccountImport() {
    if (!accountImportJobId.value) return
    accountImportAction.value = 'cancel'
    accountImportLoading.value = true
    try {
      await apiPost(`/accounts/import/cancel?job_id=${encodeURIComponent(accountImportJobId.value)}`, {}, { token: auth.state.token })
      startAccountImportStatusPolling()
    } catch (e) {
      accountImportMessage.value = mapApiError(e?.message)
      accountImportLoading.value = false
      accountImportAction.value = ''
    }
  }

  function downloadGamesExport() {
    gameImportMessage.value = 'Выгрузка будет добавлена позже'
    showGameImport.value = true
  }

  return {
    openGameImport,
    openAccountImport,
    openSlotImport,
    closeSlotImport,
    closeGameImport,
    closeAccountImport,
    stopGameImportStatusPolling,
    stopAccountImportStatusPolling,
    stopSlotImportStatusPolling,
    scrollToImportDetails,
    scrollToAccountImportDetails,
    onGameImportFile,
    onAccountImportFile,
    onSlotImportFile,
    downloadGameTemplate,
    downloadAccountTemplate,
    downloadGameImportReport,
    validateGameImport,
    downloadAccountImportReport,
    validateAccountImport,
    cleanSlotImport,
    validateSlotImport,
    uploadSlotImport,
    downloadSlotImportReport,
    cancelSlotImport,
    uploadGameImport,
    uploadAccountImport,
    cancelGameImport,
    cancelAccountImport,
    downloadGamesExport,
  }
}
