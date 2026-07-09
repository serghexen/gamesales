export const DEAL_LIST_COLUMN_DEFS = [
  { key: 'type', label: 'Тип' },
  { key: 'customer', label: 'Покупатель' },
  { key: 'product', label: 'Товар' },
  { key: 'datetime', label: 'Дата/время' },
  { key: 'status', label: 'Статус' },
  { key: 'responsible', label: 'Ответственный' },
  { key: 'action', label: 'Действие' },
]

export const ACTIVE_DEAL_CONTEXTS = [
  { key: 'new.sale', label: 'Новая услуга' },
  { key: 'view.sale', label: 'Просмотр услуги' },
  { key: 'edit.sale', label: 'Редакт. услуги' },
  { key: 'new.rental', label: 'Новый шеринг' },
  { key: 'view.rental', label: 'Просмотр шеринга' },
  { key: 'edit.rental', label: 'Редакт. шеринга' },
]

export const COMPLETED_DEAL_CONTEXTS = [
  { key: 'view.sale', label: 'Просмотр услуги' },
  { key: 'edit.sale', label: 'Редакт. услуги' },
  { key: 'view.rental', label: 'Просмотр шеринга' },
  { key: 'edit.rental', label: 'Редакт. шеринга' },
]

export const DRAFT_DEAL_CONTEXTS = COMPLETED_DEAL_CONTEXTS

export const ACTIVE_DEAL_CONTEXT_ACTIONS = [
  { action: 'deals_active.new.sale.create', label: 'Услуга - создание' },
  { action: 'deals_active.new.sale.draft', label: 'Услуга - черновик' },
  { action: 'deals_active.view.sale.edit', label: 'Услуга - редактирование' },
  { action: 'deals_active.new.rental.create', label: 'Шеринг - создание' },
  { action: 'deals_active.new.rental.draft', label: 'Шеринг - черновик' },
  { action: 'deals_active.view.rental.edit', label: 'Шеринг - редактирование' },
]

export const COMPLETED_DEAL_CONTEXT_ACTIONS = [
  { action: 'deals_completed.view', label: 'Просматривать' },
  { action: 'deals_completed.edit', label: 'Редактирование' },
  { action: 'deals_completed.save', label: 'Сохранять' },
  { action: 'deals_completed.change_status', label: 'Смена статуса сделки' },
  { action: 'deals_completed.change_deal_date', label: 'Смена даты сделки' },
  { action: 'deals_completed.change_completed_date', label: 'Смена даты завершение' },
  { action: 'deals_completed.process_return', label: 'Произвести возврат' },
  { action: 'deals_completed.press_return', label: 'Нажать возврат' },
]

export const DRAFT_DEAL_CONTEXT_ACTIONS = [
  { action: 'deals_draft.view', label: 'Просматривать' },
  { action: 'deals_draft.edit', label: 'Редактирование' },
  { action: 'deals_draft.save', label: 'Сохранять' },
  { action: 'deals_draft.change_status', label: 'Смена статуса сделки' },
  { action: 'deals_draft.delete', label: 'Удалять' },
  { action: 'deals_draft.change_deal_date', label: 'Смена даты сделки' },
  { action: 'deals_draft.change_completed_date', label: 'Смена даты завершение' },
]

export const ACTIVE_DEAL_FIELD_GROUPS = [
  {
    key: 'system',
    label: 'Основное',
    fields: [
      { key: 'created_at', label: 'Дата создания', contexts: ['view.sale', 'view.rental', 'edit.sale', 'edit.rental'] },
      { key: 'completed_at', label: 'Дата завершения', contexts: ['view.sale', 'view.rental', 'edit.sale', 'edit.rental'] },
      { key: 'status', label: 'Статус', contexts: ['view.sale', 'view.rental', 'edit.sale', 'edit.rental'] },
      { key: 'return', label: 'Возврат', contexts: ['view.sale', 'view.rental', 'edit.sale', 'edit.rental'] },
    ],
  },
  {
    key: 'order',
    label: 'Клиент и заказ',
    fields: [
      { key: 'source', label: 'Источник', contexts: ACTIVE_DEAL_CONTEXTS.map((context) => context.key) },
      { key: 'messenger', label: 'Мессенджер', contexts: ACTIVE_DEAL_CONTEXTS.map((context) => context.key), requiredContexts: ['new.sale', 'new.rental'] },
      { key: 'order_number', label: 'Номер заказа', contexts: ACTIVE_DEAL_CONTEXTS.map((context) => context.key) },
      { key: 'customer', label: 'Покупатель', contexts: ACTIVE_DEAL_CONTEXTS.map((context) => context.key), requiredContexts: ['new.sale'] },
      { key: 'responsible', label: 'Ответственный', contexts: ACTIVE_DEAL_CONTEXTS.map((context) => context.key) },
    ],
  },
  {
    key: 'finance',
    label: 'Финансы',
    fields: [
      { key: 'purchase_cost', label: 'Закупочная цена', contexts: ['new.sale', 'view.sale', 'edit.sale'] },
      { key: 'price', label: 'Сумма продажи', contexts: ACTIVE_DEAL_CONTEXTS.map((context) => context.key) },
      { key: 'payment_method', label: 'Метод оплаты', contexts: ACTIVE_DEAL_CONTEXTS.map((context) => context.key) },
      { key: 'discount', label: 'Скидка', contexts: ACTIVE_DEAL_CONTEXTS.map((context) => context.key) },
    ],
  },
  {
    key: 'sale_product',
    label: 'Услуга',
    fields: [
      { key: 'login', label: 'Логин', contexts: ['new.sale', 'view.sale', 'edit.sale'] },
      { key: 'password', label: 'Пароль', contexts: ['new.sale', 'view.sale', 'edit.sale'] },
      { key: 'product_link', label: 'Ссылка на товар', contexts: ['new.sale', 'view.sale', 'edit.sale'] },
      { key: 'region', label: 'Регион', contexts: ['new.sale', 'view.sale', 'edit.sale'], requiredContexts: ['new.sale'] },
    ],
  },
  {
    key: 'sharing',
    label: 'Шеринг',
    fields: [
      { key: 'product_type', label: 'Тип товара', contexts: ['new.rental', 'view.rental', 'edit.rental'] },
      { key: 'slot_type', label: 'Тип слота', contexts: ['new.rental', 'view.rental', 'edit.rental'], requiredContexts: ['new.rental'] },
      { key: 'subscription_term', label: 'Срок подписки', contexts: ['new.rental', 'view.rental', 'edit.rental'] },
      { key: 'product', label: 'Товар', contexts: ['new.rental', 'view.rental', 'edit.rental'], requiredContexts: ['new.rental'] },
      { key: 'account', label: 'Аккаунт', contexts: ['new.rental', 'view.rental', 'edit.rental'], requiredContexts: ['new.rental'] },
      { key: 'account_login', label: 'Логин аккаунта', contexts: ['new.rental', 'view.rental', 'edit.rental'] },
      { key: 'account_password', label: 'Пароль аккаунта', contexts: ['new.rental', 'view.rental', 'edit.rental'] },
      { key: 'reserve', label: 'Резерв', contexts: ['new.rental', 'view.rental', 'edit.rental'] },
    ],
  },
  {
    key: 'notes',
    label: 'Комментарий',
    fields: [
      { key: 'notes', label: 'Комментарий', contexts: ACTIVE_DEAL_CONTEXTS.map((context) => context.key) },
    ],
  },
]

export const ACTIVE_DEAL_LIST_COLUMNS = dealListColumns('deals_active')

export function dealListColumns(groupCode) {
  return DEAL_LIST_COLUMN_DEFS.map((column) => ({
    ...column,
    action: `${groupCode}.list.${column.key}`,
  }))
}

export function dealPermissionContexts(groupCode) {
  const code = String(groupCode || '').trim()
  if (code === 'deals_completed') return COMPLETED_DEAL_CONTEXTS
  if (code === 'deals_draft') return DRAFT_DEAL_CONTEXTS
  return ACTIVE_DEAL_CONTEXTS
}

export function dealPermissionActions(groupCode) {
  const code = String(groupCode || '').trim()
  if (code === 'deals_completed') return COMPLETED_DEAL_CONTEXT_ACTIONS
  if (code === 'deals_draft') return DRAFT_DEAL_CONTEXT_ACTIONS
  return ACTIVE_DEAL_CONTEXT_ACTIONS
}

export function dealFieldAction(groupCode, contextKey, fieldKey) {
  return `${groupCode}.${contextKey}.field.${fieldKey}`
}

export function activeDealFieldAction(contextKey, fieldKey) {
  return dealFieldAction('deals_active', contextKey, fieldKey)
}
