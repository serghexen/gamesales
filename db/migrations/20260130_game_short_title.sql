BEGIN;

ALTER TABLE app.game_titles
  ADD COLUMN IF NOT EXISTS short_title text;

COMMIT;
