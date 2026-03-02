import { onBeforeUnmount, onMounted } from 'vue'

export function useWorkLifecycle({
  auth,
  router,
  route,
  isAdmin,
  loadUsers,
  startPresenceHeartbeatPolling,
  stopGameImportStatusPolling,
  stopAccountImportStatusPolling,
  stopSlotImportStatusPolling,
  stopManagersWorkloadPolling,
  stopPresenceHeartbeatPolling,
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
    startPresenceHeartbeatPolling()
  })

  onBeforeUnmount(() => {
    stopGameImportStatusPolling()
    stopAccountImportStatusPolling()
    stopSlotImportStatusPolling()
    stopManagersWorkloadPolling()
    stopPresenceHeartbeatPolling()
    stopTelegramPolling()
    revokeTelegramMediaUrls()
    window.removeEventListener('mousemove', onModalDrag)
    window.removeEventListener('mouseup', stopModalDrag)
  })
}
