export function useProductLogoCache({ cacheKey, fallbackCacheKey = '', ttlMs, storage = globalThis.localStorage } = {}) {
  // Читает JSON-кэш по ключу и безопасно возвращает объект.
  function readStoreByKey(key) {
    if (!storage || !key) return {}
    try {
      const raw = storage.getItem(key)
      return raw ? JSON.parse(raw) : {}
    } catch {
      return {}
    }
  }

  // Читает весь кэш логотипов из localStorage.
  function getLogoCacheStore() {
    const primary = readStoreByKey(cacheKey)
    if (Object.keys(primary).length) return primary
    if (!fallbackCacheKey) return primary
    const fallback = readStoreByKey(fallbackCacheKey)
    if (!Object.keys(fallback).length) return fallback
    // Мигрируем legacy-кэш на новый ключ один раз, чтобы не терять уже загруженные логотипы.
    saveLogoCacheStore(fallback)
    try {
      storage?.removeItem?.(fallbackCacheKey)
    } catch {
      // Если хранилище недоступно, просто оставляем старый ключ.
    }
    return fallback
  }

  function saveLogoCacheStore(store) {
    if (!storage || !cacheKey) return
    try {
      storage.setItem(cacheKey, JSON.stringify(store))
    } catch {
      // Если хранилище недоступно, просто пропускаем запись.
    }
  }

  // Возвращает логотип из кэша, если запись еще не устарела.
  function readLogoCache(productId) {
    const store = getLogoCacheStore()
    const item = store[productId]
    if (!item) return null
    if (Date.now() - item.ts > ttlMs) {
      delete store[productId]
      saveLogoCacheStore(store)
      return null
    }
    return item
  }

  // Сохраняет логотип в кэш с текущим временем.
  function writeLogoCache(productId, value) {
    const store = getLogoCacheStore()
    store[productId] = { ...value, ts: Date.now() }
    saveLogoCacheStore(store)
  }

  // Удаляет кэш конкретного товара.
  function clearLogoCache(productId) {
    const store = getLogoCacheStore()
    if (store[productId]) {
      delete store[productId]
      saveLogoCacheStore(store)
    }
  }

  return {
    readLogoCache,
    writeLogoCache,
    clearLogoCache,
  }
}
