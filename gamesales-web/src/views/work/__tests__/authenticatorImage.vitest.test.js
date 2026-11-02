import { afterEach, describe, expect, it, vi } from 'vitest'
import { AUTHENTICATOR_IMAGE_MAX_BYTES, readAuthenticatorImage } from '../authenticatorImage'

function imageDecoder({ width = 1, height = 1, fails = false } = {}) {
  // Подменяем только декодер пикселей, FileReader читает настоящий объект File.
  vi.stubGlobal('Image', class {
    naturalWidth = width
    naturalHeight = height
    set src(_value) { queueMicrotask(() => fails ? this.onerror() : this.onload()) }
  })
}
afterEach(() => vi.unstubAllGlobals())

describe('authenticator image file reading', () => {
  it.each(['image/png', 'image/jpeg', 'image/webp'])('reads a supported %s file', async (type) => {
    // Поддерживаем распространённые форматы без преобразования содержимого QR.
    imageDecoder()
    const value = await readAuthenticatorImage(new File(['pixels'], 'qr', { type }))
    expect(value).toBe(`data:${type};base64,cGl4ZWxz`)
  })

  it.each(['image/svg+xml', 'text/html', ''])('rejects unsupported type %s', async (type) => {
    // Активное содержимое и неопределённый MIME не попадают в предпросмотр.
    await expect(readAuthenticatorImage(new File(['data'], 'qr.png', { type }))).rejects.toThrow('PNG, JPEG или WebP')
  })

  it('rejects an oversized file before decoding it', async () => {
    // Не читаем лишний мегабайт в FileReader, если размер уже превышен.
    await expect(readAuthenticatorImage(new File([new Uint8Array(AUTHENTICATOR_IMAGE_MAX_BYTES + 1)], 'qr.png', { type: 'image/png' }))).rejects.toThrow('до 15 МБ')
  })

  it.each([5665558, 15 * 1024 * 1024])('accepts clipboard images of %s bytes', async (bytes) => {
    // Принимаем увеличившийся PNG из буфера и точную границу нового лимита без сжатия.
    imageDecoder({ width: 2560, height: 1920 })
    const result = await readAuthenticatorImage(new File([new Uint8Array(bytes)], 'image.png', { type: 'image/png' }), { fromClipboard: true })
    expect(result.startsWith('data:image/png;base64,')).toBe(true)
    expect(result.split(',')[1].length).toBe(4 * Math.ceil(bytes / 3))
  })

  it('reports actual clipboard size and suggests attaching the original', async () => {
    // Копирование JPEG может дать большой PNG: ошибка должна объяснять размер полученного буфера.
    const bytes = 15 * 1024 * 1024 + 1
    const file = new File([new Uint8Array(bytes)], 'image.png', { type: 'image/png' })
    await expect(readAuthenticatorImage(file, { fromClipboard: true })).rejects.toThrow(`${bytes.toLocaleString('ru-RU')} байт`)
    await expect(readAuthenticatorImage(file, { fromClipboard: true })).rejects.toThrow('исходный файл через скрепку')
    await expect(readAuthenticatorImage(file)).rejects.not.toThrow('из буфера')
  })

  it('accepts a JPEG with the reported source size and dimensions without conversion', async () => {
    // Воспроизводим параметры исходника; реальное содержимое пользовательского файла не храним в тестах.
    imageDecoder({ width: 2560, height: 1920 })
    const file = new File([new Uint8Array(888422)], 'photo.jpg', { type: 'image/jpeg' })
    const result = await readAuthenticatorImage(file)
    expect(result.startsWith('data:image/jpeg;base64,')).toBe(true)
    expect(atob(result.split(',')[1]).length).toBe(888422)
  })

  it('distinguishes an empty file from an unsupported format', async () => {
    // Пустой файл и неизвестный MIME требуют разных действий пользователя.
    await expect(readAuthenticatorImage(new File([], 'empty.jpg', { type: 'image/jpeg' }))).rejects.toThrow('пустое')
    await expect(readAuthenticatorImage(new File(['data'], 'qr.tiff', { type: 'image/tiff' }))).rejects.toThrow('image/tiff')
  })

  it('rejects a corrupt image', async () => {
    // MIME сам по себе не подтверждает, что браузер сможет показать файл.
    imageDecoder({ fails: true })
    await expect(readAuthenticatorImage(new File(['broken'], 'qr.png', { type: 'image/png' }))).rejects.toThrow('не удалось открыть')
  })

  it('rejects excessive image dimensions', async () => {
    // Ограничиваем размеры независимо от веса сжатого файла.
    imageDecoder({ width: 5000 })
    await expect(readAuthenticatorImage(new File(['pixels'], 'qr.png', { type: 'image/png' }))).rejects.toThrow('4096')
  })
})
