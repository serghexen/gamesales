BEGIN;

ALTER TABLE app.game_titles
  ADD COLUMN IF NOT EXISTS link text,
  ADD COLUMN IF NOT EXISTS logo_url text,
  ADD COLUMN IF NOT EXISTS text_lang text,
  ADD COLUMN IF NOT EXISTS audio_lang text,
  ADD COLUMN IF NOT EXISTS vr_support text;

COMMIT;
