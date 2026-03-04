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
})

