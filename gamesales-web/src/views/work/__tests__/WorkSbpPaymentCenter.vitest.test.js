import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import WorkSbpPaymentCenter from '../sections/WorkSbpPaymentCenter.vue'
import { apiGet, apiPost } from '../../../api/http'

vi.mock('../../../api/http', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
}))

function payment(overrides = {}) {
  // Даём компоненту полный публичный объект операции без банковских секретов.
  return {
    id: '32f79af6-285e-4a37-a74f-10116fb963bb',
    order_id: 'crm_123',
    description: 'A Way Out для PS5',
    buyer: 'Покупатель из Telegram',
    created_by: 'manager-1',
    amount: 199000,
    currency: 'RUB',
    state: 'pending',
    provider_status: 'NEW',
    qr_data_url: 'data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=',
    last_error: '',
    expires_at: '2026-08-31T15:15:00Z',
    confirmed_at: null,
    created_at: '2026-08-31T15:00:00Z',
    is_seen: false,
    ...overrides,
  }
}

function mountCenter() {
  // Teleport оставляем внутри wrapper, чтобы тест проверял реальную форму модалки.
  return mount(WorkSbpPaymentCenter, {
    props: { ctx: { authToken: 'token-1', currentUsername: 'manager-1' } },
    global: { stubs: { teleport: true, transition: false, 'transition-group': false } },
  })
}

async function openPaymentForDownload(overrides = {}) {
  // Открываем платёж из истории, чтобы проверить скачивание при любом его статусе.
  apiGet.mockImplementation(async (path) => path.includes('/config')
    ? { enabled: true }
    : { total: 1, unseen_confirmed_count: 0, items: [payment(overrides)] })
  apiPost.mockResolvedValue(null)
  const wrapper = mountCenter()
  await flushPromises()
  await wrapper.find('[data-test="sbp-open"]').trigger('click')
  await wrapper.find('[data-test="sbp-tab-history"]').trigger('click')
  await flushPromises()
  await wrapper.find('.sbp-history-row__open').trigger('click')
  return wrapper
}

function mockPngExport() {
  // Подменяем графические API, чтобы проверить фон, формат и загрузку без браузера.
  const image = { naturalWidth: 300, naturalHeight: 300 }
  vi.stubGlobal('Image', vi.fn(function () { return image }))
  const context = { fillRect: vi.fn(), drawImage: vi.fn() }
  const getContext = vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(context)
  const png = new Blob(['png'], { type: 'image/png' })
  const toBlob = vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation((callback) => callback(png))
  const createObjectURL = vi.fn(() => 'blob:crm-sbp-qr')
  const revokeObjectURL = vi.fn()
  vi.stubGlobal('URL', { createObjectURL, revokeObjectURL })
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  return { image, context, getContext, png, toBlob, createObjectURL, revokeObjectURL, click }
}

afterEach(() => {
  vi.clearAllMocks()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('WorkSbpPaymentCenter', () => {
  it('sends description, internal buyer and amount in kopecks without preset buttons', async () => {
    apiGet.mockImplementation(async (path) => path.includes('/config')
      ? { enabled: true, min_amount: 1000, max_amount: 10000000, qr_lifetime_minutes: 15 }
      : { total: 0, unseen_confirmed_count: 0, items: [] })
    apiPost.mockResolvedValue(payment())
    const wrapper = mountCenter()
    await flushPromises()

    await wrapper.find('[data-test="sbp-open"]').trigger('click')
    expect(wrapper.find('#sbp-title').text()).toBe('Платежи')
    expect(wrapper.find('[data-test="sbp-description"]').element.value).toBe('Услуга по оформлению цифрового контента')
    await wrapper.find('[data-test="sbp-description"]').setValue('A Way Out для PS5')
    await wrapper.find('[data-test="sbp-buyer"]').setValue('Покупатель из Telegram')
    await wrapper.find('[data-test="sbp-amount"]').setValue('1990')
    expect(wrapper.text()).not.toContain('500 ₽')
    await wrapper.find('[data-test="sbp-create"]').trigger('submit')
    await flushPromises()

    expect(apiPost).toHaveBeenCalledWith('/payments/tbank/sbp', {
      description: 'A Way Out для PS5',
      buyer: 'Покупатель из Telegram',
      amount: 199000,
    }, { token: 'token-1' })
    expect(wrapper.find('[data-test="sbp-payment-result"]').text()).toContain('Покупатель из Telegram')

    wrapper.unmount()
  })

  it.each(['pending', 'confirmed'])('downloads a white-background PNG for a %s payment', async (state) => {
    const wrapper = await openPaymentForDownload({ state, order_id: state === 'confirmed' ? '' : 'crm_123' })
    const graphics = mockPngExport()
    if (state === 'confirmed') graphics.image.naturalHeight = 150
    vi.useFakeTimers()
    await wrapper.find('[data-test="sbp-download"]').trigger('click')
    expect(graphics.image.src).toBe(payment().qr_data_url)
    expect(graphics.click).not.toHaveBeenCalled()
    graphics.image.onload()
    await flushPromises()

    const canvas = graphics.getContext.mock.instances[0]
    expect([canvas.width, canvas.height]).toEqual([1024, 1024])
    expect(graphics.context.fillStyle).toBe('#ffffff')
    expect(graphics.context.fillRect).toHaveBeenCalledWith(0, 0, 1024, 1024)
    expect(graphics.context.fillRect.mock.invocationCallOrder[0]).toBeLessThan(graphics.context.drawImage.mock.invocationCallOrder[0])
    expect(graphics.context.drawImage).toHaveBeenCalledWith(graphics.image, 0, state === 'confirmed' ? 256 : 0, 1024, state === 'confirmed' ? 512 : 1024)
    expect(graphics.toBlob).toHaveBeenCalledWith(expect.any(Function), 'image/png')
    expect(graphics.createObjectURL).toHaveBeenCalledWith(graphics.png)
    expect(graphics.png.type).toBe('image/png')
    expect(graphics.click).toHaveBeenCalledOnce()
    const link = graphics.click.mock.instances[0]
    expect(link.download).toBe(`sbp-${state === 'confirmed' ? payment().id : 'crm_123'}.png`)
    expect(link.href).toBe('blob:crm-sbp-qr')
    expect(link.isConnected).toBe(false)
    expect(graphics.revokeObjectURL).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(1000)
    expect(graphics.revokeObjectURL).toHaveBeenCalledWith('blob:crm-sbp-qr')
    wrapper.unmount()
  })

  it.each(['image', 'context', 'encoding'])('shows a download error and allows retry after an %s failure', async (failure) => {
    const wrapper = await openPaymentForDownload()
    const graphics = mockPngExport()
    if (failure === 'context') graphics.getContext.mockReturnValueOnce(null)
    if (failure === 'encoding') graphics.toBlob.mockImplementationOnce((callback) => callback(null))
    await wrapper.find('[data-test="sbp-download"]').trigger('click')
    if (failure === 'image') graphics.image.onerror()
    else graphics.image.onload()
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Не удалось скачать QR-код')
    expect(graphics.click).not.toHaveBeenCalled()
    expect(graphics.createObjectURL).not.toHaveBeenCalled()

    vi.useFakeTimers()
    await wrapper.find('[data-test="sbp-download"]').trigger('click')
    graphics.image.onload()
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    expect(graphics.click).toHaveBeenCalledOnce()
    await vi.advanceTimersByTimeAsync(1000)
    wrapper.unmount()
  })

  it('shows shared history and marks confirmed payments seen only when history is opened', async () => {
    const confirmed = payment({ state: 'confirmed', confirmed_at: '2026-08-31T15:02:00Z' })
    let unseenConfirmed = 1
    apiGet.mockImplementation(async (path) => path.includes('/config')
      ? { enabled: true, min_amount: 1000, max_amount: 10000000, qr_lifetime_minutes: 15 }
      : { total: 25, unseen_confirmed_count: unseenConfirmed, items: [confirmed] })
    apiPost.mockImplementation(async (path) => {
      if (path.includes('/mark-seen')) unseenConfirmed = 0
      return null
    })
    const wrapper = mountCenter()
    await flushPromises()

    expect(wrapper.find('[data-test="sbp-unseen"]').text()).toBe('1')
    await wrapper.find('[data-test="sbp-open"]').trigger('click')
    await wrapper.find('[data-test="sbp-tab-history"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('A Way Out для PS5')
    expect(wrapper.text()).toContain('manager-1')
    expect(wrapper.findAll('[data-test="sbp-history-row"]')).toHaveLength(1)
    expect(wrapper.find('[data-test="sbp-refresh"]').text()).toBe('Обновить')

    const historyCallCount = () => apiGet.mock.calls.filter(([path]) => path.startsWith('/payments/tbank/sbp?')).length
    const callsBeforeRefresh = historyCallCount()
    await wrapper.find('[data-test="sbp-refresh"]').trigger('click')
    await flushPromises()
    expect(historyCallCount()).toBe(callsBeforeRefresh + 1)

    await wrapper.find('[data-test="sbp-history-search"]').setValue('FIFA 27')
    await wrapper.find('.sbp-search').trigger('submit')
    await flushPromises()
    let historyParams = new URLSearchParams(apiGet.mock.calls.at(-1)[0].split('?')[1])
    expect(historyParams.get('q')).toBe('FIFA 27')
    expect(historyParams.get('offset')).toBe('0')

    await wrapper.find('[data-test="sbp-history-state"]').setValue('confirmed')
    await flushPromises()
    historyParams = new URLSearchParams(apiGet.mock.calls.at(-1)[0].split('?')[1])
    expect(historyParams.get('state')).toBe('confirmed')

    await wrapper.find('[data-test="sbp-page-next"]').trigger('click')
    await flushPromises()
    historyParams = new URLSearchParams(apiGet.mock.calls.at(-1)[0].split('?')[1])
    expect(historyParams.get('limit')).toBe('12')
    expect(historyParams.get('offset')).toBe('12')
    expect(historyParams.get('q')).toBe('FIFA 27')
    expect(historyParams.get('state')).toBe('confirmed')
    expect(apiPost).toHaveBeenCalledWith('/payments/tbank/sbp/mark-seen', {}, { token: 'token-1' })
    expect(wrapper.find('[data-test="sbp-unseen"]').exists()).toBe(false)
    wrapper.unmount()
  })
})
