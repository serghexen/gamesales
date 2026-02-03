BEGIN;

CREATE TABLE IF NOT EXISTS app.deal_flow_statuses (
  code text PRIMARY KEY,
  name text NOT NULL
);

INSERT INTO app.deal_flow_statuses(code, name)
VALUES
  ('pending', 'В ожидании'),
  ('completed', 'Завершен')
ON CONFLICT (code) DO NOTHING;

ALTER TABLE app.deals
  ADD COLUMN IF NOT EXISTS flow_status_code text NOT NULL DEFAULT 'pending' REFERENCES app.deal_flow_statuses(code),
  ADD COLUMN IF NOT EXISTS region_id smallint REFERENCES app.regions(region_id);

ALTER TABLE app.deal_items
  ADD COLUMN IF NOT EXISTS purchase_cost numeric(12,2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS game_link text;

UPDATE app.deal_types
SET name = 'Шеринг'
WHERE code = 'rental';

CREATE TABLE IF NOT EXISTS app.deal_audit (
  audit_id bigserial PRIMARY KEY,
  deal_id bigint,
  deal_item_id bigint,
  table_name text NOT NULL,
  action text NOT NULL,
  changed_at timestamptz NOT NULL DEFAULT now(),
  changed_by text,
  old_data jsonb,
  new_data jsonb
);

CREATE OR REPLACE FUNCTION app.log_deal_audit()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  v_user text;
BEGIN
  v_user := current_setting('app.user', true);
  IF TG_OP = 'UPDATE' THEN
    IF to_jsonb(OLD) IS DISTINCT FROM to_jsonb(NEW) THEN
      INSERT INTO app.deal_audit(
        deal_id,
        deal_item_id,
        table_name,
        action,
        changed_by,
        old_data,
        new_data
      )
      VALUES (
        NEW.deal_id,
        CASE WHEN TG_TABLE_NAME = 'deal_items' THEN NEW.deal_item_id ELSE NULL END,
        TG_TABLE_NAME,
        TG_OP,
        v_user,
        to_jsonb(OLD),
        to_jsonb(NEW)
      );
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_deals_audit ON app.deals;
CREATE TRIGGER trg_deals_audit
AFTER UPDATE ON app.deals
FOR EACH ROW EXECUTE FUNCTION app.log_deal_audit();

DROP TRIGGER IF EXISTS trg_deal_items_audit ON app.deal_items;
CREATE TRIGGER trg_deal_items_audit
AFTER UPDATE ON app.deal_items
FOR EACH ROW EXECUTE FUNCTION app.log_deal_audit();

COMMIT;
