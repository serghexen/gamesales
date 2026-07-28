-- migrate:no-transaction
-- Хранит устойчивое состояние массовой покупки ваучеров, чтобы повтор запроса не создал дополнительные списания.

ALTER TABLE app.interhub_transactions
  ADD COLUMN IF NOT EXISTS voucher_batch_id uuid;
ALTER TABLE app.interhub_transactions
  ADD COLUMN IF NOT EXISTS voucher_batch_position integer;

CREATE TABLE IF NOT EXISTS app.interhub_voucher_purchase_batches (
  batch_id uuid PRIMARY KEY,
  first_agent_transaction_id text NOT NULL UNIQUE,
  service_id integer NOT NULL,
  account text NOT NULL DEFAULT '',
  amount numeric(14,2) NOT NULL DEFAULT 0,
  request_params jsonb NOT NULL DEFAULT '{}'::jsonb,
  requested_quantity integer NOT NULL CHECK (requested_quantity BETWEEN 1 AND 20),
  state text NOT NULL DEFAULT 'ready',
  message text NOT NULL DEFAULT '',
  active_agent_transaction_id text NOT NULL DEFAULT '',
  lease_token uuid,
  lease_expires_at timestamptz,
  created_by text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_interhub_transactions_voucher_batch_position
  ON app.interhub_transactions(voucher_batch_id, voucher_batch_position)
  WHERE voucher_batch_id IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_interhub_voucher_purchase_batches_lease
  ON app.interhub_voucher_purchase_batches(state, lease_expires_at);
