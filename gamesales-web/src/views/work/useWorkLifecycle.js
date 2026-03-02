import { onBeforeUnmount, onMounted } from 'vue'

export function useWorkLifecycle({
  auth,
  router,
  route,
  isAdmin,
  loadUsers,
  stopGameImportStatusPolling,
  stopAccountImportStatusPolling,
  stopSlotImportStatusPolling,
  stopManagersWorkloadPolling,
  stopTelegramPolling,
  revokeTelegramMediaUrls,
  onModalDrag,
  stopModalDrag,
}) {
  onMounted(async () => {
    await auth.loadMe()
    if (!auth.isAuthed()) {
      router.replace({ name: 'login', query: { next: route.fullPath } })
      return
    }
    if (isAdmin.value) {
      await loadUsers()
    }
  })

  onBeforeUnmount(() => {
    stopGameImportStatusPolling()
    stopAccountImportStatusPolling()
    stopSlotImportStatusPolling()
    stopManagersWorkloadPolling()
    stopTelegramPolling()
    revokeTelegramMediaUrls()
    window.removeEventListener('mousemove', onModalDrag)
    window.removeEventListener('mouseup', stopModalDrag)
  })
}
