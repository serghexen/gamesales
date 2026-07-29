-- migrate:no-transaction
-- Локальная фиксация выдачи только для fake-заказов тестового кабинета Яндекс Маркета.
ALTER TABLE app.marketplace_yandex_order_items
  ADD COLUMN IF NOT EXISTS is_sandbox boolean NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS app.marketplace_yandex_sandbox_deliveries (
  store_code text NOT NULL,
  order_id bigint NOT NULL,
  item_id bigint NOT NULL,
  offer_id text NOT NULL,
  required_qty integer NOT NULL CHECK (required_qty > 0),
  delivery_source text NOT NULL CHECK (delivery_source IN ('manual', 'pool')),
  status text NOT NULL DEFAULT 'locally_issued' CHECK (status IN ('locally_issued')),
  issued_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (store_code, order_id, item_id),
  FOREIGN KEY (store_code, order_id, item_id)
    REFERENCES app.marketplace_yandex_order_items(store_code, order_id, item_id)
    ON DELETE RESTRICT
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_yandex_market_sandbox_deliveries_offer
  ON app.marketplace_yandex_sandbox_deliveries(store_code, offer_id, issued_at DESC);
