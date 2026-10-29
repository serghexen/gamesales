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

  it('keeps the previous image when a selected file is invalid', async () => {
    // Ошибка чтения не очищает уже прикреплённый QR.
    const wrapper = create({ image: 'data:image/png;base64,OLD' })
    readAuthenticatorImage.mockRejectedValue(new Error('Неверный файл'))
    await select(wrapper)
    expect(wrapper.emitted('update:image')).toBeUndefined()
    expect(wrapper.find('[role=alert]').text()).toBe('Неверный файл')
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
