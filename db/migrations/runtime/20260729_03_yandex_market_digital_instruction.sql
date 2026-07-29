-- Инструкция покупателю для передачи цифрового кода в slip Яндекс Маркета.
ALTER TABLE app.marketplace_yandex_stock_settings
  ADD COLUMN IF NOT EXISTS activation_instruction text NOT NULL DEFAULT '';
