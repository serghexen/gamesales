-- migrate:no-transaction
-- Хранит отдельное время начала внешней отправки, которое не сдвигается обычной синхронизацией заказа.

ALTER TABLE app.marketplace_ozon_digital_orders
  ADD COLUMN IF NOT EXISTS delivery_started_at timestamptz;

ALTER TABLE app.marketplace_yandex_digital_deliveries
  ADD COLUMN IF NOT EXISTS market_send_started_at timestamptz;

-- Старые зависшие отправки получают исходную отметку времени и подбираются новым восстановлением.
UPDATE app.marketplace_ozon_digital_orders
SET delivery_started_at=updated_at
WHERE status='delivering' AND delivery_started_at IS NULL;

UPDATE app.marketplace_yandex_digital_deliveries
SET market_send_started_at=updated_at
WHERE status='market_sending' AND market_send_started_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ozon_digital_orders_stale_delivering
  ON app.marketplace_ozon_digital_orders(delivery_started_at, id)
  WHERE status='delivering';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_yandex_digital_deliveries_stale_market_sending
  ON app.marketplace_yandex_digital_deliveries(market_send_started_at, id)
  WHERE status='market_sending';
