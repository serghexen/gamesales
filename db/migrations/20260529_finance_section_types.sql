CREATE TABLE IF NOT EXISTS finance.section_types (
  type_id bigserial PRIMARY KEY,
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  sort_order integer NOT NULL DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE finance.section_types IS 'Типы верхнего уровня для классификации P&L';

INSERT INTO finance.section_types(code, name, sort_order, is_active)
VALUES
  ('revenue', 'Выручка', 10, true),
  ('direct_expense', 'Прямые расходы', 20, true),
  ('indirect_expense', 'Косвенные расходы', 30, true),
  ('other', 'Другое', 40, true)
ON CONFLICT (code) DO UPDATE
SET name=excluded.name,
    sort_order=excluded.sort_order,
    is_active=true,
    updated_at=now();

ALTER TABLE finance.sections
  ADD COLUMN IF NOT EXISTS type_id bigint;

UPDATE finance.sections s
SET type_id = st.type_id
FROM finance.section_types st
WHERE s.type_id IS NULL
  AND st.code = COALESCE(NULLIF(s.kind, ''), 'other');

UPDATE finance.sections s
SET type_id = st.type_id
FROM finance.section_types st
WHERE s.type_id IS NULL
  AND st.code = 'other';

ALTER TABLE finance.sections
  ALTER COLUMN type_id SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_finance_sections_type'
      AND conrelid = 'finance.sections'::regclass
  ) THEN
    ALTER TABLE finance.sections
      ADD CONSTRAINT fk_finance_sections_type
      FOREIGN KEY (type_id)
      REFERENCES finance.section_types(type_id);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_finance_sections_type
  ON finance.sections(type_id, sort_order);
