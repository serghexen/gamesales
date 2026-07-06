BEGIN;

ALTER TABLE app.accounts
  ADD COLUMN IF NOT EXISTS purchase_cost numeric(12,2) NOT NULL DEFAULT 0;

COMMENT ON COLUMN app.accounts.purchase_cost IS 'Закупочная цена аккаунта для косвенного расхода закуп шеринга';

INSERT INTO app.rbac_actions(action_code, action_name, group_code, sort_order)
VALUES ('accounts.reflect_purchase_cost', 'Отражение закупочной цены', 'accounts', 135)
ON CONFLICT (action_code) DO UPDATE
  SET action_name=EXCLUDED.action_name,
      group_code=EXCLUDED.group_code,
      sort_order=EXCLUDED.sort_order;

INSERT INTO app.role_rbac_actions(role_code, action_code, can_do, updated_by)
SELECT
  r.code,
  'accounts.reflect_purchase_cost',
  CASE
    WHEN lower(r.code) IN ('owner', 'admin') THEN true
    ELSE false
  END,
  'system'
FROM app.user_roles r
WHERE lower(r.code) IN ('admin', 'owner', 'manager', 'operator')
ON CONFLICT (role_code, action_code) DO UPDATE
  SET can_do = EXCLUDED.can_do,
      updated_at = now(),
      updated_by = EXCLUDED.updated_by;

COMMIT;
