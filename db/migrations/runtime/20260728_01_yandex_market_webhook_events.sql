-- migrate:no-transaction
-- Журнал входящих уведомлений Маркета отделен от заказов: на первом этапе он не меняет статус и не выдает ключи.
CREATE TABLE IF NOT EXISTS app.marketplace_yandex_market_webhook_events (
  id bigserial PRIMARY KEY,
  event_fingerprint text NOT NULL,
  notification_type text NOT NULL,
  campaign_id bigint,
  order_id bigint,
  status text NOT NULL DEFAULT '',
  substatus text NOT NULL DEFAULT '',
  event_time timestamptz,
  source_ip text NOT NULL DEFAULT '',
  payload_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  processing_state text NOT NULL DEFAULT 'received',
  received_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_yandex_market_webhook_events_received_at
  ON app.marketplace_yandex_market_webhook_events(received_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_yandex_market_webhook_events_order
  ON app.marketplace_yandex_market_webhook_events(campaign_id, order_id, received_at DESC)
  WHERE order_id IS NOT NULL;
