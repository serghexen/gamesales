import { computed, reactive, ref } from 'vue'

const YANDEX_MARKET_STORE_CODES = [...new Set(String(
  import.meta.env.VITE_YANDEX_MARKET_STORE_CODES || import.meta.env.VITE_YANDEX_MARKET_STORE_CODE || 'test',
).split(',').map((value) => value.trim().toLowerCase()).filter(Boolean))]

export function useYandexMarketCatalog({ auth, apiGet, apiPost, apiPut, mapApiError, requestDealConfirm }) {
  // Хранит выбранный кабинет, чтобы товары и ключи разных магазинов никогда не смешивались.
  const yandexMarketStoreCode = ref(YANDEX_MARKET_STORE_CODES[0] || 'test')
  const yandexMarketSandboxMode = computed(() => yandexMarketStoreCode.value === 'test')
  const showYandexMarketCatalog = ref(false)
  const yandexMarketCatalogItems = ref([])
  const yandexMarketCatalogLoading = ref(false)
  const yandexMarketCatalogSyncing = ref(false)
  const yandexMarketCatalogItemActionId = ref('')
  const yandexMarketCatalogError = ref('')
  const yandexMarketCatalogOk = ref('')
  const showYandexMarketCatalogDetails = ref(false)
  const yandexMarketCatalogDetails = ref(null)
  const yandexMarketCatalogDetailsLoading = ref(false)
  const yandexMarketCatalogDetailsError = ref('')
  const showYandexMarketDigitalSettings = ref(false)
  const yandexMarketSelectedOfferId = ref('')
  const yandexMarketOrders = ref([])
  const yandexMarketOrdersLoading = ref(false)
  const yandexMarketOrdersSyncing = ref(false)
  const yandexMarketOrdersLastSyncedAt = ref(null)
  const yandexMarketSandboxDeliverySaving = ref('')
  const yandexMarketProductionManualOrders = ref([])
  const yandexMarketProductionManualOrdersLoading = ref(false)
  const yandexMarketProductionManualDeliverySaving = ref(0)
  const yandexMarketProductionManualDeliveryError = ref('')
  const yandexMarketProductionStartDeliverySaving = ref(0)
  const yandexMarketInterhubServices = ref([])
  const yandexMarketInterhubServicesLoading = ref(false)
  const yandexMarketStockSettingsLoading = ref(false)
  const yandexMarketStockSettingsSaving = ref(false)
  const yandexMarketStockSettings = reactive({
    offer_id: '',
    manual_stock_limit: 0,
    sales_limit: null,
    sales_limit_daily_extra: 0,
    sales_limit_effective: null,
    sales_limit_day: null,
    sales_limit_add_units: '',
    sales_limit_used: 0,
    sales_limit_reserved: 0,
    sales_limit_remaining: null,
    archived_by_sales_limit: false,
    sales_limit_exhausted_at: null,
    activation_instruction: '',
    support_error_message: '',
    auto_issue_enabled: false,
    pool_issue_enabled: false,
    support_message_delivery_enabled: false,
    interhub_service_id: null,
    interhub_nominal_id: '',
    interhub_enabled: false,
    published_stock: 0,
    last_stock_sync_at: null,
    market_available_stock: null,
    market_stock_updated_at: null,
  })
  let catalogRequestSeq = 0
  let detailsRequestSeq = 0

  function yandexMarketError(error, fallback) {
    // Не подменяет сетевую ошибку Маркета текстом про Excel, который относится только к импорту файлов.
    const message = String(error?.message || '').trim()
    if (!message || message.includes('Load failed')) return fallback
    return mapApiError(message) || fallback
  }

  function yandexMarketTestPath(path) {
    // Передает выбранный кабинет во все запросы, чтобы магазины не читали данные друг друга.
    return `${path}${path.includes('?') ? '&' : '?'}store_code=${encodeURIComponent(yandexMarketStoreCode.value)}`
  }

  function applyYandexMarketStockSettings(value) {
    // Переносит серверные настройки остатка в форму, не смешивая их с данными карточки каталога.
    const source = value && typeof value === 'object' ? value : {}
    const hasMarketStock = Object.prototype.hasOwnProperty.call(source, 'market_available_stock')
    const hasMarketStockUpdatedAt = Object.prototype.hasOwnProperty.call(source, 'market_stock_updated_at')
    Object.assign(yandexMarketStockSettings, {
      offer_id: String(source.offer_id || yandexMarketSelectedOfferId.value || ''),
      manual_stock_limit: Math.max(0, Number(source.manual_stock_limit || 0)),
      sales_limit: source.sales_limit === null || source.sales_limit === undefined ? null : Math.max(1, Number(source.sales_limit || 1)),
      sales_limit_daily_extra: Math.max(0, Number(source.sales_limit_daily_extra || 0)),
      sales_limit_effective: source.sales_limit_effective === null || source.sales_limit_effective === undefined ? null : Math.max(1, Number(source.sales_limit_effective || 1)),
      sales_limit_day: source.sales_limit_day || null,
      sales_limit_used: Math.max(0, Number(source.sales_limit_used || 0)),
      sales_limit_reserved: Math.max(0, Number(source.sales_limit_reserved || 0)),
      sales_limit_remaining: source.sales_limit_remaining === null || source.sales_limit_remaining === undefined ? null : Math.max(0, Number(source.sales_limit_remaining || 0)),
      archived_by_sales_limit: Boolean(source.archived_by_sales_limit),
      sales_limit_exhausted_at: source.sales_limit_exhausted_at || null,
      activation_instruction: String(source.activation_instruction || ''),
      support_error_message: String(source.support_error_message || ''),
      auto_issue_enabled: Boolean(source.auto_issue_enabled), pool_issue_enabled: Boolean(source.pool_issue_enabled),
      support_message_delivery_enabled: Boolean(source.support_message_delivery_enabled),
      interhub_service_id: source.interhub_service_id ? Number(source.interhub_service_id) : null,
      interhub_nominal_id: String(source.interhub_nominal_id || ''), interhub_enabled: Boolean(source.interhub_enabled),
      published_stock: Math.max(0, Number(source.published_stock || 0)),
      last_stock_sync_at: source.last_stock_sync_at || null,
      market_available_stock: hasMarketStock
        ? (source.market_available_stock === null || source.market_available_stock === undefined ? null : Math.max(0, Number(source.market_available_stock || 0)))
        : yandexMarketStockSettings.market_available_stock,
      market_stock_updated_at: hasMarketStockUpdatedAt ? (source.market_stock_updated_at || null) : yandexMarketStockSettings.market_stock_updated_at,
    })
  }

  async function loadYandexMarketCatalog() {
    // Загружает только локальный снимок, чтобы открытие каталога не создавало запросов в кабинет Маркета.
    const requestId = ++catalogRequestSeq
    yandexMarketCatalogLoading.value = true
    yandexMarketCatalogError.value = ''
    try {
      const data = await apiGet(yandexMarketTestPath('/marketplaces/yandex/catalog'), { token: auth.state.token })
      if (requestId !== catalogRequestSeq) return
      yandexMarketCatalogItems.value = Array.isArray(data?.items) ? data.items : []
    } catch (error) {
      if (requestId !== catalogRequestSeq) return
      yandexMarketCatalogItems.value = []
      yandexMarketCatalogError.value = yandexMarketError(error, 'Не удалось загрузить каталог Яндекс Маркета')
    } finally {
      if (requestId === catalogRequestSeq) yandexMarketCatalogLoading.value = false
    }
  }

  async function syncYandexMarketCatalog() {
    // Обновляет снимок карточек вручную и не меняет цены, заказы или ключи.
    if (yandexMarketCatalogSyncing.value) return
    yandexMarketCatalogSyncing.value = true
    yandexMarketCatalogError.value = ''
    yandexMarketCatalogOk.value = ''
    try {
      const result = await apiPost(yandexMarketTestPath('/marketplaces/yandex/catalog/sync'), {}, { token: auth.state.token })
      yandexMarketCatalogOk.value = `Синхронизировано карточек: ${Number(result?.synced_items || 0)}`
      await loadYandexMarketCatalog()
    } catch (error) {
      yandexMarketCatalogError.value = yandexMarketError(error, 'Не удалось синхронизировать каталог Яндекс Маркета')
    } finally {
      yandexMarketCatalogSyncing.value = false
    }
  }

  async function updateYandexMarketCatalogArchive(item, archived) {
    // Спрашивает подтверждение перед скрытием карточки, чтобы случайный клик не остановил продажи.
    const offerId = String(item?.offer_id || '').trim()
    if (!offerId || yandexMarketCatalogItemActionId.value) return
    if (archived) {
      const title = String(item?.title || offerId).trim()
      const confirmed = typeof requestDealConfirm === 'function' && await requestDealConfirm({
        title: 'Архивировать карточку?',
        message: `«${title}» станет недоступна на Яндекс Маркете. Остаток и ключи не меняются.`,
        confirmText: 'Архивировать',
        cancelText: 'Отмена',
      })
      if (!confirmed) return
    }
    yandexMarketCatalogItemActionId.value = offerId
    yandexMarketCatalogError.value = ''
    yandexMarketCatalogOk.value = ''
    try {
      await apiPost(yandexMarketTestPath(`/marketplaces/yandex/catalog/${encodeURIComponent(offerId)}/${archived ? 'archive' : 'unarchive'}`), {}, { token: auth.state.token })
      yandexMarketCatalogItems.value = yandexMarketCatalogItems.value.map((current) => (
        String(current?.offer_id || '') === offerId ? { ...current, archived } : current
      ))
      yandexMarketCatalogOk.value = archived ? 'Карточка перенесена в архив' : 'Карточка восстановлена из архива'
    } catch (error) {
      yandexMarketCatalogError.value = yandexMarketError(error, 'Не удалось изменить статус карточки на Яндекс Маркете')
    } finally {
      yandexMarketCatalogItemActionId.value = ''
    }
  }

  function openYandexMarketCatalog() {
    // Открывает каталог с последним снимком, чтобы оператор сам решил, когда запускать синхронизацию.
    showYandexMarketCatalog.value = true
    yandexMarketCatalogOk.value = ''
    loadYandexMarketCatalog()
  }

  async function selectYandexMarketStore(storeCode) {
    // Переключает кабинет только в каталоге и сбрасывает карточку, чтобы не сохранить настройки не того магазина.
    const normalizedStoreCode = String(storeCode || '').trim().toLowerCase()
    if (!YANDEX_MARKET_STORE_CODES.includes(normalizedStoreCode) || normalizedStoreCode === yandexMarketStoreCode.value) return
    ++catalogRequestSeq
    ++detailsRequestSeq
    yandexMarketStoreCode.value = normalizedStoreCode
    yandexMarketCatalogItems.value = []
    yandexMarketCatalogDetails.value = null
    yandexMarketSelectedOfferId.value = ''
    yandexMarketOrders.value = []
    yandexMarketProductionManualOrders.value = []
    yandexMarketInterhubServices.value = []
    yandexMarketCatalogError.value = ''
    yandexMarketCatalogOk.value = ''
    await loadYandexMarketCatalog()
  }

  function closeYandexMarketCatalog() {
    // Закрывает окно без очистки списка, чтобы повторное открытие не показывало мерцание пустого состояния.
    showYandexMarketCatalog.value = false
  }

  async function openYandexMarketCatalogDetails(item) {
    // Открывает карточку в режиме чтения: детали берутся из снимка, а остаток — безопасным запросом к Маркету.
    const offerId = String(item?.offer_id || '').trim()
    if (!offerId) return
    const requestId = ++detailsRequestSeq
    showYandexMarketCatalog.value = false
    showYandexMarketCatalogDetails.value = true
    // Запоминает SKU открытой карточки, чтобы инструкция сохранялась именно для него.
    yandexMarketSelectedOfferId.value = offerId
    yandexMarketCatalogDetails.value = null
    yandexMarketCatalogDetailsError.value = ''
    yandexMarketOrders.value = []
    yandexMarketOrdersLastSyncedAt.value = null
    yandexMarketCatalogDetailsLoading.value = true
    try {
      const [details, stockSettings] = await Promise.all([
        apiGet(yandexMarketTestPath(`/marketplaces/yandex/catalog/${encodeURIComponent(offerId)}`), { token: auth.state.token }),
        apiGet(yandexMarketTestPath(`/marketplaces/yandex/catalog/${encodeURIComponent(offerId)}/stock-settings`), { token: auth.state.token }),
      ])
      if (requestId !== detailsRequestSeq) return
      yandexMarketCatalogDetails.value = details || null
      applyYandexMarketStockSettings(stockSettings)
    } catch (error) {
      if (requestId !== detailsRequestSeq) return
      yandexMarketCatalogDetailsError.value = yandexMarketError(error, 'Не удалось загрузить параметры карточки Яндекс Маркета')
    } finally {
      if (requestId === detailsRequestSeq) yandexMarketCatalogDetailsLoading.value = false
    }
  }

  function closeYandexMarketCatalogDetails() {
    // Возвращает к локальному списку без новой синхронизации и без изменения карточки на Маркете.
    showYandexMarketCatalogDetails.value = false
    showYandexMarketCatalog.value = true
  }

  function openYandexMarketDigitalSettings() {
    // Открывает отдельные настройки источников выдачи для выбранной карточки в нужном контуре.
    if (!yandexMarketCatalogDetails.value) return
    showYandexMarketCatalogDetails.value = false
    showYandexMarketDigitalSettings.value = true
    if (yandexMarketSandboxMode.value) loadYandexMarketOrders()
    else {
      loadYandexMarketProductionManualOrders()
      loadYandexMarketInterhubServices()
    }
  }

  function closeYandexMarketDigitalSettings() {
    // Возвращает к карточке, сохраняя только просмотренные данные и не меняя настройки Маркета.
    showYandexMarketDigitalSettings.value = false
    showYandexMarketCatalogDetails.value = true
  }

  async function loadYandexMarketOrders() {
    // Читает только сохраненную историю товара, не создавая запросов в кабинет Маркета.
    const offerId = String(yandexMarketCatalogDetails.value?.offer_id || '').trim()
    if (!offerId || yandexMarketOrdersLoading.value) return
    yandexMarketOrdersLoading.value = true
    try {
      const data = await apiGet(yandexMarketTestPath(`/marketplaces/yandex/catalog/${encodeURIComponent(offerId)}/orders`), { token: auth.state.token })
      yandexMarketOrders.value = Array.isArray(data?.items) ? data.items : []
    } catch (error) {
      yandexMarketCatalogDetailsError.value = yandexMarketError(error, 'Не удалось загрузить историю заказов Яндекс Маркета')
    } finally {
      yandexMarketOrdersLoading.value = false
    }
  }

  async function loadYandexMarketProductionManualOrders() {
    // Читает только остановленные боевые выдачи выбранной карточки, без синхронизации или внешней отправки.
    const offerId = String(yandexMarketCatalogDetails.value?.offer_id || '').trim()
    if (!offerId || yandexMarketSandboxMode.value || yandexMarketProductionManualOrdersLoading.value) return
    yandexMarketProductionManualOrdersLoading.value = true
    yandexMarketProductionManualDeliveryError.value = ''
    try {
      const data = await apiGet(yandexMarketTestPath(`/marketplaces/yandex/catalog/${encodeURIComponent(offerId)}/manual-deliveries`), { token: auth.state.token })
      yandexMarketProductionManualOrders.value = Array.isArray(data?.items) ? data.items : []
    } catch (error) {
      yandexMarketProductionManualDeliveryError.value = yandexMarketError(error, 'Не удалось загрузить очередь ручной выдачи Яндекс Маркета')
    } finally {
      yandexMarketProductionManualOrdersLoading.value = false
    }
  }

  async function loadYandexMarketInterhubServices() {
    // Получает каталог услуг только через наш API, чтобы токен Interhub не попадал в браузер.
    if (yandexMarketSandboxMode.value || yandexMarketInterhubServicesLoading.value) return
    yandexMarketInterhubServicesLoading.value = true
    try {
      const data = await apiGet('/integrations/interhub/services', { token: auth.state.token })
      yandexMarketInterhubServices.value = Array.isArray(data?.items) ? data.items : []
    } catch {
      // Оставляет ручную выдачу доступной, если каталог поставщика временно недоступен.
      yandexMarketInterhubServices.value = []
    } finally {
      yandexMarketInterhubServicesLoading.value = false
    }
  }

  async function deliverYandexMarketProductionOrder(order, rawCodes) {
    // Передает ручные коды только выбранной остановленной выдаче и обновляет локальную очередь после ответа Маркета.
    const deliveryId = Number(order?.id || 0)
    const codes = String(rawCodes || '').split(/\r?\n/).map((code) => code.trim()).filter(Boolean)
    const repeatsSavedCodes = Number(order?.collected_qty || 0) >= Math.max(1, Number(order?.required_qty || 1))
    if (!deliveryId || (!codes.length && !repeatsSavedCodes)) return { ok: false, message: 'Введите ключ для отправки' }
    yandexMarketProductionManualDeliverySaving.value = deliveryId
    yandexMarketProductionManualDeliveryError.value = ''
    try {
      await apiPost(`/marketplaces/yandex/digital-deliveries/${encodeURIComponent(deliveryId)}/deliver`, { codes }, { token: auth.state.token })
      await loadYandexMarketProductionManualOrders()
      return { ok: true, message: '' }
    } catch (error) {
      const message = yandexMarketError(error, 'Не удалось отправить ключ в Яндекс Маркет')
      yandexMarketProductionManualDeliveryError.value = message
      return { ok: false, message }
    } finally {
      yandexMarketProductionManualDeliverySaving.value = 0
    }
  }

  async function issueYandexMarketProductionOrderFromPool(order) {
    // Берет полный комплект из боевого ручного пула только после прямого действия оператора.
    const deliveryId = Number(order?.id || 0)
    if (!deliveryId) return { ok: false, message: 'Не удалось определить выдачу' }
    yandexMarketProductionManualDeliverySaving.value = deliveryId
    yandexMarketProductionManualDeliveryError.value = ''
    try {
      await apiPost(`/marketplaces/yandex/digital-deliveries/${encodeURIComponent(deliveryId)}/issue-from-pool`, {}, { token: auth.state.token })
      await loadYandexMarketProductionManualOrders()
      return { ok: true, message: '' }
    } catch (error) {
      const message = yandexMarketError(error, 'Не удалось выдать ключ из ручного пула')
      yandexMarketProductionManualDeliveryError.value = message
      return { ok: false, message }
    } finally {
      yandexMarketProductionManualDeliverySaving.value = 0
    }
  }

  async function startYandexMarketProductionOrder(order) {
    // Явно запускает выдачу старого сохраненного заказа, не ослабляя порог новых webhook-уведомлений.
    const orderId = Number(order?.order_id || 0)
    const itemId = Number(order?.item_id || 0)
    if (!orderId || !itemId) return { ok: false, message: 'Не удалось определить заказ для выдачи' }
    const confirmed = typeof requestDealConfirm === 'function' && await requestDealConfirm({
      title: 'Запустить выдачу?',
      message: `Заказ №${orderId} будет обработан с сохраненным источником. При включенном Interhub начнется покупка, а ключ после успеха будет отправлен в Яндекс Маркет.`,
      confirmText: 'Запустить',
      cancelText: 'Отмена',
    })
    if (!confirmed) return { ok: false, message: '' }
    yandexMarketProductionStartDeliverySaving.value = orderId
    yandexMarketCatalogDetailsError.value = ''
    try {
      await apiPost(yandexMarketTestPath(`/marketplaces/yandex/orders/${encodeURIComponent(orderId)}/items/${encodeURIComponent(itemId)}/start-delivery`), {}, { token: auth.state.token })
      await Promise.all([loadYandexMarketOrders(), loadYandexMarketProductionManualOrders()])
      return { ok: true, message: '' }
    } catch (error) {
      const message = yandexMarketError(error, 'Не удалось запустить выдачу заказа Яндекс Маркета')
      yandexMarketCatalogDetailsError.value = message
      return { ok: false, message }
    } finally {
      yandexMarketProductionStartDeliverySaving.value = 0
    }
  }

  async function revealYandexMarketProductionOrderCodes(order) {
    // Загружает уже отправленный ключ только по явному действию владельца, не добавляя его в историю заказов.
    const orderId = Number(order?.order_id || 0)
    const itemId = Number(order?.item_id || 0)
    if (!orderId || !itemId) return { ok: false, codes: [], message: 'Не удалось определить заказ для просмотра ключа' }
    try {
      const result = await apiGet(
        yandexMarketTestPath(`/marketplaces/yandex/orders/${encodeURIComponent(orderId)}/items/${encodeURIComponent(itemId)}/codes`),
        { token: auth.state.token },
      )
      const codes = Array.isArray(result?.codes) ? result.codes.map((code) => String(code || '').trim()).filter(Boolean) : []
      return codes.length ? { ok: true, codes, message: '' } : { ok: false, codes: [], message: 'Отправленный ключ не найден' }
    } catch (error) {
      return { ok: false, codes: [], message: yandexMarketError(error, 'Не удалось загрузить отправленный ключ') }
    }
  }

  async function syncYandexMarketOrders() {
    // Обновляет историю вручную безопасным чтением заказов, без выдачи ключей и смены статусов.
    const offerId = String(yandexMarketCatalogDetails.value?.offer_id || '').trim()
    if (!offerId || yandexMarketOrdersSyncing.value) return
    yandexMarketOrdersSyncing.value = true
    yandexMarketCatalogDetailsError.value = ''
    try {
      const result = await apiPost(yandexMarketTestPath(`/marketplaces/yandex/catalog/${encodeURIComponent(offerId)}/orders/sync`), {}, { token: auth.state.token })
      yandexMarketOrdersLastSyncedAt.value = result?.synced_at || null
      await loadYandexMarketOrders()
    } catch (error) {
      yandexMarketCatalogDetailsError.value = yandexMarketError(error, 'Не удалось синхронизировать заказы Яндекс Маркета')
    } finally {
      yandexMarketOrdersSyncing.value = false
    }
  }

  async function deliverYandexMarketSandboxOrder(order, rawCodes = []) {
    // Фиксирует ручные коды локально для fake-заказа и не отправляет их в Яндекс Маркет.
    const orderId = Number(order?.order_id || 0)
    const itemId = Number(order?.item_id || 0)
    const codes = Array.isArray(rawCodes) ? rawCodes.map((code) => String(code || '').trim()).filter(Boolean) : []
    if (!orderId || !itemId || !codes.length || yandexMarketSandboxDeliverySaving.value) return { ok: false, message: 'Введите ключи для позиции заказа' }
    const savingKey = `${orderId}:${itemId}`
    yandexMarketSandboxDeliverySaving.value = savingKey
    yandexMarketCatalogDetailsError.value = ''
    try {
      const result = await apiPost(
        yandexMarketTestPath(`/marketplaces/yandex/sandbox/orders/${encodeURIComponent(orderId)}/items/${encodeURIComponent(itemId)}/deliver`),
        { codes },
        { token: auth.state.token },
      )
      yandexMarketOrders.value = yandexMarketOrders.value.map((current) => (
        Number(current?.order_id) === orderId && Number(current?.item_id) === itemId
          ? { ...current, sandbox_delivery_status: String(result?.status || 'locally_issued') }
          : current
      ))
      return { ok: true, message: '' }
    } catch (error) {
      const message = yandexMarketError(error, 'Не удалось локально зафиксировать ручную выдачу')
      yandexMarketCatalogDetailsError.value = message
      return { ok: false, message }
    } finally {
      yandexMarketSandboxDeliverySaving.value = ''
    }
  }

  async function issueYandexMarketSandboxOrderFromPool(order) {
    // Выбирает ключи только из локального test-пула и не меняет заказ в кабинете Маркета.
    const orderId = Number(order?.order_id || 0)
    const itemId = Number(order?.item_id || 0)
    if (!orderId || !itemId || yandexMarketSandboxDeliverySaving.value) return { ok: false, message: 'Не удалось определить позицию fake-заказа' }
    const savingKey = `${orderId}:${itemId}`
    yandexMarketSandboxDeliverySaving.value = savingKey
    yandexMarketCatalogDetailsError.value = ''
    try {
      const result = await apiPost(
        yandexMarketTestPath(`/marketplaces/yandex/sandbox/orders/${encodeURIComponent(orderId)}/items/${encodeURIComponent(itemId)}/issue-from-pool`),
        {},
        { token: auth.state.token },
      )
      yandexMarketOrders.value = yandexMarketOrders.value.map((current) => (
        Number(current?.order_id) === orderId && Number(current?.item_id) === itemId
          ? { ...current, sandbox_delivery_status: String(result?.status || 'locally_issued') }
          : current
      ))
      return { ok: true, message: '' }
    } catch (error) {
      const message = yandexMarketError(error, 'Не удалось выдать ключи из локального пула')
      yandexMarketCatalogDetailsError.value = message
      return { ok: false, message }
    } finally {
      yandexMarketSandboxDeliverySaving.value = ''
    }
  }

  async function sendYandexMarketSandboxOrderToMarket(order) {
    // Отправляет уже закрепленные ключи только в test-Маркет после отдельного подтверждения оператора.
    const orderId = Number(order?.order_id || 0)
    const itemId = Number(order?.item_id || 0)
    if (!orderId || !itemId || yandexMarketSandboxDeliverySaving.value) return { ok: false, message: 'Не удалось определить позицию fake-заказа' }
    const confirmed = typeof requestDealConfirm === 'function' && await requestDealConfirm({
      title: 'Отправить ключ в test Маркет?',
      message: `Ключ будет передан только в fake-заказ ${orderId}. После этого Маркет начнет доставку покупателю и может перевести заказ в DELIVERED.`,
      confirmText: 'Отправить в test Маркет',
      cancelText: 'Отмена',
    })
    if (!confirmed) return { ok: false, message: '' }
    const savingKey = `${orderId}:${itemId}`
    yandexMarketSandboxDeliverySaving.value = savingKey
    yandexMarketCatalogDetailsError.value = ''
    try {
      const result = await apiPost(
        yandexMarketTestPath(`/marketplaces/yandex/sandbox/orders/${encodeURIComponent(orderId)}/items/${encodeURIComponent(itemId)}/send-to-market`),
        {},
        { token: auth.state.token },
      )
      yandexMarketOrders.value = yandexMarketOrders.value.map((current) => (
        Number(current?.order_id) === orderId && Number(current?.item_id) === itemId
          ? { ...current, sandbox_delivery_status: String(result?.status || 'market_submitted') }
          : current
      ))
      return { ok: true, message: '' }
    } catch (error) {
      const message = yandexMarketError(error, 'Не удалось отправить ключ в test Маркет')
      yandexMarketCatalogDetailsError.value = message
      return { ok: false, message }
    } finally {
      yandexMarketSandboxDeliverySaving.value = ''
    }
  }

  async function selectYandexMarketCatalogItem(item) {
    // Открывает панель и читает текущий остаток Маркета для выбранного SKU без публикации нового значения.
    const offerId = String(item?.offer_id || '').trim()
    if (!offerId) return
    yandexMarketSelectedOfferId.value = offerId
    yandexMarketStockSettingsLoading.value = true
    yandexMarketCatalogError.value = ''
    try {
      const settings = await apiGet(yandexMarketTestPath(`/marketplaces/yandex/catalog/${encodeURIComponent(offerId)}/stock-settings`), { token: auth.state.token })
      if (yandexMarketSelectedOfferId.value === offerId) applyYandexMarketStockSettings(settings)
    } catch (error) {
      if (yandexMarketSelectedOfferId.value === offerId) {
        yandexMarketCatalogError.value = yandexMarketError(error, 'Не удалось загрузить настройки остатка')
      }
    } finally {
      if (yandexMarketSelectedOfferId.value === offerId) yandexMarketStockSettingsLoading.value = false
    }
  }

  function closeYandexMarketStockSettings() {
    // Возвращает к списку карточек и сохраняет снимок каталога для дальнейшей работы.
    yandexMarketSelectedOfferId.value = ''
  }

  async function saveYandexMarketStockSettings({ publishStock = false } = {}) {
    // Сохраняет лимит, а внешний остаток публикует только после отдельного явного действия.
    const offerId = yandexMarketSelectedOfferId.value
    if (!offerId || yandexMarketStockSettingsSaving.value) return
    yandexMarketStockSettingsSaving.value = true
    yandexMarketCatalogError.value = ''
    yandexMarketCatalogOk.value = ''
    yandexMarketCatalogDetailsError.value = ''
    try {
      // Пустое поле передает NULL как безлимит, а введенное значение нормализует до целого положительного числа.
      const rawSalesLimit = yandexMarketStockSettings.sales_limit
      const salesLimit = rawSalesLimit === '' || rawSalesLimit === null || rawSalesLimit === undefined
        ? null
        : Math.max(1, Math.floor(Number(rawSalesLimit) || 1))
      const saved = await apiPut(
        yandexMarketTestPath(`/marketplaces/yandex/catalog/${encodeURIComponent(offerId)}/stock-settings${publishStock ? '?publish_stock=true' : ''}`),
        {
          manual_stock_limit: Math.max(0, Math.floor(Number(yandexMarketStockSettings.manual_stock_limit || 0))),
          sales_limit: salesLimit,
          activation_instruction: String(yandexMarketStockSettings.activation_instruction || '').trim(),
          support_error_message: String(yandexMarketStockSettings.support_error_message || '').trim(),
          auto_issue_enabled: Boolean(yandexMarketStockSettings.auto_issue_enabled), pool_issue_enabled: Boolean(yandexMarketStockSettings.pool_issue_enabled),
          support_message_delivery_enabled: Boolean(yandexMarketStockSettings.support_message_delivery_enabled),
          interhub_service_id: yandexMarketStockSettings.interhub_service_id ? Number(yandexMarketStockSettings.interhub_service_id) : null,
          interhub_nominal_id: String(yandexMarketStockSettings.interhub_nominal_id || '').trim(), interhub_enabled: Boolean(yandexMarketStockSettings.interhub_enabled),
        },
        { token: auth.state.token },
      )
      applyYandexMarketStockSettings(saved)
      yandexMarketCatalogOk.value = publishStock
        ? `На Яндекс Маркете опубликован остаток: ${yandexMarketStockSettings.published_stock}`
        : 'Настройки карточки сохранены'
    } catch (error) {
      const message = yandexMarketError(error, (
        publishStock ? 'Не удалось обновить остаток на Яндекс Маркете' : 'Не удалось сохранить лимит остатка'
      ))
      yandexMarketCatalogError.value = message
      yandexMarketCatalogDetailsError.value = message
    } finally {
      yandexMarketStockSettingsSaving.value = false
    }
  }

  async function addYandexMarketDailyLimitUnits() {
    // Прибавляет введенное количество только к текущему дню и не меняет базовый лимит следующих дней.
    const offerId = yandexMarketSelectedOfferId.value
    const units = Math.floor(Number(yandexMarketStockSettings.sales_limit_add_units || 0))
    if (!offerId || yandexMarketStockSettingsSaving.value || !Number.isFinite(units) || units <= 0) return
    yandexMarketStockSettingsSaving.value = true
    yandexMarketCatalogError.value = ''
    yandexMarketCatalogOk.value = ''
    yandexMarketCatalogDetailsError.value = ''
    try {
      const saved = await apiPost(
        yandexMarketTestPath(`/marketplaces/yandex/catalog/${encodeURIComponent(offerId)}/daily-limit/add`),
        { units },
        { token: auth.state.token },
      )
      applyYandexMarketStockSettings(saved)
      yandexMarketStockSettings.sales_limit_add_units = ''
      yandexMarketCatalogOk.value = `К дневному лимиту добавлено: ${units}`
    } catch (error) {
      const message = yandexMarketError(error, 'Не удалось увеличить лимит на сегодня')
      yandexMarketCatalogError.value = message
      yandexMarketCatalogDetailsError.value = message
    } finally {
      yandexMarketStockSettingsSaving.value = false
    }
  }

  return {
    showYandexMarketCatalog,
    yandexMarketCatalogItems,
    yandexMarketCatalogLoading,
    yandexMarketCatalogSyncing,
    yandexMarketCatalogItemActionId,
    yandexMarketCatalogError,
    yandexMarketCatalogOk,
    showYandexMarketCatalogDetails,
    yandexMarketCatalogDetails,
    yandexMarketCatalogDetailsLoading,
    yandexMarketCatalogDetailsError,
    showYandexMarketDigitalSettings,
    yandexMarketSelectedOfferId,
    yandexMarketStockSettings,
    yandexMarketStockSettingsLoading,
    yandexMarketStockSettingsSaving,
    yandexMarketOrders,
    yandexMarketOrdersLoading,
    yandexMarketOrdersSyncing,
    yandexMarketOrdersLastSyncedAt,
    yandexMarketSandboxDeliverySaving,
    yandexMarketProductionManualOrders,
    yandexMarketProductionManualOrdersLoading,
    yandexMarketProductionManualDeliverySaving,
    yandexMarketProductionManualDeliveryError,
    yandexMarketProductionStartDeliverySaving,
    yandexMarketInterhubServices,
    yandexMarketInterhubServicesLoading,
    yandexMarketStoreCodes: YANDEX_MARKET_STORE_CODES,
    yandexMarketStoreCode,
    yandexMarketSandboxMode,
    openYandexMarketCatalog,
    selectYandexMarketStore,
    closeYandexMarketCatalog,
    loadYandexMarketCatalog,
    syncYandexMarketCatalog,
    openYandexMarketCatalogDetails,
    closeYandexMarketCatalogDetails,
    openYandexMarketDigitalSettings,
    closeYandexMarketDigitalSettings,
    loadYandexMarketOrders,
    loadYandexMarketProductionManualOrders,
    loadYandexMarketInterhubServices,
    syncYandexMarketOrders,
    deliverYandexMarketSandboxOrder,
    issueYandexMarketSandboxOrderFromPool,
    sendYandexMarketSandboxOrderToMarket,
    deliverYandexMarketProductionOrder,
    issueYandexMarketProductionOrderFromPool,
    startYandexMarketProductionOrder,
    revealYandexMarketProductionOrderCodes,
    updateYandexMarketCatalogArchive,
    selectYandexMarketCatalogItem,
    closeYandexMarketStockSettings,
    saveYandexMarketStockSettings,
    addYandexMarketDailyLimitUnits,
  }
}
