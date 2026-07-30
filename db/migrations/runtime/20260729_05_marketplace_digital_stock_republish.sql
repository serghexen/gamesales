-- Хранит ошибку повторной публикации витринного остатка отдельно от успешной выдачи цифрового ключа.
ALTER TABLE app.marketplace_ozon_digital_settings
  ADD COLUMN IF NOT EXISTS last_stock_sync_error text NOT NULL DEFAULT '';

ALTER TABLE app.marketplace_yandex_stock_settings
  ADD COLUMN IF NOT EXISTS last_stock_sync_error text NOT NULL DEFAULT '';
