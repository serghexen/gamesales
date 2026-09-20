-- Услуга хранит общее имя, собственные номиналы объединяют предложения разных поставщиков.
CREATE TABLE app.voucher_catalog_nominals (
  catalog_nominal_id bigserial PRIMARY KEY,
  item_id bigint NOT NULL REFERENCES app.voucher_catalog_items(item_id),
  name text NOT NULL CHECK (length(btrim(name)) > 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by text NOT NULL DEFAULT '',
  UNIQUE (item_id, name),
  UNIQUE (catalog_nominal_id, item_id)
);

ALTER TABLE app.voucher_catalog_offers ADD COLUMN catalog_nominal_id bigint;

-- Переносим все связки, включая отключённые, не меняя цены, остатки и внешние ID.
INSERT INTO app.voucher_catalog_nominals(item_id, name, created_by)
SELECT DISTINCT item_id, COALESCE(NULLIF(btrim(nominal_title), ''), nominal_id), 'migration'
FROM app.voucher_catalog_offers;

UPDATE app.voucher_catalog_offers o
SET catalog_nominal_id=n.catalog_nominal_id
FROM app.voucher_catalog_nominals n
WHERE n.item_id=o.item_id AND n.name=COALESCE(NULLIF(btrim(o.nominal_title), ''), o.nominal_id);

ALTER TABLE app.voucher_catalog_offers ALTER COLUMN catalog_nominal_id SET NOT NULL;
ALTER TABLE app.voucher_catalog_offers ADD CONSTRAINT voucher_offer_own_nominal_fk
  FOREIGN KEY (catalog_nominal_id, item_id)
  REFERENCES app.voucher_catalog_nominals(catalog_nominal_id, item_id);
