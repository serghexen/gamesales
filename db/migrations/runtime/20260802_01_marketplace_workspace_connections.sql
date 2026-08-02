-- Изолирует данные нового Marketplace-продукта от существующего CRM-контура.
CREATE SCHEMA IF NOT EXISTS marketplace;

CREATE TABLE IF NOT EXISTS marketplace.workspaces (
  id bigserial PRIMARY KEY,
  name text NOT NULL,
  owner_user_id bigint NOT NULL REFERENCES app.users(user_id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS marketplace.workspace_members (
  workspace_id bigint NOT NULL REFERENCES marketplace.workspaces(id) ON DELETE CASCADE,
  user_id bigint NOT NULL REFERENCES app.users(user_id) ON DELETE RESTRICT,
  role_code text NOT NULL DEFAULT 'owner' CHECK (role_code IN ('owner', 'operator', 'viewer')),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, user_id)
);

CREATE TABLE IF NOT EXISTS marketplace.connections (
  id bigserial PRIMARY KEY,
  workspace_id bigint NOT NULL REFERENCES marketplace.workspaces(id) ON DELETE CASCADE,
  provider_code text NOT NULL CHECK (provider_code IN ('ozon', 'yandex_market')),
  display_name text NOT NULL,
  client_id text NOT NULL DEFAULT '',
  token_ciphertext bytea NOT NULL,
  token_suffix text NOT NULL DEFAULT '',
  status text NOT NULL DEFAULT 'saved' CHECK (status IN ('saved', 'active', 'error', 'disabled')),
  last_checked_at timestamptz,
  last_error text NOT NULL DEFAULT '',
  created_by_user_id bigint NOT NULL REFERENCES app.users(user_id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, provider_code, client_id)
);
