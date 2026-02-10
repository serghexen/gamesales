export function createNewDealState() {
  // Базовое состояние для новой сделки в модалке.
  return {
    deal_type_code: 'sale',
    account_id: '',
    game_id: '',
    customer_nickname: '',
    order_number: '',
    source_id: '',
    region_code: '',
    slot_type_code: '',
    price: 0,
    purchase_cost: 0,
    login: '',
    password: '',
    game_link: '',
    purchase_at: '',
    slots_used: 1,
    notes: '',
  }
}

export function createEditDealState() {
  // Базовое состояние для просмотра/редактирования существующей сделки.
  return {
    open: false,
    deal_id: null,
    created_at: '',
    completed_at: '',
    deal_type_code: 'sale',
    account_id: '',
    game_id: '',
    customer_nickname: '',
    order_number: '',
    source_id: '',
    region_code: '',
    slot_type_code: '',
    price: 0,
    purchase_cost: 0,
    login: '',
    password: '',
    game_link: '',
    purchase_at: '',
    slots_used: 1,
    notes: '',
    flow_status_code: '',
  }
}

export function createDealFiltersState() {
  // Пустые фильтры таблицы сделок при первом открытии экрана.
  return {
    search_q: '',
    customer_q: '',
    responsible_q: '',
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
