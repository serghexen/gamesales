-- Отдельный резервный сценарий: вместо ключа можно намеренно отправить покупателю сообщение поддержки.
ALTER TABLE app.marketplace_yandex_stock_settings
  ADD COLUMN IF NOT EXISTS support_message_delivery_enabled boolean NOT NULL DEFAULT false;

-- Хранит источник фактически отправленного содержимого, чтобы сообщение поддержки не принять за лицензионный ключ.
ALTER TABLE app.marketplace_yandex_digital_deliveries
  ADD COLUMN IF NOT EXISTS delivery_source text NOT NULL DEFAULT '';
