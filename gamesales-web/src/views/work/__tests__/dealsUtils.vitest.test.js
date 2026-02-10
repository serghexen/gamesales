import { describe, it, expect } from 'vitest'

import {
  createNewDealState,
  createEditDealState,
  createDealFiltersState,
  resolveDealFlowStatusFilter,
} from '../dealsUtils.js'

describe('dealsUtils', () => {
  it('createNewDealState returns expected defaults', () => {
    const state = createNewDealState()
    expect(state.deal_type_code).toBe('sale')
    expect(state.order_number).toBe('')
    expect(state.login).toBe('')
    expect(state.password).toBe('')
    expect(state.price).toBe(0)
    expect(state.slots_used).toBe(1)
    expect(state.notes).toBe('')
  })

  it('createEditDealState contains edit-specific fields', () => {
    const state = createEditDealState()
    expect(state.open).toBe(false)
    expect(state.deal_id).toBeNull()
    expect(state.order_number).toBe('')
    expect(state.login).toBe('')
    expect(state.password).toBe('')
    expect(state.completed_at).toBe('')
    expect(state.flow_status_code).toBe('')
  })

  it('createDealFiltersState returns empty filters', () => {
    expect(createDealFiltersState()).toEqual({
      search_q: '',
      customer_q: '',
      responsible_q: '',
      region_q: '',
      status_q: '',
      purchase_from: '',
      purchase_to: '',
      type_q: '',
    })
  })

  it('resolveDealFlowStatusFilter respects explicit filter and fallback', () => {
    expect(resolveDealFlowStatusFilter('canceled', false)).toBe('canceled')
    expect(resolveDealFlowStatusFilter('', true)).toBe('completed')
    expect(resolveDealFlowStatusFilter('', false)).toBe('pending')
  })
})
