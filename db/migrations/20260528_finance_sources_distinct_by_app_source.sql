-- Переводим справочник источников finance на отдельные записи из app.sources,
-- даже если у них совпадает code (например ym/wb для разных направлений).

ALTER TABLE finance.dim_sources
  DROP CONSTRAINT IF EXISTS dim_sources_code_key;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'uq_finance_dim_sources_app_source_id'
      AND conrelid = 'finance.dim_sources'::regclass
  ) THEN
    ALTER TABLE finance.dim_sources
      ADD CONSTRAINT uq_finance_dim_sources_app_source_id UNIQUE (app_source_id);
  END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_finance_dim_sources_code_name
  ON finance.dim_sources(code, name);
