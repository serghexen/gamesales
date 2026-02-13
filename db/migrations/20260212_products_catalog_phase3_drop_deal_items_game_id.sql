BEGIN;

-- В сделках полностью перешли на product_id; очищаем legacy-колонку game_id.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'app' AND table_name = 'deal_items' AND column_name = 'game_id'
  ) THEN
    UPDATE app.deal_items
    SET game_id = NULL
    WHERE game_id IS NOT NULL;
  END IF;
END $$;

ALTER TABLE app.deal_items
  DROP COLUMN IF EXISTS game_id;

COMMIT;
