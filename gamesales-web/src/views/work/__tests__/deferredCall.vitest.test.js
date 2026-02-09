import { describe, it, expect, vi } from 'vitest'

import { createDeferredCall } from '../deferredCall.js'

describe('createDeferredCall', () => {
  it('throws clear error before implementation is set', () => {
    const deferred = createDeferredCall('myAction')
    expect(() => deferred.call()).toThrow('myAction is called before initialization')
  })

  it('calls implementation after set and forwards args', () => {
    const deferred = createDeferredCall('myAction')
    const fn = vi.fn((a, b) => a + b)
    deferred.set(fn)

    expect(deferred.call(2, 3)).toBe(5)
    expect(fn).toHaveBeenCalledWith(2, 3)
  })

  it('allows replacing implementation', () => {
    const deferred = createDeferredCall('myAction')
    deferred.set(() => 'first')
    expect(deferred.call()).toBe('first')
    deferred.set(() => 'second')
    expect(deferred.call()).toBe('second')
  })
})
