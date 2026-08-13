-- Переводит общий лимит Яндекс Маркета в дневной и хранит временную прибавку только до полуночи по Москве.

ALTER TABLE app.marketplace_yandex_stock_settings
  ADD COLUMN IF NOT EXISTS sales_limit_daily_extra integer NOT NULL DEFAULT 0
  CHECK (sales_limit_daily_extra >= 0);

ALTER TABLE app.marketplace_yandex_stock_settings
  ADD COLUMN IF NOT EXISTS sales_limit_day date NOT NULL
  DEFAULT ((CURRENT_TIMESTAMP AT TIME ZONE 'Europe/Moscow')::date);

ALTER TABLE app.marketplace_yandex_stock_settings
  ADD COLUMN IF NOT EXISTS sales_limit_rollover_pending boolean NOT NULL DEFAULT false;
