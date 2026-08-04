import { computed, reactive, ref } from 'vue'

export function useMarketplaceKeyPool({ auth, apiGet, apiPost, apiDelete, mapApiError, requestDealConfirm }) {
  const showMarketplaceKeyPool = ref(false)
  const marketplaceKeyPoolLoading = ref(false)
  const marketplaceKeyPoolSaving = ref(false)
  const marketplaceKeyPoolError = ref('')
  const marketplaceKeyPoolOk = ref('')
  const marketplaceKeyPoolPage = ref(1)
  const marketplaceKeyPoolRevealingId = ref(0)
  const marketplaceKeyPoolRevealedCodes = reactive({})
  const marketplaceKeyPool = reactive({
    marketplace: '',
    product_key: '',
    product_title: '',
    store_code: '',
    free_count: 0,
    reserved_count: 0,
    delivered_count: 0,
    expired_count: 0,
    total: 0,
    page: 1,
    page_size: 20,
    items: [],
  })

  const marketplaceKeyPoolTotalPages = computed(() => Math.max(1, Math.ceil(Number(marketplaceKeyPool.total || 0) / Number(marketplaceKeyPool.page_size || 20))))

  function keyPoolError(error, fallback) {
    // Не заменяет ошибку пула текстом про Excel: этот экран не работает с файлами.
    const message = String(error?.message || '').trim()
    if (!message || message.includes('Load failed')) return 'API пула ключей пока недоступен. Примените миграцию и перезапустите API.'
    return mapApiError(message) || fallback
  }

  function poolPath() {
    // Собирает адрес строго для выбранной карточки, чтобы добавление не попадало в соседний пул.
    const marketplace = encodeURIComponent(String(marketplaceKeyPool.marketplace || '').trim())
    const productKey = encodeURIComponent(String(marketplaceKeyPool.product_key || '').trim())
    return `/marketplaces/key-pools/${marketplace}/${productKey}`
  }

  function applyMarketplaceKeyPool(value) {
    // Переносит ответ сервера в единое состояние для Ozon и Яндекс Маркета.
    const source = value && typeof value === 'object' ? value : {}
    Object.assign(marketplaceKeyPool, {
      free_count: Math.max(0, Number(source.free_count || 0)),
      reserved_count: Math.max(0, Number(source.reserved_count || 0)),
      delivered_count: Math.max(0, Number(source.delivered_count || 0)),
      expired_count: Math.max(0, Number(source.expired_count || 0)),
      total: Math.max(0, Number(source.total || 0)),
      page: Math.max(1, Number(source.page || marketplaceKeyPoolPage.value || 1)),
      page_size: Math.max(1, Number(source.page_size || 20)),
      items: Array.isArray(source.items) ? source.items : [],
    })
    marketplaceKeyPoolPage.value = marketplaceKeyPool.page
  }

  function marketplaceKeyPoolRevealedCode(key) {
    // Возвращает полный ключ только после явного запроса владельца для этой строки.
    return marketplaceKeyPoolRevealedCodes[Number(key?.id || 0)] || ''
  }

  async function loadMarketplaceKeyPool(page = marketplaceKeyPoolPage.value) {
    // Читает только маски ключей и статусы: исходные коды не возвращаются в браузер.
    if (!marketplaceKeyPool.marketplace || !marketplaceKeyPool.product_key || !marketplaceKeyPool.store_code || marketplaceKeyPoolLoading.value) {
      if (!marketplaceKeyPool.store_code) marketplaceKeyPoolError.value = 'Не определен кабинет для ручного пула ключей'
      return
    }
    marketplaceKeyPoolLoading.value = true
    marketplaceKeyPoolError.value = ''
    try {
      const query = new URLSearchParams({
        store_code: marketplaceKeyPool.store_code,
        page: String(Math.max(1, Number(page || 1))),
        page_size: '20',
      })
      const result = await apiGet(`${poolPath()}?${query.toString()}`, { token: auth.state.token })
      applyMarketplaceKeyPool(result)
    } catch (error) {
      marketplaceKeyPoolError.value = keyPoolError(error, 'Не удалось загрузить ручной пул ключей')
    } finally {
      marketplaceKeyPoolLoading.value = false
    }
  }

  function setMarketplaceKeyPoolContext({ marketplace, productKey, productTitle = '', storeCode = '' } = {}) {
    // Требует кабинет вместе с карточкой, чтобы отсутствие параметра не записывало ключи в ASAT по умолчанию.
    marketplaceKeyPool.marketplace = String(marketplace || '').trim()
    marketplaceKeyPool.product_key = String(productKey || '').trim()
    marketplaceKeyPool.product_title = String(productTitle || '').trim()
    marketplaceKeyPool.store_code = String(storeCode || '').trim().toLowerCase()
    marketplaceKeyPoolPage.value = 1
    marketplaceKeyPoolError.value = ''
    marketplaceKeyPoolOk.value = ''
    Object.keys(marketplaceKeyPoolRevealedCodes).forEach((id) => delete marketplaceKeyPoolRevealedCodes[id])
  }

  async function loadMarketplaceKeyPoolFor(context = {}) {
    // Загружает пул в основной экран настроек, не открывая окно добавления ключей.
    setMarketplaceKeyPoolContext(context)
    await loadMarketplaceKeyPool(1)
  }

  async function openMarketplaceKeyPool(context = {}) {
    // Открывает компактное окно добавления поверх уже загруженного пула выбранной карточки.
    setMarketplaceKeyPoolContext(context)
    showMarketplaceKeyPool.value = true
    await loadMarketplaceKeyPool(1)
  }

  function closeMarketplaceKeyPool() {
    // Закрывает только верхний экран пула и возвращает оператора к настройкам ключей карточки.
    showMarketplaceKeyPool.value = false
    Object.keys(marketplaceKeyPoolRevealedCodes).forEach((id) => delete marketplaceKeyPoolRevealedCodes[id])
  }

  async function revealMarketplaceKeyPoolKey(key) {
    // Раскрывает один сохраненный ключ для проверки, не зависит от его статуса и не меняет историю выдачи.
    const keyId = Number(key?.id || 0)
    if (!keyId || marketplaceKeyPoolRevealingId.value || marketplaceKeyPoolSaving.value) return
    marketplaceKeyPoolRevealingId.value = keyId
    marketplaceKeyPoolError.value = ''
    try {
      const result = await apiPost(`${poolPath()}/keys/${encodeURIComponent(keyId)}/reveal?store_code=${encodeURIComponent(marketplaceKeyPool.store_code)}`, {}, { token: auth.state.token })
      const code = String(result?.code || '').trim()
      if (!code) throw new Error('Ключ не удалось расшифровать')
      marketplaceKeyPoolRevealedCodes[keyId] = code
    } catch (error) {
      marketplaceKeyPoolError.value = keyPoolError(error, 'Не удалось показать ключ')
    } finally {
      marketplaceKeyPoolRevealingId.value = 0
    }
  }

  async function addMarketplaceKeyPoolKeys(rawCodes, expiresAt = '') {
    // Разбивает вставленную пачку по строкам и отправляет ее только в локальное зашифрованное хранилище.
    if (marketplaceKeyPoolSaving.value) return { ok: false, message: '' }
    const codes = String(rawCodes || '').split(/\r?\n/).map((code) => code.trim()).filter(Boolean)
    if (!codes.length) return { ok: false, message: 'Вставьте хотя бы один ключ' }
    marketplaceKeyPoolSaving.value = true
    marketplaceKeyPoolError.value = ''
    marketplaceKeyPoolOk.value = ''
    try {
      const payload = { codes }
      if (expiresAt) payload.expires_at = expiresAt
      const result = await apiPost(`${poolPath()}/keys?store_code=${encodeURIComponent(marketplaceKeyPool.store_code)}`, payload, { token: auth.state.token })
      const added = Number(result?.added || 0)
      const duplicates = Number(result?.duplicates || 0)
      marketplaceKeyPoolOk.value = duplicates ? `Добавлено ключей: ${added}. Повторы пропущены: ${duplicates}.` : `Добавлено ключей: ${added}`
      await loadMarketplaceKeyPool(1)
      return { ok: true, message: '' }
    } catch (error) {
      const message = keyPoolError(error, 'Не удалось добавить ключи в пул')
      marketplaceKeyPoolError.value = message
      return { ok: false, message }
    } finally {
      marketplaceKeyPoolSaving.value = false
    }
  }

  async function deleteMarketplaceKeyPoolKey(key) {
    // Удаляет только свободный ключ после явного подтверждения, не затрагивая историю выдачи.
    const keyId = Number(key?.id || 0)
    if (!keyId || marketplaceKeyPoolSaving.value) return
    const accepted = typeof requestDealConfirm === 'function' && await requestDealConfirm({
      title: 'Удалить свободный ключ?',
      message: `Ключ ${String(key?.masked_code || '').trim() || 'из пула'} будет удален без возможности восстановления.`,
      confirmText: 'Удалить',
      cancelText: 'Отмена',
    })
    if (!accepted) return
    marketplaceKeyPoolSaving.value = true
    marketplaceKeyPoolError.value = ''
    try {
      await apiDelete(`${poolPath()}/keys/${encodeURIComponent(keyId)}?store_code=${encodeURIComponent(marketplaceKeyPool.store_code)}`, { token: auth.state.token })
      marketplaceKeyPoolOk.value = 'Свободный ключ удалён'
      await loadMarketplaceKeyPool(marketplaceKeyPoolPage.value)
    } catch (error) {
      marketplaceKeyPoolError.value = keyPoolError(error, 'Не удалось удалить ключ')
    } finally {
      marketplaceKeyPoolSaving.value = false
    }
  }

  async function deleteAllFreeMarketplaceKeyPoolKeys() {
    // Очищает остаток пула только после отдельного подтверждения и не удаляет выданные ключи.
    if (!marketplaceKeyPool.free_count || marketplaceKeyPoolSaving.value) return
    const accepted = typeof requestDealConfirm === 'function' && await requestDealConfirm({
      title: 'Удалить все свободные ключи?',
      message: `Будет удалено свободных ключей: ${marketplaceKeyPool.free_count}. Выданные и зарезервированные ключи останутся в истории.`,
      confirmText: 'Удалить',
      cancelText: 'Отмена',
    })
    if (!accepted) return
    marketplaceKeyPoolSaving.value = true
    marketplaceKeyPoolError.value = ''
    try {
      await apiDelete(`${poolPath()}/keys?store_code=${encodeURIComponent(marketplaceKeyPool.store_code)}`, { token: auth.state.token })
      marketplaceKeyPoolOk.value = 'Свободные ключи удалены'
      await loadMarketplaceKeyPool(1)
    } catch (error) {
      marketplaceKeyPoolError.value = keyPoolError(error, 'Не удалось очистить свободные ключи')
    } finally {
      marketplaceKeyPoolSaving.value = false
    }
  }

  return {
    showMarketplaceKeyPool,
    marketplaceKeyPool,
    marketplaceKeyPoolLoading,
    marketplaceKeyPoolSaving,
    marketplaceKeyPoolError,
    marketplaceKeyPoolOk,
    marketplaceKeyPoolPage,
    marketplaceKeyPoolRevealingId,
    marketplaceKeyPoolRevealedCode,
    marketplaceKeyPoolTotalPages,
    loadMarketplaceKeyPoolFor,
    openMarketplaceKeyPool,
    closeMarketplaceKeyPool,
    loadMarketplaceKeyPool,
    addMarketplaceKeyPoolKeys,
    revealMarketplaceKeyPoolKey,
    deleteMarketplaceKeyPoolKey,
    deleteAllFreeMarketplaceKeyPoolKeys,
  }
}
