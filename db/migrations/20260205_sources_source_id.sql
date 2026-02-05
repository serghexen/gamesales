BEGIN;

-- Drop old FK on customers.source_code if it exists (to allow duplicate source codes).
ALTER TABLE app.customers DROP CONSTRAINT IF EXISTS customers_source_code_fkey;

-- Add surrogate key to sources.
ALTER TABLE app.sources ADD COLUMN IF NOT EXISTS source_id bigserial;

-- Remove old PK/unique on code, then make source_id the PK.
ALTER TABLE app.sources DROP CONSTRAINT IF EXISTS sources_pkey;
ALTER TABLE app.sources DROP CONSTRAINT IF EXISTS sources_code_key;

-- Populate source_id for existing rows (in case column existed without values).
UPDATE app.sources
SET source_id = nextval('app.sources_source_id_seq')
WHERE source_id IS NULL;

ALTER TABLE app.sources ALTER COLUMN source_id SET NOT NULL;
ALTER TABLE app.sources ADD CONSTRAINT sources_pkey PRIMARY KEY (source_id);

CREATE INDEX IF NOT EXISTS ix_sources_code ON app.sources (code);

-- Add source_id to customers (if missing) and backfill from source_code.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'app' AND table_name = 'customers' AND column_name = 'source_id'
  ) THEN
    ALTER TABLE app.customers ADD COLUMN source_id bigint;
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'app' AND table_name = 'customers' AND column_name = 'source_code'
  ) THEN
    UPDATE app.customers c
    SET source_id = s.source_id
    FROM app.sources s
    WHERE c.source_id IS NULL AND c.source_code = s.code;
  END IF;
END$$;

-- Add FK on customers.source_id if missing.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'customers_source_id_fkey'
      AND conrelid = 'app.customers'::regclass
  ) THEN
    ALTER TABLE app.customers
      ADD CONSTRAINT customers_source_id_fkey
      FOREIGN KEY (source_id) REFERENCES app.sources(source_id);
  END IF;
END$$;

COMMIT;
