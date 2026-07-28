-- migrate:no-transaction
-- Снимок карточек Яндекс Маркета и ручные лимиты остатка для DBS без очереди выдачи ключей.
CREATE TABLE IF NOT EXISTS app.marketplace_yandex_catalog_items (
  store_code text NOT NULL,
  offer_id text NOT NULL,
  market_sku bigint,
  title text NOT NULL DEFAULT '',
  archived boolean NOT NULL DEFAULT false,
  card_status text NOT NULL DEFAULT '',
  category_name text NOT NULL DEFAULT '',
  downloadable boolean NOT NULL DEFAULT false,
  price text NOT NULL DEFAULT '',
  currency_code text NOT NULL DEFAULT '',
  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  synced_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (store_code, offer_id)
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_marketplace_yandex_catalog_items_listing
  ON app.marketplace_yandex_catalog_items(store_code, archived, title, offer_id);

CREATE TABLE IF NOT EXISTS app.marketplace_yandex_stock_settings (
  store_code text NOT NULL,
  offer_id text NOT NULL,
  manual_stock_limit integer NOT NULL DEFAULT 0 CHECK (manual_stock_limit >= 0),
  published_stock integer NOT NULL DEFAULT 0 CHECK (published_stock >= 0),
  last_stock_sync_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (store_code, offer_id),
  FOREIGN KEY (store_code, offer_id)
    REFERENCES app.marketplace_yandex_catalog_items(store_code, offer_id)
    ON DELETE RESTRICT
);
