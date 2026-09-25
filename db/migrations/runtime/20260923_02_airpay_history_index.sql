-- migrate:no-transaction
-- История владельца читается постранично без обхода всего журнала.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_airpay_transactions_owner_history
    ON app.airpay_transactions(created_by, created_at DESC, agent_transaction_id DESC);
