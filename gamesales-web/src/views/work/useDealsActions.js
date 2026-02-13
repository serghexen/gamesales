export function useDealsActions({
  auth,
  apiPost,
  apiPut,
  apiDelete,
  mapApiError,
  toUtcDateTime,
  newDeal,
  editDeal,
  newDealResponsible,
  editDealResponsible,
  dealPage,
  dealError,
  dealOk,
  dealLoading,
  dealSaving,
  dealCompletingId,
  dealBackgroundSync,
  loadDeals,
  loadAccountsAll,
  closeDealModal,
  suppressUnsavedConfirm,
  showDealWarning,
  requestDealConfirm,
}) {
  // Проверяет, может ли текущий пользователь проводить возврат (admin/owner).
  function canCompleteRefund() {
    const role = String(auth?.state?.role || '').trim().toLowerCase()
    return role === 'admin' || role === 'owner'
  }

  // Приводит поле ответственного к значению, которое понимает API.
  function normalizeResponsible(value) {
    if (value === 'current_user') return auth.state.user || null
    const normalized = String(value || '').trim()
    return normalized || null
  }

  // Определяет, нужно ли ослаблять проверки и сохранять сделку как черновик.
  function isSaleDraftSave(dealTypeCode, saveAsDraft) {
    return Boolean(saveAsDraft) && dealTypeCode === 'sale'
  }

  // Нормализует дату/время из формы в ISO, чтобы API всегда получал единый формат.
  function normalizeOptionalDateTime(value) {
    const raw = String(value || '').trim()
    if (!raw) return null
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return `${raw}T00:00:00Z`
    const parsed = new Date(raw)
    if (Number.isNaN(parsed.getTime())) return null
    return parsed.toISOString()
  }

  // Собирает payload для create/update в едином формате, чтобы не дублировать маппинг полей.
  function buildDealPayload(deal, responsible, saveAsDraft = false) {
    const dealTypeCode = deal.deal_type_code
    const saleDraft = isSaleDraftSave(dealTypeCode, saveAsDraft)
    const payload = {
      deal_type_code: dealTypeCode,
      account_id: dealTypeCode === 'rental' ? deal.account_id : null,
      // В сделках используем единый идентификатор товара через product_id.
      product_id: deal.product_id || null,
      customer_nickname: deal.customer_nickname || null,
      order_number: deal.order_number || null,
      responsible_username: normalizeResponsible(responsible?.value),
      source_id: deal.source_id || null,
      region_code: deal.region_code || null,
      slot_type_code: dealTypeCode === 'rental' ? (deal.slot_type_code || null) : null,
      price: deal.price || 0,
      purchase_cost: deal.purchase_cost || 0,
      login: deal.login || null,
      password: deal.password || null,
      product_link: deal.product_link || null,
      purchase_at: dealTypeCode === 'sale' ? null : toUtcDateTime(deal.purchase_at),
      slots_used: dealTypeCode === 'rental' ? 1 : 0,
      notes: deal.notes || null,
      flow_status_code: saleDraft ? 'draft' : (deal.flow_status_code || null),
      // Признак возврата отправляем только для продаж, для остальных типов не трогаем поле.
      is_refund: dealTypeCode === 'sale' ? Boolean(deal.is_refund) : null,
    }
    // Системные даты передаем только при редактировании существующей сделки.
    if (deal?.deal_id) {
      payload.created_at = normalizeOptionalDateTime(deal.created_at)
      payload.completed_at = normalizeOptionalDateTime(deal.completed_at)
    }
    return payload
  }

  // Проверяет обязательные поля. Для черновика продажи допускаем пустые поля.
  function validateDealBeforeSave(deal, { saveAsDraft = false } = {}) {
    const saleDraft = isSaleDraftSave(deal.deal_type_code, saveAsDraft)
    if (!saleDraft && !deal.customer_nickname) return 'Укажите покупателя'
    if (deal.deal_type_code === 'rental') {
      if (!deal.account_id || !deal.product_id) return 'Для шеринга укажите аккаунт и товар'
      if (!deal.slot_type_code) return 'Для шеринга выберите тип слота'
    }
    if (deal.deal_type_code === 'sale' && !saleDraft) {
      if (!deal.region_code) return 'Укажите регион'
      if (!deal.source_id) return 'Укажите источник'
    }
    return null
  }

  // Создает новую сделку после простых проверок формы.
  async function createDealInternal({ saveAsDraft = false } = {}) {
    dealError.value = null
    dealOk.value = null
    const validationError = validateDealBeforeSave(newDeal, { saveAsDraft })
    if (validationError) {
      dealError.value = validationError
      return
    }
    dealLoading.value = true
    dealSaving.value = true
    let createdOk = false
    try {
      await apiPost(
        '/deals',
        buildDealPayload(newDeal, newDealResponsible, saveAsDraft),
        { token: auth.state.token }
      )
      createdOk = true
      dealOk.value = saveAsDraft ? 'Черновик сохранен' : 'Сделка сохранена'
      newDeal.customer_nickname = ''
      newDeal.price = 0
      newDeal.purchase_cost = 0
      newDeal.login = ''
      newDeal.password = ''
      newDeal.product_link = ''
      newDeal.purchase_at = ''
      newDeal.notes = ''
    } catch (e) {
      dealError.value = mapApiError(e?.message)
    } finally {
      // Если сохранение не удалось, сразу снимаем лоадер здесь.
      if (!createdOk) {
        dealLoading.value = false
        dealSaving.value = false
      }
    }

    if (createdOk) {
      // Закрываем модалку программно без лишнего предупреждения о несохраненных изменениях.
      if (suppressUnsavedConfirm) suppressUnsavedConfirm.value = true
      try {
        closeDealModal()
      } finally {
        if (suppressUnsavedConfirm) suppressUnsavedConfirm.value = false
      }
      dealLoading.value = false
      dealSaving.value = false
      // Обновляем списки в фоне, чтобы подвисший запрос не держал модалку в лоадере.
      dealBackgroundSync.value = true
      try {
        await Promise.allSettled([loadDeals(1), loadAccountsAll()])
      } finally {
        dealBackgroundSync.value = false
      }
    }
  }

  async function createDeal() {
    await createDealInternal({ saveAsDraft: false })
  }

  async function createDealDraft() {
    await createDealInternal({ saveAsDraft: true })
  }

  // Обновляет существующую сделку.
  async function updateDealInternal({ saveAsDraft = false } = {}) {
    dealError.value = null
    dealOk.value = null
    if (!editDeal.deal_id) return
    const validationError = validateDealBeforeSave(editDeal, { saveAsDraft })
    if (validationError) {
      dealError.value = validationError
      return
    }
    const nextFlowStatus = isSaleDraftSave(editDeal.deal_type_code, saveAsDraft)
      ? 'draft'
      : (editDeal.flow_status_code || null)
    // Для возврата проверяем право проведения заранее, чтобы не ждать ответ сервера.
    const triesCompleteRefund = editDeal.deal_type_code === 'sale'
      && Boolean(editDeal.is_refund)
      && nextFlowStatus === 'completed'
      && !editDeal.completed_at
    if (triesCompleteRefund && !canCompleteRefund()) {
      const warningText = 'не достаточно прав для проведения возврата'
      // Показываем явное предупреждение, чтобы в таблице было понятно, почему действие не выполнено.
      if (typeof showDealWarning === 'function') showDealWarning(warningText)
      return
    }
    dealLoading.value = true
    dealSaving.value = true
    let updatedOk = false
    try {
      await apiPut(
        `/deals/${editDeal.deal_id}`,
        buildDealPayload(editDeal, editDealResponsible, saveAsDraft),
        { token: auth.state.token }
      )
      updatedOk = true
      dealOk.value = saveAsDraft ? 'Черновик обновлен' : 'Сделка обновлена'
    } catch (e) {
      dealError.value = mapApiError(e?.message)
    } finally {
      // Если обновление не удалось, снимаем блокировку сразу.
      if (!updatedOk) {
        dealLoading.value = false
        dealSaving.value = false
      }
    }

    if (updatedOk) {
      // После сохранения закрываем форму как "безопасное" действие, без confirm-диалога.
      if (suppressUnsavedConfirm) suppressUnsavedConfirm.value = true
      try {
        closeDealModal()
      } finally {
        if (suppressUnsavedConfirm) suppressUnsavedConfirm.value = false
      }
      dealLoading.value = false
      dealSaving.value = false
      dealBackgroundSync.value = true
      try {
        await Promise.allSettled([loadDeals(dealPage.value), loadAccountsAll()])
      } finally {
        dealBackgroundSync.value = false
      }
    }
  }

  async function updateDeal() {
    await updateDealInternal({ saveAsDraft: false })
  }

  async function updateDealDraft() {
    await updateDealInternal({ saveAsDraft: true })
  }

  // Мягко удаляет сделку: переводит ее в cancelled, не трогая историю в БД.
  async function deleteDeal() {
    dealError.value = null
    dealOk.value = null
    if (!editDeal.deal_id) return
    // Дополнительно проверяем на клиенте, чтобы не отправлять лишний запрос.
    if (editDeal.flow_status_code !== 'draft') {
      dealError.value = 'Удалить можно только черновик'
      return
    }
    const isConfirmed = typeof requestDealConfirm === 'function'
      ? await requestDealConfirm({
        title: 'Предупреждение',
        message: 'Удалить черновик?',
        confirmText: 'Удалить',
        cancelText: 'Отмена',
      })
      : window.confirm('Удалить черновик?')
    if (!isConfirmed) return

    dealLoading.value = true
    dealSaving.value = true
    let deletedOk = false
    try {
      await apiDelete(`/deals/${editDeal.deal_id}`, { token: auth.state.token })
      deletedOk = true
      dealOk.value = 'Черновик удален'
    } catch (e) {
      dealError.value = mapApiError(e?.message)
    } finally {
      if (!deletedOk) {
        dealLoading.value = false
        dealSaving.value = false
      }
    }

    if (deletedOk) {
      if (suppressUnsavedConfirm) suppressUnsavedConfirm.value = true
      try {
        closeDealModal()
      } finally {
        if (suppressUnsavedConfirm) suppressUnsavedConfirm.value = false
      }
      dealLoading.value = false
      dealSaving.value = false
      dealBackgroundSync.value = true
      try {
        await Promise.allSettled([loadDeals(dealPage.value), loadAccountsAll()])
      } finally {
        dealBackgroundSync.value = false
      }
    }
  }

  // Быстро переводит сделку в статус "completed".
  async function markDealCompleted(deal) {
    if (!deal?.deal_id) return
    dealError.value = null
    dealOk.value = null
    // Не даем обычным ролям проводить возврат, чтобы сразу показать понятную ошибку в UI.
    if (deal.is_refund && !canCompleteRefund()) {
      const warningText = 'не достаточно прав для проведения возврата'
      // Для быстрого завершения тоже показываем модальное предупреждение в стиле интерфейса.
      if (typeof showDealWarning === 'function') showDealWarning(warningText)
      return
    }
    // Сохраняем id строки, чтобы сразу показать лоадер на нужной кнопке в таблице.
    if (dealCompletingId) dealCompletingId.value = deal.deal_id
    dealSaving.value = true
    try {
      await apiPut(
        `/deals/${deal.deal_id}`,
        { flow_status_code: 'completed' },
        { token: auth.state.token }
      )
      await loadDeals(dealPage.value)
    } catch (e) {
      dealError.value = mapApiError(e?.message)
    } finally {
      dealSaving.value = false
      if (dealCompletingId) dealCompletingId.value = null
    }
  }

  // Возвращает завершенную продажу в "pending", включает признак возврата и передает владельцу.
  async function markDealReturned(deal) {
    if (!deal?.deal_id) return
    dealError.value = null
    dealOk.value = null
    // Дублируем клиентскую проверку, чтобы не отправлять лишний запрос.
    if (deal.deal_type_code !== 'sale' || deal.is_refund) return
    if (dealCompletingId) dealCompletingId.value = deal.deal_id
    dealSaving.value = true
    try {
      await apiPost(
        `/deals/${deal.deal_id}/return`,
        {},
        { token: auth.state.token }
      )
      await loadDeals(dealPage.value)
    } catch (e) {
      dealError.value = mapApiError(e?.message)
    } finally {
      dealSaving.value = false
      if (dealCompletingId) dealCompletingId.value = null
    }
  }

  return {
    createDeal,
    createDealDraft,
    updateDeal,
    updateDealDraft,
    deleteDeal,
    markDealCompleted,
    markDealReturned,
  }
}
