-- migrate:no-transaction
-- Защищает фоновый опрос поставщика от одновременной обработки одной попытки разными воркерами.

ALTER TABLE app.marketplace_ozon_digital_supplier_attempts
  ADD COLUMN IF NOT EXISTS status_check_lock_token uuid;

ALTER TABLE app.marketplace_ozon_digital_supplier_attempts
  ADD COLUMN IF NOT EXISTS status_check_locked_until timestamptz;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ozon_supplier_attempts_due_lease
  ON app.marketplace_ozon_digital_supplier_attempts(state, next_status_check_at, status_check_locked_until);
