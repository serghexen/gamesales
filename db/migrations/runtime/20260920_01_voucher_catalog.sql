-- Собственный каталог и предложения поставщиков хранятся отдельно от товаров CRM.
CREATE TABLE app.voucher_catalog_suppliers (
  code text PRIMARY KEY,
  name text NOT NULL
);
INSERT INTO app.voucher_catalog_suppliers(code, name) VALUES ('interhub', 'Интерхаб');

CREATE TABLE app.voucher_catalog_items (
  item_id bigserial PRIMARY KEY,
  name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 250),
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by text NOT NULL DEFAULT ''
);

CREATE TABLE app.voucher_catalog_offers (
  offer_id bigserial PRIMARY KEY,
  item_id bigint NOT NULL REFERENCES app.voucher_catalog_items(item_id),
  supplier_code text NOT NULL REFERENCES app.voucher_catalog_suppliers(code),
  service_id text NOT NULL,
  nominal_id text NOT NULL,
  service_title text NOT NULL,
  nominal_title text NOT NULL,
  price numeric(20, 6) CHECK (price IS NULL OR price >= 0),
  currency text NOT NULL DEFAULT 'RUB',
  price_updated_at timestamptz,
  price_checked_at timestamptz,
  price_error text NOT NULL DEFAULT '',
  stock_count bigint CHECK (stock_count IS NULL OR stock_count >= 0),
  stock_updated_at timestamptz,
  stock_checked_at timestamptz,
  stock_error text NOT NULL DEFAULT '',
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by text NOT NULL DEFAULT '',
  UNIQUE (item_id, supplier_code, service_id, nominal_id)
);

CREATE TABLE app.voucher_catalog_sync_runs (
  job text PRIMARY KEY CHECK (job IN ('prices', 'stocks')),
  slot timestamptz NOT NULL,
  finished_at timestamptz NOT NULL,
  errors integer NOT NULL DEFAULT 0
);

INSERT INTO app.ui_sections(section_code, section_name, sort_order)
VALUES ('voucher-catalog', 'Каталог', 75)
ON CONFLICT (section_code) DO NOTHING;
INSERT INTO app.role_ui_sections(role_code, section_code, can_view, updated_by)
SELECT code, 'voucher-catalog', code IN ('admin', 'owner'), 'migration'
FROM app.user_roles
ON CONFLICT (role_code, section_code) DO NOTHING;
