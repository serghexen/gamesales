export function createNewAccountState() {
  return {
    login_name: '',
    domain_code: '',
    region_code: '',
    notes: '',
    account_date: '',
    email_password: '',
    account_password: '',
    reserve_text: '',
    auth_code: '',
    product_ids: [],
  }
}

export function createEditAccountState() {
  return {
    open: false,
    account_id: null,
    login_name: '',
    domain_code: '',
    region_code: '',
    status_code: 'active',
    is_deactivated: false,
    deactivated_at: '',
    next_activation_at: '',
    notes: '',
    account_date: '',
    email_password: '',
    account_password: '',
    account_key: 'account_password',
    email_key: 'email_password',
    auth_code: '',
    auth_key: 'auth_code',
    reserve_text: '',
    existing_reserve_keys: [],
    has_account: false,
    has_email: false,
    has_auth: false,
    product_ids: [],
  }
}

export function createAccountFiltersState() {
  return {
    search_q: '',
    login_q: '',
    product_q: '',
    region_q: '',
    status_q: '',
    date_from: '',
    date_to: '',
  }
}

const ACCOUNT_SORT_MAP = {
  login_asc: { key: 'login', dir: 'asc' },
  login_desc: { key: 'login', dir: 'desc' },
  products_asc: { key: 'products', dir: 'asc' },
  products_desc: { key: 'products', dir: 'desc' },
  region_asc: { key: 'region', dir: 'asc' },
  region_desc: { key: 'region', dir: 'desc' },
  status_asc: { key: 'status', dir: 'asc' },
  status_desc: { key: 'status', dir: 'desc' },
  date_asc: { key: 'date', dir: 'asc' },
  date_desc: { key: 'date', dir: 'desc' },
}

export function resolveAccountSort(sortCode) {
  // Возвращает конфиг сортировки по коду, с безопасным fallback.
  return ACCOUNT_SORT_MAP[sortCode] || ACCOUNT_SORT_MAP.login_asc
}
