-- migrate:no-transaction
-- Уникальность SKU проверяется БД; индекс строится без блокировки обычных записей.
CREATE UNIQUE INDEX CONCURRENTLY voucher_catalog_nominals_sku_uidx
  ON app.voucher_catalog_nominals (sku);
