-- Расширяет action-RBAC для компактной матрицы активных сделок.

INSERT INTO app.rbac_actions(action_code, action_name, group_code, sort_order)
VALUES
  ('deals_active.list.type', 'Список: тип', 'deals_active', 100),
  ('deals_active.list.customer', 'Список: покупатель', 'deals_active', 110),
  ('deals_active.list.product', 'Список: товар', 'deals_active', 120),
  ('deals_active.list.datetime', 'Список: дата/время', 'deals_active', 130),
  ('deals_active.list.status', 'Список: статус', 'deals_active', 140),
  ('deals_active.list.responsible', 'Список: ответственный', 'deals_active', 150),
  ('deals_active.list.action', 'Список: действие', 'deals_active', 160),
  ('deals_active.new.sale.create', 'Услуга - создание', 'deals_active', 200),
  ('deals_active.new.sale.draft', 'Услуга - черновик', 'deals_active', 210),
  ('deals_active.view.sale.edit', 'Услуга - редактирование', 'deals_active', 220),
  ('deals_active.new.rental.create', 'Шеринг - создание', 'deals_active', 230),
  ('deals_active.new.rental.draft', 'Шеринг - черновик', 'deals_active', 240),
  ('deals_active.view.rental.edit', 'Шеринг - редактирование', 'deals_active', 250)
ON CONFLICT (action_code) DO UPDATE SET
  action_name = EXCLUDED.action_name,
  group_code = EXCLUDED.group_code,
  sort_order = EXCLUDED.sort_order;

WITH contexts(context_code, context_name, context_order) AS (
  VALUES
    ('new.sale', 'Новая услуга', 0),
    ('view.sale', 'Просмотр услуги', 1),
    ('edit.sale', 'Редактирование услуги', 2),
    ('new.rental', 'Новый шеринг', 3),
    ('view.rental', 'Просмотр шеринга', 4),
    ('edit.rental', 'Редактирование шеринга', 5)
),
fields(field_code, field_name, field_order, allowed_contexts) AS (
  VALUES
    ('created_at', 'Дата создания', 1, ARRAY['view.sale','view.rental','edit.sale','edit.rental']::text[]),
    ('completed_at', 'Дата завершения', 2, ARRAY['view.sale','view.rental','edit.sale','edit.rental']::text[]),
    ('status', 'Статус', 3, ARRAY['view.sale','view.rental','edit.sale','edit.rental']::text[]),
    ('return', 'Возврат', 4, ARRAY['view.sale','view.rental','edit.sale','edit.rental']::text[]),
    ('source', 'Источник', 5, NULL::text[]),
    ('messenger', 'Мессенджер', 6, NULL::text[]),
    ('order_number', 'Номер заказа', 7, NULL::text[]),
    ('customer', 'Покупатель', 8, NULL::text[]),
    ('responsible', 'Ответственный', 9, NULL::text[]),
    ('purchase_cost', 'Закупочная цена', 10, ARRAY['new.sale','view.sale','edit.sale']::text[]),
    ('price', 'Сумма продажи', 11, NULL::text[]),
    ('payment_method', 'Метод оплаты', 12, NULL::text[]),
    ('discount', 'Скидка', 13, NULL::text[]),
    ('login', 'Логин', 14, ARRAY['new.sale','view.sale','edit.sale']::text[]),
    ('password', 'Пароль', 15, ARRAY['new.sale','view.sale','edit.sale']::text[]),
    ('product_link', 'Ссылка на товар', 16, ARRAY['new.sale','view.sale','edit.sale']::text[]),
    ('region', 'Регион', 17, ARRAY['new.sale','view.sale','edit.sale']::text[]),
    ('product_type', 'Тип товара', 18, ARRAY['new.rental','view.rental','edit.rental']::text[]),
    ('slot_type', 'Тип слота', 19, ARRAY['new.rental','view.rental','edit.rental']::text[]),
    ('subscription_term', 'Срок подписки', 20, ARRAY['new.rental','view.rental','edit.rental']::text[]),
    ('product', 'Товар', 21, ARRAY['new.rental','view.rental','edit.rental']::text[]),
    ('account', 'Аккаунт', 22, ARRAY['new.rental','view.rental','edit.rental']::text[]),
    ('account_login', 'Логин аккаунта', 23, ARRAY['new.rental','view.rental','edit.rental']::text[]),
    ('account_password', 'Пароль аккаунта', 24, ARRAY['new.rental','view.rental','edit.rental']::text[]),
    ('reserve', 'Резерв', 25, ARRAY['new.rental','view.rental','edit.rental']::text[]),
    ('notes', 'Комментарий', 26, NULL::text[])
),
matrix_actions AS (
  SELECT
    'deals_active.' || c.context_code || '.field.' || f.field_code AS action_code,
    c.context_name || ': ' || f.field_name AS action_name,
    300 + c.context_order * 100 + f.field_order AS sort_order
  FROM contexts c
  CROSS JOIN fields f
  WHERE f.allowed_contexts IS NULL OR c.context_code = ANY(f.allowed_contexts)
)
INSERT INTO app.rbac_actions(action_code, action_name, group_code, sort_order)
SELECT action_code, action_name, 'deals_active', sort_order
FROM matrix_actions
ON CONFLICT (action_code) DO UPDATE SET
  action_name = EXCLUDED.action_name,
  group_code = EXCLUDED.group_code,
  sort_order = EXCLUDED.sort_order;

INSERT INTO app.role_rbac_actions(role_code, action_code, can_do, updated_by)
SELECT
  r.code,
  a.action_code,
  CASE
    WHEN r.code = 'owner' THEN true
    WHEN r.code IN ('manager', 'operator') AND a.action_code LIKE 'deals_active.%.field.discount' THEN false
    ELSE true
  END,
  'migration'
FROM app.roles r
CROSS JOIN app.rbac_actions a
WHERE a.action_code LIKE 'deals_active.list.%'
   OR a.action_code LIKE 'deals_active.new.%'
   OR a.action_code LIKE 'deals_active.view.%'
   OR a.action_code LIKE 'deals_active.edit.%'
ON CONFLICT (role_code, action_code) DO NOTHING;
