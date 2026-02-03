BEGIN;

ALTER TABLE app.account_assets
  ALTER COLUMN game_id DROP NOT NULL;

COMMIT;
