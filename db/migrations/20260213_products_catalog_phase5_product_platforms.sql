BEGIN;

-- Нейтральная связка товар <-> платформа (без legacy game_id).
CREATE TABLE IF NOT EXISTS app.product_platforms (
  product_id bigint NOT NULL REFERENCES app.products(product_id) ON DELETE CASCADE,
  platform_id smallint NOT NULL REFERENCES app.platforms(platform_id),
  CONSTRAINT pk_product_platforms PRIMARY KEY (product_id, platform_id)
);

COMMENT ON TABLE app.product_platforms IS 'Связь товаров и платформ';
COMMENT ON COLUMN app.product_platforms.product_id IS 'Товар';
COMMENT ON COLUMN app.product_platforms.platform_id IS 'Платформа';

CREATE INDEX IF NOT EXISTS ix_product_platforms_platform_id
  ON app.product_platforms(platform_id);

-- Бэкфилл из текущего legacy-слоя game_titles/game_platforms.
INSERT INTO app.product_platforms(product_id, platform_id)
SELECT DISTINCT
  gt.product_id,
  gp.platform_id
FROM app.game_platforms gp
JOIN app.game_titles gt ON gt.game_id = gp.game_id
WHERE gt.product_id IS NOT NULL
ON CONFLICT (product_id, platform_id) DO NOTHING;

-- Синхронизация: пока старый код пишет в game_platforms, держим product_platforms актуальным.
CREATE OR REPLACE FUNCTION app.sync_product_platforms_from_game_platforms()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  v_product_id bigint;
BEGIN
  IF TG_OP = 'INSERT' THEN
    SELECT gt.product_id INTO v_product_id
    FROM app.game_titles gt
    WHERE gt.game_id = NEW.game_id;

    IF v_product_id IS NOT NULL THEN
      INSERT INTO app.product_platforms(product_id, platform_id)
      VALUES (v_product_id, NEW.platform_id)
      ON CONFLICT (product_id, platform_id) DO NOTHING;
    END IF;
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    SELECT gt.product_id INTO v_product_id
    FROM app.game_titles gt
    WHERE gt.game_id = OLD.game_id;

    IF v_product_id IS NOT NULL THEN
      DELETE FROM app.product_platforms pp
      WHERE pp.product_id = v_product_id
        AND pp.platform_id = OLD.platform_id;
    END IF;
    RETURN OLD;
  ELSE
    -- UPDATE: пересобираем через delete+insert для пары game_id/platform_id.
    SELECT gt.product_id INTO v_product_id
    FROM app.game_titles gt
    WHERE gt.game_id = OLD.game_id;

    IF v_product_id IS NOT NULL THEN
      DELETE FROM app.product_platforms pp
      WHERE pp.product_id = v_product_id
        AND pp.platform_id = OLD.platform_id;
    END IF;

    SELECT gt.product_id INTO v_product_id
    FROM app.game_titles gt
    WHERE gt.game_id = NEW.game_id;

    IF v_product_id IS NOT NULL THEN
      INSERT INTO app.product_platforms(product_id, platform_id)
      VALUES (v_product_id, NEW.platform_id)
      ON CONFLICT (product_id, platform_id) DO NOTHING;
    END IF;
    RETURN NEW;
  END IF;
END $$;

DROP TRIGGER IF EXISTS trg_sync_product_platforms_from_game_platforms ON app.game_platforms;

CREATE TRIGGER trg_sync_product_platforms_from_game_platforms
AFTER INSERT OR UPDATE OR DELETE ON app.game_platforms
FOR EACH ROW
EXECUTE FUNCTION app.sync_product_platforms_from_game_platforms();

COMMIT;
