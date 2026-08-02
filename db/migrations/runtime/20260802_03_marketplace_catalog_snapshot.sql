-- migrate:no-transaction
-- Хранит только снимок каталога подключенного магазина, не меняя товары на стороне маркетплейса.
CREATE TABLE IF NOT EXISTS marketplace.catalog_items (
  connection_id bigint NOT NULL REFERENCES marketplace.connections(id) ON DELETE CASCADE,
  external_product_id text NOT NULL,
  offer_id text NOT NULL DEFAULT '',
  title text NOT NULL DEFAULT '',
  status text NOT NULL DEFAULT '',
  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  synced_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (connection_id, external_product_id)
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_marketplace_catalog_items_connection_synced
  ON marketplace.catalog_items(connection_id, synced_at DESC);
