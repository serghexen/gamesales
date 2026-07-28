-- migrate:no-transaction
-- Ускоряет выборку оплаченных операций InterHub для истории продаж и фильтра по датам.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_interhub_transactions_paid_created
  ON app.interhub_transactions(created_at DESC, agent_transaction_id DESC)
  WHERE state='paid';
