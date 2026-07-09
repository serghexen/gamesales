-- Расширяет action-RBAC для компактной матрицы аккаунтов.

WITH contexts(context_code, context_name, context_order) AS (
  VALUES
    ('create', 'Создание', 0),
    ('view', 'Просмотр', 1),
    ('edit', 'Редактирование', 2)
),
fields(field_code, field_name, field_order, allowed_contexts) AS (
  VALUES
    ('email', 'Почта', 1, ARRAY['create','view','edit']::text[]),
    ('region', 'Регион', 2, ARRAY['create','view','edit']::text[]),
    ('date', 'Дата', 3, ARRAY['create','view','edit']::text[]),
    ('purchase_cost', 'Закупочная цена', 4, ARRAY['create','view','edit']::text[]),
    ('notes', 'Комментарий', 5, ARRAY['create','view','edit']::text[]),
    ('account_password', 'Пароль аккаунта', 6, ARRAY['create','view','edit']::text[]),
    ('email_password', 'Пароль почты', 7, ARRAY['create','view','edit']::text[]),
    ('auth_code', 'Код аутентификатора', 8, ARRAY['create','view','edit']::text[]),
    ('reserves', 'Резервы', 9, ARRAY['create','view','edit']::text[]),
    ('products', 'Товары', 10, ARRAY['create','view','edit']::text[]),
    ('slots', 'Слоты аккаунта', 11, ARRAY['view','edit']::text[]),
    ('deals', 'Пользователи по сделкам', 12, ARRAY['view','edit']::text[])
),
matrix_actions AS (
  SELECT
    'accounts.' || c.context_code || '.field.' || f.field_code AS action_code,
    c.context_name || ': ' || f.field_name AS action_name,
    300 + c.context_order * 100 + f.field_order AS sort_order
  FROM contexts c
  CROSS JOIN fields f
  WHERE c.context_code = ANY(f.allowed_contexts)
)
INSERT INTO app.rbac_actions(action_code, action_name, group_code, sort_order)
SELECT action_code, action_name, 'accounts', sort_order
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
    WHEN r.code IN ('manager', 'operator')
      AND (
        a.action_code LIKE 'accounts.%.field.date'
        OR a.action_code LIKE 'accounts.%.field.region'
        OR a.action_code LIKE 'accounts.%.field.purchase_cost'
        OR a.action_code LIKE 'accounts.%.field.email_password'
        OR a.action_code LIKE 'accounts.%.field.auth_code'
        OR a.action_code LIKE 'accounts.%.field.reserves'
        OR a.action_code LIKE 'accounts.%.field.products'
        OR a.action_code LIKE 'accounts.%.field.slots'
      )
      THEN false
    ELSE true
  END,
  'migration'
FROM app.user_roles r
CROSS JOIN app.rbac_actions a
WHERE a.action_code LIKE 'accounts.create.field.%'
   OR a.action_code LIKE 'accounts.view.field.%'
   OR a.action_code LIKE 'accounts.edit.field.%'
ON CONFLICT (role_code, action_code) DO NOTHING;
