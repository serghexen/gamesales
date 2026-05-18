import { describe, it, expect, vi } from 'vitest'
import { reactive, ref } from 'vue'

import { useDeals } from '../useDeals.js'

describe('useDeals', () => {
  it('sorts deals by date ascending by default so newer deals are at the bottom', async () => {
    const dealFilters = reactive({
      search_q: '',
      type_q: '',
      customer_q: '',
      responsible_q: '',
      region_q: '',
      status_q: '',
      purchase_from: '',
      purchase_to: '',
    })
    const dealShowCompleted = ref(false)
    const apiGet = vi.fn().mockResolvedValue({
      items: [
        { deal_id: 2, purchase_at: '2026-03-02T10:00:00Z', created_at: '2026-03-02T10:00:00Z' },
        { deal_id: 1, purchase_at: '2026-03-01T10:00:00Z', created_at: '2026-03-01T10:00:00Z' },
      ],
      total: 2,
    })

    const h = useDeals({
      auth: { state: { token: 't' } },
      apiGet,
      mapApiError: (v) => v,
      resolveDealFlowStatusFilter: () => '',
      dealFilters,
      dealShowCompleted,
    })

    await h.loadDeals(1)

    expect(h.sortedDeals.value.map((item) => item.deal_id)).toEqual([1, 2])
  })

  it('ignores stale responses when requests overlap', async () => {
    const dealFilters = reactive({
      search_q: '',
      type_q: '',
      customer_q: '',
      responsible_q: '',
      region_q: '',
      status_q: '',
      purchase_from: '',
      purchase_to: '',
    })
    const dealShowCompleted = ref(false)
    let resolveFirst
    let resolveSecond
    const apiGet = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveFirst = resolve
          }),
      )
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveSecond = resolve
          }),
      )

    const h = useDeals({
      auth: { state: { token: 't' } },
      apiGet,
      mapApiError: (v) => v,
      resolveDealFlowStatusFilter: () => '',
      dealFilters,
      dealShowCompleted,
    })

    const firstRequest = h.loadDeals(1)
    const secondRequest = h.loadDeals(2)

    resolveSecond({
      items: [{ deal_id: 2, purchase_at: '2026-03-02T10:00:00Z', created_at: '2026-03-02T10:00:00Z' }],
      total: 1,
    })
    await secondRequest

    resolveFirst({
      items: [{ deal_id: 1, purchase_at: '2026-03-01T10:00:00Z', created_at: '2026-03-01T10:00:00Z' }],
      total: 1,
    })
    await firstRequest

    expect(h.dealItems.value.map((item) => item.deal_id)).toEqual([2])
    expect(h.dealPage.value).toBe(2)
  })

  it('reloads last valid page when current page goes out of range', async () => {
    const dealFilters = reactive({
      search_q: '',
      type_q: '',
      customer_q: '',
      responsible_q: '',
      region_q: '',
      status_q: '',
      purchase_from: '',
      purchase_to: '',
    })
    const dealShowCompleted = ref(false)
    const apiGet = vi
      .fn()
      .mockResolvedValueOnce({ items: [], total: 25 })
      .mockResolvedValueOnce({
        items: [{ deal_id: 7, purchase_at: '2026-03-02T10:00:00Z', created_at: '2026-03-02T10:00:00Z' }],
        total: 25,
      })

    const h = useDeals({
      auth: { state: { token: 't' } },
      apiGet,
      mapApiError: (v) => v,
      resolveDealFlowStatusFilter: () => '',
      dealFilters,
      dealShowCompleted,
    })

    await h.loadDeals(3)
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(apiGet).toHaveBeenCalledTimes(2)
    expect(h.dealPage.value).toBe(2)
    expect(h.dealItems.value.map((item) => item.deal_id)).toEqual([7])
  })
})
