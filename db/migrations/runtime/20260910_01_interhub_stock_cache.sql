-- Последний результат проверки каждого номинала, включая ошибки и несовпадения имён.
CREATE TABLE IF NOT EXISTS app.interhub_stock_cache (
  service_id integer NOT NULL,
  nominal_id integer NOT NULL,
  service_title text NOT NULL DEFAULT '',
  nominal_title text NOT NULL DEFAULT '',
  stock_count bigint,
  match_status text NOT NULL,
  provider_name text NOT NULL DEFAULT '',
  message text NOT NULL DEFAULT '',
  provider_response jsonb NOT NULL,
  checked_at timestamptz NOT NULL,
  batch_id text NOT NULL,
  created_by text NOT NULL DEFAULT '',
  PRIMARY KEY (service_id, nominal_id),
  CHECK (stock_count IS NULL OR stock_count >= 0),
  CHECK (match_status IN ('matched', 'normalized', 'missing', 'ambiguous', 'invalid_count', 'error')),
  CHECK ((match_status IN ('matched', 'normalized')) = (stock_count IS NOT NULL))
);
