-- migrate:no-transaction
-- Хранит только безопасный read-only снимок позиций заказов подключенных магазинов.
CREATE TABLE IF NOT EXISTS marketplace.order_items (
  connection_id bigint NOT NULL REFERENCES marketplace.connections(id) ON DELETE CASCADE,
  external_order_id text NOT NULL,
  external_item_id text NOT NULL,
  offer_id text NOT NULL DEFAULT '',
  sku text NOT NULL DEFAULT '',
  title text NOT NULL DEFAULT '',
  quantity integer NOT NULL DEFAULT 1 CHECK (quantity >= 0),
  status text NOT NULL DEFAULT '',
  substatus text NOT NULL DEFAULT '',
  delivery_type text NOT NULL DEFAULT '',
  created_at timestamptz,
  updated_at timestamptz,
  synced_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (connection_id, external_order_id, external_item_id)
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_marketplace_order_items_connection_created
  ON marketplace.order_items(connection_id, created_at DESC, external_order_id DESC);
