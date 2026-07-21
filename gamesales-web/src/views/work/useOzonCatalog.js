import { ref } from 'vue'

export function useOzonCatalog({ auth, apiGet, apiPost, mapApiError }) {
  const showOzonCatalog = ref(false)
  const ozonCatalogItems = ref([])
  const ozonCatalogLoading = ref(false)
  const ozonCatalogSyncing = ref(false)
  const ozonCatalogError = ref('')
  const ozonCatalogOk = ref('')
  let catalogRequestSeq = 0

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

  return {
    showOzonCatalog,
    ozonCatalogItems,
    ozonCatalogLoading,
    ozonCatalogSyncing,
    ozonCatalogError,
    ozonCatalogOk,
    loadOzonCatalog,
    syncOzonCatalog,
    openOzonCatalog,
    closeOzonCatalog,
  }
}
