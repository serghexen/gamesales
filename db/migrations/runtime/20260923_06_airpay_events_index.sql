-- migrate:no-transaction
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_airpay_events_transaction
ON app.airpay_events(transaction_id, id DESC);
