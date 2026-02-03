BEGIN;

ALTER TABLE app.deal_items
  DROP CONSTRAINT IF EXISTS ck_one_target;

COMMIT;
