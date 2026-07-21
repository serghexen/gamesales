import { describe, expect, it, vi } from 'vitest'
import { reactive } from 'vue'

import { useOzonCatalog } from '../useOzonCatalog.js'

function createHarness() {
  const apiGet = vi.fn()
  const apiPost = vi.fn()
  const auth = { state: reactive({ token: 'ozon-token' }) }
  const catalog = useOzonCatalog({
    auth,
    apiGet,
    apiPost,
    mapApiError: (value) => String(value || ''),
  })
  return { apiGet, apiPost, catalog }
}

describe('useOzonCatalog', () => {
  it('opens the local Ozon snapshot without starting a synchronization', async () => {
    const { apiGet, apiPost, catalog } = createHarness()
    apiGet.mockResolvedValueOnce({ items: [{ external_product_id: 101, offer_id: 'steam-1000' }] })

    catalog.openOzonCatalog()
    await Promise.resolve()

    expect(catalog.showOzonCatalog.value).toBe(true)
    expect(apiGet).toHaveBeenCalledWith('/marketplaces/ozon/catalog', { token: 'ozon-token' })
    expect(apiPost).not.toHaveBeenCalled()
    expect(catalog.ozonCatalogItems.value).toEqual([{ external_product_id: 101, offer_id: 'steam-1000' }])
  })

  it('synchronizes first and then refreshes the local Ozon snapshot', async () => {
    const { apiGet, apiPost, catalog } = createHarness()
    apiPost.mockResolvedValueOnce({ synced_items: 2 })
    apiGet.mockResolvedValueOnce({ items: [{ external_product_id: 102, offer_id: 'psn-500' }] })

    await catalog.syncOzonCatalog()

    expect(apiPost).toHaveBeenCalledWith('/marketplaces/ozon/catalog/sync', {}, { token: 'ozon-token' })
    expect(apiGet).toHaveBeenCalledWith('/marketplaces/ozon/catalog', { token: 'ozon-token' })
    expect(catalog.ozonCatalogOk.value).toBe('Синхронизировано карточек: 2')
    expect(catalog.ozonCatalogItems.value).toEqual([{ external_product_id: 102, offer_id: 'psn-500' }])
  })
})
