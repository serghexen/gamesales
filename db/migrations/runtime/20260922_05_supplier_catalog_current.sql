-- Текущее состояние поставщика: одна строка на номинал, без истории опросов.
CREATE TABLE app.supplier_catalog_current (
  supplier_code text NOT NULL,
  service_id text NOT NULL,
  nominal_id text NOT NULL,
  service_title text NOT NULL DEFAULT '',
  nominal_title text NOT NULL DEFAULT '',
  category text NOT NULL DEFAULT '',
  service_type text NOT NULL DEFAULT 'VOUCHER',
  currency text NOT NULL DEFAULT 'RUB',
  price numeric(20,6) CHECK (price >= 0),
  stock_count bigint CHECK (stock_count >= 0),
  price_updated_at timestamptz,
  price_checked_at timestamptz,
  price_error text NOT NULL DEFAULT '',
  price_response jsonb NOT NULL DEFAULT '{}',
  price_attempt_response jsonb NOT NULL DEFAULT '{}',
  stock_updated_at timestamptz,
  stock_checked_at timestamptz,
  stock_error text NOT NULL DEFAULT '',
  stock_response jsonb NOT NULL DEFAULT '{}',
  stock_attempt_response jsonb NOT NULL DEFAULT '{}',
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspect', 'unavailable')),
  missing_count integer NOT NULL DEFAULT 0,
  first_seen_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz,
  reviewed_at timestamptz,
  review_revision bigint NOT NULL DEFAULT 1,
  review_reason text NOT NULL DEFAULT 'new',
  PRIMARY KEY(supplier_code, service_id, nominal_id)
);
CREATE TABLE app.supplier_catalog_sync_state (
  supplier_code text PRIMARY KEY,
  services jsonb NOT NULL DEFAULT '[]',
  discovery_at timestamptz,
  checked_at timestamptz,
  error text NOT NULL DEFAULT ''
);

-- Имена, цены и остатки выбираются независимо: более свежая цена не затирает свежий остаток.
WITH names AS (
  SELECT 'interhub'::text supplier_code, service_id::text, nominal_id::text,
    service_title, nominal_title, category, service_type, calculated_at stamp
  FROM app.interhub_price_calculations
  UNION ALL
  SELECT 'interhub', s.service_id::text, s.nominal_id::text, s.service_title, s.nominal_title,
    COALESCE(p.category,''), COALESCE(p.service_type,'VOUCHER'), s.checked_at
  FROM app.interhub_stock_cache s LEFT JOIN LATERAL (SELECT category,service_type FROM app.interhub_price_calculations
    WHERE service_id=s.service_id AND nominal_id=s.nominal_id ORDER BY calculated_at DESC,id DESC LIMIT 1) p ON true
  UNION ALL
  SELECT supplier_code, service_id, nominal_id, service_title, nominal_title, '', 'VOUCHER',
    GREATEST(price_updated_at, stock_updated_at)
  FROM app.voucher_catalog_offers WHERE supplier_code <> 'warehouse'
), chosen AS (
  SELECT DISTINCT ON (supplier_code, service_id, nominal_id) * FROM names
  ORDER BY supplier_code, service_id, nominal_id, stamp DESC NULLS LAST, category DESC
)
INSERT INTO app.supplier_catalog_current(supplier_code, service_id, nominal_id, service_title, nominal_title,
  category, service_type, reviewed_at, review_reason)
SELECT supplier_code, service_id, nominal_id, service_title, nominal_title, category, service_type, now(), '' FROM chosen;

WITH prices AS (
  SELECT 'interhub'::text supplier_code, service_id::text, nominal_id::text, fixed_amount price,
    calculated_at stamp, provider_response response
  FROM app.interhub_price_calculations
  WHERE success AND fixed_amount >= 0 AND fixed_amount < 100000000000000
  UNION ALL
  SELECT supplier_code, service_id, nominal_id, price, price_updated_at, '{}'::jsonb
  FROM app.voucher_catalog_offers WHERE supplier_code <> 'warehouse' AND price IS NOT NULL
), chosen AS (
  SELECT DISTINCT ON (supplier_code, service_id, nominal_id) * FROM prices
  ORDER BY supplier_code, service_id, nominal_id, stamp DESC NULLS LAST
)
UPDATE app.supplier_catalog_current c SET price=p.price, price_updated_at=p.stamp,
  price_checked_at=p.stamp, price_response=COALESCE(p.response, '{}'::jsonb)
FROM chosen p WHERE (c.supplier_code,c.service_id,c.nominal_id)=(p.supplier_code,p.service_id,p.nominal_id);

WITH stocks AS (
  SELECT 'interhub'::text supplier_code, service_id::text, nominal_id::text, stock_count,
    checked_at stamp, provider_response response
  FROM app.interhub_stock_cache WHERE stock_count IS NOT NULL
  UNION ALL
  SELECT supplier_code, service_id, nominal_id, stock_count, stock_updated_at, '{}'::jsonb
  FROM app.voucher_catalog_offers WHERE supplier_code <> 'warehouse' AND stock_count IS NOT NULL
), chosen AS (
  SELECT DISTINCT ON (supplier_code, service_id, nominal_id) * FROM stocks
  ORDER BY supplier_code, service_id, nominal_id, stamp DESC NULLS LAST
)
UPDATE app.supplier_catalog_current c SET stock_count=s.stock_count, stock_updated_at=s.stamp,
  stock_checked_at=s.stamp, stock_response=COALESCE(s.response, '{}'::jsonb)
FROM chosen s WHERE (c.supplier_code,c.service_id,c.nominal_id)=(s.supplier_code,s.service_id,s.nominal_id);

-- Последняя неудачная попытка не стирает успешное значение, но должна быть видна оператору.
WITH attempts AS (
  SELECT 'interhub'::text supplier_code, service_id::text, nominal_id::text, calculated_at stamp,
    CASE WHEN success THEN '' ELSE COALESCE(NULLIF(provider_message,''),'Ошибка calculate') END error
  FROM app.interhub_price_calculations
  UNION ALL
  SELECT supplier_code,service_id,nominal_id,price_checked_at,price_error
  FROM app.voucher_catalog_offers WHERE supplier_code<>'warehouse'
), chosen AS (
  SELECT DISTINCT ON(supplier_code,service_id,nominal_id) * FROM attempts
  ORDER BY supplier_code,service_id,nominal_id,stamp DESC NULLS LAST
)
UPDATE app.supplier_catalog_current c SET price_checked_at=a.stamp,price_error=a.error
FROM chosen a WHERE (c.supplier_code,c.service_id,c.nominal_id)=(a.supplier_code,a.service_id,a.nominal_id)
  AND a.stamp IS NOT NULL;
WITH attempts AS (
  SELECT 'interhub'::text supplier_code,service_id::text,nominal_id::text,checked_at stamp,
    CASE WHEN stock_count IS NOT NULL THEN '' ELSE COALESCE(NULLIF(message,''),'Остаток неизвестен') END error
  FROM app.interhub_stock_cache
  UNION ALL
  SELECT supplier_code,service_id,nominal_id,stock_checked_at,stock_error
  FROM app.voucher_catalog_offers WHERE supplier_code<>'warehouse'
), chosen AS (
  SELECT DISTINCT ON(supplier_code,service_id,nominal_id) * FROM attempts
  ORDER BY supplier_code,service_id,nominal_id,stamp DESC NULLS LAST
)
UPDATE app.supplier_catalog_current c SET stock_checked_at=a.stamp,stock_error=a.error
FROM chosen a WHERE (c.supplier_code,c.service_id,c.nominal_id)=(a.supplier_code,a.service_id,a.nominal_id)
  AND a.stamp IS NOT NULL;

-- История покупок получает названия из нового справочника; старые записи остаются страховкой.
CREATE VIEW app.supplier_catalog_labels AS
SELECT service_id::integer, nominal_id::integer, service_title, nominal_title,
       COALESCE(last_seen_at,price_updated_at,first_seen_at) AS calculated_at, 0::bigint id, true success
FROM app.supplier_catalog_current WHERE supplier_code='interhub'
UNION ALL
SELECT p.service_id,p.nominal_id,p.service_title,p.nominal_title,p.calculated_at,p.id,p.success
FROM app.interhub_price_calculations p
WHERE NOT EXISTS (SELECT 1 FROM app.supplier_catalog_current c WHERE c.supplier_code='interhub'
                  AND c.service_id=p.service_id::text AND c.nominal_id=p.nominal_id::text);
