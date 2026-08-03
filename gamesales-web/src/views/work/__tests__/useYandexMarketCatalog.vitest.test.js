import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import { useYandexMarketCatalog } from '../useYandexMarketCatalog.js'
import WorkYandexMarketCatalogModal from '../sections/WorkYandexMarketCatalogModal.vue'
import WorkYandexMarketCatalogDetailsModal from '../sections/WorkYandexMarketCatalogDetailsModal.vue'
import WorkYandexMarketDigitalSettingsModal from '../sections/WorkYandexMarketDigitalSettingsModal.vue'
import WorkMarketplaceKeyPoolModal from '../sections/WorkMarketplaceKeyPoolModal.vue'
import WorkMarketplaceKeyPoolPanel from '../sections/WorkMarketplaceKeyPoolPanel.vue'
import { useMarketplaceKeyPool } from '../useMarketplaceKeyPool.js'

describe('useYandexMarketCatalog', () => {
  it('syncs the catalog and then reloads its local snapshot', async () => {
    const apiPost = vi.fn().mockResolvedValue({ synced_items: 2 })
    const apiGet = vi.fn().mockResolvedValue({ items: [{ offer_id: 'PSN-500' }] })
    const instance = useYandexMarketCatalog({
      auth: { state: { token: 'market-token' } }, apiGet, apiPost, apiPut: vi.fn(), mapApiError: vi.fn(), requestDealConfirm: vi.fn(),
    })

    await instance.syncYandexMarketCatalog()

    expect(apiPost).toHaveBeenCalledWith('/marketplaces/yandex/catalog/sync?store_code=test', {}, { token: 'market-token' })
    expect(apiGet).toHaveBeenCalledWith('/marketplaces/yandex/catalog?store_code=test', { token: 'market-token' })
    expect(instance.yandexMarketCatalogItems.value).toEqual([{ offer_id: 'PSN-500' }])
  })

  it('opens card details and reads the market stock without a PUT request', async () => {
    const apiGet = vi.fn().mockImplementation((url) => {
      if (url.includes('/stock-settings')) return Promise.resolve({ offer_id: 'PSN-500', market_available_stock: 2 })
      return Promise.resolve({ offer_id: 'PSN-500', title: 'PSN 500' })
    })
    const apiPut = vi.fn()
    const instance = useYandexMarketCatalog({
      auth: { state: { token: 'market-token' } }, apiGet, apiPost: vi.fn(), apiPut, mapApiError: vi.fn(), requestDealConfirm: vi.fn(),
    })

    await instance.openYandexMarketCatalogDetails({ offer_id: 'PSN-500' })

    expect(instance.showYandexMarketCatalogDetails.value).toBe(true)
    expect(apiGet).toHaveBeenCalledWith('/marketplaces/yandex/catalog/PSN-500?store_code=test', { token: 'market-token' })
    expect(apiGet).toHaveBeenCalledWith('/marketplaces/yandex/catalog/PSN-500/stock-settings?store_code=test', { token: 'market-token' })
    expect(instance.yandexMarketStockSettings.market_available_stock).toBe(2)
    expect(instance.yandexMarketSelectedOfferId.value).toBe('PSN-500')
    expect(apiPut).not.toHaveBeenCalled()
  })

  it('saves the buyer instruction for the selected SKU before a digital delivery', async () => {
    const apiPut = vi.fn().mockResolvedValue({ offer_id: 'PSN-500', activation_instruction: 'Активируйте код в магазине.' })
    const instance = useYandexMarketCatalog({
      auth: { state: { token: 'market-token' } }, apiGet: vi.fn(), apiPost: vi.fn(), apiPut, mapApiError: vi.fn(), requestDealConfirm: vi.fn(),
    })
    instance.yandexMarketSelectedOfferId.value = 'PSN-500'
    instance.yandexMarketStockSettings.activation_instruction = 'Активируйте код в магазине.'

    await instance.saveYandexMarketStockSettings()

    expect(apiPut).toHaveBeenCalledWith(
      '/marketplaces/yandex/catalog/PSN-500/stock-settings?store_code=test',
      expect.objectContaining({ manual_stock_limit: 0, activation_instruction: 'Активируйте код в магазине.', auto_issue_enabled: false, pool_issue_enabled: false }),
      { token: 'market-token' },
    )
  })

  it('opens the key screen without saving settings or sending anything to Market', async () => {
    const instance = useYandexMarketCatalog({
      auth: { state: { token: 'market-token' } }, apiGet: vi.fn(), apiPost: vi.fn(), apiPut: vi.fn(), mapApiError: vi.fn(), requestDealConfirm: vi.fn(),
    })
    instance.yandexMarketCatalogDetails.value = { offer_id: 'PSN-500' }

    instance.openYandexMarketDigitalSettings()

    expect(instance.showYandexMarketDigitalSettings.value).toBe(true)
    expect(instance.showYandexMarketCatalogDetails.value).toBe(false)
    instance.closeYandexMarketDigitalSettings()
    expect(instance.showYandexMarketCatalogDetails.value).toBe(true)
  })

  it('issues a fake order only through the local sandbox endpoints', async () => {
    const apiPost = vi.fn().mockResolvedValue({ status: 'locally_issued' })
    const instance = useYandexMarketCatalog({
      auth: { state: { token: 'market-token' } }, apiGet: vi.fn(), apiPost, apiPut: vi.fn(), mapApiError: vi.fn(), requestDealConfirm: vi.fn(),
    })
    const order = { order_id: 501, item_id: 99, offer_id: 'PSN-500', quantity: 2 }
    instance.yandexMarketOrders.value = [order]

    await instance.deliverYandexMarketSandboxOrder(order, ['AAAA-1111', 'BBBB-2222'])
    await instance.issueYandexMarketSandboxOrderFromPool({ order_id: 502, item_id: 100, offer_id: 'PSN-500', quantity: 1 })

    expect(apiPost).toHaveBeenCalledWith('/marketplaces/yandex/sandbox/orders/501/items/99/deliver?store_code=test', { codes: ['AAAA-1111', 'BBBB-2222'] }, { token: 'market-token' })
    expect(apiPost).toHaveBeenCalledWith('/marketplaces/yandex/sandbox/orders/502/items/100/issue-from-pool?store_code=test', {}, { token: 'market-token' })
    expect(instance.yandexMarketOrders.value[0].sandbox_delivery_status).toBe('locally_issued')
  })

  it('sends a locally issued key to test Market only after confirmation', async () => {
    const apiPost = vi.fn().mockResolvedValue({ status: 'market_submitted' })
    const requestDealConfirm = vi.fn().mockResolvedValue(true)
    const instance = useYandexMarketCatalog({
      auth: { state: { token: 'market-token' } }, apiGet: vi.fn(), apiPost, apiPut: vi.fn(), mapApiError: vi.fn(), requestDealConfirm,
    })
    const order = { order_id: 501, item_id: 99, sandbox_delivery_status: 'locally_issued' }
    instance.yandexMarketOrders.value = [order]

    await instance.sendYandexMarketSandboxOrderToMarket(order)

    expect(requestDealConfirm).toHaveBeenCalledWith(expect.objectContaining({ title: 'Отправить ключ в test Маркет?' }))
    expect(apiPost).toHaveBeenCalledWith('/marketplaces/yandex/sandbox/orders/501/items/99/send-to-market?store_code=test', {}, { token: 'market-token' })
    expect(instance.yandexMarketOrders.value[0].sandbox_delivery_status).toBe('market_submitted')
  })
})

describe('WorkYandexMarketCatalogModal', () => {
  it('keeps the search and splits a long catalog into pages with all working columns', async () => {
    const updateYandexMarketCatalogArchive = vi.fn()
    const selectYandexMarketStore = vi.fn()
    const yandexMarketCatalogItems = Array.from({ length: 21 }, (_, index) => ({
      offer_id: `SKU-${index + 1}`,
      title: `Игра ${index + 1}`,
      market_sku: String(1000 + index),
      category_name: 'Игры',
      price: '1999',
      currency_code: 'RUB',
      card_status: 'HAS_CARD_CAN_UPDATE',
      archived: false,
    }))
    const wrapper = mount(WorkYandexMarketCatalogModal, {
      props: {
        showYandexMarketCatalog: true, closeYandexMarketCatalog: vi.fn(), syncYandexMarketCatalog: vi.fn(), updateYandexMarketCatalogArchive, openYandexMarketCatalogDetails: vi.fn(), yandexMarketCatalogItems, yandexMarketCatalogLoading: false, yandexMarketCatalogSyncing: false, yandexMarketStoreCodes: ['asat', 'joycards'], yandexMarketStoreCode: 'asat', selectYandexMarketStore,
      },
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.get('input[aria-label="Поиск по названию или SKU карточки Яндекс Маркета"]').exists()).toBe(true)
    await wrapper.get('select').setValue('joycards')
    expect(selectYandexMarketStore).toHaveBeenCalledWith('joycards')
    expect(wrapper.findAll('.yandex-catalog-modal__table th').map((cell) => cell.text())).toEqual(['Карточка Яндекс Маркета', 'Действие'])
    expect(wrapper.findAll('.yandex-catalog-modal__table tbody tr')).toHaveLength(20)
    expect(wrapper.text()).toContain('Страница 1 из 2')
    expect(wrapper.get('button.yandex-catalog-modal__open-btn').text()).toBe('В архив')
    await wrapper.get('button.yandex-catalog-modal__open-btn').trigger('click')
    expect(updateYandexMarketCatalogArchive).toHaveBeenCalledWith(expect.objectContaining({ offer_id: 'SKU-1' }), true)

    await wrapper.get('[aria-label="Следующая страница каталога Яндекс Маркета"]').trigger('click')
    expect(wrapper.text()).toContain('SKU-21')

    await wrapper.get('input[aria-label="Поиск по названию или SKU карточки Яндекс Маркета"]').setValue('SKU-21')
    expect(wrapper.findAll('.yandex-catalog-modal__table tbody tr')).toHaveLength(1)
    expect(wrapper.text()).toContain('Игра 21')
  })
})

describe('WorkYandexMarketCatalogDetailsModal', () => {
  it('publishes stock explicitly and keeps delivery settings out of the stock form', async () => {
    const saveYandexMarketStockSettings = vi.fn()
    const wrapper = mount(WorkYandexMarketCatalogDetailsModal, {
      props: {
        showYandexMarketCatalogDetails: true, closeYandexMarketCatalogDetails: vi.fn(), openYandexMarketDigitalSettings: vi.fn(), yandexMarketSandboxMode: false, yandexMarketCatalogDetailsLoading: false, yandexMarketCatalogDetails: { offer_id: 'PSN-500', market_sku: '123', title: 'PSN 500', category_name: 'Игровые карты', price: '500', currency_code: 'RUB', card_status: 'HAS_CARD_CAN_UPDATE' }, yandexMarketStockSettings: { manual_stock_limit: 4, market_available_stock: 4, market_stock_updated_at: '2026-07-25T11:33:00Z', activation_instruction: 'Активируйте ключ здесь.', auto_issue_enabled: true, pool_issue_enabled: true }, yandexMarketStockSettingsSaving: false, saveYandexMarketStockSettings, yandexMarketOrders: [{ order_id: 501, item_id: 99, offer_id: 'PSN-500', quantity: 2, status: 'PROCESSING', created_at: '2026-07-25T12:00:00Z' }], yandexMarketOrdersLoading: false, yandexMarketOrdersSyncing: false, yandexMarketOrdersLastSyncedAt: '2026-07-25T12:01:00Z', loadYandexMarketOrders: vi.fn(), syncYandexMarketOrders: vi.fn(),
      },
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.text()).toContain('Параметры карточки Яндекс Маркета')
    expect(wrapper.findAll('.yandex-catalog-details-modal__grid dt').map((cell) => cell.text())).toEqual(['Артикул продавца', 'SKU', 'Цена', 'Остаток'])
    expect(wrapper.findAll('.yandex-catalog-details-modal__grid dd').map((cell) => cell.text())).toEqual(['123', 'PSN-500', '500 RUB', '4'])
    expect(wrapper.text()).toContain('4')
    expect(wrapper.findAll('.yandex-catalog-details-modal__work-block-toggle')).toHaveLength(2)
    await wrapper.findAll('.yandex-catalog-details-modal__work-block-toggle').at(0).trigger('click')
    expect(wrapper.get('input[aria-label="Остаток для публикации на Маркете"]').element.value).toBe('4')
    await wrapper.get('button[title="Опубликовать указанный остаток в Яндекс Маркете"]').trigger('click')
    expect(saveYandexMarketStockSettings).toHaveBeenCalledWith({ publishStock: true })
    expect(wrapper.find('input[aria-label="Автовыдача Яндекс Маркета"]').exists()).toBe(false)
    expect(wrapper.find('input[aria-label="Выдача из ручного пула Яндекс Маркета"]').exists()).toBe(false)
    expect(wrapper.get('textarea[aria-label="Инструкция покупателю"]').element.value).toBe('Активируйте ключ здесь.')
    const saveSettingsButton = wrapper.get('button[aria-label="Сохранить настройки карточки"]')
    expect(saveSettingsButton.attributes('title')).toBe('Сохранить инструкцию и настройки выдачи')
    await saveSettingsButton.trigger('click')
    expect(saveYandexMarketStockSettings).toHaveBeenLastCalledWith()
    await wrapper.findAll('.yandex-catalog-details-modal__work-block-toggle').at(1).trigger('click')
    expect(wrapper.text()).toContain('Заказ 501')
    expect(wrapper.text()).toContain('В обработке')
  })
})

describe('WorkYandexMarketDigitalSettingsModal', () => {
  it('keeps auto-issue disabled but lets an operator issue one fake order locally', async () => {
    const deliverYandexMarketSandboxOrder = vi.fn().mockResolvedValue({ ok: true })
    const issueYandexMarketSandboxOrderFromPool = vi.fn().mockResolvedValue({ ok: true })
    const wrapper = mount(WorkYandexMarketDigitalSettingsModal, {
      props: {
        showYandexMarketDigitalSettings: true, closeYandexMarketDigitalSettings: vi.fn(), yandexMarketOfferId: 'PSN-500', openMarketplaceKeyPool: vi.fn(),
        yandexMarketSandboxMode: true,
        yandexMarketOrders: [{ order_id: 501, item_id: 99, offer_id: 'PSN-500', quantity: 2, status: 'PROCESSING' }],
        deliverYandexMarketSandboxOrder, issueYandexMarketSandboxOrderFromPool,
      },
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.text()).toContain('Ключи Яндекс Маркета')
    expect(wrapper.text()).toContain('Автовыдача')
    expect(wrapper.text()).toContain('Локальная выдача fake-заказов')
    expect(wrapper.get('input[aria-label="Автовыдача пока не подключена"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('input[aria-label="Автоматическая выдача из ручного пула выключена"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('button[aria-label="Сохранить настройки"]').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Список ключей')
    expect(wrapper.find('.ozon-key-settings__block').classes()).not.toContain('is-open')
    await wrapper.get('.ozon-key-settings__block .ozon-catalog-details-modal__work-block-toggle').trigger('click')
    expect(wrapper.find('.ozon-digital-modal__supplier').text()).toContain('Товар')
    expect(wrapper.find('.ozon-digital-modal__supplier').text()).not.toContain('Номинал')
    await wrapper.get('textarea[aria-label="Ручные ключи для fake-заказа 501"]').setValue('AAAA-1111\nBBBB-2222')
    await wrapper.get('button.btn--primary').trigger('click')
    expect(deliverYandexMarketSandboxOrder).toHaveBeenCalledWith(expect.objectContaining({ order_id: 501 }), ['AAAA-1111', 'BBBB-2222'])
    await wrapper.get('button.btn--secondary').trigger('click')
    expect(issueYandexMarketSandboxOrderFromPool).toHaveBeenCalledWith(expect.objectContaining({ item_id: 99 }))
  })

  it('keeps production issue settings and the key pool in the separate keys modal', async () => {
    const saveYandexMarketStockSettings = vi.fn()
    const loadMarketplaceKeyPoolFor = vi.fn()
    const deliverYandexMarketProductionOrder = vi.fn().mockResolvedValue({ ok: true })
    const issueYandexMarketProductionOrderFromPool = vi.fn().mockResolvedValue({ ok: true })
    const settings = { interhub_service_id: 25, interhub_nominal_id: '250', auto_issue_enabled: false, interhub_enabled: false, pool_issue_enabled: true }
    const wrapper = mount(WorkYandexMarketDigitalSettingsModal, {
      props: {
        showYandexMarketDigitalSettings: true,
        closeYandexMarketDigitalSettings: vi.fn(),
        yandexMarketSandboxMode: false,
        yandexMarketOfferId: 'PSN-500',
        yandexMarketTitle: 'PSN 500',
        yandexMarketStockSettings: settings,
        saveYandexMarketStockSettings,
        openMarketplaceKeyPool: vi.fn(),
        loadMarketplaceKeyPoolFor,
        yandexMarketInterhubServices: [{ service_id: 25, title: 'PlayStation Turkey', category: 'Турция', fields: [{ name: 'nominal', value_list: [{ id: 250, title: '250 TRY' }] }] }],
        yandexMarketProductionManualOrders: [{ id: 25, order_id: 501, offer_id: 'PSN-500', item_name: 'PSN 500', required_qty: 1, collected_qty: 0, status: 'manual_required' }],
        deliverYandexMarketProductionOrder,
        issueYandexMarketProductionOrderFromPool,
      },
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.text()).toContain('Ключи Яндекс Маркета')
    expect(wrapper.text()).not.toContain('Локальная выдача fake-заказов')
    expect(wrapper.text()).toContain('Ручная выдача')
    expect(wrapper.get('input[aria-label="Автовыдача через Interhub Яндекс Маркета"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.get('input[aria-label="Выдача из ручного пула Яндекс Маркета"]').element.checked).toBe(true)
    expect(loadMarketplaceKeyPoolFor).toHaveBeenCalledWith(expect.objectContaining({ marketplace: 'yandex_market', productKey: 'PSN-500', storeCode: 'asat' }))
    await wrapper.get('.ozon-key-settings__block .ozon-catalog-details-modal__work-block-toggle').trigger('click')
    expect(wrapper.get('input[role="combobox"]').element.value).toContain('PlayStation Turkey')
    await wrapper.get('button[aria-label="Показать список товаров Interhub"]').trigger('click')
    expect(wrapper.get('#yandex-interhub-service-results').text()).toContain('PlayStation Turkey')
    expect(wrapper.get('select[aria-label="Номинал Interhub Яндекс Маркета"]').element.value).toBe('250')
    await wrapper.get('input[aria-label="Автовыдача через Interhub Яндекс Маркета"]').setValue(true)
    expect(settings).toMatchObject({ auto_issue_enabled: true, interhub_enabled: true, pool_issue_enabled: true })
    await wrapper.get('button[aria-label="Сохранить настройки"]').trigger('click')
    expect(saveYandexMarketStockSettings).toHaveBeenCalledTimes(1)
    await wrapper.get('textarea[aria-label="Ручные ключи для заказа Яндекс Маркета 501"]').setValue('AAAA-1111')
    await wrapper.get('button.btn--primary').trigger('click')
    expect(deliverYandexMarketProductionOrder).toHaveBeenCalledWith(expect.objectContaining({ id: 25 }), 'AAAA-1111')
    await wrapper.get('button.btn--secondary').trigger('click')
    expect(issueYandexMarketProductionOrderFromPool).toHaveBeenCalledWith(expect.objectContaining({ id: 25 }))
  })
})

describe('useMarketplaceKeyPool', () => {
  it('loads one isolated pool and adds keys only to local storage', async () => {
    const apiGet = vi.fn().mockResolvedValue({ marketplace: 'yandex_market', product_key: 'PSN-500', free_count: 2, total: 2, page: 1, page_size: 20, items: [{ id: 1, masked_code: '••••1234', status: 'free' }] })
    const apiPost = vi.fn().mockResolvedValue({ added: 2, duplicates: 0 })
    const pool = useMarketplaceKeyPool({ auth: { state: { token: 'market-token' } }, apiGet, apiPost, apiDelete: vi.fn(), mapApiError: vi.fn(), requestDealConfirm: vi.fn() })

    await pool.openMarketplaceKeyPool({ marketplace: 'yandex_market', productKey: 'PSN-500', productTitle: 'PSN 500' })
    const result = await pool.addMarketplaceKeyPoolKeys('AAAA-1111\nBBBB-2222', '2026-08-25')

    expect(pool.marketplaceKeyPool.free_count).toBe(2)
    expect(pool.marketplaceKeyPool.items[0].masked_code).toBe('••••1234')
    expect(apiPost).toHaveBeenCalledWith('/marketplaces/key-pools/yandex_market/PSN-500/keys?store_code=asat', { codes: ['AAAA-1111', 'BBBB-2222'], expires_at: '2026-08-25' }, { token: 'market-token' })
    expect(result.ok).toBe(true)
  })

  it('does not show the Excel error when the key-pool API is unavailable', async () => {
    const pool = useMarketplaceKeyPool({ auth: { state: { token: 'market-token' } }, apiGet: vi.fn().mockRejectedValue(new Error('Load failed')), apiPost: vi.fn(), apiDelete: vi.fn(), mapApiError: vi.fn(() => 'Не удалось отправить файл. Проверьте формат (.xlsx/.xls) и доступность API'), requestDealConfirm: vi.fn() })

    await pool.openMarketplaceKeyPool({ marketplace: 'ozon', productKey: '103' })

    expect(pool.marketplaceKeyPoolError.value).toContain('API пула ключей')
    expect(pool.marketplaceKeyPoolError.value).not.toContain('Excel')
  })

  it('asks for a short delete confirmation before clearing free pool keys', async () => {
    const requestDealConfirm = vi.fn().mockResolvedValue(false)
    const pool = useMarketplaceKeyPool({ auth: { state: { token: 'market-token' } }, apiGet: vi.fn(), apiPost: vi.fn(), apiDelete: vi.fn(), mapApiError: vi.fn(), requestDealConfirm })
    Object.assign(pool.marketplaceKeyPool, { marketplace: 'ozon', product_key: '103', store_code: 'asat', free_count: 3 })

    await pool.deleteAllFreeMarketplaceKeyPoolKeys()

    expect(requestDealConfirm).toHaveBeenCalledWith({
      title: 'Удалить все свободные ключи?',
      message: 'Будет удалено свободных ключей: 3. Выданные и зарезервированные ключи останутся в истории.',
      confirmText: 'Удалить',
      cancelText: 'Отмена',
    })
  })

  it('reveals a selected issued key without changing its status or the rest of the pool', async () => {
    const apiPost = vi.fn().mockResolvedValue({ id: 8, code: 'SENT-CODE-1234' })
    const pool = useMarketplaceKeyPool({ auth: { state: { token: 'market-token' } }, apiGet: vi.fn(), apiPost, apiDelete: vi.fn(), mapApiError: vi.fn(), requestDealConfirm: vi.fn() })
    pool.marketplaceKeyPool.marketplace = 'ozon'
    pool.marketplaceKeyPool.product_key = '103'
    pool.marketplaceKeyPool.store_code = 'asat'
    const issuedKey = { id: 8, status: 'delivered', masked_code: '••••1234' }

    await pool.revealMarketplaceKeyPoolKey(issuedKey)

    expect(apiPost).toHaveBeenCalledWith('/marketplaces/key-pools/ozon/103/keys/8/reveal?store_code=asat', {}, { token: 'market-token' })
    expect(pool.marketplaceKeyPoolRevealedCode(issuedKey)).toBe('SENT-CODE-1234')
    expect(issuedKey.status).toBe('delivered')
  })
})

describe('WorkMarketplaceKeyPoolModal', () => {
  it('keeps the overlay focused only on adding keys', () => {
    const wrapper = mount(WorkMarketplaceKeyPoolModal, {
      props: { showMarketplaceKeyPool: true, closeMarketplaceKeyPool: vi.fn(), marketplaceKeyPool: { marketplace: 'ozon', product_key: '103', product_title: 'PSN 500', free_count: 1, reserved_count: 0, delivered_count: 2, expired_count: 0, total: 3, page: 1, page_size: 20, items: [{ id: 1, masked_code: '••••1234', status: 'free' }] }, marketplaceKeyPoolLoading: false, marketplaceKeyPoolSaving: false, marketplaceKeyPoolTotalPages: 1, marketplaceKeyPoolRevealingId: 0, marketplaceKeyPoolRevealedCode: vi.fn(() => ''), loadMarketplaceKeyPool: vi.fn(), addMarketplaceKeyPoolKeys: vi.fn(), revealMarketplaceKeyPoolKey: vi.fn(), deleteMarketplaceKeyPoolKey: vi.fn(), deleteAllFreeMarketplaceKeyPoolKeys: vi.fn() },
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.text()).toContain('Добавить ключи · Ozon')
    expect(wrapper.text()).not.toContain('Ключи для пула')
    expect(wrapper.get('button[aria-label="Сохранить ключи"]').classes()).toContain('deal-create-action-btn--save')
    expect(wrapper.get('textarea').attributes('aria-label')).toBe('Ключи')
    expect(wrapper.text()).not.toContain('••••1234')
    expect(wrapper.text()).not.toContain('Свободен')
  })

  it('adds a month or a year to the selected key expiration date', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 6, 25, 12, 0, 0))
    const wrapper = mount(WorkMarketplaceKeyPoolModal, {
      props: { showMarketplaceKeyPool: true, closeMarketplaceKeyPool: vi.fn(), marketplaceKeyPool: { marketplace: 'ozon', product_key: '103' }, marketplaceKeyPoolLoading: false, marketplaceKeyPoolSaving: false, addMarketplaceKeyPoolKeys: vi.fn() },
      global: { stubs: { teleport: true } },
    })

    await wrapper.get('button[aria-label="Добавить месяц к дате"]').trigger('click')
    expect(wrapper.get('input[type="date"]').element.value).toBe('2026-08-25')
    await wrapper.get('button[aria-label="Добавить год к дате"]').trigger('click')
    expect(wrapper.get('input[type="date"]').element.value).toBe('2027-08-25')
    vi.useRealTimers()
  })

  it('shows the hamster while the keys are being saved', () => {
    const wrapper = mount(WorkMarketplaceKeyPoolModal, {
      props: { showMarketplaceKeyPool: true, closeMarketplaceKeyPool: vi.fn(), marketplaceKeyPool: { marketplace: 'ozon', product_key: '103' }, marketplaceKeyPoolLoading: false, marketplaceKeyPoolSaving: true, addMarketplaceKeyPoolKeys: vi.fn() },
      global: { stubs: { teleport: true } },
    })

    expect(wrapper.text()).toContain('Сохраняем ключи…')
    expect(wrapper.find('.wheel-and-hamster').exists()).toBe(true)
  })
})

describe('WorkMarketplaceKeyPoolPanel', () => {
  it('keeps the counters and key table collapsed until the operator opens the list', async () => {
    const wrapper = mount(WorkMarketplaceKeyPoolPanel, {
      props: { marketplace: 'ozon', productKey: '103', productTitle: 'PSN 500', marketplaceKeyPool: { free_count: 1, reserved_count: 2, delivered_count: 3, expired_count: 4, total: 1, page: 1, page_size: 20, items: [{ id: 1, masked_code: '••••1234', status: 'free' }] }, marketplaceKeyPoolLoading: false, marketplaceKeyPoolSaving: false, marketplaceKeyPoolTotalPages: 1, marketplaceKeyPoolRevealingId: 0, marketplaceKeyPoolRevealedCode: vi.fn(() => ''), openMarketplaceKeyPool: vi.fn(), loadMarketplaceKeyPool: vi.fn(), revealMarketplaceKeyPoolKey: vi.fn(), deleteMarketplaceKeyPoolKey: vi.fn(), deleteAllFreeMarketplaceKeyPoolKeys: vi.fn() },
    })

    expect(wrapper.text()).not.toContain('Свободно')
    await wrapper.get('.ozon-catalog-details-modal__work-block-toggle').trigger('click')
    expect(wrapper.text()).toContain('Свободно')
    expect(wrapper.text()).toContain('Выдано')
    expect(wrapper.text()).toContain('Всего')
    expect(wrapper.text()).not.toContain('Зарезервированы')
    expect(wrapper.text()).toContain('••••1234')
    expect(wrapper.text()).toContain('Свободен')
  })

  it('shows the hamster while deleting or updating keys in the pool', async () => {
    const wrapper = mount(WorkMarketplaceKeyPoolPanel, {
      props: { marketplace: 'ozon', productKey: '103', marketplaceKeyPool: { free_count: 1, delivered_count: 0, total: 1, page: 1, page_size: 20, items: [] }, marketplaceKeyPoolLoading: false, marketplaceKeyPoolSaving: true },
    })

    await wrapper.get('.ozon-catalog-details-modal__work-block-toggle').trigger('click')
    expect(wrapper.text()).toContain('Обновляем список ключей…')
    expect(wrapper.find('.wheel-and-hamster').exists()).toBe(true)
  })
})
