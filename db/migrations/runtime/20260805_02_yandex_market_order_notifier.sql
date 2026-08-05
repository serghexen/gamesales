-- migrate:no-transaction
-- Добавляет независимый водораздел и журнал Telegram-событий для цифровых выдач Яндекс Маркета.
ALTER TABLE app.ozon_order_notifier_recipients
  ADD COLUMN IF NOT EXISTS yandex_from_delivery_id bigint NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS app.yandex_market_order_notifier_state (
  notifier_code text PRIMARY KEY,
  baseline_delivery_id bigint NOT NULL DEFAULT 0,
  initialized_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.yandex_market_order_notifier_deliveries (
  delivery_id bigint NOT NULL REFERENCES app.marketplace_yandex_digital_deliveries(id) ON DELETE RESTRICT,
  chat_id bigint NOT NULL REFERENCES app.ozon_order_notifier_recipients(chat_id) ON DELETE RESTRICT,
  telegram_message_id bigint,
  last_status text NOT NULL DEFAULT '',
  notified_at timestamptz,
  last_error text NOT NULL DEFAULT '',
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (delivery_id, chat_id)
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_yandex_market_order_notifier_deliveries_pending
  ON app.yandex_market_order_notifier_deliveries(updated_at)
  WHERE telegram_message_id IS NULL;
