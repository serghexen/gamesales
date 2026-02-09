BEGIN;

ALTER TABLE app.deals
  ADD COLUMN IF NOT EXISTS order_number text,
  ADD COLUMN IF NOT EXISTS responsible_username text;

COMMIT;
