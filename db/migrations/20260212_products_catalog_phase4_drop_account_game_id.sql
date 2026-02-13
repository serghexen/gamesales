BEGIN;

-- В ассетах и назначениях слотов полностью перешли на product_id.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'app' AND table_name = 'account_assets' AND column_name = 'game_id'
  ) THEN
    UPDATE app.account_assets
    SET game_id = NULL
    WHERE game_id IS NOT NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'app' AND table_name = 'account_slot_assignments' AND column_name = 'game_id'
  ) THEN
    UPDATE app.account_slot_assignments
    SET game_id = NULL
    WHERE game_id IS NOT NULL;
  END IF;
END $$;

-- Снимаем ограничения, завязанные на game_id в account_assets.
DO $$
DECLARE
  v_attnum smallint;
  r record;
BEGIN
  SELECT a.attnum
  INTO v_attnum
  FROM pg_attribute a
  WHERE a.attrelid = 'app.account_assets'::regclass
    AND a.attname = 'game_id'
    AND a.attisdropped = false;

  IF v_attnum IS NULL THEN
    RETURN;
  END IF;

  FOR r IN
    SELECT c.conname
    FROM pg_constraint c
    WHERE c.conrelid = 'app.account_assets'::regclass
      AND c.conkey @> ARRAY[v_attnum]::smallint[]
  LOOP
    EXECUTE format('ALTER TABLE app.account_assets DROP CONSTRAINT IF EXISTS %I', r.conname);
  END LOOP;
END $$;

-- Снимаем ограничения, завязанные на game_id в account_slot_assignments.
DO $$
DECLARE
  v_attnum smallint;
  r record;
BEGIN
  SELECT a.attnum
  INTO v_attnum
  FROM pg_attribute a
  WHERE a.attrelid = 'app.account_slot_assignments'::regclass
    AND a.attname = 'game_id'
    AND a.attisdropped = false;

  IF v_attnum IS NULL THEN
    RETURN;
  END IF;

  FOR r IN
    SELECT c.conname
    FROM pg_constraint c
    WHERE c.conrelid = 'app.account_slot_assignments'::regclass
      AND c.conkey @> ARRAY[v_attnum]::smallint[]
  LOOP
    EXECUTE format('ALTER TABLE app.account_slot_assignments DROP CONSTRAINT IF EXISTS %I', r.conname);
  END LOOP;
END $$;

-- Удаляем старые индексы legacy-связки.
DROP INDEX IF EXISTS app.idx_account_assets_game;
DROP INDEX IF EXISTS app.idx_account_assets_account_game;

ALTER TABLE app.account_assets
  DROP COLUMN IF EXISTS game_id;

ALTER TABLE app.account_slot_assignments
  DROP COLUMN IF EXISTS game_id;

COMMIT;
