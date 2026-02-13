BEGIN;

-- Единый справочник типов товаров.
CREATE TABLE IF NOT EXISTS app.product_types (
  code text PRIMARY KEY,
  name text NOT NULL,
  is_archived boolean NOT NULL DEFAULT false
);

COMMENT ON TABLE app.product_types IS 'Справочник типов товаров';
COMMENT ON COLUMN app.product_types.code IS 'Код типа товара (game/subscription/...)';
COMMENT ON COLUMN app.product_types.name IS 'Название типа товара';
COMMENT ON COLUMN app.product_types.is_archived IS 'Архивная запись';

INSERT INTO app.product_types(code, name)
VALUES
  ('game', 'Игра'),
  ('subscription', 'Подписка')
ON CONFLICT (code) DO NOTHING;

-- Единый справочник товаров.
CREATE TABLE IF NOT EXISTS app.products (
  product_id bigserial PRIMARY KEY,
  type_code text NOT NULL REFERENCES app.product_types(code),
  title text NOT NULL,
  short_title text,
  region_id smallint REFERENCES app.regions(region_id),
  is_archived boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  legacy_game_id bigint UNIQUE
);

COMMENT ON TABLE app.products IS 'Единый справочник товаров';
COMMENT ON COLUMN app.products.product_id IS 'Идентификатор товара';
COMMENT ON COLUMN app.products.type_code IS 'Тип товара';
COMMENT ON COLUMN app.products.title IS 'Название товара';
COMMENT ON COLUMN app.products.short_title IS 'Короткое название товара';
COMMENT ON COLUMN app.products.region_id IS 'Регион товара';
COMMENT ON COLUMN app.products.is_archived IS 'Архивная запись';
COMMENT ON COLUMN app.products.created_at IS 'Дата создания записи';
COMMENT ON COLUMN app.products.legacy_game_id IS 'Ссылка на legacy game_id для поэтапной миграции';

CREATE INDEX IF NOT EXISTS ix_products_type ON app.products (type_code);
CREATE INDEX IF NOT EXISTS ix_products_title ON app.products (title);
CREATE INDEX IF NOT EXISTS ix_products_archived ON app.products (is_archived);

-- Специализация для игровых товаров.
CREATE TABLE IF NOT EXISTS app.game_products (
  product_id bigint PRIMARY KEY REFERENCES app.products(product_id) ON DELETE CASCADE,
  link text,
  logo_url text,
  logo_blob bytea,
  logo_mime text,
  text_lang text,
  audio_lang text,
  vr_support text
);

COMMENT ON TABLE app.game_products IS 'Игровые атрибуты товара';
COMMENT ON COLUMN app.game_products.product_id IS 'Ссылка на товар типа game';

-- Специализация для подписок (поля пока необязательные).
CREATE TABLE IF NOT EXISTS app.subscription_products (
  product_id bigint PRIMARY KEY REFERENCES app.products(product_id) ON DELETE CASCADE,
  provider text,
  billing_period text,
  notes text
);

COMMENT ON TABLE app.subscription_products IS 'Атрибуты товара типа subscription';
COMMENT ON COLUMN app.subscription_products.product_id IS 'Ссылка на товар типа subscription';

-- Дочерние сущности подписок на будущее (планы/тарифы).
CREATE TABLE IF NOT EXISTS app.subscription_plans (
  plan_id bigserial PRIMARY KEY,
  product_id bigint NOT NULL REFERENCES app.subscription_products(product_id) ON DELETE CASCADE,
  name text,
  duration_months integer,
  is_active boolean NOT NULL DEFAULT true,
  price numeric(14,2),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_subscription_plans_duration_nonneg CHECK (duration_months IS NULL OR duration_months >= 0),
  CONSTRAINT ck_subscription_plans_price_nonneg CHECK (price IS NULL OR price >= 0)
);

CREATE INDEX IF NOT EXISTS ix_subscription_plans_product ON app.subscription_plans (product_id);

COMMENT ON TABLE app.subscription_plans IS 'Дочерние тарифы/планы подписки';
COMMENT ON COLUMN app.subscription_plans.product_id IS 'Товар подписки';

-- Добавляем ссылку из legacy-таблицы игр на новый товар.
ALTER TABLE app.game_titles
  ADD COLUMN IF NOT EXISTS product_id bigint;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_game_titles_product_id'
      AND conrelid = 'app.game_titles'::regclass
  ) THEN
    ALTER TABLE app.game_titles
      ADD CONSTRAINT fk_game_titles_product_id
      FOREIGN KEY (product_id) REFERENCES app.products(product_id) ON DELETE SET NULL;
  END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_game_titles_product_id
  ON app.game_titles (product_id)
  WHERE product_id IS NOT NULL;

-- Бэкфилл товаров из существующего справочника игр.
-- Классифицируем как subscription, если в title есть "под" или "плюс".
INSERT INTO app.products(type_code, title, short_title, region_id, is_archived, created_at, legacy_game_id)
SELECT
  CASE
    WHEN lower(g.title) LIKE '%под%' OR lower(g.title) LIKE '%плюс%'
      THEN 'subscription'
    ELSE 'game'
  END AS type_code,
  g.title,
  g.short_title,
  g.region_id,
  g.is_archived,
  g.created_at,
  g.game_id
FROM app.game_titles g
LEFT JOIN app.products p ON p.legacy_game_id = g.game_id
WHERE p.product_id IS NULL;

-- Синхронизируем обратную ссылку game_titles -> products.
UPDATE app.game_titles g
SET product_id = p.product_id
FROM app.products p
WHERE p.legacy_game_id = g.game_id
  AND (g.product_id IS NULL OR g.product_id <> p.product_id);

-- Заполняем игровые атрибуты только для товаров типа game.
INSERT INTO app.game_products(product_id, link, logo_url, logo_blob, logo_mime, text_lang, audio_lang, vr_support)
SELECT
  p.product_id,
  g.link,
  g.logo_url,
  g.logo_blob,
  g.logo_mime,
  g.text_lang,
  g.audio_lang,
  g.vr_support
FROM app.game_titles g
JOIN app.products p ON p.legacy_game_id = g.game_id
LEFT JOIN app.game_products gp ON gp.product_id = p.product_id
WHERE p.type_code = 'game'
  AND gp.product_id IS NULL;

-- Создаём записи специализации для подписок.
INSERT INTO app.subscription_products(product_id)
SELECT p.product_id
FROM app.products p
LEFT JOIN app.subscription_products sp ON sp.product_id = p.product_id
WHERE p.type_code = 'subscription'
  AND sp.product_id IS NULL;

COMMIT;
