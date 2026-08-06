-- migrate:no-transaction
-- Добавляет аренду и расписание повторов для долговечной обработки webhook Яндекс Маркета.

ALTER TABLE app.marketplace_yandex_market_webhook_events
  ADD COLUMN IF NOT EXISTS processing_lock_token uuid,
  ADD COLUMN IF NOT EXISTS processing_locked_until timestamptz,
  ADD COLUMN IF NOT EXISTS next_attempt_at timestamptz NOT NULL DEFAULT now(),
  ADD COLUMN IF NOT EXISTS last_attempt_at timestamptz,
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

-- Старые processing-записи получают NULL-аренду и подбираются после защитного окна старого процесса.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_yandex_market_webhook_events_retry_queue
  ON app.marketplace_yandex_market_webhook_events(next_attempt_at, id)
  WHERE processing_state IN ('received', 'failed', 'processing');
