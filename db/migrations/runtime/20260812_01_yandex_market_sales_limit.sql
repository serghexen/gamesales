-- migrate:no-transaction
-- Ограничивает суммарные продажи карточки и хранит идемпотентные резервы по позициям заказов.

ALTER TABLE app.marketplace_yandex_stock_settings
  ADD COLUMN IF NOT EXISTS sales_limit integer CHECK (sales_limit IS NULL OR sales_limit > 0);

ALTER TABLE app.marketplace_yandex_stock_settings
  ADD COLUMN IF NOT EXISTS sales_limit_revision bigint NOT NULL DEFAULT 0 CHECK (sales_limit_revision >= 0);

ALTER TABLE app.marketplace_yandex_stock_settings
  ADD COLUMN IF NOT EXISTS sales_limit_exhausted_at timestamptz;

ALTER TABLE app.marketplace_yandex_stock_settings
  ADD COLUMN IF NOT EXISTS archived_by_sales_limit boolean NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS app.marketplace_yandex_sales_limit_reservations (
  id bigserial PRIMARY KEY,
  delivery_id bigint NOT NULL UNIQUE
    REFERENCES app.marketplace_yandex_digital_deliveries(id) ON DELETE RESTRICT,
  store_code text NOT NULL,
  offer_id text NOT NULL,
  limit_revision bigint NOT NULL CHECK (limit_revision >= 0),
  quantity integer NOT NULL CHECK (quantity > 0),
  state text NOT NULL DEFAULT 'reserved'
    CHECK (state IN ('reserved', 'consumed', 'released')),
  consumed_at timestamptz,
  released_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (store_code, offer_id)
    REFERENCES app.marketplace_yandex_stock_settings(store_code, offer_id)
    ON DELETE RESTRICT
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_yandex_sales_limit_reservations_totals
  ON app.marketplace_yandex_sales_limit_reservations(store_code, offer_id, limit_revision, state);
