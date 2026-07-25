import { reactive, ref } from 'vue'

export function useYandexMarketCatalog({ auth, apiGet, apiPost, apiPut, mapApiError, requestDealConfirm }) {
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
  const yandexMarketStockSettingsLoading = ref(false)
  const yandexMarketStockSettingsSaving = ref(false)
  const yandexMarketStockSettings = reactive({
    offer_id: '',
    manual_stock_limit: 0,
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

  function applyYandexMarketStockSettings(value) {
    // Переносит серверные настройки остатка в форму, не смешивая их с данными карточки каталога.
    const source = value && typeof value === 'object' ? value : {}
    Object.assign(yandexMarketStockSettings, {
      offer_id: String(source.offer_id || yandexMarketSelectedOfferId.value || ''),
      manual_stock_limit: Math.max(0, Number(source.manual_stock_limit || 0)),
      published_stock: Math.max(0, Number(source.published_stock || 0)),
      last_stock_sync_at: source.last_stock_sync_at || null,
      market_available_stock: source.market_available_stock === null || source.market_available_stock === undefined ? null : Math.max(0, Number(source.market_available_stock || 0)),
      market_stock_updated_at: source.market_stock_updated_at || null,
    })
  }

  async function loadYandexMarketCatalog() {
    // Загружает только локальный снимок, чтобы открытие каталога не создавало запросов в кабинет Маркета.
    const requestId = ++catalogRequestSeq
    yandexMarketCatalogLoading.value = true
    yandexMarketCatalogError.value = ''
    try {
      const data = await apiGet('/marketplaces/yandex/catalog', { token: auth.state.token })
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
      const result = await apiPost('/marketplaces/yandex/catalog/sync', {}, { token: auth.state.token })
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
      await apiPost(`/marketplaces/yandex/catalog/${encodeURIComponent(offerId)}/${archived ? 'archive' : 'unarchive'}`, {}, { token: auth.state.token })
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
    yandexMarketCatalogDetails.value = null
    yandexMarketCatalogDetailsError.value = ''
    yandexMarketOrders.value = []
    yandexMarketOrdersLastSyncedAt.value = null
    yandexMarketCatalogDetailsLoading.value = true
    try {
      const [details, stockSettings] = await Promise.all([
        apiGet(`/marketplaces/yandex/catalog/${encodeURIComponent(offerId)}`, { token: auth.state.token }),
        apiGet(`/marketplaces/yandex/catalog/${encodeURIComponent(offerId)}/stock-settings`, { token: auth.state.token }),
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
    // Открывает экран будущей выдачи отдельно от карточки и не запускает работу с ключами.
    if (!yandexMarketCatalogDetails.value) return
    showYandexMarketCatalogDetails.value = false
    showYandexMarketDigitalSettings.value = true
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
      const data = await apiGet(`/marketplaces/yandex/catalog/${encodeURIComponent(offerId)}/orders`, { token: auth.state.token })
      yandexMarketOrders.value = Array.isArray(data?.items) ? data.items : []
    } catch (error) {
      yandexMarketCatalogDetailsError.value = yandexMarketError(error, 'Не удалось загрузить историю заказов Яндекс Маркета')
    } finally {
      yandexMarketOrdersLoading.value = false
    }
  }

  async function syncYandexMarketOrders() {
    // Обновляет историю вручную безопасным чтением заказов, без выдачи ключей и смены статусов.
    const offerId = String(yandexMarketCatalogDetails.value?.offer_id || '').trim()
    if (!offerId || yandexMarketOrdersSyncing.value) return
    yandexMarketOrdersSyncing.value = true
    yandexMarketCatalogDetailsError.value = ''
    try {
      const result = await apiPost(`/marketplaces/yandex/catalog/${encodeURIComponent(offerId)}/orders/sync`, {}, { token: auth.state.token })
      yandexMarketOrdersLastSyncedAt.value = result?.synced_at || null
      await loadYandexMarketOrders()
    } catch (error) {
      yandexMarketCatalogDetailsError.value = yandexMarketError(error, 'Не удалось синхронизировать заказы Яндекс Маркета')
    } finally {
      yandexMarketOrdersSyncing.value = false
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
      const settings = await apiGet(`/marketplaces/yandex/catalog/${encodeURIComponent(offerId)}/stock-settings`, { token: auth.state.token })
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
    try {
      const saved = await apiPut(
        `/marketplaces/yandex/catalog/${encodeURIComponent(offerId)}/stock-settings${publishStock ? '?publish_stock=true' : ''}`,
        { manual_stock_limit: Math.max(0, Number(yandexMarketStockSettings.manual_stock_limit || 0)) },
        { token: auth.state.token },
      )
      applyYandexMarketStockSettings(saved)
      yandexMarketCatalogOk.value = publishStock
        ? `На Яндекс Маркете опубликован остаток: ${yandexMarketStockSettings.published_stock}`
        : 'Лимит остатка сохранён'
    } catch (error) {
      yandexMarketCatalogError.value = yandexMarketError(error, (
        publishStock ? 'Не удалось обновить остаток на Яндекс Маркете' : 'Не удалось сохранить лимит остатка'
      ))
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
    openYandexMarketCatalog,
    closeYandexMarketCatalog,
    loadYandexMarketCatalog,
    syncYandexMarketCatalog,
    openYandexMarketCatalogDetails,
    closeYandexMarketCatalogDetails,
    openYandexMarketDigitalSettings,
    closeYandexMarketDigitalSettings,
    loadYandexMarketOrders,
    syncYandexMarketOrders,
    updateYandexMarketCatalogArchive,
    selectYandexMarketCatalogItem,
    closeYandexMarketStockSettings,
    saveYandexMarketStockSettings,
  }
}
