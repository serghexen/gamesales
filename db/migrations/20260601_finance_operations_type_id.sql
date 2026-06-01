-- Привязываем операции напрямую к типам, чтобы в UI модель была "Тип -> Операция" без промежуточных разделов.
ALTER TABLE finance.operations
  ADD COLUMN IF NOT EXISTS type_id bigint;

-- Переносим связь из section_id в type_id для уже существующих операций.
UPDATE finance.operations o
SET type_id = s.type_id
FROM finance.sections s
WHERE o.type_id IS NULL
  AND o.section_id = s.section_id;

-- Подстраховка: если операция осталась без типа, отправляем в "other".
UPDATE finance.operations o
SET type_id = st.type_id
FROM finance.section_types st
WHERE o.type_id IS NULL
  AND st.code = 'other';

ALTER TABLE finance.operations
  ALTER COLUMN type_id SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_finance_operations_type'
      AND conrelid = 'finance.operations'::regclass
  ) THEN
    ALTER TABLE finance.operations
      ADD CONSTRAINT fk_finance_operations_type
      FOREIGN KEY (type_id)
      REFERENCES finance.section_types(type_id);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_finance_operations_type
  ON finance.operations(type_id, sort_order, operation_id);

-- section_id оставляем для обратной совместимости, но снимаем обязательность.
ALTER TABLE finance.operations
  ALTER COLUMN section_id DROP NOT NULL;
