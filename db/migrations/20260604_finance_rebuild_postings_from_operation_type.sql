-- Приводим базовые finance postings к текущему типу операции.
-- Это закрывает рассинхрон после ручной смены operation.type_id в справочнике.
WITH desired_postings AS (
  SELECT
    p.posting_id,
    CASE st.code
      WHEN 'revenue' THEN 'revenue'
      WHEN 'direct_expense' THEN 'direct_expense'
      WHEN 'indirect_expense' THEN 'indirect_expense'
      ELSE 'other'
    END AS metric_code
  FROM finance.entry_postings p
  JOIN finance.entries e
    ON e.entry_id = p.entry_id
   AND e.biz_date = p.entry_biz_date
  JOIN finance.operations o ON o.operation_id = e.operation_id
  JOIN finance.section_types st ON st.type_id = o.type_id
  WHERE p.formula_id IS NULL
)
UPDATE finance.entry_postings p
SET metric_code = d.metric_code
FROM desired_postings d
WHERE p.posting_id = d.posting_id
  AND p.metric_code IS DISTINCT FROM d.metric_code;
