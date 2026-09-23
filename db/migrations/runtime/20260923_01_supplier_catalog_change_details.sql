-- Один снимок до непросмотренных изменений, без накопления истории обходов.
ALTER TABLE app.supplier_catalog_current
  ADD COLUMN review_before jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN changes_detected_at timestamptz,
  ADD COLUMN availability_reason text NOT NULL DEFAULT '';

-- Для старых строк восстанавливаем только достоверную причину из сохранённого состояния.
UPDATE app.supplier_catalog_current
SET availability_reason = CASE WHEN missing_count > 0 THEN 'missing' ELSE 'disabled' END
WHERE status <> 'active';
