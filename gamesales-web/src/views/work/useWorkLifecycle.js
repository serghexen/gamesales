import { onBeforeUnmount, onMounted } from 'vue'

export function useWorkLifecycle({
  auth,
  router,
  route,
  canViewUsersSection,
  loadUsers,
  refreshManagersWorkload,
  cleanupManagersRealtimeRefresh,
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
    if (canViewUsersSection?.value) {
      await loadUsers()
    }
    startPresenceHeartbeatPolling()
    // Делаем первичную загрузку блока "Сделок в работе" сразу после входа на экран.
    await refreshManagersWorkload()
  })

  onBeforeUnmount(() => {
    stopGameImportStatusPolling()
    stopAccountImportStatusPolling()
    stopSlotImportStatusPolling()
    stopManagersWorkloadPolling()
    stopPresenceHeartbeatPolling()
    stopTelegramPolling()
    cleanupManagersRealtimeRefresh()
    revokeTelegramMediaUrls()
    window.removeEventListener('mousemove', onModalDrag)
    window.removeEventListener('mouseup', stopModalDrag)
  })
}
