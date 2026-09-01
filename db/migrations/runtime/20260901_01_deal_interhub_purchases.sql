-- migrate:no-transaction
-- Связывает покупки кодов Interhub со сделкой и не допускает две незавершённые выдачи одновременно.

ALTER TABLE app.interhub_transactions
  ADD COLUMN IF NOT EXISTS deal_id bigint REFERENCES app.deals(deal_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_interhub_transactions_deal_history
  ON app.interhub_transactions(deal_id, created_at DESC)
  WHERE deal_id IS NOT NULL;

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_interhub_transactions_deal_active
  ON app.interhub_transactions(deal_id)
  WHERE deal_id IS NOT NULL AND state IN ('checked', 'processing');
