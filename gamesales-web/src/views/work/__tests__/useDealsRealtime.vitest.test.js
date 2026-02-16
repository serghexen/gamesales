import { describe, it, expect } from 'vitest'

import { buildDealsWsUrl, applyDealEditingRealtimeEvent } from '../useDealsRealtime.js'

describe('useDealsRealtime', () => {
  it('buildDealsWsUrl converts absolute http api base to ws url', () => {
    const url = buildDealsWsUrl('http://localhost:8000', 'token-1')
    expect(url).toBe('ws://localhost:8000/ws/deals?token=token-1')
  })

  it('buildDealsWsUrl keeps https as wss and adds query token', () => {
    const url = buildDealsWsUrl('https://example.com/api', 'abc xyz')
    expect(url).toBe('wss://example.com/api/ws/deals?token=abc%20xyz')
  })

  it('buildDealsWsUrl builds same-origin url for relative api base', () => {
    const url = buildDealsWsUrl('/api', 'tok', { protocol: 'https:', host: 'demo.local' })
    expect(url).toBe('wss://demo.local/api/ws/deals?token=tok')
  })

  it('buildDealsWsUrl returns empty string when token is missing', () => {
    expect(buildDealsWsUrl('/api', '')).toBe('')
  })

  it('applyDealEditingRealtimeEvent hydrates state from connected payload', () => {
    const next = applyDealEditingRealtimeEvent(
      {},
      {
        event: 'connected',
        editing: [
          { deal_id: 10, actor: 'manager', changed_at: '2026-02-16T20:00:00Z' },
          { deal_id: 0, actor: 'invalid' },
        ],
      },
    )
    expect(next).toEqual({
      10: { actor: 'manager', changedAt: '2026-02-16T20:00:00Z' },
    })
  })

  it('applyDealEditingRealtimeEvent applies start/stop messages', () => {
    const started = applyDealEditingRealtimeEvent({}, { event: 'deal_edit_started', deal_id: 12, actor: 'admin' })
    expect(started[12]).toEqual({ actor: 'admin', changedAt: '' })

    const stopped = applyDealEditingRealtimeEvent(started, { event: 'deal_edit_stopped', deal_id: 12 })
    expect(stopped[12]).toBeUndefined()
  })
})
