-- Реестр отпечатков ключей предотвращает повторную выдачу одного ключа разным заказам Ozon.
CREATE TABLE IF NOT EXISTS app.marketplace_ozon_digital_code_registry (
  code_hash text PRIMARY KEY,
  order_id bigint NOT NULL REFERENCES app.marketplace_ozon_digital_orders(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now()
);
