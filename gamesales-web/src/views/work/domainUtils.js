export const TAB_KEYS = ['deals', 'accounts', 'products', 'ns-gift', 'telegram', 'analytics', 'catalogs', 'finance', 'users', 'profile', 'dashboard']

export const TELEGRAM_DIALOGS_POLL_MS = 5000
export const TELEGRAM_MESSAGES_POLL_MS = 1000
export const TELEGRAM_DIALOGS_POLL_ERROR_MS = 15000
export const TELEGRAM_MESSAGES_POLL_ERROR_MS = 3000

export const PRODUCT_IMPORT_JOB_KEY = 'gamesales_product_import_job_v1'
export const LEGACY_PRODUCT_IMPORT_JOB_FALLBACK_KEY = 'gamesales_game_import_job_v1'
export const ACCOUNT_IMPORT_JOB_KEY = 'gamesales_account_import_job_v1'
export const SLOT_VALIDATE_JOB_KEY = 'gamesales_slot_validate_job_v1'
export const SLOT_IMPORT_JOB_KEY = 'gamesales_slot_import_job_v1'

export const PRODUCT_LOGO_CACHE_KEY = 'gamesales_product_logo_cache_v1'
export const LEGACY_PRODUCT_LOGO_CACHE_FALLBACK_KEY = 'gamesales_game_logo_cache_v1'
export const PRODUCT_LOGO_CACHE_TTL_MS = 24 * 60 * 60 * 1000
export const PRODUCT_TYPE_PRIMARY = 'game'

export const dealTypeOptions = [
  { code: 'sale', name: 'Услуга' },
  { code: 'rental', name: 'Шеринг' },
  { code: 'expense', name: 'Расходы' },
  { code: 'adjustment', name: 'Корректирование' },
]

export const dealStatusOptions = [
  { code: 'draft', name: 'Черновик' },
  { code: 'confirmed', name: 'Подтвержден' },
  { code: 'cancelled', name: 'Отменен' },
  { code: 'closed', name: 'Закрыт' },
]

export const dealFlowStatusOptions = [
  { code: 'draft', name: 'Черновик' },
  { code: 'pending', name: 'В ожидании' },
  { code: 'completed', name: 'Завершен' },
]

export const minDate = '2020-01-01'
export const maxPrice = 999999
export const maxProductTitleLength = 10

export const getMaxDate = () => new Date().toISOString().slice(0, 10)

export const clampPrice = (value) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return 0
  return Math.min(Math.max(num, 0), maxPrice)
}

export const clampPriceFilter = (value) => {
  if (value === '' || value === null || value === undefined) return ''
  const num = Number(value)
  if (!Number.isFinite(num)) return ''
  return String(Math.min(Math.max(num, 0), maxPrice))
}

export const formatPrice = (value) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return '—'
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 })
    .format(num)
    .replace(/\u00A0/g, ' ')
}

export const formatPercent = (value) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return '—'
  return new Intl.NumberFormat('ru-RU', { style: 'percent', maximumFractionDigits: 1 })
    .format(num)
    .replace(/\u00A0/g, ' ')
}

export const toUtcDateTime = (value) => (value ? `${value}T00:00:00Z` : null)

export const mapApiError = (message) => {
  // Приводим ошибки API к коротким и понятным текстам для интерфейса.
  const text = String(message || '')
  if (!text) return 'Ошибка'
  if (text.includes('Load failed')) return 'Не удалось отправить файл. Проверьте формат (.xlsx/.xls) и доступность API'
  if (text.includes('Not enough free slots.')) {
    const free = text.match(/free_slots=([0-9]+)/)?.[1]
    const req = text.match(/requested=([0-9]+)/)?.[1]
    if (free && req) return `Недостаточно свободных слотов: свободно ${free}, нужно ${req}`
    return 'Недостаточно свободных слотов'
  }
  if (text.includes('slot_type_code is required for rental')) return 'Для шеринга нужно выбрать тип слота'
  if (text.includes('slots_used must be >= 1 for rental')) return 'Для шеринга укажите количество слотов (минимум 1)'
  if (text.includes('slots_used must be >= 1')) return 'Количество слотов должно быть не меньше 1'
  if (text.includes('deal_type_code must be sale or rental')) return 'Тип сделки должен быть услуга или шеринг'
  if (text.includes('order_number must be unique for source ym/ozon/wb')) {
    // Оставляем подробности конфликта в тексте, чтобы менеджер мог быстро найти нужную сделку.
    const conflictDealId = text.match(/deal_id=([0-9]+)/)?.[1]
    const conflictCustomer = text.match(/customer=([^;]+)/)?.[1]?.trim()
    const conflictProduct = text.match(/product=([^;]+)/)?.[1]?.trim()
    const conflictDate = text.match(/created_at=([^;]+)/)?.[1]?.trim()
    const details = [
      conflictDealId ? `Сделка #${conflictDealId}` : '',
      conflictCustomer ? `покупатель: ${conflictCustomer}` : '',
      conflictProduct ? `товар: ${conflictProduct}` : '',
      conflictDate ? `дата: ${conflictDate}` : '',
    ].filter(Boolean).join(', ')
    return details
      ? `Для источников ym/ozon/wb номер заказа уже используется. ${details}`
      : 'Для источников ym/ozon/wb номер заказа уже используется'
  }
  if (text.includes('Unknown flow_status_code')) return 'Неизвестный статус'
  if (text.includes('flow_status_code draft is allowed only for sale deals')) return 'Черновик доступен только для продажи'
  if (text.includes('draft deal cannot be completed directly')) return 'Черновик нельзя сразу перевести в статус Завершен'
  if (text.includes('deal was modified by another user') || text.includes('lock_version is required')) {
    return 'Сделка уже изменена другим пользователем. Обновите список и попробуйте снова'
  }
  if (text.includes('customer_nickname is required for non-draft sale')) return 'Укажите покупателя'
  if (text.includes('delete is allowed only for draft deals')) return 'Удалить можно только черновик'
  if (text.includes('is_refund can be changed only for pending deals')) return 'Признак возврата можно менять только у сделки в ожидании'
  if (text.includes('не достаточно прав для проведения возврата')) return 'не достаточно прав для проведения возврата'
  if (text.includes('region_code is required for sale')) return 'Укажите регион'
  if (text.includes('account_id is required for rental')) return 'Для шеринга укажите аккаунт'
  if (text.includes('product_id is required for rental')) return 'Для шеринга укажите товар'
  if (text.includes('login_name and domain_code are required')) return 'Укажите логин и домен'
  if (text.includes('title is required')) return 'Укажите название товара'
  if (text.includes('account_date must be between')) return 'Дата аккаунта должна быть между 2020-01-01 и сегодня'
  if (text.includes('purchase_at must be between')) return 'Дата покупки должна быть между 2020-01-01 и сегодня'
  if (text.includes('start_at must be between')) return 'Дата начала должна быть между 2020-01-01 и сегодня'
  if (text.includes('end_at must be between')) return 'Дата окончания должна быть между 2020-01-01 и сегодня'
  if (text.includes('end_at must be >= start_at')) return 'Дата окончания не может быть раньше даты начала'
  if (text.includes('completed_at must be >= created_at')) return 'Дата завершения не может быть раньше даты создания'
  if (text.includes('Unknown platform_code')) return 'Неизвестная платформа'
  if (text.includes('Unknown slot_type_code')) return 'Неизвестный тип слота'
  if (text.includes('Unknown region_code')) return 'Неизвестный регион'
  if (text.includes('Unknown domain')) return 'Неизвестный домен'
  if (text.includes('Account already exists') || text.includes('uq_account_login') || text.includes('duplicate key value violates unique constraint "uq_account_login"')) {
    return 'Данный аккаунт уже есть в базе данных'
  }
  if (text.includes('User not found')) return 'Покупатель не найден'
  if (text.includes('Account not found')) return 'Аккаунт не найден'
  if (text.includes('Product not found')) return 'Товар не найден'
  if (text.includes('Source not found')) return 'Источник не найден'
  if (text.includes('Domain not found')) return 'Домен не найден'
  if (text.includes('Region not found')) return 'Регион не найден'
  if (text.includes('Platform not found')) return 'Платформа не найдена'
  if (text.includes('query.payload: Field required') || text.includes('body.payload: Field required')) {
    return 'Некорректный формат запроса. Обновите страницу и попробуйте снова'
  }
  if (text.includes('Product already exists for platforms:')) {
    const list = text.split('Product already exists for platforms:')[1]?.trim()
    return `Товар с таким названием уже есть на платформах: ${list || ''}`.trim()
  }
  return text
}
