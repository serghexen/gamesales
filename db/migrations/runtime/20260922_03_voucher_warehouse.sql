-- Позиции склада читаются из каталога: копии номиналов и отдельная синхронизация не нужны.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE app.voucher_warehouse_positions (
  catalog_nominal_id bigint PRIMARY KEY REFERENCES app.voucher_catalog_nominals(catalog_nominal_id) ON DELETE CASCADE,
  price numeric(20, 6) CHECK (price IS NULL OR price >= 0),
  updated_at timestamptz NOT NULL DEFAULT now(),
  updated_by text NOT NULL
);
CREATE TABLE app.voucher_warehouse_keys (
  key_id bigserial PRIMARY KEY,
  catalog_nominal_id bigint NOT NULL REFERENCES app.voucher_catalog_nominals(catalog_nominal_id) ON DELETE RESTRICT,
  code_ciphertext bytea NOT NULL,
  code_hash text NOT NULL UNIQUE,
  code_suffix text NOT NULL,
  status text NOT NULL DEFAULT 'free' CHECK (status IN ('free', 'reserved', 'sending', 'delivered', 'disabled')),
  expires_at date,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by text NOT NULL
);
-- Просроченные ключи исключаются сразу по московской дате, без фонового задания.
CREATE VIEW app.voucher_warehouse_stock AS
SELECT n.catalog_nominal_id, n.item_id, n.name, n.sku, i.name AS service_name,
       p.price, p.updated_at AS price_updated_at,
       COUNT(k.key_id) AS total,
       COUNT(k.key_id) FILTER (WHERE k.status='free' AND (k.expires_at IS NULL OR k.expires_at >= (now() AT TIME ZONE 'Europe/Moscow')::date)) AS free_count,
       COUNT(k.key_id) FILTER (WHERE k.status IN ('reserved','sending')) AS reserved_count,
       COUNT(k.key_id) FILTER (WHERE k.status='delivered') AS delivered_count,
       COUNT(k.key_id) FILTER (WHERE k.status='free' AND k.expires_at < (now() AT TIME ZONE 'Europe/Moscow')::date) AS expired_count
FROM app.voucher_catalog_nominals n
JOIN app.voucher_catalog_items i ON i.item_id=n.item_id
LEFT JOIN app.voucher_warehouse_positions p ON p.catalog_nominal_id=n.catalog_nominal_id
LEFT JOIN app.voucher_warehouse_keys k ON k.catalog_nominal_id=n.catalog_nominal_id
GROUP BY n.catalog_nominal_id, n.item_id, n.name, n.sku, i.name, p.price, p.updated_at;
INSERT INTO app.voucher_catalog_suppliers(code,name) VALUES ('warehouse','Склад')
ON CONFLICT (code) DO NOTHING;
-- Раздел мог появиться при чтении прав старым RBAC-кодом; сохраняем уже заданные права.
INSERT INTO app.ui_sections(section_code,section_name,sort_order) VALUES ('voucher-warehouse','Склад',76)
ON CONFLICT (section_code) DO NOTHING;
INSERT INTO app.role_ui_sections(role_code,section_code,can_view,updated_by)
SELECT code,'voucher-warehouse',code IN ('admin','owner'),'migration' FROM app.user_roles
ON CONFLICT (role_code,section_code) DO NOTHING;
