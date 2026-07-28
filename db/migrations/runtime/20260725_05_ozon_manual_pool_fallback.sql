-- Включает ручной пул как независимый источник для цепочки выдачи Ozon.
ALTER TABLE app.marketplace_ozon_digital_settings
  ADD COLUMN IF NOT EXISTS pool_issue_enabled boolean NOT NULL DEFAULT false;
