CREATE TABLE IF NOT EXISTS app.rbac_action_groups (
  group_code text PRIMARY KEY,
  group_name text NOT NULL,
  group_description text NOT NULL DEFAULT '',
  sort_order integer NOT NULL DEFAULT 0
);

UPDATE app.user_roles
SET name = 'Управляющий'
WHERE lower(code) = 'owner';

CREATE TABLE IF NOT EXISTS app.rbac_actions (
  action_code text PRIMARY KEY,
  action_name text NOT NULL,
  group_code text NOT NULL REFERENCES app.rbac_action_groups(group_code) ON DELETE CASCADE,
  sort_order integer NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS app.role_rbac_actions (
  role_code text NOT NULL REFERENCES app.user_roles(code) ON DELETE CASCADE,
  action_code text NOT NULL REFERENCES app.rbac_actions(action_code) ON DELETE CASCADE,
  can_do boolean NOT NULL DEFAULT true,
  updated_at timestamptz NOT NULL DEFAULT now(),
  updated_by text NOT NULL DEFAULT '',
  PRIMARY KEY (role_code, action_code)
);

INSERT INTO app.rbac_action_groups(group_code, group_name, group_description, sort_order)
VALUES
  ('deals_active', 'Активные сделки', 'Что можно делать в активных сделках', 10),
  ('deals_draft', 'Черновики', 'Что можно делать в черновиках', 20),
  ('deals_completed', 'Завершенные сделки', 'Что можно делать в завершенных сделках', 30),
  ('accounts', 'Аккаунты', 'Что можно делать с аккаунтами', 40),
  ('products', 'Товары', 'Что можно делать с товарами', 50)
ON CONFLICT (group_code) DO UPDATE
  SET group_name=EXCLUDED.group_name,
      group_description=EXCLUDED.group_description,
      sort_order=EXCLUDED.sort_order;

INSERT INTO app.rbac_actions(action_code, action_name, group_code, sort_order)
VALUES
  ('deals_active.create', 'Создание', 'deals_active', 10),
  ('deals_active.edit', 'Редактирование', 'deals_active', 20),
  ('deals_active.fill_fields', 'Заполнять поля', 'deals_active', 30),
  ('deals_active.save', 'Сохранение', 'deals_active', 50),
  ('deals_active.change_status', 'Смена статуса сделки', 'deals_active', 60),
  ('deals_active.draft', 'Черновик', 'deals_active', 70),
  ('deals_active.discount', 'Скидка', 'deals_active', 80),
  ('deals_active.approve_return', 'Одобрить возврат', 'deals_active', 90),
  ('deals_draft.view', 'Просматривать', 'deals_draft', 10),
  ('deals_draft.edit', 'Редактирование', 'deals_draft', 20),
  ('deals_draft.save', 'Сохранять', 'deals_draft', 30),
  ('deals_draft.change_status', 'Смена статуса сделки', 'deals_draft', 40),
  ('deals_draft.delete', 'Удалять', 'deals_draft', 50),
  ('deals_draft.change_deal_date', 'Смена даты сделки', 'deals_draft', 60),
  ('deals_draft.change_completed_date', 'Смена даты завершение', 'deals_draft', 70),
  ('deals_completed.view', 'Просматривать', 'deals_completed', 10),
  ('deals_completed.edit', 'Редактирование', 'deals_completed', 20),
  ('deals_completed.save', 'Сохранять', 'deals_completed', 30),
  ('deals_completed.change_status', 'Смена статуса сделки', 'deals_completed', 40),
  ('deals_completed.change_deal_date', 'Смена даты сделки', 'deals_completed', 60),
  ('deals_completed.change_completed_date', 'Смена даты завершение', 'deals_completed', 70),
  ('deals_completed.process_return', 'Произвести возврат', 'deals_completed', 80),
  ('deals_completed.press_return', 'Нажать возврат', 'deals_completed', 90),
  ('accounts.view_email', 'Просмотр почты', 'accounts', 10),
  ('accounts.view_games', 'Просмотр игры', 'accounts', 20),
  ('accounts.view_slots', 'Просмотр слотов', 'accounts', 30),
  ('accounts.view_reserves', 'Просмотр резервов', 'accounts', 40),
  ('accounts.create', 'Создание аккаунта', 'accounts', 50),
  ('accounts.reflect_email', 'Отражение почты', 'accounts', 60),
  ('accounts.reflect_date', 'Отражение даты', 'accounts', 70),
  ('accounts.reflect_region', 'Отражение региона', 'accounts', 80),
  ('accounts.reflect_account_password', 'Отражение пароля акк', 'accounts', 90),
  ('accounts.reflect_email_password', 'Отражения пароля почты', 'accounts', 100),
  ('accounts.reflect_auth_code', 'Отражение кода аутен', 'accounts', 110),
  ('accounts.reflect_reserves', 'Отражение резервов', 'accounts', 120),
  ('accounts.reflect_slots', 'Отражение слотов', 'accounts', 130),
  ('accounts.reflect_purchase_cost', 'Отражение закупочной цены', 'accounts', 135),
  ('accounts.reflect_deals', 'Отражение сделок', 'accounts', 140),
  ('accounts.edit', 'Редактирование', 'accounts', 150),
  ('accounts.delete', 'Удаление', 'accounts', 160),
  ('products.view_games', 'Просмотр игр', 'products', 10),
  ('products.create_games', 'Создание игр', 'products', 20),
  ('products.reflect_accounts', 'Отражение аккаунтов', 'products', 30),
  ('products.reflect_deals', 'Отражение сделок', 'products', 40),
  ('products.reflect_slots', 'Отражение слотов', 'products', 50),
  ('products.edit', 'Редактирование', 'products', 60),
  ('products.delete', 'Удаление', 'products', 70)
ON CONFLICT (action_code) DO UPDATE
  SET action_name=EXCLUDED.action_name,
      group_code=EXCLUDED.group_code,
      sort_order=EXCLUDED.sort_order;

WITH valid_actions(action_code) AS (
  VALUES
    ('deals_active.create'),
    ('deals_active.edit'),
    ('deals_active.fill_fields'),
    ('deals_active.save'),
    ('deals_active.change_status'),
    ('deals_active.draft'),
    ('deals_active.discount'),
    ('deals_active.approve_return'),
    ('deals_draft.view'),
    ('deals_draft.edit'),
    ('deals_draft.save'),
    ('deals_draft.change_status'),
    ('deals_draft.delete'),
    ('deals_draft.change_deal_date'),
    ('deals_draft.change_completed_date'),
    ('deals_completed.view'),
    ('deals_completed.edit'),
    ('deals_completed.save'),
    ('deals_completed.change_status'),
    ('deals_completed.change_deal_date'),
    ('deals_completed.change_completed_date'),
    ('deals_completed.process_return'),
    ('deals_completed.press_return'),
    ('accounts.view_email'),
    ('accounts.view_games'),
    ('accounts.view_slots'),
    ('accounts.view_reserves'),
    ('accounts.create'),
    ('accounts.reflect_email'),
    ('accounts.reflect_date'),
    ('accounts.reflect_region'),
    ('accounts.reflect_account_password'),
    ('accounts.reflect_email_password'),
    ('accounts.reflect_auth_code'),
    ('accounts.reflect_reserves'),
    ('accounts.reflect_slots'),
    ('accounts.reflect_purchase_cost'),
    ('accounts.reflect_deals'),
    ('accounts.edit'),
    ('accounts.delete'),
    ('products.view_games'),
    ('products.create_games'),
    ('products.reflect_accounts'),
    ('products.reflect_deals'),
    ('products.reflect_slots'),
    ('products.edit'),
    ('products.delete')
)
DELETE FROM app.role_rbac_actions rp
WHERE NOT EXISTS (
  SELECT 1 FROM valid_actions va WHERE va.action_code = rp.action_code
);

WITH valid_actions(action_code) AS (
  VALUES
    ('deals_active.create'),
    ('deals_active.edit'),
    ('deals_active.fill_fields'),
    ('deals_active.save'),
    ('deals_active.change_status'),
    ('deals_active.draft'),
    ('deals_active.discount'),
    ('deals_active.approve_return'),
    ('deals_draft.view'),
    ('deals_draft.edit'),
    ('deals_draft.save'),
    ('deals_draft.change_status'),
    ('deals_draft.delete'),
    ('deals_draft.change_deal_date'),
    ('deals_draft.change_completed_date'),
    ('deals_completed.view'),
    ('deals_completed.edit'),
    ('deals_completed.save'),
    ('deals_completed.change_status'),
    ('deals_completed.change_deal_date'),
    ('deals_completed.change_completed_date'),
    ('deals_completed.process_return'),
    ('deals_completed.press_return'),
    ('accounts.view_email'),
    ('accounts.view_games'),
    ('accounts.view_slots'),
    ('accounts.view_reserves'),
    ('accounts.create'),
    ('accounts.reflect_email'),
    ('accounts.reflect_date'),
    ('accounts.reflect_region'),
    ('accounts.reflect_account_password'),
    ('accounts.reflect_email_password'),
    ('accounts.reflect_auth_code'),
    ('accounts.reflect_reserves'),
    ('accounts.reflect_slots'),
    ('accounts.reflect_purchase_cost'),
    ('accounts.reflect_deals'),
    ('accounts.edit'),
    ('accounts.delete'),
    ('products.view_games'),
    ('products.create_games'),
    ('products.reflect_accounts'),
    ('products.reflect_deals'),
    ('products.reflect_slots'),
    ('products.edit'),
    ('products.delete')
)
DELETE FROM app.rbac_actions a
WHERE NOT EXISTS (
  SELECT 1 FROM valid_actions va WHERE va.action_code = a.action_code
);

INSERT INTO app.role_rbac_actions(role_code, action_code, can_do, updated_by)
SELECT
  r.code,
  a.action_code,
  CASE
    WHEN lower(r.code) = 'owner' THEN true
    WHEN lower(r.code) = 'admin' AND a.action_code IN (
      'deals_draft.change_deal_date',
      'deals_draft.change_completed_date',
      'deals_completed.change_deal_date',
      'deals_completed.change_completed_date'
    ) THEN false
    WHEN lower(r.code) IN ('manager', 'operator') AND a.action_code IN (
      'deals_active.discount',
      'deals_draft.delete',
      'deals_draft.change_deal_date',
      'deals_draft.change_completed_date',
      'deals_completed.edit',
      'deals_completed.save',
      'deals_completed.change_status',
      'deals_completed.change_deal_date',
      'deals_completed.change_completed_date',
      'deals_completed.process_return',
      'accounts.reflect_date',
      'accounts.reflect_region',
      'accounts.reflect_email_password',
      'accounts.reflect_auth_code',
      'accounts.reflect_reserves',
      'accounts.reflect_slots',
      'accounts.reflect_purchase_cost',
      'accounts.edit',
      'accounts.delete',
      'products.reflect_slots',
      'products.edit',
      'products.delete'
    ) THEN false
    ELSE true
  END AS can_do,
  'system'
FROM app.user_roles r
CROSS JOIN app.rbac_actions a
WHERE lower(r.code) IN ('admin', 'owner', 'manager', 'operator')
ON CONFLICT (role_code, action_code) DO UPDATE
  SET can_do = EXCLUDED.can_do,
      updated_at = now(),
      updated_by = EXCLUDED.updated_by;
