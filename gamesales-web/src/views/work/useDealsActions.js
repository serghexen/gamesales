export function useDealsActions({
  auth,
  apiPost,
  apiPut,
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

  // Создает новую сделку после простых проверок формы.
  async function createDeal() {
    dealError.value = null
    dealOk.value = null
    if (!newDeal.customer_nickname) {
      dealError.value = 'Укажите покупателя'
      return
    }
    if (newDeal.deal_type_code === 'rental') {
      if (!newDeal.account_id || !newDeal.game_id) {
        dealError.value = 'Для шеринга укажите аккаунт и игру'
        return
      }
      if (!newDeal.slot_type_code) {
        dealError.value = 'Для шеринга выберите тип слота'
        return
      }
    }
    if (newDeal.deal_type_code === 'sale' && !newDeal.region_code) {
      dealError.value = 'Укажите регион'
      return
    }
    // Для продажи держим единый набор обязательных полей, чтобы форма не сохранялась с неполными данными.
    if (newDeal.deal_type_code === 'sale') {
      if (!newDeal.source_id) {
        dealError.value = 'Укажите источник'
        return
      }
      if (!(Number(newDeal.price) > 0)) {
        dealError.value = 'Укажите сумму'
        return
      }
    }
    dealLoading.value = true
    dealSaving.value = true
    let createdOk = false
    try {
      await apiPost(
        '/deals',
        {
          deal_type_code: newDeal.deal_type_code,
          account_id: newDeal.deal_type_code === 'rental' ? newDeal.account_id : null,
          game_id: newDeal.deal_type_code === 'rental' ? newDeal.game_id : null,
          customer_nickname: newDeal.customer_nickname,
          order_number: newDeal.order_number || null,
          responsible_username: normalizeResponsible(newDealResponsible?.value),
          source_id: newDeal.source_id || null,
          region_code: newDeal.region_code || null,
          slot_type_code: newDeal.deal_type_code === 'rental' ? (newDeal.slot_type_code || null) : null,
          price: newDeal.price || 0,
          purchase_cost: newDeal.purchase_cost || 0,
          login: newDeal.login || null,
          password: newDeal.password || null,
          game_link: newDeal.game_link || null,
          purchase_at: newDeal.deal_type_code === 'sale' ? null : toUtcDateTime(newDeal.purchase_at),
          slots_used: newDeal.deal_type_code === 'rental' ? 1 : 0,
          notes: newDeal.notes || null,
        },
        { token: auth.state.token }
      )
      createdOk = true
      dealOk.value = 'Сделка сохранена'
      newDeal.customer_nickname = ''
      newDeal.price = 0
      newDeal.purchase_cost = 0
      newDeal.login = ''
      newDeal.password = ''
      newDeal.game_link = ''
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

  // Обновляет существующую сделку.
  async function updateDeal() {
    dealError.value = null
    dealOk.value = null
    if (!editDeal.deal_id) return
    if (!editDeal.customer_nickname) {
      dealError.value = 'Укажите покупателя'
      return
    }
    if (editDeal.deal_type_code === 'rental') {
      if (!editDeal.account_id || !editDeal.game_id) {
        dealError.value = 'Для шеринга укажите аккаунт и игру'
        return
      }
      if (!editDeal.slot_type_code) {
        dealError.value = 'Для шеринга выберите тип слота'
        return
      }
    }
    if (editDeal.deal_type_code === 'sale' && !editDeal.region_code) {
      dealError.value = 'Укажите регион'
      return
    }
    // Повторяем обязательные поля продажи и в режиме редактирования, чтобы правила были одинаковыми.
    if (editDeal.deal_type_code === 'sale') {
      if (!editDeal.source_id) {
        dealError.value = 'Укажите источник'
        return
      }
      if (!(Number(editDeal.price) > 0)) {
        dealError.value = 'Укажите сумму'
        return
      }
    }
    // Для возврата проверяем право проведения заранее, чтобы не ждать ответ сервера.
    const triesCompleteRefund = editDeal.deal_type_code === 'sale'
      && Boolean(editDeal.is_refund)
      && editDeal.flow_status_code === 'completed'
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
        {
          deal_type_code: editDeal.deal_type_code,
          account_id: editDeal.deal_type_code === 'rental' ? editDeal.account_id : null,
          game_id: editDeal.deal_type_code === 'rental' ? editDeal.game_id : null,
          customer_nickname: editDeal.customer_nickname,
          order_number: editDeal.order_number || null,
          responsible_username: normalizeResponsible(editDealResponsible?.value),
          source_id: editDeal.source_id || null,
          region_code: editDeal.region_code || null,
          slot_type_code: editDeal.deal_type_code === 'rental' ? (editDeal.slot_type_code || null) : null,
          price: editDeal.price,
          purchase_cost: editDeal.purchase_cost || 0,
          login: editDeal.login || null,
          password: editDeal.password || null,
          game_link: editDeal.game_link || null,
          purchase_at: editDeal.deal_type_code === 'sale' ? null : toUtcDateTime(editDeal.purchase_at),
          slots_used: editDeal.deal_type_code === 'rental' ? 1 : 0,
          notes: editDeal.notes || null,
          flow_status_code: editDeal.flow_status_code || null,
          // Признак возврата отправляем только для продаж, для остальных типов не трогаем поле.
          is_refund: editDeal.deal_type_code === 'sale' ? Boolean(editDeal.is_refund) : null,
        },
        { token: auth.state.token }
      )
      updatedOk = true
      dealOk.value = 'Сделка обновлена'
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

  return {
    createDeal,
    updateDeal,
    markDealCompleted,
  }
}
