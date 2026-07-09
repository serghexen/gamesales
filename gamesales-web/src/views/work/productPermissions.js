export const PRODUCT_LIST_COLUMNS = [
  { key: 'type', action: 'products.list.type', label: 'Тип' },
  { key: 'title', action: 'products.list.title', label: 'Товар' },
  { key: 'platform', action: 'products.list.platform', label: 'Платформа' },
]

export const PRODUCT_CONTEXTS = [
  { key: 'create', label: 'Создание' },
  { key: 'view', label: 'Просмотр' },
  { key: 'edit', label: 'Редактирование' },
]

export const PRODUCT_CONTEXT_ACTIONS = [
  { action: 'products.create_games', label: 'Создание товара' },
  { action: 'products.reflect_accounts', label: 'Отражение аккаунтов' },
  { action: 'products.reflect_deals', label: 'Отражение сделок' },
  { action: 'products.reflect_slots', label: 'Отражение слотов' },
  { action: 'products.edit', label: 'Редактирование' },
  { action: 'products.delete', label: 'Удаление' },
]

export const PRODUCT_FIELD_GROUPS = [
  {
    key: 'main',
    label: 'Основное',
    fields: [
      { key: 'title', label: 'Название', contexts: ['create', 'view', 'edit'], requiredContexts: ['create'] },
      { key: 'short_title', label: 'Короткое название', contexts: ['create', 'view', 'edit'] },
      { key: 'region', label: 'Регион', contexts: ['create', 'view', 'edit'] },
      { key: 'platforms', label: 'Платформа', contexts: ['create', 'view', 'edit'] },
      { key: 'notes', label: 'Комментарий', contexts: ['create', 'view', 'edit'] },
    ],
  },
  {
    key: 'game',
    label: 'Игра',
    fields: [
      { key: 'link', label: 'Ссылка', contexts: ['create', 'view', 'edit'] },
      { key: 'text_lang', label: 'Язык текста', contexts: ['create', 'view', 'edit'] },
      { key: 'audio_lang', label: 'Язык озвучки', contexts: ['create', 'view', 'edit'] },
      { key: 'vr_support', label: 'Поддержка VR', contexts: ['create', 'view', 'edit'] },
      { key: 'accounts', label: 'Аккаунты', contexts: ['create', 'view', 'edit'] },
    ],
  },
  {
    key: 'links',
    label: 'Связанные данные',
    fields: [
      { key: 'deals', label: 'Сделки', contexts: ['view', 'edit'] },
      { key: 'slots', label: 'Слоты по товару', contexts: ['view', 'edit'] },
      { key: 'subscription_terms', label: 'Сроки подписки', contexts: ['view', 'edit'] },
    ],
  },
]

export function productFieldAction(contextKey, fieldKey) {
  return `products.${contextKey}.field.${fieldKey}`
}
