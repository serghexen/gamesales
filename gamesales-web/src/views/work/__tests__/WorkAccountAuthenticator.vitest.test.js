import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import WorkAccountAuthenticator from '../sections/WorkAccountAuthenticator.vue'
import { readAuthenticatorImage } from '../authenticatorImage'

vi.mock('../authenticatorImage', () => ({ readAuthenticatorImage: vi.fn() }))
const wrappers = []

function create(props = {}) {
  // Проверяем компонент без браузерного интерфейса и без реальных QR.
  const wrapper = mount(WorkAccountAuthenticator, { props })
  wrappers.push(wrapper)
  return wrapper
}

async function select(wrapper) {
  // Имитируем выбор локального файла штатным input[type=file].
  const input = wrapper.find('input[type=file]')
  Object.defineProperty(input.element, 'files', { configurable: true, value: [new File(['test'], 'qr.png', { type: 'image/png' })] })
  await input.trigger('change')
  await flushPromises()
}

async function paste(wrapper, clipboardData, selector = '.account-authenticator__image') {
  // Событие с буфером проверяет обработку вставки без доступа к системному буферу.
  const event = new Event('paste', { bubbles: true, cancelable: true })
  Object.defineProperty(event, 'clipboardData', { value: clipboardData })
  wrapper.find(selector).element.dispatchEvent(event)
  await flushPromises()
  return event
}

function imageClipboard(type = 'image/png') {
  // Имитируем изображение из браузера или снимок экрана в буфере обмена.
  const file = new File(['test'], 'clipboard.png', { type })
  return { items: [{ kind: 'file', type, getAsFile: () => file }], files: [file] }
}

beforeEach(() => {
  // jsdom не открывает нативные диалоги; сохраняем их контракт открытия и закрытия.
  vi.clearAllMocks()
  HTMLDialogElement.prototype.showModal = function () { this.open = true }
  HTMLDialogElement.prototype.close = function () { this.open = false }
})
afterEach(() => wrappers.splice(0).forEach((wrapper) => wrapper.unmount()))

describe('account authenticator field', () => {
  it('attaches an image locally and exposes a separate save-loading state', async () => {
    // Сам выбор файла не отправляет данные на сервер, а обновляет модель формы.
    const wrapper = create()
    readAuthenticatorImage.mockResolvedValue('data:image/png;base64,TEST')
    await select(wrapper)
    expect(wrapper.emitted('update:image')).toEqual([['data:image/png;base64,TEST']])
    expect(wrapper.emitted('loading')).toEqual([[true], [false]])
  })

  it('shows the saved image in view mode and opens a separate preview', async () => {
    // Полноразмерное изображение открывается в dialog, а миниатюра остаётся в карточке.
    const image = 'data:image/png;base64,TEST'
    const wrapper = create({ image, readonly: true })
    expect(wrapper.find('input[type=file]').exists()).toBe(false)
    const thumbnail = wrapper.find('button[aria-label="Увеличить QR аутентификатора"]')
    expect(thumbnail.find('img').attributes('src')).toBe(image)
    await thumbnail.trigger('click')
    expect(wrapper.find('dialog').element.open).toBe(true)
    expect(wrapper.find('dialog img').attributes('src')).toBe(image)
    await wrapper.find('dialog').trigger('keydown', { key: 'Escape' })
    expect(wrapper.find('dialog').element.open).toBe(false)
  })

  it('offers replacement and removal only while editing', async () => {
    // Удаление меняет только модель и может быть отменено закрытием карточки.
    const wrapper = create({ image: 'data:image/png;base64,OLD' })
    expect(wrapper.text()).toContain('Заменить')
    await wrapper.findAll('button').find((button) => button.text() === 'Удалить').trigger('click')
    expect(wrapper.emitted('update:image')).toEqual([['']])
    await wrapper.setProps({ readonly: true })
    expect(wrapper.text()).not.toContain('Удалить')
  })

  it('keeps QR controls outside the wide compact-form button rule', async () => {
    // Именно этот общий селектор растягивал кнопки до 200px внутри колонки шириной 170px.
    const wrapper = create()
    const page = document.createElement('div')
    page.className = 'work-page'
    const form = document.createElement('div')
    form.className = 'form--compact'
    page.append(form)
    form.append(wrapper.element)
    const wideButton = '.work-page .form--compact .btn:not(.btn--icon-plain):not(.btn--icon-clear):not(.btn--icon-clear--select)'
    expect(wrapper.findAll('.account-authenticator__actions button')).toHaveLength(1)
    expect(page.querySelector(wideButton)).toBeNull()
    await wrapper.setProps({ image: 'data:image/png;base64,TEST' })
    expect(wrapper.findAll('.account-authenticator__actions button')).toHaveLength(2)
    expect(page.querySelector(wideButton)).toBeNull()
  })

  it('closes the preview with the account-style cross without changing account data', async () => {
    // Крестик использует общие стили шапки аккаунта; закрытие не меняет сам файл.
    const wrapper = create({ image: 'data:image/png;base64,TEST' })
    await wrapper.find('.account-authenticator__thumbnail').trigger('click')
    const close = wrapper.find('dialog .modal__head button[aria-label="Закрыть"]')
    expect(close.classes()).toContain('deal-create-action-btn--close')
    expect(close.classes()).toContain('btn--icon-round')
    expect(close.find('svg').exists()).toBe(true)
    await close.trigger('click')
    expect(wrapper.find('dialog').element.open).toBe(false)
    expect(wrapper.find('dialog img').exists()).toBe(false)
    expect(wrapper.emitted('update:image')).toBeUndefined()
    expect(wrapper.emitted('update:code')).toBeUndefined()
  })

  it('keeps the previous image when a selected file is invalid', async () => {
    // Ошибка чтения не очищает уже прикреплённый QR.
    const wrapper = create({ image: 'data:image/png;base64,OLD' })
    readAuthenticatorImage.mockRejectedValue(new Error('Неверный файл'))
    await select(wrapper)
    expect(wrapper.emitted('update:image')).toBeUndefined()
    expect(wrapper.find('[role=alert]').text()).toBe('Неверный файл')
    expect(wrapper.emitted('loading').at(-1)).toEqual([false])
  })

  it.each(['items', 'files'])('pastes an image from clipboard %s through the file validator', async (source) => {
    // Вставка заменяет локальную модель и использует ту же проверку, что выбор файла.
    const wrapper = create({ image: 'data:image/png;base64,OLD' })
    const clipboard = imageClipboard()
    readAuthenticatorImage.mockResolvedValue('data:image/png;base64,NEW')
    const event = await paste(wrapper, { [source]: clipboard[source] })
    expect(event.defaultPrevented).toBe(true)
    expect(readAuthenticatorImage).toHaveBeenCalledWith(clipboard.files[0])
    expect(wrapper.emitted('update:image')).toEqual([['data:image/png;base64,NEW']])
    expect(wrapper.emitted('loading')).toEqual([[true], [false]])
  })

  it('leaves text pastes and pastes outside the QR area untouched', async () => {
    // Поле кода и другие поля не должны прикреплять изображения по общему Ctrl+V.
    const wrapper = create()
    const text = await paste(wrapper, { items: [{ kind: 'string', type: 'text/plain' }] })
    const code = await paste(wrapper, imageClipboard(), '.account-authenticator__code input')
    expect(text.defaultPrevented).toBe(false)
    expect(code.defaultPrevented).toBe(false)
    expect(readAuthenticatorImage).not.toHaveBeenCalled()
  })

  it('does not paste in view mode or start another read while busy', async () => {
    // Просмотр не меняет данные, повторная вставка не обгоняет начатую загрузку.
    const wrapper = create({ readonly: true })
    expect(wrapper.find('.account-authenticator__image').attributes('tabindex')).toBeUndefined()
    await paste(wrapper, imageClipboard())
    expect(readAuthenticatorImage).not.toHaveBeenCalled()
    await wrapper.setProps({ readonly: false })
    let finish
    readAuthenticatorImage.mockImplementation(() => new Promise((resolve) => { finish = resolve }))
    await paste(wrapper, imageClipboard())
    await paste(wrapper, imageClipboard())
    expect(readAuthenticatorImage).toHaveBeenCalledTimes(1)
    finish('data:image/png;base64,NEW')
    await flushPromises()
    expect(wrapper.emitted('update:image')).toHaveLength(1)
  })

  it('keeps the current QR if the clipboard image fails validation', async () => {
    // Неподходящий формат или размер показывает штатную ошибку и сохраняет прежний QR.
    const wrapper = create({ image: 'data:image/png;base64,OLD' })
    readAuthenticatorImage.mockRejectedValue(new Error('Выберите PNG, JPEG или WebP размером до 1 МБ'))
    await paste(wrapper, imageClipboard('image/svg+xml'))
    expect(wrapper.find('[role=alert]').text()).toContain('до 1 МБ')
    expect(wrapper.emitted('update:image')).toBeUndefined()
    expect(wrapper.emitted('loading').at(-1)).toEqual([false])
  })

  it.each(['readonly', 'unmount'])('ignores late clipboard reading after %s', async (action) => {
    // Отмена редактирования или закрытие карточки отменяет и результат вставки.
    const wrapper = create()
    let finish
    readAuthenticatorImage.mockImplementation(() => new Promise((resolve) => { finish = resolve }))
    await paste(wrapper, imageClipboard())
    if (action === 'readonly') await wrapper.setProps({ readonly: true })
    else wrapper.unmount()
    finish('data:image/png;base64,NEW')
    await flushPromises()
    expect(wrapper.emitted('update:image')).toBeUndefined()
    expect(wrapper.emitted('loading').at(-1)).toEqual([false])
  })

  it.each(['readonly', 'unmount'])('ignores late file reading after %s', async (action) => {
    // Поздний ответ не возвращает файл после отмены редактирования или закрытия карточки.
    let finish
    readAuthenticatorImage.mockReturnValue(new Promise((resolve) => { finish = resolve }))
    const wrapper = create()
    await select(wrapper)
    if (action === 'readonly') await wrapper.setProps({ readonly: true })
    else wrapper.unmount()
    finish('data:image/png;base64,OLD')
    await flushPromises()
    expect(wrapper.emitted('update:image')).toBeUndefined()
    expect(wrapper.emitted('loading').at(-1)).toEqual([false])
  })
})
