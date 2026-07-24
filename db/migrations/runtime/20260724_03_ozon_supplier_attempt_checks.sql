-- Считает проверки неопределенной оплаты, чтобы не ждать ответ поставщика бесконечно.
ALTER TABLE app.marketplace_ozon_digital_supplier_attempts
  ADD COLUMN IF NOT EXISTS status_check_attempts integer NOT NULL DEFAULT 0;
