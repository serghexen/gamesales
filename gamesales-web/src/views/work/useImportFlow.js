import { confirmDiscardIfNeeded } from './unsavedChanges'

// Проверяет, что загруженный файл подходит для excel-импорта.
const isSupportedExcelFile = (file) => {
  const fileName = String(file?.name || '').toLowerCase().trim()
  return Boolean(fileName.endsWith('.xlsx') || fileName.endsWith('.xls'))
}

export function useImportFlow({
  auth,
  API_BASE,
  apiGet,
  apiPost,
  apiPostForm,
  apiGetFile,
  mapApiError,
  PRODUCT_IMPORT_JOB_KEY,
  LEGACY_PRODUCT_IMPORT_JOB_FALLBACK_KEY,
  ACCOUNT_IMPORT_JOB_KEY,
  SLOT_VALIDATE_JOB_KEY,
  SLOT_IMPORT_JOB_KEY,
  closeAllModals,
  resetModalPos,
  showProductImport,
  showAccountImport,
  showSlotImport,
  productImportFile,
  accountImportFile,
  slotImportFile,
  slotImportLimit,
  productImportValidated,
  accountImportValidated,
  slotImportValidated,
  productImportErrors,
  accountImportErrors,
  slotImportErrors,
  productImportWarnings,
  accountImportWarnings,
  slotImportWarnings,
  productImportTotal,
  accountImportTotal,
  slotImportTotal,
  productImportLoading,
  accountImportLoading,
  slotImportLoading,
  productImportMessage,
  accountImportMessage,
  slotImportMessage,
  slotImportError,
  slotImportAction,
  slotImportProgress,
  slotImportJobId,
  slotImportStats,
  productImportAction,
  accountImportAction,
  productImportStats,
  accountImportStats,
  productImportProgress,
  accountImportProgress,
  productImportJobId,
  accountImportJobId,
  importDetailsRef,
  accountImportDetailsRef,
  loadProducts,
  loadProductsAll,
  loadAccounts,
  loadAccountsAll,
  accounts,
  ensureAccountSecretsLoaded,
  suppressUnsavedConfirm,
  requestUnsavedConfirm,
}) {
  // Таймеры опроса фоновых задач импорта.
  let productImportStatusTimer = null
  let accountImportStatusTimer = null
  let slotImportStatusTimer = null

  // Читает job_id из нового ключа и при необходимости из legacy-ключа.
  const getStoredJobId = (primaryKey, fallbackKey = '') => {
    const primary = localStorage.getItem(primaryKey)
    if (primary) return primary
    if (!fallbackKey) return ''
    return localStorage.getItem(fallbackKey) || ''
  }

  // Удаляет job_id сразу из нового и legacy-ключа.
  const clearStoredJobId = (primaryKey, fallbackKey = '') => {
    localStorage.removeItem(primaryKey)
    if (fallbackKey) localStorage.removeItem(fallbackKey)
  }

  // После массового импорта перечитывает секреты видимых аккаунтов, чтобы резервы не оставались старыми в таблице.
  async function refreshVisibleAccountSecrets() {
    if (typeof ensureAccountSecretsLoaded !== 'function') return
    const list = Array.isArray(accounts?.value) ? accounts.value : []
    const ids = [...new Set(list.map((item) => Number(item?.account_id || 0)).filter((id) => id > 0))]
    if (!ids.length) return
    await Promise.allSettled(ids.map((id) => ensureAccountSecretsLoaded(id, true)))
  }

  // Открывает окно импорта товаров и сбрасывает прошлое состояние.
  function openProductImport() {
    closeAllModals()
    resetModalPos()
    showProductImport.value = true
    productImportFile.value = null
    productImportValidated.value = false
    productImportErrors.value = []
    productImportWarnings.value = []
    productImportTotal.value = 0
    productImportLoading.value = false
    productImportMessage.value = ''
    productImportAction.value = ''
    productImportStats.value = null
    productImportProgress.current = 0
    productImportProgress.total = 0
    productImportProgress.phase = ''
    productImportJobId.value = ''
    stopProductImportStatusPolling()
    const stored = getStoredJobId(PRODUCT_IMPORT_JOB_KEY, LEGACY_PRODUCT_IMPORT_JOB_FALLBACK_KEY)
    if (stored) {
      productImportJobId.value = stored
      productImportAction.value = 'upload'
      productImportLoading.value = true
      startProductImportStatusPolling()
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
  async function closeSlotImport() {
    const guardEnabled = !suppressUnsavedConfirm?.value
    const isDirty = Boolean(slotImportFile.value || slotImportValidated.value || slotImportErrors.value.length || slotImportWarnings.value.length || slotImportJobId.value || slotImportMessage.value || slotImportError.value)
    if (guardEnabled && !(await confirmDiscardIfNeeded(isDirty, { requestConfirm: requestUnsavedConfirm }))) return false

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
    return true
  }

  // Закрывает импорт товаров и очищает временные данные.
  async function closeProductImport() {
    const guardEnabled = !suppressUnsavedConfirm?.value
    const isDirty = Boolean(productImportFile.value || productImportValidated.value || productImportErrors.value.length || productImportWarnings.value.length || productImportJobId.value || productImportMessage.value)
    if (guardEnabled && !(await confirmDiscardIfNeeded(isDirty, { requestConfirm: requestUnsavedConfirm }))) return false

    showProductImport.value = false
    productImportFile.value = null
    productImportValidated.value = false
    productImportErrors.value = []
    productImportWarnings.value = []
    productImportTotal.value = 0
    productImportLoading.value = false
    productImportMessage.value = ''
    productImportAction.value = ''
    productImportStats.value = null
    productImportProgress.current = 0
    productImportProgress.total = 0
    productImportProgress.phase = ''
    productImportJobId.value = ''
    stopProductImportStatusPolling()
    return true
  }

  // Закрывает импорт аккаунтов и очищает временные данные.
  async function closeAccountImport() {
    const guardEnabled = !suppressUnsavedConfirm?.value
    const isDirty = Boolean(accountImportFile.value || accountImportValidated.value || accountImportErrors.value.length || accountImportWarnings.value.length || accountImportJobId.value || accountImportMessage.value)
    if (guardEnabled && !(await confirmDiscardIfNeeded(isDirty, { requestConfirm: requestUnsavedConfirm }))) return false

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
    return true
  }

  // Один шаг опроса статуса импорта товаров.
  async function pollProductImportStatusOnce() {
    if (!productImportJobId.value) return
    try {
      const status = await apiGet(`/products/import/status?job_id=${encodeURIComponent(productImportJobId.value)}`, { token: auth.state.token })
      if (!status) return
      productImportProgress.current = Number(status.current || 0)
      productImportProgress.total = Number(status.total || 0)
      productImportProgress.phase = status.phase || ''
      if (status.done && status.result) {
        applyProductImportResult(status.result)
        return
      }
      if (status.done) {
        productImportMessage.value = 'Импорт завершен'
        productImportLoading.value = false
        productImportAction.value = ''
        productImportJobId.value = ''
        clearStoredJobId(PRODUCT_IMPORT_JOB_KEY, LEGACY_PRODUCT_IMPORT_JOB_FALLBACK_KEY)
        stopProductImportStatusPolling()
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

  function startProductImportStatusPolling() {
    stopProductImportStatusPolling()
    pollProductImportStatusOnce()
    productImportStatusTimer = setInterval(async () => {
      try {
        if (!productImportJobId.value) return
        const status = await apiGet(`/products/import/status?job_id=${encodeURIComponent(productImportJobId.value)}`, { token: auth.state.token })
        if (!status) return
        productImportProgress.current = Number(status.current || 0)
        productImportProgress.total = Number(status.total || 0)
        productImportProgress.phase = status.phase || ''
        if (status.done && status.result) {
          applyProductImportResult(status.result)
        }
        if (status.done && !status.result) {
          productImportMessage.value = 'Импорт завершен'
          productImportLoading.value = false
          productImportAction.value = ''
          productImportJobId.value = ''
          clearStoredJobId(PRODUCT_IMPORT_JOB_KEY, LEGACY_PRODUCT_IMPORT_JOB_FALLBACK_KEY)
          stopProductImportStatusPolling()
        }
        if (status.done && !productImportLoading.value) stopProductImportStatusPolling()
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

  function stopProductImportStatusPolling() {
    if (!productImportStatusTimer) return
    clearInterval(productImportStatusTimer)
    productImportStatusTimer = null
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

  async function applyProductImportResult(res) {
    if (!res) return
    if (res?.cancelled) {
      productImportMessage.value = 'Импорт отменен'
      productImportErrors.value = []
      productImportWarnings.value = []
      productImportStats.value = null
      productImportLoading.value = false
      productImportAction.value = ''
      productImportJobId.value = ''
      clearStoredJobId(PRODUCT_IMPORT_JOB_KEY, LEGACY_PRODUCT_IMPORT_JOB_FALLBACK_KEY)
      stopProductImportStatusPolling()
      return
    }
    const created = res?.created || 0
    const updated = res?.updated || 0
    const skipped = res?.skipped || 0
    const failed = res?.failed || 0
    productImportErrors.value = res?.errors || []
    productImportWarnings.value = res?.warnings || []
    if (res?.ok) {
      productImportMessage.value = `Загружено. Создано: ${created}, обновлено: ${updated}, пропущено: ${skipped}`
    } else {
      const until = res?.success_until_row ? `до строки ${res.success_until_row}` : 'до строки —'
      productImportMessage.value = `Загрузка с ошибками, успешно ${until}. Ошибок: ${failed}`
    }
    productImportStats.value = { created, updated, skipped, failed, total: res?.total || 0 }
    productImportLoading.value = false
    productImportAction.value = ''
    productImportJobId.value = ''
    clearStoredJobId(PRODUCT_IMPORT_JOB_KEY, LEGACY_PRODUCT_IMPORT_JOB_FALLBACK_KEY)
    stopProductImportStatusPolling()
    await loadProducts()
    await loadProductsAll()
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
    // Сохраняем детализацию из бэка, чтобы в модалке было видно, что именно изменилось.
    accountImportStats.value = {
      created,
      updated,
      skipped,
      failed,
      total: res?.total || 0,
      details: res?.details || null,
    }
    accountImportLoading.value = false
    accountImportAction.value = ''
    accountImportJobId.value = ''
    localStorage.removeItem(ACCOUNT_IMPORT_JOB_KEY)
    stopAccountImportStatusPolling()
    await loadAccounts()
    await loadAccountsAll()
    await refreshVisibleAccountSecrets()
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

  function onProductImportFileInternal(event) {
    const file = event?.target?.files?.[0]
    productImportFile.value = file || null
    productImportValidated.value = false
    productImportErrors.value = []
    productImportWarnings.value = []
    productImportTotal.value = 0
    productImportMessage.value = ''
    productImportAction.value = ''
    productImportStats.value = null
    productImportProgress.current = 0
    productImportProgress.total = 0
    productImportProgress.phase = ''
    productImportJobId.value = ''
    stopProductImportStatusPolling()
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
    // Сразу подсказываем нужный формат и не запускаем серверные проверки с неподходящим файлом.
    if (accountImportFile.value && !isSupportedExcelFile(accountImportFile.value)) {
      accountImportMessage.value = 'Поддерживаются только файлы .xlsx/.xls'
    }
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

  async function downloadProductTemplateInternal() {
    try {
      const blob = await apiGetFile('/products/import/template', { token: auth.state.token })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'products_import_template.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      productImportMessage.value = mapApiError(e?.message)
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

  // Скачивает полный экспорт БД в структуре импортного файла.
  async function downloadAccountImportExport() {
    try {
      const blob = await apiGetFile('/accounts/import/export', { token: auth.state.token })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'gamesales_import_export.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      accountImportMessage.value = mapApiError(e?.message)
    }
  }

  async function downloadProductImportReportInternal() {
    try {
      const payload = { errors: productImportErrors.value || [], warnings: productImportWarnings.value || [] }
      const res = await fetch(`${API_BASE}/products/import/report`, {
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
      a.download = 'products_import_report.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      productImportMessage.value = mapApiError(e?.message)
    }
  }

  async function validateProductImport() {
    if (!productImportFile.value) return
    const form = new FormData()
    form.append('file', productImportFile.value)
    productImportValidated.value = false
    productImportAction.value = 'validate'
    productImportLoading.value = true
    productImportProgress.current = 0
    productImportProgress.total = productImportTotal.value || 0
    productImportProgress.phase = ''
    try {
      const res = await apiPostForm('/products/import/validate', form, { token: auth.state.token })
      productImportErrors.value = res?.errors || []
      productImportWarnings.value = res?.warnings || []
      productImportTotal.value = res?.total || 0
      productImportValidated.value = Boolean(res?.ok)
      if (res?.ok) {
        productImportMessage.value = productImportWarnings.value.length
          ? `Файл корректный. Некоторые строки будут пропущены: ${productImportWarnings.value.length}.`
          : `Файл корректный. Строк: ${productImportTotal.value}. Можно загружать.`
      } else {
        productImportMessage.value = 'Файл не корректен. Исправьте ошибки ниже.'
      }
    } catch (e) {
      productImportValidated.value = false
      productImportErrors.value = []
      productImportWarnings.value = []
      productImportMessage.value = mapApiError(e?.message)
    } finally {
      productImportLoading.value = false
      productImportAction.value = ''
      stopProductImportStatusPolling()
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
    if (!isSupportedExcelFile(accountImportFile.value)) {
      accountImportMessage.value = 'Поддерживаются только файлы .xlsx/.xls'
      return
    }
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

  // Отдельная проверка листа "Пользователи": ищет неполный набор слотов по аккаунтам.
  async function validateAccountSlotsCheck() {
    if (!accountImportFile.value) return
    if (!isSupportedExcelFile(accountImportFile.value)) {
      accountImportMessage.value = 'Поддерживаются только файлы .xlsx/.xls'
      return
    }
    const form = new FormData()
    form.append('file', accountImportFile.value)
    accountImportAction.value = 'validate'
    accountImportLoading.value = true
    accountImportProgress.current = 0
    accountImportProgress.total = accountImportTotal.value || 0
    accountImportProgress.phase = ''
    try {
      const res = await apiPostForm('/accounts/import/slots-check', form, { token: auth.state.token })
      accountImportErrors.value = res?.errors || []
      accountImportWarnings.value = res?.warnings || []
      const totalRows = Number(res?.total || 0)
      if (res?.ok) {
        accountImportMessage.value = totalRows
          ? `Проверка слотов пройдена. Проверено строк: ${totalRows}.`
          : 'Проверка слотов пройдена. Отклонений не найдено.'
      } else {
        accountImportMessage.value = `Проверка слотов завершена. Найдено отклонений: ${accountImportErrors.value.length + accountImportWarnings.value.length}.`
      }
    } catch (e) {
      accountImportErrors.value = []
      accountImportWarnings.value = []
      accountImportMessage.value = mapApiError(e?.message)
    } finally {
      accountImportLoading.value = false
      accountImportAction.value = ''
      stopAccountImportStatusPolling()
    }
  }

  // Отдельная проверка внешнего файла: ищет сделки по связке дата + ник покупателя.
  async function validateAccountDealsCheck() {
    if (!accountImportFile.value) return
    if (!isSupportedExcelFile(accountImportFile.value)) {
      accountImportMessage.value = 'Поддерживаются только файлы .xlsx/.xls'
      return
    }
    const form = new FormData()
    form.append('file', accountImportFile.value)
    accountImportAction.value = 'validate'
    accountImportLoading.value = true
    accountImportProgress.current = 0
    accountImportProgress.total = accountImportTotal.value || 0
    accountImportProgress.phase = ''
    try {
      const res = await apiPostForm('/accounts/import/deals-check', form, { token: auth.state.token })
      accountImportErrors.value = res?.errors || []
      accountImportWarnings.value = res?.warnings || []
      const totalRows = Number(res?.total || 0)
      if (res?.ok) {
        accountImportMessage.value = totalRows
          ? `Проверка сделок пройдена. Проверено строк: ${totalRows}.`
          : 'Проверка сделок пройдена. Отклонений не найдено.'
      } else {
        accountImportMessage.value = `Проверка сделок завершена. Найдено отклонений: ${accountImportErrors.value.length + accountImportWarnings.value.length}.`
      }
    } catch (e) {
      accountImportErrors.value = []
      accountImportWarnings.value = []
      accountImportMessage.value = mapApiError(e?.message)
    } finally {
      accountImportLoading.value = false
      accountImportAction.value = ''
      stopAccountImportStatusPolling()
    }
  }

  // Отдельная заливка: ставит номер заявки в найденные сделки из текущего файла.
  async function fillAccountDealsOrderNumbers() {
    if (!accountImportFile.value) return
    if (!isSupportedExcelFile(accountImportFile.value)) {
      accountImportMessage.value = 'Поддерживаются только файлы .xlsx/.xls'
      return
    }
    const form = new FormData()
    form.append('file', accountImportFile.value)
    accountImportAction.value = 'upload'
    accountImportLoading.value = true
    accountImportProgress.current = 0
    accountImportProgress.total = accountImportTotal.value || 0
    accountImportProgress.phase = ''
    try {
      const res = await apiPostForm('/accounts/import/deals-fill', form, { token: auth.state.token })
      accountImportErrors.value = res?.errors || []
      accountImportWarnings.value = res?.warnings || []
      const updated = Number(res?.updated || 0)
      const skipped = Number(res?.skipped || 0)
      const totalRows = Number(res?.total || 0)
      accountImportMessage.value = totalRows
        ? `Заливка заявок завершена. Обновлено сделок: ${updated}, пропущено строк: ${skipped}.`
        : 'Заливка заявок завершена. Подходящих строк не найдено.'
    } catch (e) {
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

  async function uploadProductImport() {
    if (!productImportFile.value || !productImportValidated.value) return
    const form = new FormData()
    form.append('file', productImportFile.value)
    productImportAction.value = 'upload'
    productImportLoading.value = true
    productImportProgress.current = 0
    productImportProgress.total = productImportTotal.value || 0
    productImportProgress.phase = ''
    try {
      const res = await apiPostForm('/products/import', form, { token: auth.state.token })
      if (res?.job_id) {
        productImportJobId.value = res.job_id
        clearStoredJobId(PRODUCT_IMPORT_JOB_KEY, LEGACY_PRODUCT_IMPORT_JOB_FALLBACK_KEY)
        localStorage.setItem(PRODUCT_IMPORT_JOB_KEY, res.job_id)
        startProductImportStatusPolling()
      } else {
        productImportMessage.value = 'Не удалось запустить импорт'
        productImportLoading.value = false
        productImportAction.value = ''
      }
    } catch (e) {
      productImportMessage.value = mapApiError(e?.message)
      productImportLoading.value = false
      productImportAction.value = ''
    }
  }

  async function uploadAccountImport() {
    if (!accountImportFile.value || !accountImportValidated.value) return
    if (!isSupportedExcelFile(accountImportFile.value)) {
      accountImportMessage.value = 'Поддерживаются только файлы .xlsx/.xls'
      return
    }
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

  async function cancelProductImport() {
    if (!productImportJobId.value) return
    productImportAction.value = 'cancel'
    productImportLoading.value = true
    try {
      await apiPost(`/products/import/cancel?job_id=${encodeURIComponent(productImportJobId.value)}`, {}, { token: auth.state.token })
      startProductImportStatusPolling()
    } catch (e) {
      productImportMessage.value = mapApiError(e?.message)
      productImportLoading.value = false
      productImportAction.value = ''
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

  function downloadProductsExport() {
    productImportMessage.value = 'Выгрузка будет добавлена позже'
    showProductImport.value = true
  }

  const onProductImportFile = onProductImportFileInternal
  const downloadProductTemplate = downloadProductTemplateInternal
  const downloadProductImportReport = downloadProductImportReportInternal
  // Совместимость для старого контракта lifecycle-хука.
  const stopGameImportStatusPolling = stopProductImportStatusPolling

  return {
    openProductImport,
    openAccountImport,
    openSlotImport,
    closeProductImport,
    closeAccountImport,
    closeSlotImport,
    stopProductImportStatusPolling,
    stopGameImportStatusPolling,
    stopAccountImportStatusPolling,
    stopSlotImportStatusPolling,
    scrollToImportDetails,
    scrollToAccountImportDetails,
    onProductImportFile,
    onAccountImportFile,
    onSlotImportFile,
    downloadProductTemplate,
    downloadAccountTemplate,
    downloadAccountImportExport,
    downloadProductImportReport,
    downloadAccountImportReport,
    validateProductImport,
    validateAccountImport,
    validateAccountSlotsCheck,
    validateAccountDealsCheck,
    fillAccountDealsOrderNumbers,
    validateSlotImport,
    uploadProductImport,
    uploadAccountImport,
    uploadSlotImport,
    cancelProductImport,
    cancelAccountImport,
    cancelSlotImport,
    downloadProductsExport,
    cleanSlotImport,
    downloadSlotImportReport,
  }
}
