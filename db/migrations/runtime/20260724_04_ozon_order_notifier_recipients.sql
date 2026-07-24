-- migrate:no-transaction
-- Бот хранит подписавшиеся личные и групповые чаты, чтобы не требовать ручной настройки Telegram chat_id.
ALTER TABLE app.ozon_order_notifier_state
  ADD COLUMN IF NOT EXISTS baseline_order_id bigint NOT NULL DEFAULT 0;
ALTER TABLE app.ozon_order_notifier_state
  ADD COLUMN IF NOT EXISTS telegram_update_offset bigint NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS app.ozon_order_notifier_recipients (
  chat_id bigint PRIMARY KEY,
  chat_type text NOT NULL DEFAULT '',
  title text NOT NULL DEFAULT '',
  orders_from_id bigint NOT NULL DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  subscribed_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.ozon_order_notifier_deliveries (
  order_id bigint NOT NULL REFERENCES app.marketplace_ozon_digital_orders(id) ON DELETE RESTRICT,
  chat_id bigint NOT NULL REFERENCES app.ozon_order_notifier_recipients(chat_id) ON DELETE RESTRICT,
  telegram_message_id bigint,
  last_status text NOT NULL DEFAULT '',
  notified_at timestamptz,
  last_error text NOT NULL DEFAULT '',
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (order_id, chat_id)
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ozon_order_notifier_recipients_active
  ON app.ozon_order_notifier_recipients(orders_from_id)
  WHERE is_active=true;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ozon_order_notifier_deliveries_pending
  ON app.ozon_order_notifier_deliveries(updated_at)
  WHERE telegram_message_id IS NULL;
