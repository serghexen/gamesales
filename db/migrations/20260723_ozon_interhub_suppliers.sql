-- Связь цифровых карточек Ozon с поставщиками ключей и журнал безопасных попыток выдачи.
CREATE TABLE IF NOT EXISTS app.marketplace_ozon_digital_suppliers (
  id bigserial PRIMARY KEY,
  store_code text NOT NULL,
  external_product_id bigint NOT NULL,
  provider_code text NOT NULL,
  priority integer NOT NULL DEFAULT 1,
  enabled boolean NOT NULL DEFAULT false,
  service_id integer NOT NULL,
  nominal_id text NOT NULL DEFAULT '',
  params jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (store_code, external_product_id, provider_code, priority)
);

CREATE TABLE IF NOT EXISTS app.marketplace_ozon_digital_supplier_attempts (
  id bigserial PRIMARY KEY,
  order_id bigint NOT NULL REFERENCES app.marketplace_ozon_digital_orders(id) ON DELETE CASCADE,
  supplier_id bigint NOT NULL REFERENCES app.marketplace_ozon_digital_suppliers(id) ON DELETE RESTRICT,
  agent_transaction_id text NOT NULL UNIQUE,
  state text NOT NULL DEFAULT 'processing',
  provider_status integer NOT NULL DEFAULT 0,
  provider_message text NOT NULL DEFAULT '',
  provider_response jsonb NOT NULL DEFAULT '{}'::jsonb,
  next_status_check_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (order_id, supplier_id)
);

CREATE INDEX IF NOT EXISTS idx_marketplace_ozon_digital_supplier_attempts_pending
  ON app.marketplace_ozon_digital_supplier_attempts(state, next_status_check_at);
