export function createNewDealState() {
  // Базовое состояние для новой сделки в модалке.
  return {
    deal_type_code: 'sale',
    account_id: '',
    product_id: '',
    customer_nickname: '',
    order_number: '',
    source_id: '',
    region_code: '',
    slot_type_code: '',
    reserve_key: '',
    price: 0,
    purchase_cost: 0,
    login: '',
    password: '',
    product_link: '',
    purchase_at: '',
    slots_used: 1,
    notes: '',
    is_refund: false,
  }
}

export function createEditDealState() {
  // Базовое состояние для просмотра/редактирования существующей сделки.
  return {
    open: false,
    deal_id: null,
    lock_version: 1,
    created_at: '',
    completed_at: '',
    deal_type_code: 'sale',
    account_id: '',
    product_id: '',
    customer_nickname: '',
    order_number: '',
    source_id: '',
    region_code: '',
    slot_type_code: '',
    reserve_key: '',
    price: 0,
    purchase_cost: 0,
    login: '',
    password: '',
    product_link: '',
    purchase_at: '',
    slots_used: 1,
    notes: '',
    flow_status_code: '',
    is_refund: false,
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
  // В режиме "в ожидании" показываем и черновики, чтобы их можно было найти и доработать.
  return showCompleted ? 'completed' : 'pending,draft'
}
