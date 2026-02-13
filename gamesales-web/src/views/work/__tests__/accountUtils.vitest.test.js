import { describe, it, expect } from 'vitest'

import {
  createNewAccountState,
  createEditAccountState,
  createAccountFiltersState,
  resolveAccountSort,
} from '../accountUtils.js'

describe('accountUtils', () => {
  it('createNewAccountState returns expected defaults', () => {
    const state = createNewAccountState()
    expect(state.login_name).toBe('')
    expect(state.domain_code).toBe('')
    expect(state.product_ids).toEqual([])
  })

  it('createEditAccountState contains edit metadata defaults', () => {
    const state = createEditAccountState()
    expect(state.open).toBe(false)
    expect(state.account_id).toBeNull()
    expect(state.status_code).toBe('active')
    expect(state.account_key).toBe('account_password')
  })

  it('createAccountFiltersState returns empty filters', () => {
    expect(createAccountFiltersState()).toEqual({
      search_q: '',
      login_q: '',
      product_q: '',
      region_q: '',
      status_q: '',
      date_from: '',
      date_to: '',
    })
  })

  it('resolveAccountSort maps code and falls back to login asc', () => {
    expect(resolveAccountSort('date_desc')).toEqual({ key: 'date', dir: 'desc' })
    expect(resolveAccountSort('unknown_code')).toEqual({ key: 'login', dir: 'asc' })
  })
})
