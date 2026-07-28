-- Хранит отметку успешного чтения заказов Яндекс Маркета, чтобы не загружать всю историю повторно.
CREATE TABLE IF NOT EXISTS app.marketplace_yandex_order_sync_state (
  store_code text PRIMARY KEY,
  last_checked_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);
