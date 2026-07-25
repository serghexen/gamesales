-- migrate:no-transaction
-- Ручные ключи храним отдельно от заказов: один пул принадлежит одной карточке конкретного маркетплейса.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS app.marketplace_manual_key_pools (
  id bigserial PRIMARY KEY,
  marketplace text NOT NULL CHECK (marketplace IN ('ozon', 'yandex_market')),
  store_code text NOT NULL,
  product_key text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (marketplace, store_code, product_key)
);

CREATE TABLE IF NOT EXISTS app.marketplace_manual_keys (
  id bigserial PRIMARY KEY,
  pool_id bigint NOT NULL REFERENCES app.marketplace_manual_key_pools(id) ON DELETE RESTRICT,
  code_ciphertext bytea NOT NULL,
  code_hash text NOT NULL UNIQUE,
  code_suffix text NOT NULL DEFAULT '',
  status text NOT NULL DEFAULT 'free' CHECK (status IN ('free', 'reserved', 'sending', 'delivered', 'expired', 'disabled')),
  expires_at date,
  issued_order_ref text NOT NULL DEFAULT '',
  reserved_at timestamptz,
  issued_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_marketplace_manual_keys_pool_status
  ON app.marketplace_manual_keys(pool_id, status, created_at DESC);
