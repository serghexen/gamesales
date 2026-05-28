CREATE SCHEMA IF NOT EXISTS finance;
COMMENT ON SCHEMA finance IS 'Обособленный контур управленческой аналитики и учета';

CREATE TABLE IF NOT EXISTS finance.dim_regions (
  region_id bigserial PRIMARY KEY,
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  app_region_id smallint,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE finance.dim_regions IS 'Справочник регионов в контуре finance';
COMMENT ON COLUMN finance.dim_regions.app_region_id IS 'Опциональная ссылка на app.regions.region_id без внешнего ключа';

CREATE TABLE IF NOT EXISTS finance.dim_sources (
  source_id bigserial PRIMARY KEY,
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  app_source_id bigint,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE finance.dim_sources IS 'Справочник источников в контуре finance';
COMMENT ON COLUMN finance.dim_sources.app_source_id IS 'Опциональная ссылка на app.sources.source_id без внешнего ключа';

CREATE TABLE IF NOT EXISTS finance.projects (
  project_id bigserial PRIMARY KEY,
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE finance.projects IS 'Справочник проектов для отчетов и группировок';

CREATE TABLE IF NOT EXISTS finance.sections (
  section_id bigserial PRIMARY KEY,
  parent_section_id bigint REFERENCES finance.sections(section_id),
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  kind text NOT NULL,
  sort_order integer NOT NULL DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_finance_section_kind CHECK (kind IN ('revenue', 'direct_expense', 'indirect_expense', 'other'))
);
COMMENT ON TABLE finance.sections IS 'Дерево разделов управленки (выручка/расходы/прочее)';

CREATE TABLE IF NOT EXISTS finance.operations (
  operation_id bigserial PRIMARY KEY,
  section_id bigint NOT NULL REFERENCES finance.sections(section_id),
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  input_mode text NOT NULL DEFAULT 'manual',
  requires_region boolean NOT NULL DEFAULT false,
  requires_source boolean NOT NULL DEFAULT false,
  requires_project boolean NOT NULL DEFAULT false,
  requires_qty boolean NOT NULL DEFAULT false,
  allows_negative boolean NOT NULL DEFAULT false,
  sort_order integer NOT NULL DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_finance_operation_mode CHECK (input_mode IN ('manual', 'api', 'bot', 'formula', 'mixed'))
);
COMMENT ON TABLE finance.operations IS 'Операции внутри разделов, определяют правила ввода';

CREATE TABLE IF NOT EXISTS finance.operation_formulas (
  formula_id bigserial PRIMARY KEY,
  operation_id bigint NOT NULL REFERENCES finance.operations(operation_id) ON DELETE CASCADE,
  version integer NOT NULL,
  expression_json jsonb NOT NULL,
  rounding_mode text NOT NULL DEFAULT 'half_up',
  scale integer NOT NULL DEFAULT 2,
  effective_from date NOT NULL,
  effective_to date,
  is_active boolean NOT NULL DEFAULT true,
  comment text,
  created_by text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_finance_formula_version UNIQUE (operation_id, version),
  CONSTRAINT ck_finance_formula_dates CHECK (effective_to IS NULL OR effective_to >= effective_from),
  CONSTRAINT ck_finance_formula_scale CHECK (scale BETWEEN 0 AND 6)
);
COMMENT ON TABLE finance.operation_formulas IS 'Версии формул расчета по операциям';

CREATE TABLE IF NOT EXISTS finance.entry_statuses (
  code text PRIMARY KEY,
  name text NOT NULL
);
COMMENT ON TABLE finance.entry_statuses IS 'Статусы первичных финансовых записей';

INSERT INTO finance.entry_statuses(code, name)
VALUES
  ('draft', 'Черновик'),
  ('confirmed', 'Подтверждено'),
  ('cancelled', 'Отменено')
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS finance.entries (
  entry_id bigserial NOT NULL,
  biz_date date NOT NULL,
  operation_id bigint NOT NULL REFERENCES finance.operations(operation_id),
  region_id bigint REFERENCES finance.dim_regions(region_id),
  source_id bigint REFERENCES finance.dim_sources(source_id),
  project_id bigint REFERENCES finance.projects(project_id),
  qty numeric(14,4) NOT NULL DEFAULT 1,
  amount numeric(16,2) NOT NULL,
  currency text NOT NULL DEFAULT 'RUB',
  input_channel text NOT NULL DEFAULT 'manual',
  external_key text,
  status_code text NOT NULL DEFAULT 'confirmed' REFERENCES finance.entry_statuses(code),
  comment text,
  payload_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  app_deal_id bigint,
  app_deal_item_id bigint,
  created_by text NOT NULL DEFAULT '',
  approved_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (entry_id, biz_date),
  CONSTRAINT ck_finance_entries_qty_nonzero CHECK (qty <> 0),
  CONSTRAINT ck_finance_entries_currency CHECK (currency ~ '^[A-Z]{3}$'),
  CONSTRAINT ck_finance_entries_channel CHECK (input_channel IN ('manual', 'api', 'bot', 'import', 'formula'))
) PARTITION BY RANGE (biz_date);
COMMENT ON TABLE finance.entries IS 'Первичные финансовые записи (большой объем, партиционирование по дате)';
COMMENT ON COLUMN finance.entries.app_deal_id IS 'Опциональная ссылка на app.deals.deal_id';
COMMENT ON COLUMN finance.entries.app_deal_item_id IS 'Опциональная ссылка на app.deal_items.deal_item_id';

CREATE TABLE IF NOT EXISTS finance.entries_default
  PARTITION OF finance.entries DEFAULT;

DO $$
DECLARE
  start_month date;
  i integer;
  part_name text;
  part_from date;
  part_to date;
BEGIN
  start_month := date_trunc('month', current_date)::date;
  FOR i IN 0..5 LOOP
    part_from := (start_month + (i || ' month')::interval)::date;
    part_to := (start_month + ((i + 1) || ' month')::interval)::date;
    part_name := format('entries_%s', to_char(part_from, 'YYYYMM'));
    EXECUTE format(
      'CREATE TABLE IF NOT EXISTS finance.%I PARTITION OF finance.entries FOR VALUES FROM (%L) TO (%L)',
      part_name,
      part_from,
      part_to
    );
  END LOOP;
END $$;

CREATE INDEX IF NOT EXISTS ix_finance_entries_biz_date ON finance.entries (biz_date);
CREATE INDEX IF NOT EXISTS ix_finance_entries_operation ON finance.entries (operation_id, biz_date);
CREATE INDEX IF NOT EXISTS ix_finance_entries_region_date ON finance.entries (region_id, biz_date);
CREATE INDEX IF NOT EXISTS ix_finance_entries_project_date ON finance.entries (project_id, biz_date);
CREATE INDEX IF NOT EXISTS ix_finance_entries_source_date ON finance.entries (source_id, biz_date);
CREATE INDEX IF NOT EXISTS ix_finance_entries_status_date ON finance.entries (status_code, biz_date);

CREATE TABLE IF NOT EXISTS finance.entry_dedupe_keys (
  dedupe_id bigserial PRIMARY KEY,
  input_channel text NOT NULL,
  external_key text NOT NULL,
  entry_id bigint NOT NULL,
  entry_biz_date date NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_finance_entry_dedupe UNIQUE (input_channel, external_key),
  CONSTRAINT fk_finance_entry_dedupe_entry FOREIGN KEY (entry_id, entry_biz_date)
    REFERENCES finance.entries(entry_id, biz_date)
    ON DELETE CASCADE
);
COMMENT ON TABLE finance.entry_dedupe_keys IS 'Глобальный реестр идемпотентности для входящих записей';

CREATE TABLE IF NOT EXISTS finance.entry_postings (
  posting_id bigserial PRIMARY KEY,
  entry_id bigint NOT NULL,
  entry_biz_date date NOT NULL,
  metric_code text NOT NULL,
  amount numeric(16,2) NOT NULL,
  calc_version integer,
  formula_id bigint REFERENCES finance.operation_formulas(formula_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT fk_finance_postings_entry FOREIGN KEY (entry_id, entry_biz_date)
    REFERENCES finance.entries(entry_id, biz_date)
    ON DELETE CASCADE
);
COMMENT ON TABLE finance.entry_postings IS 'Результат применения формул к первичным записям (готово для быстрых отчетов)';

CREATE INDEX IF NOT EXISTS ix_finance_postings_metric_date ON finance.entry_postings (metric_code, entry_biz_date);
CREATE INDEX IF NOT EXISTS ix_finance_postings_entry ON finance.entry_postings (entry_id, entry_biz_date);

CREATE TABLE IF NOT EXISTS finance.entry_audit (
  audit_id bigserial PRIMARY KEY,
  entry_id bigint,
  entry_biz_date date,
  action text NOT NULL,
  changed_by text NOT NULL DEFAULT '',
  changed_at timestamptz NOT NULL DEFAULT now(),
  old_data jsonb,
  new_data jsonb,
  CONSTRAINT ck_finance_entry_audit_action CHECK (action IN ('insert', 'update', 'status_change', 'delete'))
);
COMMENT ON TABLE finance.entry_audit IS 'Аудит изменений первичных записей finance';

CREATE INDEX IF NOT EXISTS ix_finance_entry_audit_entry ON finance.entry_audit (entry_id, changed_at DESC);

CREATE TABLE IF NOT EXISTS finance.import_batches (
  batch_id bigserial PRIMARY KEY,
  input_channel text NOT NULL DEFAULT 'import',
  file_name text,
  total_rows integer NOT NULL DEFAULT 0,
  success_rows integer NOT NULL DEFAULT 0,
  failed_rows integer NOT NULL DEFAULT 0,
  status text NOT NULL DEFAULT 'new',
  started_by text NOT NULL DEFAULT '',
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  details_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT ck_finance_import_status CHECK (status IN ('new', 'running', 'done', 'failed'))
);
COMMENT ON TABLE finance.import_batches IS 'Журнал массовых загрузок в finance';

CREATE TABLE IF NOT EXISTS finance.import_batch_rows (
  batch_row_id bigserial PRIMARY KEY,
  batch_id bigint NOT NULL REFERENCES finance.import_batches(batch_id) ON DELETE CASCADE,
  row_no integer NOT NULL,
  external_key text,
  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'new',
  error_message text,
  created_entry_id bigint,
  created_entry_biz_date date,
  CONSTRAINT ck_finance_import_row_status CHECK (status IN ('new', 'ok', 'failed', 'skipped'))
);
COMMENT ON TABLE finance.import_batch_rows IS 'Построчный протокол импорта с ошибками';

CREATE INDEX IF NOT EXISTS ix_finance_import_rows_batch
  ON finance.import_batch_rows(batch_id, row_no);

CREATE MATERIALIZED VIEW IF NOT EXISTS finance.mv_pnl_daily AS
SELECT
  p.entry_biz_date AS biz_date,
  e.region_id,
  e.source_id,
  e.project_id,
  SUM(CASE WHEN p.metric_code = 'revenue' THEN p.amount ELSE 0 END) AS revenue,
  SUM(CASE WHEN p.metric_code = 'direct_expense' THEN p.amount ELSE 0 END) AS direct_expense,
  SUM(CASE WHEN p.metric_code = 'indirect_expense' THEN p.amount ELSE 0 END) AS indirect_expense,
  SUM(CASE WHEN p.metric_code = 'revenue' THEN p.amount ELSE 0 END)
    - SUM(CASE WHEN p.metric_code = 'direct_expense' THEN p.amount ELSE 0 END)
    - SUM(CASE WHEN p.metric_code = 'indirect_expense' THEN p.amount ELSE 0 END) AS operating_profit
FROM finance.entry_postings p
JOIN finance.entries e
  ON e.entry_id = p.entry_id
 AND e.biz_date = p.entry_biz_date
WHERE e.status_code = 'confirmed'
GROUP BY p.entry_biz_date, e.region_id, e.source_id, e.project_id;

CREATE UNIQUE INDEX IF NOT EXISTS uq_finance_mv_pnl_daily_dims
  ON finance.mv_pnl_daily (biz_date, region_id, source_id, project_id);
