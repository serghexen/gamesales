-- migrate:no-transaction
-- Локальный read-only снимок позиций DBS-заказов Яндекс Маркета для истории в карточке товара.
CREATE TABLE IF NOT EXISTS app.marketplace_yandex_order_items (
  store_code text NOT NULL,
  order_id bigint NOT NULL,
  item_id bigint NOT NULL,
  campaign_id bigint NOT NULL,
  offer_id text NOT NULL,
  item_name text NOT NULL DEFAULT '',
  quantity integer NOT NULL DEFAULT 0 CHECK (quantity >= 0),
  status text NOT NULL DEFAULT '',
  substatus text NOT NULL DEFAULT '',
  price text NOT NULL DEFAULT '',
  currency_code text NOT NULL DEFAULT '',
  created_at timestamptz,
  updated_at timestamptz,
  synced_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (store_code, order_id, item_id)
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_marketplace_yandex_order_items_offer
  ON app.marketplace_yandex_order_items(store_code, offer_id, created_at DESC, order_id DESC);
