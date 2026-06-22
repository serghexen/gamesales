-- Дозаполняем finance-регионы из основного справочника и держим связь при будущих изменениях.
INSERT INTO finance.dim_regions(code, name, app_region_id, is_active)
SELECT
  upper(trim(r.code)) AS code,
  trim(r.name) AS name,
  r.region_id AS app_region_id,
  r.is_archived IS NOT TRUE AS is_active
FROM app.regions r
ON CONFLICT (code) DO UPDATE
SET name=excluded.name,
    app_region_id=excluded.app_region_id,
    is_active=excluded.is_active,
    updated_at=now();

CREATE UNIQUE INDEX IF NOT EXISTS ux_finance_dim_regions_app_region_id
  ON finance.dim_regions(app_region_id)
  WHERE app_region_id IS NOT NULL;

CREATE OR REPLACE FUNCTION finance.sync_dim_region_from_app()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  normalized_code text;
  normalized_name text;
  active_value boolean;
BEGIN
  -- Обновляем finance-измерение при любом изменении основного региона, чтобы отчеты не теряли группировку.
  normalized_code := upper(trim(NEW.code));
  normalized_name := trim(COALESCE(NEW.name, ''));
  active_value := NEW.is_archived IS NOT TRUE;

  UPDATE finance.dim_regions
  SET code=normalized_code,
      name=normalized_name,
      is_active=active_value,
      updated_at=now()
  WHERE app_region_id=NEW.region_id;

  IF NOT FOUND THEN
    INSERT INTO finance.dim_regions(code, name, app_region_id, is_active)
    VALUES (normalized_code, normalized_name, NEW.region_id, active_value)
    ON CONFLICT (code) DO UPDATE
    SET name=excluded.name,
        app_region_id=excluded.app_region_id,
        is_active=excluded.is_active,
        updated_at=now();
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sync_finance_dim_regions ON app.regions;
CREATE TRIGGER trg_sync_finance_dim_regions
AFTER INSERT OR UPDATE OF code, name, is_archived ON app.regions
FOR EACH ROW
EXECUTE FUNCTION finance.sync_dim_region_from_app();
