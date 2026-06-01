-- Добавляем связь операции со справочником источников (опционально).
ALTER TABLE finance.operations
  ADD COLUMN IF NOT EXISTS source_id bigint;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_finance_operations_source'
      AND conrelid = 'finance.operations'::regclass
  ) THEN
    ALTER TABLE finance.operations
      ADD CONSTRAINT fk_finance_operations_source
      FOREIGN KEY (source_id)
      REFERENCES finance.dim_sources(source_id);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_finance_operations_source
  ON finance.operations(source_id, sort_order, operation_id);
