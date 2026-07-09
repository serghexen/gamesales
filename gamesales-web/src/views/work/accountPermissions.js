export const ACCOUNT_LIST_COLUMNS = [
  { key: 'email', action: 'accounts.view_email', label: 'Почта' },
  { key: 'games', action: 'accounts.view_games', label: 'Товары' },
  { key: 'slots', action: 'accounts.view_slots', label: 'Слоты' },
  { key: 'reserves', action: 'accounts.view_reserves', label: 'Резервы' },
]

export const ACCOUNT_CONTEXTS = [
  { key: 'create', label: 'Создание' },
  { key: 'view', label: 'Просмотр' },
  { key: 'edit', label: 'Редактирование' },
]

export const ACCOUNT_CONTEXT_ACTIONS = [
  { action: 'accounts.create', label: 'Создание аккаунта' },
  { action: 'accounts.edit', label: 'Редактирование' },
  { action: 'accounts.delete', label: 'Удаление' },
]

export const ACCOUNT_FIELD_GROUPS = [
  {
    key: 'main',
    label: 'Основное',
    fields: [
      { key: 'email', label: 'Почта', contexts: ['create', 'view', 'edit'], requiredContexts: ['create'] },
      { key: 'region', label: 'Регион', contexts: ['create', 'view', 'edit'] },
      { key: 'date', label: 'Дата', contexts: ['create', 'view', 'edit'], requiredContexts: ['create'] },
      { key: 'purchase_cost', label: 'Закупочная цена', contexts: ['create', 'view', 'edit'] },
      { key: 'notes', label: 'Комментарий', contexts: ['create', 'view', 'edit'] },
    ],
  },
  {
    key: 'secrets',
    label: 'Секреты',
    fields: [
      { key: 'account_password', label: 'Пароль аккаунта', contexts: ['create', 'view', 'edit'] },
      { key: 'email_password', label: 'Пароль почты', contexts: ['create', 'view', 'edit'] },
      { key: 'auth_code', label: 'Код аутентификатора', contexts: ['create', 'view', 'edit'] },
      { key: 'reserves', label: 'Резервы', contexts: ['create', 'view', 'edit'] },
    ],
  },
  {
    key: 'links',
    label: 'Связи',
    fields: [
      { key: 'products', label: 'Товары', contexts: ['create', 'view', 'edit'] },
      { key: 'slots', label: 'Слоты аккаунта', contexts: ['view', 'edit'] },
      { key: 'deals', label: 'Пользователи по сделкам', contexts: ['view', 'edit'] },
    ],
  },
]

export function accountFieldAction(contextKey, fieldKey) {
  return `accounts.${contextKey}.field.${fieldKey}`
}
