-- migrate:no-transaction
-- Индекс ускоряет подсчёт свободных ключей и просмотр конкретного SKU.
CREATE INDEX CONCURRENTLY voucher_warehouse_keys_nominal_status_idx
  ON app.voucher_warehouse_keys(catalog_nominal_id,status,key_id DESC);
