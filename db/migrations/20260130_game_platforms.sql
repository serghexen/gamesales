BEGIN;

CREATE TABLE IF NOT EXISTS app.game_platforms (
  game_id     bigint NOT NULL REFERENCES app.game_titles(game_id) ON DELETE CASCADE,
  platform_id smallint NOT NULL REFERENCES app.platforms(platform_id),
  CONSTRAINT pk_game_platforms PRIMARY KEY (game_id, platform_id)
);

-- Backfill from legacy platform_id
INSERT INTO app.game_platforms(game_id, platform_id)
SELECT game_id, platform_id
FROM app.game_titles
WHERE platform_id IS NOT NULL
ON CONFLICT (game_id, platform_id) DO NOTHING;

COMMIT;
