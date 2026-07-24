-- migrate:no-transaction
-- Эта миграция переносит прежнюю startup-инициализацию схемы в отдельный шаг деплоя.

ALTER TABLE app.regions ADD COLUMN IF NOT EXISTS purchase_cost_rate numeric(12,6) NOT NULL DEFAULT 1.0;
ALTER TABLE app.deals ADD COLUMN IF NOT EXISTS completed_at timestamptz;
ALTER TABLE app.deals ADD COLUMN IF NOT EXISTS order_number text;
ALTER TABLE app.deals ADD COLUMN IF NOT EXISTS responsible_username text;
ALTER TABLE app.deals ADD COLUMN IF NOT EXISTS lock_version integer NOT NULL DEFAULT 1;
ALTER TABLE app.accounts ADD COLUMN IF NOT EXISTS is_deactivated boolean NOT NULL DEFAULT false;
ALTER TABLE app.accounts ADD COLUMN IF NOT EXISTS deactivated_at timestamptz;
ALTER TABLE app.accounts ADD COLUMN IF NOT EXISTS next_activation_at timestamptz;

CREATE TABLE IF NOT EXISTS app.account_reserve_claims (
  claim_token uuid PRIMARY KEY,
  account_id bigint NOT NULL REFERENCES app.accounts(account_id) ON DELETE CASCADE,
  reserve_key text NOT NULL,
  claimed_by text NOT NULL DEFAULT '',
  claimed_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (account_id, reserve_key)
);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_account_reserve_claims_account ON app.account_reserve_claims(account_id);

CREATE TABLE IF NOT EXISTS app.subscription_terms (
  term_id bigserial PRIMARY KEY,
  product_id bigint NOT NULL REFERENCES app.subscription_products(product_id) ON DELETE CASCADE,
  account_id bigint NOT NULL REFERENCES app.accounts(account_id) ON DELETE RESTRICT,
  valid_until date NOT NULL,
  notes text,
  is_archived boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_subscription_terms_product ON app.subscription_terms(product_id, valid_until);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_subscription_terms_account ON app.subscription_terms(account_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_subscription_terms_archived ON app.subscription_terms(is_archived);
ALTER TABLE app.deal_items ADD COLUMN IF NOT EXISTS subscription_term_id bigint REFERENCES app.subscription_terms(term_id) ON DELETE RESTRICT;
ALTER TABLE app.account_slot_assignments ADD COLUMN IF NOT EXISTS subscription_term_id bigint REFERENCES app.subscription_terms(term_id) ON DELETE RESTRICT;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_deal_items_subscription_term_id ON app.deal_items(subscription_term_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_slot_assignments_subscription_term_id ON app.account_slot_assignments(subscription_term_id);

CREATE TABLE IF NOT EXISTS app.messengers (
  messenger_id bigserial PRIMARY KEY,
  code text NOT NULL,
  name text NOT NULL,
  is_archived boolean NOT NULL DEFAULT false
);
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_messengers_archived ON app.messengers(is_archived);
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_messengers_code ON app.messengers(code);
ALTER TABLE app.deals ADD COLUMN IF NOT EXISTS messenger_id bigint REFERENCES app.messengers(messenger_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_deals_messenger_id ON app.deals(messenger_id);

CREATE SCHEMA IF NOT EXISTS finance;
CREATE TABLE IF NOT EXISTS finance.cash_flow_opening_balances (
  balance_month date PRIMARY KEY,
  amount numeric(14,2) NOT NULL DEFAULT 0,
  comment text,
  created_by text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS finance.card_balance_snapshots (
  snapshot_id bigserial PRIMARY KEY,
  card_code text NOT NULL,
  region_code text NOT NULL,
  currency text NOT NULL DEFAULT 'TRY',
  amount numeric(14,2) NOT NULL DEFAULT 0,
  comment text,
  created_by text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_card_balance_snapshots_card_created
  ON finance.card_balance_snapshots(card_code, created_at DESC, snapshot_id DESC);
DROP INDEX CONCURRENTLY IF EXISTS app.uq_slot_assignments_active_subscription_term;

INSERT INTO app.deal_flow_statuses(code, name)
VALUES ('draft', 'Черновик')
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS tg.dialog_snapshot (
  chat_id bigint PRIMARY KEY,
  title text NOT NULL DEFAULT '',
  unread_count integer NOT NULL DEFAULT 0,
  is_group boolean NOT NULL DEFAULT false,
  is_channel boolean NOT NULL DEFAULT false,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tg_dialog_snapshot_updated_at ON tg.dialog_snapshot(updated_at DESC);

CREATE TABLE IF NOT EXISTS app.interhub_transactions (
  agent_transaction_id text PRIMARY KEY,
  service_id integer NOT NULL,
  account text NOT NULL DEFAULT '',
  amount numeric(14,2) NOT NULL DEFAULT 0,
  request_params jsonb NOT NULL DEFAULT '{}'::jsonb,
  state text NOT NULL DEFAULT 'checked',
  provider_status integer NOT NULL DEFAULT 0,
  provider_message text NOT NULL DEFAULT '',
  provider_transaction_id text NOT NULL DEFAULT '',
  gift_code text NOT NULL DEFAULT '',
  provider_response jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by text NOT NULL DEFAULT '',
  ozon_order_id bigint,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  status_check_attempts integer NOT NULL DEFAULT 0,
  next_status_check_at timestamptz
);
ALTER TABLE app.interhub_transactions ADD COLUMN IF NOT EXISTS status_check_attempts integer NOT NULL DEFAULT 0;
ALTER TABLE app.interhub_transactions ADD COLUMN IF NOT EXISTS ozon_order_id bigint;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_interhub_transactions_ozon_order
  ON app.interhub_transactions(ozon_order_id, created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_interhub_transactions_pending
  ON app.interhub_transactions(state, next_status_check_at);

CREATE TABLE IF NOT EXISTS app.interhub_price_calculations (
  id bigserial PRIMARY KEY,
  batch_id text NOT NULL,
  service_id integer NOT NULL,
  service_title text NOT NULL DEFAULT '',
  category text NOT NULL DEFAULT '',
  service_type text NOT NULL DEFAULT '',
  nominal_id integer NOT NULL,
  nominal_title text NOT NULL DEFAULT '',
  success boolean NOT NULL DEFAULT false,
  provider_status integer NOT NULL DEFAULT 0,
  provider_message text NOT NULL DEFAULT '',
  fixed_amount numeric(14,2) NOT NULL DEFAULT 0,
  provider_response jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by text NOT NULL DEFAULT '',
  calculated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_interhub_price_calculations_latest
  ON app.interhub_price_calculations(service_id, nominal_id, calculated_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_interhub_price_calculations_batch
  ON app.interhub_price_calculations(batch_id, calculated_at DESC);

CREATE TABLE IF NOT EXISTS app.marketplace_ozon_catalog_items (
  store_code text NOT NULL,
  external_product_id bigint NOT NULL,
  offer_id text NOT NULL DEFAULT '',
  title text NOT NULL DEFAULT '',
  visibility text NOT NULL DEFAULT '',
  state text NOT NULL DEFAULT '',
  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  synced_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (store_code, external_product_id)
);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_marketplace_ozon_catalog_offer
  ON app.marketplace_ozon_catalog_items(store_code, offer_id);

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
  ozon_status text NOT NULL DEFAULT '',
  waiting_deadline_at timestamptz,
  created_at timestamptz,
  delivered_at timestamptz,
  delivered_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
  last_error text NOT NULL DEFAULT '',
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (store_code, posting_number, sku)
);
ALTER TABLE app.marketplace_ozon_digital_orders ADD COLUMN IF NOT EXISTS ozon_status text NOT NULL DEFAULT '';
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_marketplace_ozon_digital_orders_product
  ON app.marketplace_ozon_digital_orders(store_code, external_product_id, status, created_at DESC);

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
  updated_at timestamptz NOT NULL DEFAULT now()
);
DO $$
DECLARE constraint_name text;
BEGIN
  SELECT constraint_row.conname INTO constraint_name
  FROM pg_constraint AS constraint_row
  JOIN pg_attribute AS attribute_row
    ON attribute_row.attrelid=constraint_row.conrelid
   AND attribute_row.attnum=ANY(constraint_row.conkey)
  WHERE constraint_row.conrelid='app.marketplace_ozon_digital_supplier_attempts'::regclass
    AND constraint_row.contype='u'
  GROUP BY constraint_row.conname, constraint_row.conkey
  HAVING array_agg(attribute_row.attname::text ORDER BY array_position(constraint_row.conkey, attribute_row.attnum))
    = ARRAY['order_id', 'supplier_id']
  LIMIT 1;
  IF constraint_name IS NOT NULL THEN
    EXECUTE 'ALTER TABLE app.marketplace_ozon_digital_supplier_attempts DROP CONSTRAINT ' || quote_ident(constraint_name);
  END IF;
END $$;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_marketplace_ozon_digital_supplier_attempts_pending
  ON app.marketplace_ozon_digital_supplier_attempts(state, next_status_check_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_marketplace_ozon_digital_supplier_attempts_order_supplier
  ON app.marketplace_ozon_digital_supplier_attempts(order_id, supplier_id, updated_at DESC);
