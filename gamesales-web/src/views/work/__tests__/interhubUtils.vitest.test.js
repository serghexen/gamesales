import { describe, expect, it } from 'vitest'

import { createInterhubAgentTransactionId } from '../interhubUtils'

describe('createInterhubAgentTransactionId', () => {
  it('creates a digits-only transaction identifier', () => {
    // Подставляем фиксированные значения, чтобы проверить формат без зависимости от часов.
    const id = createInterhubAgentTransactionId(() => 1763200000123, () => 0.042)

    expect(id).toBe('1763200000123042')
    expect(id).toMatch(/^\d+$/)
  })
})
