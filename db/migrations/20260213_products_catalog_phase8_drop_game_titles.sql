BEGIN;

-- Поля game-типа перенесены в products/game_products; legacy-таблица больше не используется.
DROP TABLE IF EXISTS app.game_titles;

COMMIT;
