-- Добавляем версию записи, чтобы защищать сделки от перезаписи при параллельном редактировании.
ALTER TABLE app.deals
  ADD COLUMN IF NOT EXISTS lock_version integer NOT NULL DEFAULT 1;

COMMENT ON COLUMN app.deals.lock_version IS 'Версия записи для optimistic locking';
