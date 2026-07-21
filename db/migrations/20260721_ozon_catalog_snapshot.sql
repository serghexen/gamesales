-- Локальный снимок карточек Ozon: первый шаг интеграции без управления остатками и выдачей ключей.
CREATE TABLE IF NOT EXISTS app.marketplace_ozon_catalog_items (
  store_code text NOT NULL,
  external_product_id bigint NOT NULL,
  offer_id text NOT NULL DEFAULT '',
  title text NOT NULL DEFAULT '',
  visibility text NOT NULL DEFAULT '',
  state text NOT NULL DEFAULT '',
  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  synced_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (store_code, external_product_id)
);

CREATE INDEX IF NOT EXISTS idx_marketplace_ozon_catalog_offer
  ON app.marketplace_ozon_catalog_items(store_code, offer_id);
