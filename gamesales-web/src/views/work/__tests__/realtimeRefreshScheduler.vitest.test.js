import { afterEach, describe, expect, it, vi } from 'vitest'

import { createRealtimeRefreshScheduler, isDealMutationRealtimeEvent } from '../realtimeRefreshScheduler.js'

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('realtimeRefreshScheduler', () => {
  it('detects only deal mutation realtime events', () => {
    expect(isDealMutationRealtimeEvent({ event: 'deal_created' })).toBe(true)
    expect(isDealMutationRealtimeEvent({ event: 'deal_updated' })).toBe(true)
    expect(isDealMutationRealtimeEvent({ event: 'deal_deleted' })).toBe(true)
    expect(isDealMutationRealtimeEvent({ event: 'connected' })).toBe(false)
    expect(isDealMutationRealtimeEvent({ event: 'deal_edit_started' })).toBe(false)
  })

  it('debounces frequent refresh events into one call', () => {
    vi.useFakeTimers()
    vi.setSystemTime(0)
    const refresh = vi.fn()
    const scheduler = createRealtimeRefreshScheduler(refresh, 1000)

    scheduler.schedule()
    scheduler.schedule()
    expect(refresh).toHaveBeenCalledTimes(0)

    vi.advanceTimersByTime(1000)
    expect(refresh).toHaveBeenCalledTimes(1)

    scheduler.schedule()
    scheduler.schedule()
    vi.advanceTimersByTime(999)
    expect(refresh).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(1)
    expect(refresh).toHaveBeenCalledTimes(2)
  })

  it('cleans pending refresh timer', () => {
    vi.useFakeTimers()
    vi.setSystemTime(0)
    const refresh = vi.fn()
    const scheduler = createRealtimeRefreshScheduler(refresh, 1000)

    scheduler.schedule()
    scheduler.cleanup()
    vi.advanceTimersByTime(1000)

    expect(refresh).not.toHaveBeenCalled()
  })
})
