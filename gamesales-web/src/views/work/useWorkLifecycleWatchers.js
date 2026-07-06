import { watch } from 'vue'

export function useWorkLifecycleWatchers({
  route,
  TAB_KEYS,
  normalizeWorkTab,
  setActiveTab,
  activeTab,
  telegram,
  startTelegramPolling,
  stopTelegramPolling,
  handleTelegramActiveChatChange,
  editAccount,
  domains,
  loadDomains,
  resetModalPos,
}) {
  watch(
    () => route.query.tab,
    (tab) => {
      // При чтении из URL поддерживаем alias products как вкладку товаров.
      const raw = String(tab || '').trim().toLowerCase()
      const next = typeof normalizeWorkTab === 'function'
        ? normalizeWorkTab(tab)
        : (TAB_KEYS.includes(String(tab)) ? String(tab) : 'deals')
      if (raw && raw !== next && typeof setActiveTab === 'function') {
        // Переписываем старые или битые ссылки на реальную вкладку, чтобы URL не вводил в заблуждение.
        setActiveTab(next)
        return
      }
      if (activeTab.value !== next) {
        activeTab.value = next
      }
    },
    { immediate: true }
  )

  watch(
    () => telegram.status,
    (status) => {
      if (status === 'ready') startTelegramPolling()
      else stopTelegramPolling()
    }
  )

  watch(
    () => telegram.activeChatId,
    () => {
      handleTelegramActiveChatChange()
    }
  )

  watch([() => editAccount.open], async ([showEdit]) => {
    if (showEdit && !domains.value.length) {
      await loadDomains()
    }
  })

  watch(
    () => editAccount.open,
    (open) => {
      if (open) {
        resetModalPos()
      }
    }
  )
}
