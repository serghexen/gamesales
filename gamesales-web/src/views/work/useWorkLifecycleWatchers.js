import { watch } from 'vue'

export function useWorkLifecycleWatchers({
  route,
  TAB_KEYS,
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
      const next = TAB_KEYS.includes(String(tab)) ? String(tab) : 'deals'
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
