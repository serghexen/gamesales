import { describe, it, expect, beforeEach } from 'vitest'

import {
  buildDealFiltersSessionKey,
  readDealFiltersSession,
  writeDealFiltersSession,
  clearDealFiltersSessionByPrefix,
  DEAL_FILTERS_SESSION_KEY_PREFIX,
} from '../dealsSessionFilters.js'

describe('dealsSessionFilters', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('builds stable key by normalized username', () => {
    expect(buildDealFiltersSessionKey(' Manager ')).toBe(`${DEAL_FILTERS_SESSION_KEY_PREFIX}manager`)
    expect(buildDealFiltersSessionKey('')).toBe('')
  })

  it('writes and reads filters payload', () => {
    writeDealFiltersSession(
      'manager',
      {
        search_q: 'abc',
        customer_q: 'cust',
        responsible_q: 'Иван,Петр',
        region_q: 'RU',
        status_q: 'pending',
        purchase_from: '2026-01-01',
        purchase_to: '2026-01-31',
        type_q: 'sale',
      },
      true,
    )
    const data = readDealFiltersSession('manager')
    expect(data?.showCompleted).toBe(true)
    expect(data?.filters?.responsible_q).toBe('Иван,Петр')
    expect(data?.filters?.search_q).toBe('abc')
  })

  it('clears all keys by prefix', () => {
    sessionStorage.setItem(`${DEAL_FILTERS_SESSION_KEY_PREFIX}u1`, '{}')
    sessionStorage.setItem(`${DEAL_FILTERS_SESSION_KEY_PREFIX}u2`, '{}')
    sessionStorage.setItem('other:key', '{}')
    clearDealFiltersSessionByPrefix()
    expect(sessionStorage.getItem(`${DEAL_FILTERS_SESSION_KEY_PREFIX}u1`)).toBeNull()
    expect(sessionStorage.getItem(`${DEAL_FILTERS_SESSION_KEY_PREFIX}u2`)).toBeNull()
    expect(sessionStorage.getItem('other:key')).toBe('{}')
  })
})
