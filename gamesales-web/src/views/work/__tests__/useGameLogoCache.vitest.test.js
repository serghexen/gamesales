import { describe, it, expect, vi, afterEach } from 'vitest'

import { useGameLogoCache } from '../useGameLogoCache.js'

function createMemoryStorage() {
  const data = new Map()
  return {
    getItem(key) {
      return data.has(key) ? data.get(key) : null
    },
    setItem(key, value) {
      data.set(key, value)
    },
  }
}

describe('useGameLogoCache', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('writes and reads fresh cache entry', () => {
    vi.spyOn(Date, 'now').mockReturnValue(1000)
    const storage = createMemoryStorage()
    const cache = useGameLogoCache({
      cacheKey: 'logo-cache',
      ttlMs: 5000,
      storage,
    })

    cache.writeLogoCache(7, { data_b64: 'abc', mime: 'image/png' })
    expect(cache.readLogoCache(7)).toEqual({
      data_b64: 'abc',
      mime: 'image/png',
      ts: 1000,
    })
  })

  it('drops expired entry and returns null', () => {
    const nowSpy = vi.spyOn(Date, 'now')
    const storage = createMemoryStorage()
    const cache = useGameLogoCache({
      cacheKey: 'logo-cache',
      ttlMs: 1000,
      storage,
    })

    nowSpy.mockReturnValue(1000)
    cache.writeLogoCache(7, { data_b64: 'abc', mime: 'image/png' })
    nowSpy.mockReturnValue(2501)
    expect(cache.readLogoCache(7)).toBeNull()
    expect(cache.readLogoCache(7)).toBeNull()
  })

  it('clears specific game entry', () => {
    vi.spyOn(Date, 'now').mockReturnValue(1000)
    const storage = createMemoryStorage()
    const cache = useGameLogoCache({
      cacheKey: 'logo-cache',
      ttlMs: 1000,
      storage,
    })

    cache.writeLogoCache(7, { data_b64: 'abc', mime: 'image/png' })
    cache.clearLogoCache(7)
    expect(cache.readLogoCache(7)).toBeNull()
  })

  it('works safely when storage is unavailable or throws', () => {
    const badStorage = {
      getItem() {
        throw new Error('no access')
      },
      setItem() {
        throw new Error('no access')
      },
    }
    const cache = useGameLogoCache({
      cacheKey: 'logo-cache',
      ttlMs: 1000,
      storage: badStorage,
    })

    expect(cache.readLogoCache(1)).toBeNull()
    expect(() => cache.writeLogoCache(1, { data_b64: 'x', mime: 'image/png' })).not.toThrow()
    expect(() => cache.clearLogoCache(1)).not.toThrow()
  })
})
