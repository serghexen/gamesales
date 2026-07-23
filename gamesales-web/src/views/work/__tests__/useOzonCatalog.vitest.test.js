import { describe, expect, it, vi } from 'vitest'
import { reactive } from 'vue'

import { useOzonCatalog } from '../useOzonCatalog.js'

function createHarness() {
  const apiGet = vi.fn()
  const apiPost = vi.fn()
  const apiPut = vi.fn()
  const auth = { state: reactive({ token: 'ozon-token' }) }
  const catalog = useOzonCatalog({
    auth,
    apiGet,
    apiPost,
    apiPut,
    mapApiError: (value) => String(value || ''),
  })
  return { apiGet, apiPost, apiPut, catalog }
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

  it('opens selected card details from the local API snapshot', async () => {
    const { apiGet, apiPost, catalog } = createHarness()
    apiGet.mockResolvedValueOnce({
      external_product_id: 103,
      barcodes: ['4601234567890'],
      category_id: 123,
    })

    catalog.showOzonCatalog.value = true
    catalog.openOzonCatalogDetails({ external_product_id: 103 })
    await Promise.resolve()

    expect(catalog.showOzonCatalog.value).toBe(false)
    expect(catalog.showOzonCatalogDetails.value).toBe(true)
    expect(apiGet).toHaveBeenCalledWith('/marketplaces/ozon/catalog/103', { token: 'ozon-token' })
    expect(apiPost).not.toHaveBeenCalled()
    expect(catalog.ozonCatalogDetails.value).toMatchObject({ category_id: 123 })
  })

  it('publishes a manual limit only after opening the digital key settings', async () => {
    const { apiGet, apiPut, catalog } = createHarness()
    apiGet
      .mockResolvedValueOnce({ external_product_id: 103, offer_id: 'PS5-6', manual_stock_limit: 0 })
      .mockResolvedValueOnce({ items: [] })
    apiPut.mockResolvedValueOnce({ external_product_id: 103, offer_id: 'PS5-6', manual_stock_limit: 1, published_stock: 1, available_stock: 1 })

    catalog.ozonCatalogDetails.value = { external_product_id: 103 }
    catalog.openOzonDigitalSettings()
    await Promise.resolve()
    await Promise.resolve()
    catalog.ozonDigitalSettings.manual_stock_limit = 1
    await catalog.saveOzonDigitalSettings()

    expect(apiPut).toHaveBeenCalledWith(
      '/marketplaces/ozon/catalog/103/digital-settings',
      expect.objectContaining({ offer_id: 'PS5-6', manual_stock_limit: 1, auto_issue_enabled: false }),
      { token: 'ozon-token' },
    )
    expect(catalog.ozonDigitalSettings.published_stock).toBe(1)
    expect(catalog.ozonDigitalSettingsOk.value).toBe('В Ozon опубликован остаток: 1')
  })

  it('checks digital orders only for the card opened by the operator', async () => {
    const { apiGet, apiPost, catalog } = createHarness()
    apiPost.mockResolvedValueOnce({ imported_orders: 1 })
    apiGet
      .mockResolvedValueOnce({ external_product_id: 103, offer_id: 'PS5-6' })
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce({ external_product_id: 103, offer_id: 'PS5-6' })
      .mockResolvedValueOnce({ items: [{ id: 88, posting_number: '123-1' }] })

    catalog.ozonCatalogDetails.value = { external_product_id: 103 }
    catalog.openOzonDigitalSettings()
    await Promise.resolve()
    await Promise.resolve()
    await catalog.syncOzonDigitalOrders()

    expect(apiPost).toHaveBeenCalledWith('/marketplaces/ozon/catalog/103/digital-orders/sync', {}, { token: 'ozon-token' })
    expect(catalog.ozonDigitalOrders.value).toEqual([{ id: 88, posting_number: '123-1' }])
  })
})
