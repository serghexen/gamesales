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
    game_ids: [],
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
    game_ids: [],
  }
}

export function createAccountFiltersState() {
  return {
    search_q: '',
    login_q: '',
    game_q: '',
    region_q: '',
    status_q: '',
    date_from: '',
    date_to: '',
  }
}

const ACCOUNT_SORT_MAP = {
  login_asc: { key: 'login', dir: 'asc' },
  login_desc: { key: 'login', dir: 'desc' },
  games_asc: { key: 'games', dir: 'asc' },
  games_desc: { key: 'games', dir: 'desc' },
  region_asc: { key: 'region', dir: 'asc' },
  region_desc: { key: 'region', dir: 'desc' },
  status_asc: { key: 'status', dir: 'asc' },
  status_desc: { key: 'status', dir: 'desc' },
  date_asc: { key: 'date', dir: 'asc' },
  date_desc: { key: 'date', dir: 'desc' },
}

export function resolveAccountSort(sortCode) {
  return ACCOUNT_SORT_MAP[sortCode] || ACCOUNT_SORT_MAP.login_asc
}
