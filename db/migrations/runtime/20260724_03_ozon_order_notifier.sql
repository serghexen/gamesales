-- migrate:no-transaction
-- Отдельный сервис хранит привязку заказа Ozon к Telegram-сообщению, чтобы обновлять статус без дублей.
CREATE TABLE IF NOT EXISTS app.ozon_order_notifier_state (
  notifier_code text PRIMARY KEY,
  initialized_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.marketplace_ozon_order_notifications (
  order_id bigint PRIMARY KEY REFERENCES app.marketplace_ozon_digital_orders(id) ON DELETE RESTRICT,
  telegram_message_id bigint,
  last_status text NOT NULL DEFAULT '',
  is_baseline boolean NOT NULL DEFAULT false,
  notified_at timestamptz,
  last_error text NOT NULL DEFAULT '',
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_marketplace_ozon_order_notifications_pending
  ON app.marketplace_ozon_order_notifications(updated_at)
  WHERE telegram_message_id IS NULL AND is_baseline=false;
