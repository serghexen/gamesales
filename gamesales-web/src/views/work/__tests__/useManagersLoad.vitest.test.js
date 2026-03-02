import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

import { useManagersLoad } from '../useManagersLoad.js'

describe('useManagersLoad', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('loads managers workload and maps payload', async () => {
    const apiGet = vi.fn().mockResolvedValue({
      timezone: 'Europe/Moscow',
      date: '2026-03-02',
      online_count: 2,
      items: [{ username: 'm1', name: 'Менеджер 1', pending_count: 3 }],
    })
    const apiPost = vi.fn().mockResolvedValue({ ok: true })
    const h = useManagersLoad({
      auth: { state: { token: 'token-1' } },
      apiGet,
      apiPost,
      mapApiError: (msg) => msg || 'err',
    })

    await h.refreshManagersWorkload()

    expect(apiPost).toHaveBeenCalledWith('/presence/heartbeat', {}, { token: 'token-1' })
    expect(apiGet).toHaveBeenCalledWith('/dashboard/managers-load', { token: 'token-1' })
    expect(h.managersLoadOnlineCount.value).toBe(2)
    expect(h.managersLoadItems.value).toEqual([{ username: 'm1', name: 'Менеджер 1', pending_count: 3 }])
  })

  it('starts and stops polling without duplicate timers', async () => {
    const apiGet = vi.fn().mockResolvedValue({ online_count: 0, items: [] })
    const apiPost = vi.fn().mockResolvedValue({ ok: true })
    const h = useManagersLoad({
      auth: { state: { token: 'token-1' } },
      apiGet,
      apiPost,
      mapApiError: (msg) => msg || 'err',
    })

    h.startManagersWorkloadPolling()
    h.startManagersWorkloadPolling()
    await vi.runOnlyPendingTimersAsync()
    h.stopManagersWorkloadPolling()
    await vi.advanceTimersByTimeAsync(31_000)

    expect(apiPost).toHaveBeenCalled()
    expect(apiGet).toHaveBeenCalled()
  })

  it('sends presence heartbeat every 5 seconds', async () => {
    const apiGet = vi.fn().mockResolvedValue({ online_count: 0, items: [] })
    const apiPost = vi.fn().mockResolvedValue({ ok: true })
    const h = useManagersLoad({
      auth: { state: { token: 'token-1' } },
      apiGet,
      apiPost,
      mapApiError: (msg) => msg || 'err',
    })

    h.startPresenceHeartbeatPolling()
    await Promise.resolve()
    expect(apiPost).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(5_000)
    expect(apiPost).toHaveBeenCalledTimes(2)

    await vi.advanceTimersByTimeAsync(5_000)
    expect(apiPost).toHaveBeenCalledTimes(3)

    h.stopPresenceHeartbeatPolling()
  })
})
