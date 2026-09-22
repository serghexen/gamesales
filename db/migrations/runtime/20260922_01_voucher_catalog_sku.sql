-- SKU относится к собственному номиналу, а не к услуге или предложению поставщика.
ALTER TABLE app.voucher_catalog_nominals ADD COLUMN sku_number bigint;

-- Ранее созданные номиналы получают номера по порядку создания, начиная с единицы.
WITH numbered AS (
  SELECT catalog_nominal_id, row_number() OVER (ORDER BY catalog_nominal_id) AS number
  FROM app.voucher_catalog_nominals
)
UPDATE app.voucher_catalog_nominals n SET sku_number=numbered.number
FROM numbered WHERE n.catalog_nominal_id=numbered.catalog_nominal_id;

-- Последовательность защищает от дублей при параллельном сохранении разных услуг.
CREATE SEQUENCE app.voucher_catalog_sku_seq AS bigint
  OWNED BY app.voucher_catalog_nominals.sku_number;
SELECT setval('app.voucher_catalog_sku_seq', COALESCE(MAX(sku_number), 1), COUNT(*) > 0)
FROM app.voucher_catalog_nominals;

ALTER TABLE app.voucher_catalog_nominals
  ALTER COLUMN sku_number SET DEFAULT nextval('app.voucher_catalog_sku_seq'),
  ALTER COLUMN sku_number SET NOT NULL,
  ADD CONSTRAINT voucher_catalog_sku_number_positive CHECK (sku_number > 0),
  ADD COLUMN sku text GENERATED ALWAYS AS (
    'HT' || lpad(sku_number::text, GREATEST(7, length(sku_number::text)), '0')
  ) STORED;

COMMENT ON COLUMN app.voucher_catalog_nominals.sku IS
  'Постоянный SKU номинала. Номера удалённых записей не используются повторно.';
