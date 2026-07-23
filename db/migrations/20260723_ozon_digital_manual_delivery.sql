-- Ручная выдача цифровых ключей Ozon: лимиты карточек, очередь заказов и история отправки.
CREATE TABLE IF NOT EXISTS app.marketplace_ozon_digital_settings (
  store_code text NOT NULL,
  external_product_id bigint NOT NULL,
  offer_id text NOT NULL DEFAULT '',
  manual_stock_limit integer NOT NULL DEFAULT 0,
  auto_issue_enabled boolean NOT NULL DEFAULT false,
  activation_instruction text NOT NULL DEFAULT '',
  support_error_message text NOT NULL DEFAULT '',
  published_stock integer NOT NULL DEFAULT 0,
  last_stock_sync_at timestamptz,
  last_orders_sync_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (store_code, external_product_id)
);

CREATE TABLE IF NOT EXISTS app.marketplace_ozon_digital_orders (
  id bigserial PRIMARY KEY,
  store_code text NOT NULL,
  external_product_id bigint NOT NULL,
  posting_number text NOT NULL,
  order_number text NOT NULL DEFAULT '',
  product_name text NOT NULL DEFAULT '',
  sku bigint NOT NULL,
  required_qty integer NOT NULL DEFAULT 1,
  status text NOT NULL DEFAULT 'manual_required',
  waiting_deadline_at timestamptz,
  created_at timestamptz,
  delivered_at timestamptz,
  delivered_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
  last_error text NOT NULL DEFAULT '',
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (store_code, posting_number, sku)
);

CREATE INDEX IF NOT EXISTS idx_marketplace_ozon_digital_orders_product
  ON app.marketplace_ozon_digital_orders(store_code, external_product_id, status, created_at DESC);
