-- migrate:no-transaction
-- Связывает общий журнал Interhub с выдачами Яндекс Маркета, не смешивая их с заказами Ozon.
ALTER TABLE app.interhub_transactions
  ADD COLUMN IF NOT EXISTS yandex_market_delivery_id bigint;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_interhub_transactions_yandex_delivery
  ON app.interhub_transactions(yandex_market_delivery_id, created_at DESC)
  WHERE yandex_market_delivery_id IS NOT NULL;
