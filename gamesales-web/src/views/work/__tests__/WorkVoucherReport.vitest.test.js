import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import WorkVoucherReport from '../sections/WorkVoucherReport.vue'
import { apiGetFile } from '../../../api/http'

vi.mock('../../../api/http', () => ({ apiGetFile: vi.fn() }))
let wrapper
afterEach(() => {
  // Не оставляем телепорт и подмены браузера между сценариями.
  wrapper?.unmount(); document.body.innerHTML = ''; vi.restoreAllMocks(); vi.clearAllMocks()
})

async function open() {
  // Открываем форму реальной кнопкой, как это делает пользователь в платежах.
  wrapper = mount(WorkVoucherReport, { props: { token: 'test-token' }, attachTo: document.body })
  await wrapper.find('button').trigger('click')
  return document.querySelector('[role="dialog"]')
}

async function setDates(first, last) {
  // Вводим даты через события полей, чтобы проверить связку с запросом.
  const inputs = document.querySelectorAll('input')
  for (const [index, value] of [first, last].entries()) {
    inputs[index].value = value; inputs[index].dispatchEvent(new Event('input', { bubbles: true }))
  }
  await flushPromises()
}

describe('Voucher report', () => {
  it('sends dates, blocks duplicate clicks and downloads Excel', async () => {
    let finish
    apiGetFile.mockImplementation(() => new Promise(resolve => { finish = resolve }))
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:test'), revokeObjectURL: vi.fn() }))
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const dialog = await open()
    await setDates('2026-09-13', '2026-09-16')
    dialog.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    await flushPromises()
    expect(apiGetFile).toHaveBeenCalledExactlyOnceWith('/integrations/interhub/voucher-sales/export?date_from=2026-09-13&date_to=2026-09-16', { token: 'test-token' })
    expect(dialog.querySelector('button[type="submit"]').disabled).toBe(true)
    dialog.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    expect(apiGetFile).toHaveBeenCalledTimes(1)
    finish(new Blob(['file'])); await flushPromises()
    expect(click).toHaveBeenCalledOnce(); expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:test')
    expect(dialog.textContent).toContain('Файл готов')
  })

  it('validates dates and keeps errors visible for retry', async () => {
    const dialog = await open()
    await setDates('2026-09-16', '2026-09-13')
    dialog.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    await flushPromises(); expect(apiGetFile).not.toHaveBeenCalled()
    expect(dialog.textContent).toContain('корректный диапазон')
    await setDates('2026-09-13', '2026-09-16')
    apiGetFile.mockRejectedValue(new Error('За выбранный период продаж ваучеров нет'))
    dialog.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    await flushPromises(); expect(dialog.textContent).toContain('продаж ваучеров нет')
    expect(dialog.querySelector('button[type="submit"]').disabled).toBe(false)
    dialog.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises(); expect(document.querySelector('[role="dialog"]')).toBeNull()
  })
})
