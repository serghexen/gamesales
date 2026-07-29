-- migrate:no-transaction
-- Отдельно хранит состояние явной отправки ключа из sandbox в test-кабинет Маркета.
ALTER TABLE app.marketplace_yandex_sandbox_deliveries
  ADD COLUMN IF NOT EXISTS market_submitted_at timestamptz;
ALTER TABLE app.marketplace_yandex_sandbox_deliveries
  ADD COLUMN IF NOT EXISTS last_error text NOT NULL DEFAULT '';

ALTER TABLE app.marketplace_yandex_sandbox_deliveries
  DROP CONSTRAINT IF EXISTS marketplace_yandex_sandbox_deliveries_status_check;
ALTER TABLE app.marketplace_yandex_sandbox_deliveries
  ADD CONSTRAINT marketplace_yandex_sandbox_deliveries_status_check
  CHECK (status IN ('locally_issued', 'market_sending', 'market_submitted', 'market_unknown', 'market_delivered'));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_yandex_market_sandbox_deliveries_status
  ON app.marketplace_yandex_sandbox_deliveries(store_code, status, updated_at DESC);
