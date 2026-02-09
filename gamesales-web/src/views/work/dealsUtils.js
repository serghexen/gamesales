export function createNewDealState() {
  return {
    deal_type_code: 'sale',
    account_id: '',
    game_id: '',
    customer_nickname: '',
    source_id: '',
    region_code: '',
    slot_type_code: '',
    price: 0,
    purchase_cost: 0,
    game_link: '',
    purchase_at: '',
    slots_used: 1,
    notes: '',
  }
}

export function createEditDealState() {
  return {
    open: false,
    deal_id: null,
    created_at: '',
    deal_type_code: 'sale',
    account_id: '',
    game_id: '',
    customer_nickname: '',
    source_id: '',
    region_code: '',
    slot_type_code: '',
    price: 0,
    purchase_cost: 0,
    game_link: '',
    purchase_at: '',
    slots_used: 1,
    notes: '',
    flow_status_code: '',
  }
}

export function createDealFiltersState() {
  return {
    search_q: '',
    customer_q: '',
    region_q: '',
    status_q: '',
    purchase_from: '',
    purchase_to: '',
    type_q: '',
  }
}

export function resolveDealFlowStatusFilter(statusQ, showCompleted) {
  if (statusQ) return statusQ
  return showCompleted ? 'completed' : 'pending'
}
