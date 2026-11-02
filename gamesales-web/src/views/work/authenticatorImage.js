export const AUTHENTICATOR_IMAGE_MAX_BYTES = 1024 * 1024
const allowedTypes = new Set(['image/png', 'image/jpeg', 'image/webp'])

export async function readAuthenticatorImage(file, { fromClipboard = false } = {}) {
  // Называем конкретную причину отказа, не читая заведомо неподходящий файл.
  if (!file || !file.size) throw new Error('Изображение пустое. Выберите другой файл.')
  if (!allowedTypes.has(file.type)) {
    throw new Error(`Формат ${file.type || 'не определён'}. Поддерживаются PNG, JPEG или WebP.`)
  }
  if (file.size > AUTHENTICATOR_IMAGE_MAX_BYTES) {
    const size = file.size.toLocaleString('ru-RU')
    const source = fromClipboard ? 'Изображение из буфера' : 'Файл'
    const hint = fromClipboard ? ' При копировании формат и размер могут измениться. Выберите исходный файл через скрепку.' : ''
    throw new Error(`${source}: ${size} байт. Допустимо до 1 МБ (1 048 576 байт).${hint}`)
  }
  const dataUrl = await new Promise((resolve, reject) => {
    // Содержимое остаётся локальным до сохранения аккаунта.
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('Не удалось прочитать изображение'))
    reader.onabort = () => reject(new Error('Чтение изображения отменено'))
    reader.readAsDataURL(file)
  })
  await new Promise((resolve, reject) => {
    // Проверяем декодирование и размеры, чтобы повреждённый файл не стал пустой миниатюрой.
    const image = new Image()
    image.onload = () => {
      if (!image.naturalWidth || !image.naturalHeight || image.naturalWidth > 4096 || image.naturalHeight > 4096) {
        reject(new Error('Размер изображения должен быть не больше 4096 × 4096'))
      } else resolve()
    }
    image.onerror = () => reject(new Error('Файл не удалось открыть как изображение'))
    image.src = dataUrl
  })
  return dataUrl
}
