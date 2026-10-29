export const AUTHENTICATOR_IMAGE_MAX_BYTES = 1024 * 1024
const allowedTypes = new Set(['image/png', 'image/jpeg', 'image/webp'])

export async function readAuthenticatorImage(file) {
  // Проверяем файл до чтения и не принимаем активные форматы вроде SVG.
  if (!file || !allowedTypes.has(file.type) || !file.size || file.size > AUTHENTICATOR_IMAGE_MAX_BYTES) {
    throw new Error('Выберите PNG, JPEG или WebP размером до 1 МБ')
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
