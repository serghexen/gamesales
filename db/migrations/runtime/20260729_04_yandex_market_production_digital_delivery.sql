-- migrate:no-transaction
-- Боевой контур цифровой выдачи Яндекс Маркета. По умолчанию все переключатели выключены.
ALTER TABLE app.marketplace_yandex_stock_settings
  ADD COLUMN IF NOT EXISTS auto_issue_enabled boolean NOT NULL DEFAULT false;

ALTER TABLE app.marketplace_yandex_stock_settings
  ADD COLUMN IF NOT EXISTS pool_issue_enabled boolean NOT NULL DEFAULT false;

ALTER TABLE app.marketplace_yandex_stock_settings
  ADD COLUMN IF NOT EXISTS support_error_message text NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS app.marketplace_yandex_digital_suppliers (
  id bigserial PRIMARY KEY,
  store_code text NOT NULL,
  offer_id text NOT NULL,
  provider_code text NOT NULL,
  priority integer NOT NULL DEFAULT 1,
  enabled boolean NOT NULL DEFAULT false,
  service_id integer NOT NULL,
  nominal_id text NOT NULL DEFAULT '',
  params jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (store_code, offer_id, provider_code, priority),
  FOREIGN KEY (store_code, offer_id)
    REFERENCES app.marketplace_yandex_catalog_items(store_code, offer_id)
    ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS app.marketplace_yandex_digital_deliveries (
  id bigserial PRIMARY KEY,
  store_code text NOT NULL,
  order_id bigint NOT NULL,
  item_id bigint NOT NULL,
  offer_id text NOT NULL,
  required_qty integer NOT NULL CHECK (required_qty > 0),
  delivered_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
  status text NOT NULL DEFAULT 'manual_required'
    CHECK (status IN ('manual_required', 'supplier_processing', 'market_sending', 'market_submitted', 'market_unknown', 'market_delivered', 'cancelled')),
  last_error text NOT NULL DEFAULT '',
  market_submitted_at timestamptz,
  delivered_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (store_code, order_id, item_id),
  FOREIGN KEY (store_code, order_id, item_id)
    REFERENCES app.marketplace_yandex_order_items(store_code, order_id, item_id)
    ON DELETE RESTRICT
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_yandex_market_digital_deliveries_queue
  ON app.marketplace_yandex_digital_deliveries(store_code, offer_id, status, created_at DESC);

CREATE TABLE IF NOT EXISTS app.marketplace_yandex_digital_code_registry (
  code_hash text PRIMARY KEY,
  delivery_id bigint NOT NULL REFERENCES app.marketplace_yandex_digital_deliveries(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.marketplace_yandex_digital_supplier_attempts (
  id bigserial PRIMARY KEY,
  delivery_id bigint NOT NULL REFERENCES app.marketplace_yandex_digital_deliveries(id) ON DELETE CASCADE,
  supplier_id bigint NOT NULL REFERENCES app.marketplace_yandex_digital_suppliers(id) ON DELETE RESTRICT,
  agent_transaction_id text NOT NULL UNIQUE,
  state text NOT NULL DEFAULT 'processing' CHECK (state IN ('processing', 'paid', 'failed', 'manual_required')),
  provider_status integer NOT NULL DEFAULT 0,
  provider_message text NOT NULL DEFAULT '',
  provider_response jsonb NOT NULL DEFAULT '{}'::jsonb,
  next_status_check_at timestamptz,
  status_check_attempts integer NOT NULL DEFAULT 0 CHECK (status_check_attempts >= 0),
  status_check_lock_token uuid,
  status_check_locked_until timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_yandex_market_supplier_attempts_due
  ON app.marketplace_yandex_digital_supplier_attempts(state, next_status_check_at, status_check_locked_until);
