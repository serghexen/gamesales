BEGIN;

-- После перехода записи платформ на product_platforms синхронизирующий триггер больше не нужен.
DROP TRIGGER IF EXISTS trg_sync_product_platforms_from_game_platforms ON app.game_platforms;
DROP FUNCTION IF EXISTS app.sync_product_platforms_from_game_platforms();

COMMIT;
