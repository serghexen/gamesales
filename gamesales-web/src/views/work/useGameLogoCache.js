export function useGameLogoCache({ cacheKey, ttlMs, storage = globalThis.localStorage } = {}) {
  // Читает весь кэш логотипов из localStorage.
  function getLogoCacheStore() {
    if (!storage || !cacheKey) return {}
    try {
      const raw = storage.getItem(cacheKey)
      return raw ? JSON.parse(raw) : {}
    } catch {
      return {}
    }
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
  function readLogoCache(gameId) {
    const store = getLogoCacheStore()
    const item = store[gameId]
    if (!item) return null
    if (Date.now() - item.ts > ttlMs) {
      delete store[gameId]
      saveLogoCacheStore(store)
      return null
    }
    return item
  }

  // Сохраняет логотип в кэш с текущим временем.
  function writeLogoCache(gameId, value) {
    const store = getLogoCacheStore()
    store[gameId] = { ...value, ts: Date.now() }
    saveLogoCacheStore(store)
  }

  // Удаляет кэш конкретной игры.
  function clearLogoCache(gameId) {
    const store = getLogoCacheStore()
    if (store[gameId]) {
      delete store[gameId]
      saveLogoCacheStore(store)
    }
  }

  return {
    readLogoCache,
    writeLogoCache,
    clearLogoCache,
  }
}
