import { describe, it, expect, vi } from 'vitest'

import { isSameNormalized, confirmDiscardIfNeeded } from '../unsavedChanges.js'

describe('unsavedChanges', () => {
  it('treats trimmed strings and null as equal normalized values', () => {
    expect(isSameNormalized({ a: '  test  ', b: null }, { a: 'test', b: '' })).toBe(true)
  })

  it('returns true without confirm when form is not dirty', async () => {
    const spy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    await expect(confirmDiscardIfNeeded(false)).resolves.toBe(true)
    expect(spy).not.toHaveBeenCalled()
    spy.mockRestore()
  })

  it('asks confirm when form is dirty', async () => {
    const spy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    await expect(confirmDiscardIfNeeded(true)).resolves.toBe(false)
    expect(spy).toHaveBeenCalledTimes(1)
    spy.mockRestore()
  })
})
