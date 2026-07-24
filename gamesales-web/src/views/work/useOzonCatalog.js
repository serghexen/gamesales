import { reactive, ref } from 'vue'

export function useOzonCatalog({ auth, apiGet, apiPost, apiPut, mapApiError }) {
  const showOzonCatalog = ref(false)
  const ozonCatalogItems = ref([])
  const ozonCatalogLoading = ref(false)
  const ozonCatalogSyncing = ref(false)
  const ozonCatalogItemActionId = ref(0)
  const ozonCatalogError = ref('')
  const ozonCatalogOk = ref('')
  const showOzonCatalogDetails = ref(false)
  const ozonCatalogDetails = ref(null)
  const ozonCatalogDetailsLoading = ref(false)
  const ozonCatalogDetailsError = ref('')
  const showOzonDigitalSettings = ref(false)
  const ozonDigitalProductId = ref(0)
  const ozonDigitalSettingsLoading = ref(false)
  const ozonDigitalSettingsSaving = ref(false)
  const ozonDigitalOrdersSyncing = ref(false)
  const ozonDigitalSettingsError = ref('')
  const ozonDigitalSettingsOk = ref('')
  const ozonDigitalOrders = ref([])
  const ozonInterhubServices = ref([])
  const ozonInterhubServicesLoading = ref(false)
  const ozonDigitalSettings = reactive({
    external_product_id: 0,
    offer_id: '',
    manual_stock_limit: 0,
    auto_issue_enabled: false,
    activation_instruction: '',
    support_error_message: '',
    interhub_service_id: null,
    interhub_nominal_id: '',
    interhub_enabled: false,
    published_stock: 0,
    available_stock: 0,
    pending_orders: 0,
    delivered_orders: 0,
    last_stock_sync_at: null,
    last_orders_sync_at: null,
  })
  let catalogRequestSeq = 0
  let detailsRequestSeq = 0

  async function loadOzonCatalog() {
    // Загружает сохраненный снимок, чтобы открытие окна не обращалось к Ozon напрямую.
    const requestId = ++catalogRequestSeq
    ozonCatalogLoading.value = true
    ozonCatalogError.value = ''
    try {
      const data = await apiGet('/marketplaces/ozon/catalog', { token: auth.state.token })
      if (requestId !== catalogRequestSeq) return
      ozonCatalogItems.value = Array.isArray(data?.items) ? data.items : []
    } catch (error) {
      if (requestId !== catalogRequestSeq) return
      ozonCatalogItems.value = []
      ozonCatalogError.value = mapApiError(error?.message) || 'Не удалось загрузить каталог Ozon'
    } finally {
      if (requestId === catalogRequestSeq) ozonCatalogLoading.value = false
    }
  }

  async function syncOzonCatalog() {
    // Запускает только чтение карточек Ozon и затем обновляет локальный снимок.
    if (ozonCatalogSyncing.value) return
    ozonCatalogSyncing.value = true
    ozonCatalogError.value = ''
    ozonCatalogOk.value = ''
    try {
      const result = await apiPost('/marketplaces/ozon/catalog/sync', {}, { token: auth.state.token })
      ozonCatalogOk.value = `Синхронизировано карточек: ${Number(result?.synced_items || 0)}`
      await loadOzonCatalog()
    } catch (error) {
      ozonCatalogError.value = mapApiError(error?.message) || 'Не удалось синхронизировать каталог Ozon'
    } finally {
      ozonCatalogSyncing.value = false
    }
  }

  async function updateOzonCatalogArchive(item, archived) {
    // Меняет архивный статус одной карточки и обновляет локальный список без полной синхронизации.
    const productId = Number(item?.external_product_id || 0)
    if (!productId || ozonCatalogItemActionId.value) return
    ozonCatalogItemActionId.value = productId
    ozonCatalogError.value = ''
    ozonCatalogOk.value = ''
    try {
      await apiPost(
        `/marketplaces/ozon/catalog/${encodeURIComponent(productId)}/${archived ? 'archive' : 'unarchive'}`,
        {},
        { token: auth.state.token },
      )
      ozonCatalogItems.value = ozonCatalogItems.value.map((current) => (
        Number(current?.external_product_id || 0) === productId
          ? { ...current, visibility: archived ? 'ARCHIVED' : 'VISIBLE' }
          : current
      ))
      ozonCatalogOk.value = archived ? 'Карточка перенесена в архив' : 'Карточка восстановлена из архива'
    } catch (error) {
      ozonCatalogError.value = mapApiError(error?.message) || 'Не удалось изменить статус карточки в Ozon'
    } finally {
      ozonCatalogItemActionId.value = 0
    }
  }

  function openOzonCatalog() {
    // Открывает каталог и показывает последнюю сохраненную версию до ручной синхронизации.
    showOzonCatalog.value = true
    ozonCatalogOk.value = ''
    loadOzonCatalog()
  }

  function closeOzonCatalog() {
    // Закрывает окно без сброса списка, чтобы повторное открытие не мигало пустым состоянием.
    showOzonCatalog.value = false
  }

  async function loadOzonCatalogDetails(productId) {
    // Читает детальные поля из нашего снимка, поэтому клик по строке не делает запрос в Ozon.
    const requestId = ++detailsRequestSeq
    ozonCatalogDetailsLoading.value = true
    ozonCatalogDetailsError.value = ''
    ozonCatalogDetails.value = null
    try {
      const data = await apiGet(`/marketplaces/ozon/catalog/${encodeURIComponent(productId)}`, { token: auth.state.token })
      if (requestId !== detailsRequestSeq) return
      ozonCatalogDetails.value = data || null
    } catch (error) {
      if (requestId !== detailsRequestSeq) return
      ozonCatalogDetailsError.value = mapApiError(error?.message) || 'Не удалось загрузить параметры карточки Ozon'
    } finally {
      if (requestId === detailsRequestSeq) ozonCatalogDetailsLoading.value = false
    }
  }

  function openOzonCatalogDetails(item) {
    // Открывает только снимок карточки: настройки и заказы загружаются после раскрытия нужного блока.
    const productId = Number(item?.external_product_id || 0)
    if (!productId) return
    ozonDigitalProductId.value = productId
    ozonDigitalOrders.value = []
    showOzonCatalog.value = false
    showOzonCatalogDetails.value = true
    loadOzonCatalogDetails(productId)
  }

  function closeOzonCatalogDetails() {
    // Возвращает пользователя к сохраненному списку, чтобы не запускать синхронизацию заново.
    showOzonCatalogDetails.value = false
    showOzonCatalog.value = true
  }

  function applyOzonDigitalSettings(value) {
    // Переносит ответ API в реактивную форму, чтобы сохранить введенные оператором настройки между действиями.
    const source = value && typeof value === 'object' ? value : {}
    Object.assign(ozonDigitalSettings, {
      external_product_id: Number(source.external_product_id || ozonDigitalProductId.value || 0),
      offer_id: String(source.offer_id || ''),
      manual_stock_limit: Math.max(0, Number(source.manual_stock_limit || 0)),
      auto_issue_enabled: Boolean(source.auto_issue_enabled),
      activation_instruction: String(source.activation_instruction || ''),
      support_error_message: String(source.support_error_message || ''),
      interhub_service_id: source.interhub_service_id ? Number(source.interhub_service_id) : null,
      interhub_nominal_id: String(source.interhub_nominal_id || ''),
      interhub_enabled: Boolean(source.interhub_enabled),
      published_stock: Math.max(0, Number(source.published_stock || 0)),
      available_stock: Math.max(0, Number(source.available_stock || 0)),
      pending_orders: Math.max(0, Number(source.pending_orders || 0)),
      delivered_orders: Math.max(0, Number(source.delivered_orders || 0)),
      last_stock_sync_at: source.last_stock_sync_at || null,
      last_orders_sync_at: source.last_orders_sync_at || null,
    })
  }

  async function loadInterhubServices() {
    // Получает каталог поставщика только через наш сервер, поэтому токен и IP-доступ не попадают в браузер.
    if (ozonInterhubServicesLoading.value) return
    ozonInterhubServicesLoading.value = true
    try {
      const data = await apiGet('/integrations/interhub/services', { token: auth.state.token })
      ozonInterhubServices.value = Array.isArray(data?.items) ? data.items : []
    } catch {
      // Не блокируем ручную выдачу, если каталог поставщика временно недоступен.
      ozonInterhubServices.value = []
    } finally {
      ozonInterhubServicesLoading.value = false
    }
  }

  async function loadOzonDigitalSettings(productId = ozonDigitalProductId.value, { includeOrders = true } = {}) {
    // Загружает настройки для карточки, а очередь заказов — только когда оператор открывает раздел ключей.
    const normalizedProductId = Number(productId || 0)
    if (!normalizedProductId) return
    ozonDigitalSettingsLoading.value = true
    ozonDigitalSettingsError.value = ''
    try {
      const requests = [apiGet(`/marketplaces/ozon/catalog/${encodeURIComponent(normalizedProductId)}/digital-settings`, { token: auth.state.token })]
      if (includeOrders) requests.push(apiGet(`/marketplaces/ozon/catalog/${encodeURIComponent(normalizedProductId)}/digital-orders`, { token: auth.state.token }))
      const [settings, orders] = await Promise.all(requests)
      if (normalizedProductId !== ozonDigitalProductId.value) return
      applyOzonDigitalSettings(settings)
      if (includeOrders) ozonDigitalOrders.value = Array.isArray(orders?.items) ? orders.items : []
    } catch (error) {
      if (normalizedProductId !== ozonDigitalProductId.value) return
      ozonDigitalSettingsError.value = mapApiError(error?.message) || 'Не удалось загрузить настройки ключей Ozon'
    } finally {
      if (normalizedProductId === ozonDigitalProductId.value) ozonDigitalSettingsLoading.value = false
    }
  }

  function openOzonDigitalSettings() {
    // Открывает безопасный ручной режим для текущей карточки и не публикует остаток автоматически.
    const productId = Number(ozonCatalogDetails.value?.external_product_id || 0)
    if (!productId) return
    ozonDigitalProductId.value = productId
    ozonCatalogDetailsError.value = ''
    ozonDigitalSettingsOk.value = ''
    showOzonCatalogDetails.value = false
    showOzonDigitalSettings.value = true
    loadOzonDigitalSettings(productId)
    loadInterhubServices()
  }

  function closeOzonDigitalSettings() {
    // Возвращает к параметрам карточки, сохраняя открытый контекст Ozon для оператора.
    showOzonDigitalSettings.value = false
    showOzonCatalogDetails.value = true
  }

  async function saveOzonDigitalSettings() {
    // Сохраняет лимит и публикует рассчитанный остаток только после готовности ручной выдачи.
    const productId = ozonDigitalProductId.value
    if (!productId || ozonDigitalSettingsSaving.value) return
    ozonDigitalSettingsSaving.value = true
    ozonDigitalSettingsError.value = ''
    ozonDigitalSettingsOk.value = ''
    try {
      const saved = await apiPut(
        `/marketplaces/ozon/catalog/${encodeURIComponent(productId)}/digital-settings`,
        {
          offer_id: String(ozonDigitalSettings.offer_id || ''),
          manual_stock_limit: Math.max(0, Number(ozonDigitalSettings.manual_stock_limit || 0)),
          auto_issue_enabled: Boolean(ozonDigitalSettings.auto_issue_enabled),
          activation_instruction: String(ozonDigitalSettings.activation_instruction || ''),
          support_error_message: String(ozonDigitalSettings.support_error_message || ''),
          interhub_service_id: ozonDigitalSettings.interhub_service_id ? Number(ozonDigitalSettings.interhub_service_id) : null,
          interhub_nominal_id: String(ozonDigitalSettings.interhub_nominal_id || ''),
          interhub_enabled: Boolean(ozonDigitalSettings.interhub_enabled),
        },
        { token: auth.state.token },
      )
      applyOzonDigitalSettings(saved)
      ozonDigitalSettingsOk.value = `В Ozon опубликован остаток: ${ozonDigitalSettings.published_stock}`
    } catch (error) {
      ozonDigitalSettingsError.value = mapApiError(error?.message) || 'Не удалось обновить остаток в Ozon'
    } finally {
      ozonDigitalSettingsSaving.value = false
    }
  }

  async function syncOzonDigitalOrders() {
    // Запрашивает заказы только открытой карточки, чтобы список ключей не смешивал разные товары.
    const productId = ozonDigitalProductId.value
    if (!productId || ozonDigitalOrdersSyncing.value) return
    ozonDigitalOrdersSyncing.value = true
    ozonDigitalSettingsError.value = ''
    ozonDigitalSettingsOk.value = ''
    try {
      await apiPost(`/marketplaces/ozon/catalog/${encodeURIComponent(productId)}/digital-orders/sync`, {}, { token: auth.state.token })
      await loadOzonDigitalSettings()
    } catch (error) {
      ozonDigitalSettingsError.value = mapApiError(error?.message) || 'Не удалось получить цифровые заказы Ozon'
    } finally {
      ozonDigitalOrdersSyncing.value = false
    }
  }

  async function deliverOzonDigitalOrder(order, rawCodes) {
    // Передает операторские ключи в один заказ Ozon и обновляет локальную очередь после подтверждения.
    const orderId = Number(order?.id || 0)
    const codes = String(rawCodes || '').split(/\r?\n/).map((code) => code.trim()).filter(Boolean)
    if (!orderId || !codes.length) return { ok: false, message: 'Введите ключ для отправки' }
    try {
      await apiPost(
        `/marketplaces/ozon/digital-orders/${encodeURIComponent(orderId)}/deliver`,
        { codes },
        { token: auth.state.token },
      )
      ozonDigitalSettingsOk.value = 'Ключ отправлен покупателю через Ozon'
      await loadOzonDigitalSettings()
      return { ok: true, message: '' }
    } catch (error) {
      const message = mapApiError(error?.message) || 'Не удалось отправить ключ в Ozon'
      ozonDigitalSettingsError.value = message
      return { ok: false, message }
    }
  }

  async function revealOzonDigitalOrderCodes(order) {
    // Запрашивает полный ключ только после явного действия администратора в истории заказов.
    const orderId = Number(order?.id || 0)
    if (!orderId) return { ok: false, codes: [], message: 'Не удалось определить заказ' }
    try {
      const result = await apiGet(
        `/marketplaces/ozon/digital-orders/${encodeURIComponent(orderId)}/codes`,
        { token: auth.state.token },
      )
      const codes = Array.isArray(result?.codes)
        ? result.codes.map((code) => String(code || '').trim()).filter(Boolean)
        : []
      if (!codes.length) return { ok: false, codes: [], message: 'Для этого заказа ключ не найден' }
      return { ok: true, codes, message: '' }
    } catch (error) {
      return {
        ok: false,
        codes: [],
        message: mapApiError(error?.message) || 'Не удалось получить ключ заказа',
      }
    }
  }

  async function loadOzonDigitalSupplierOperation(order) {
    // Загружает реквизиты успешной операции поставщика только при открытии карточки из истории заказа.
    const orderId = Number(order?.id || 0)
    if (!orderId) return { ok: false, operation: null, message: 'Не удалось определить заказ' }
    try {
      const operation = await apiGet(
        `/marketplaces/ozon/digital-orders/${encodeURIComponent(orderId)}/supplier-operation`,
        { token: auth.state.token },
      )
      if (!operation || typeof operation !== 'object') {
        return { ok: false, operation: null, message: 'Операция поставщика не найдена' }
      }
      return { ok: true, operation, message: '' }
    } catch (error) {
      return {
        ok: false,
        operation: null,
        message: mapApiError(error?.message) || 'Не удалось загрузить операцию поставщика',
      }
    }
  }

  return {
    showOzonCatalog,
    ozonCatalogItems,
    ozonCatalogLoading,
    ozonCatalogSyncing,
    ozonCatalogItemActionId,
    ozonCatalogError,
    ozonCatalogOk,
    showOzonCatalogDetails,
    ozonCatalogDetails,
    ozonCatalogDetailsLoading,
    ozonCatalogDetailsError,
    loadOzonCatalog,
    syncOzonCatalog,
    updateOzonCatalogArchive,
    openOzonCatalog,
    closeOzonCatalog,
    openOzonCatalogDetails,
    closeOzonCatalogDetails,
    showOzonDigitalSettings,
    ozonDigitalSettings,
    ozonDigitalSettingsLoading,
    ozonDigitalSettingsSaving,
    ozonDigitalOrdersSyncing,
    ozonDigitalSettingsError,
    ozonDigitalSettingsOk,
    ozonDigitalOrders,
    ozonInterhubServices,
    ozonInterhubServicesLoading,
    openOzonDigitalSettings,
    closeOzonDigitalSettings,
    loadOzonDigitalSettings,
    saveOzonDigitalSettings,
    syncOzonDigitalOrders,
    deliverOzonDigitalOrder,
    revealOzonDigitalOrderCodes,
    loadOzonDigitalSupplierOperation,
  }
}
