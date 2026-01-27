CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE IF NOT EXISTS app.platforms (
  platform_id  smallserial PRIMARY KEY,
  code         text NOT NULL UNIQUE,
  name         text NOT NULL
);

CREATE TABLE IF NOT EXISTS app.regions (
  region_id smallserial PRIMARY KEY,
  code      text NOT NULL UNIQUE,
  name      text NOT NULL
);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'account_status' AND typnamespace = 'app'::regnamespace) THEN
    CREATE TYPE app.account_status AS ENUM ('active','banned','archived','problem');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'asset_type' AND typnamespace = 'app'::regnamespace) THEN
    CREATE TYPE app.asset_type AS ENUM ('game','subscription','dlc','other');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'deal_type' AND typnamespace = 'app'::regnamespace) THEN
    CREATE TYPE app.deal_type AS ENUM ('sale','rental','expense','adjustment');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'deal_status' AND typnamespace = 'app'::regnamespace) THEN
    CREATE TYPE app.deal_status AS ENUM ('draft','confirmed','cancelled','closed');
  END IF;
END$$;

CREATE TABLE IF NOT EXISTS app.game_titles (
  game_id      bigserial PRIMARY KEY,
  title        text NOT NULL,
  platform_id  smallint REFERENCES app.platforms(platform_id),
  region_id    smallint REFERENCES app.regions(region_id),
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_game_titles_title ON app.game_titles (title);

CREATE TABLE IF NOT EXISTS app.accounts (
  account_id     bigserial PRIMARY KEY,
  nickname       text NOT NULL UNIQUE,
  platform_id    smallint NOT NULL REFERENCES app.platforms(platform_id),
  region_id      smallint REFERENCES app.regions(region_id),
  status         app.account_status NOT NULL DEFAULT 'active',
  created_at     timestamptz NOT NULL DEFAULT now(),
  notes          text,
  slot_capacity  integer NOT NULL DEFAULT 1,
  slot_reserved  integer NOT NULL DEFAULT 0,
  CONSTRAINT ck_slots_nonneg CHECK (slot_capacity >= 0 AND slot_reserved >= 0),
  CONSTRAINT ck_slots_capacity CHECK (slot_capacity >= slot_reserved)
);

CREATE TABLE IF NOT EXISTS app.account_assets (
  account_asset_id bigserial PRIMARY KEY,
  account_id       bigint NOT NULL REFERENCES app.accounts(account_id) ON DELETE CASCADE,
  game_id          bigint NOT NULL REFERENCES app.game_titles(game_id) ON DELETE RESTRICT,
  asset_type       app.asset_type NOT NULL DEFAULT 'game',
  notes            text,
  UNIQUE (account_id, game_id, asset_type)
);

CREATE TABLE IF NOT EXISTS app.customers (
  customer_id bigserial PRIMARY KEY,
  nickname    text NOT NULL,
  contacts    text,
  notes       text,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.deals (
  deal_id      bigserial PRIMARY KEY,
  deal_type    app.deal_type NOT NULL,
  status       app.deal_status NOT NULL DEFAULT 'confirmed',
  customer_id  bigint REFERENCES app.customers(customer_id),
  currency     text NOT NULL DEFAULT 'RUB',
  total_amount numeric(14,2),
  notes        text,
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.deal_items (
  deal_item_id     bigserial PRIMARY KEY,
  deal_id          bigint NOT NULL REFERENCES app.deals(deal_id) ON DELETE CASCADE,
  account_id       bigint REFERENCES app.accounts(account_id) ON DELETE RESTRICT,
  account_asset_id bigint REFERENCES app.account_assets(account_asset_id) ON DELETE RESTRICT,
  qty              integer NOT NULL DEFAULT 1,
  price            numeric(14,2) NOT NULL DEFAULT 0,
  fee              numeric(14,2) NOT NULL DEFAULT 0,
  start_at         timestamptz,
  end_at           timestamptz,
  returned_at      timestamptz,
  slots_used       integer NOT NULL DEFAULT 1,
  notes            text,
  CONSTRAINT ck_qty_positive CHECK (qty > 0),
  CONSTRAINT ck_slots_used_nonneg CHECK (slots_used >= 0),
  CONSTRAINT ck_lease_window CHECK (end_at IS NULL OR start_at IS NULL OR end_at >= start_at),
  CONSTRAINT ck_one_target CHECK ((account_id IS NOT NULL)::int + (account_asset_id IS NOT NULL)::int >= 1)
);

CREATE OR REPLACE VIEW app.v_account_slots AS
SELECT
  a.account_id,
  a.slot_capacity,
  a.slot_reserved,
  COALESCE(SUM(
    CASE
      WHEN d.deal_type = 'rental'
       AND d.status = 'confirmed'
       AND di.returned_at IS NULL
       AND (di.start_at IS NULL OR di.start_at <= now())
       AND (di.end_at   IS NULL OR di.end_at   >= now())
      THEN di.slots_used
      ELSE 0
    END
  ), 0) AS occupied_slots,
  GREATEST(
    a.slot_capacity - a.slot_reserved - COALESCE(SUM(
      CASE
        WHEN d.deal_type = 'rental'
         AND d.status = 'confirmed'
         AND di.returned_at IS NULL
         AND (di.start_at IS NULL OR di.start_at <= now())
         AND (di.end_at   IS NULL OR di.end_at   >= now())
        THEN di.slots_used
        ELSE 0
      END
    ), 0),
    0
  ) AS free_slots
FROM app.accounts a
LEFT JOIN app.deal_items di ON di.account_id = a.account_id
LEFT JOIN app.deals d ON d.deal_id = di.deal_id
GROUP BY a.account_id, a.slot_capacity, a.slot_reserved;

INSERT INTO app.platforms(code, name)
VALUES ('steam','Steam'),('psn','PlayStation Network'),('xbox','Xbox'),('epic','Epic Games')
ON CONFLICT (code) DO NOTHING;

INSERT INTO app.regions(code, name)
VALUES ('RU','Russia'),('TR','Turkey'),('US','USA'),('EU','Europe')
ON CONFLICT (code) DO NOTHING;
