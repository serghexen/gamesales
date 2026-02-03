BEGIN;

CREATE TABLE IF NOT EXISTS app.slot_types (
  code text PRIMARY KEY,
  name text NOT NULL,
  platform_code text NOT NULL,
  mode text NOT NULL,
  capacity integer NOT NULL DEFAULT 0,
  CONSTRAINT ck_slot_type_mode CHECK (mode IN ('play', 'activate')),
  CONSTRAINT ck_slot_type_capacity CHECK (capacity >= 0)
);

INSERT INTO app.slot_types(code, name, platform_code, mode, capacity)
VALUES
  ('play_ps4', 'П2 (PS4)', 'ps4', 'play', 1),
  ('play_ps5', 'П2 (PS5)', 'ps5', 'play', 1),
  ('activate_ps4', 'П3 (PS4)', 'ps4', 'activate', 2),
  ('activate_ps5', 'П3 (PS5)', 'ps5', 'activate', 2)
ON CONFLICT (code) DO NOTHING;

ALTER TABLE app.deal_items
  ADD COLUMN IF NOT EXISTS slot_type_code text REFERENCES app.slot_types(code);

CREATE TABLE IF NOT EXISTS app.account_slot_assignments (
  assignment_id bigserial PRIMARY KEY,
  account_id bigint NOT NULL REFERENCES app.accounts(account_id) ON DELETE CASCADE,
  slot_type_code text NOT NULL REFERENCES app.slot_types(code),
  customer_id bigint REFERENCES app.customers(customer_id),
  game_id bigint REFERENCES app.game_titles(game_id),
  deal_id bigint REFERENCES app.deals(deal_id),
  deal_item_id bigint REFERENCES app.deal_items(deal_item_id),
  assigned_at timestamptz NOT NULL DEFAULT now(),
  released_at timestamptz,
  assigned_by text,
  released_by text,
  notes text
);

CREATE INDEX IF NOT EXISTS idx_account_slot_assignments_active
  ON app.account_slot_assignments(account_id, slot_type_code)
  WHERE released_at IS NULL;

CREATE OR REPLACE VIEW app.v_account_slot_status AS
SELECT
  a.account_id,
  st.code AS slot_type_code,
  st.platform_code,
  st.mode,
  st.capacity,
  COALESCE(SUM(CASE WHEN asa.released_at IS NULL THEN 1 ELSE 0 END), 0) AS occupied,
  GREATEST(st.capacity - COALESCE(SUM(CASE WHEN asa.released_at IS NULL THEN 1 ELSE 0 END), 0), 0) AS free
FROM app.accounts a
CROSS JOIN app.slot_types st
LEFT JOIN app.account_slot_assignments asa
  ON asa.account_id = a.account_id AND asa.slot_type_code = st.code
GROUP BY a.account_id, st.code, st.platform_code, st.mode, st.capacity;

COMMIT;
