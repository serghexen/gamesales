BEGIN;

ALTER TABLE app.game_titles
  ADD COLUMN IF NOT EXISTS logo_blob bytea,
  ADD COLUMN IF NOT EXISTS logo_mime text;

COMMIT;
