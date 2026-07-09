-- Расширяет action-RBAC для компактной матрицы товаров.

UPDATE app.rbac_action_groups
SET group_description = ''
WHERE group_code = 'products';

INSERT INTO app.rbac_actions(action_code, action_name, group_code, sort_order)
VALUES
  ('products.list.type', 'Список: тип', 'products', 100),
  ('products.list.title', 'Список: товар', 'products', 110),
  ('products.list.platform', 'Список: платформа', 'products', 120)
ON CONFLICT (action_code) DO UPDATE SET
  action_name = EXCLUDED.action_name,
  group_code = EXCLUDED.group_code,
  sort_order = EXCLUDED.sort_order;

WITH contexts(context_code, context_name, context_order) AS (
  VALUES
    ('create', 'Создание', 0),
    ('view', 'Просмотр', 1),
    ('edit', 'Редактирование', 2)
),
fields(field_code, field_name, field_order, allowed_contexts) AS (
  VALUES
    ('title', 'Название', 1, ARRAY['create','view','edit']::text[]),
    ('short_title', 'Короткое название', 2, ARRAY['create','view','edit']::text[]),
    ('region', 'Регион', 3, ARRAY['create','view','edit']::text[]),
    ('platforms', 'Платформа', 4, ARRAY['create','view','edit']::text[]),
    ('notes', 'Комментарий', 5, ARRAY['create','view','edit']::text[]),
    ('link', 'Ссылка', 6, ARRAY['create','view','edit']::text[]),
    ('text_lang', 'Язык текста', 7, ARRAY['create','view','edit']::text[]),
    ('audio_lang', 'Язык озвучки', 8, ARRAY['create','view','edit']::text[]),
    ('vr_support', 'Поддержка VR', 9, ARRAY['create','view','edit']::text[]),
    ('accounts', 'Аккаунты', 10, ARRAY['create','view','edit']::text[]),
    ('deals', 'Сделки', 11, ARRAY['view','edit']::text[]),
    ('slots', 'Слоты по товару', 12, ARRAY['view','edit']::text[]),
    ('subscription_terms', 'Сроки подписки', 13, ARRAY['view','edit']::text[])
),
matrix_actions AS (
  SELECT
    'products.' || c.context_code || '.field.' || f.field_code AS action_code,
    c.context_name || ': ' || f.field_name AS action_name,
    300 + c.context_order * 100 + f.field_order AS sort_order
  FROM contexts c
  CROSS JOIN fields f
  WHERE c.context_code = ANY(f.allowed_contexts)
)
INSERT INTO app.rbac_actions(action_code, action_name, group_code, sort_order)
SELECT action_code, action_name, 'products', sort_order
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
    WHEN r.code IN ('manager', 'operator') AND a.action_code LIKE 'products.%.field.slots' THEN false
    ELSE true
  END,
  'migration'
FROM app.user_roles r
CROSS JOIN app.rbac_actions a
WHERE a.action_code LIKE 'products.list.%'
   OR a.action_code LIKE 'products.create.field.%'
   OR a.action_code LIKE 'products.view.field.%'
   OR a.action_code LIKE 'products.edit.field.%'
ON CONFLICT (role_code, action_code) DO NOTHING;
