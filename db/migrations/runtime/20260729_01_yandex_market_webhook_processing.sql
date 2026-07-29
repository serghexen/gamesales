-- migrate:no-transaction
-- Хранит результат read-only обработки уведомления, не меняя заказ или выдачу в Маркете.
ALTER TABLE app.marketplace_yandex_market_webhook_events
  ADD COLUMN IF NOT EXISTS processing_attempts integer NOT NULL DEFAULT 0 CHECK (processing_attempts >= 0),
  ADD COLUMN IF NOT EXISTS last_error text NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS processed_at timestamptz;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_yandex_market_webhook_events_pending
  ON app.marketplace_yandex_market_webhook_events(received_at ASC, id ASC)
  WHERE processing_state IN ('received', 'failed');
