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
    await expect(readAuthenticatorImage(new File([new Uint8Array(AUTHENTICATOR_IMAGE_MAX_BYTES + 1)], 'qr.png', { type: 'image/png' }))).rejects.toThrow('до 1 МБ')
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
