import { ref } from 'vue'

export function useOzonCatalog({ auth, apiGet, apiPost, mapApiError }) {
  const showOzonCatalog = ref(false)
  const ozonCatalogItems = ref([])
  const ozonCatalogLoading = ref(false)
  const ozonCatalogSyncing = ref(false)
  const ozonCatalogError = ref('')
  const ozonCatalogOk = ref('')
  const showOzonCatalogDetails = ref(false)
  const ozonCatalogDetails = ref(null)
  const ozonCatalogDetailsLoading = ref(false)
  const ozonCatalogDetailsError = ref('')
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
    // Открывает отдельное окно выбранной карточки, не смешивая список и детальные реквизиты.
    const productId = Number(item?.external_product_id || 0)
    if (!productId) return
    showOzonCatalog.value = false
    showOzonCatalogDetails.value = true
    loadOzonCatalogDetails(productId)
  }

  function closeOzonCatalogDetails() {
    // Возвращает пользователя к сохраненному списку, чтобы не запускать синхронизацию заново.
    showOzonCatalogDetails.value = false
    showOzonCatalog.value = true
  }

  return {
    showOzonCatalog,
    ozonCatalogItems,
    ozonCatalogLoading,
    ozonCatalogSyncing,
    ozonCatalogError,
    ozonCatalogOk,
    showOzonCatalogDetails,
    ozonCatalogDetails,
    ozonCatalogDetailsLoading,
    ozonCatalogDetailsError,
    loadOzonCatalog,
    syncOzonCatalog,
    openOzonCatalog,
    closeOzonCatalog,
    openOzonCatalogDetails,
    closeOzonCatalogDetails,
  }
}
