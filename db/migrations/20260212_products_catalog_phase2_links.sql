BEGIN;

-- Добавляем product_id в позиции сделок для поэтапного перехода с game_id.
ALTER TABLE app.deal_items
  ADD COLUMN IF NOT EXISTS product_id bigint;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_deal_items_product_id'
      AND conrelid = 'app.deal_items'::regclass
  ) THEN
    ALTER TABLE app.deal_items
      ADD CONSTRAINT fk_deal_items_product_id
      FOREIGN KEY (product_id) REFERENCES app.products(product_id) ON DELETE RESTRICT;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_deal_items_product_id ON app.deal_items(product_id);

-- Добавляем product_id в ассеты аккаунта.
ALTER TABLE app.account_assets
  ADD COLUMN IF NOT EXISTS product_id bigint;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_account_assets_product_id'
      AND conrelid = 'app.account_assets'::regclass
  ) THEN
    ALTER TABLE app.account_assets
      ADD CONSTRAINT fk_account_assets_product_id
      FOREIGN KEY (product_id) REFERENCES app.products(product_id) ON DELETE RESTRICT;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_account_assets_product_id ON app.account_assets(product_id);

-- Добавляем product_id в назначения занятых слотов.
ALTER TABLE app.account_slot_assignments
  ADD COLUMN IF NOT EXISTS product_id bigint;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_account_slot_assignments_product_id'
      AND conrelid = 'app.account_slot_assignments'::regclass
  ) THEN
    ALTER TABLE app.account_slot_assignments
      ADD CONSTRAINT fk_account_slot_assignments_product_id
      FOREIGN KEY (product_id) REFERENCES app.products(product_id) ON DELETE RESTRICT;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_account_slot_assignments_product_id ON app.account_slot_assignments(product_id);

-- Бэкфилл ссылок product_id из legacy game_id.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'app' AND table_name = 'deal_items' AND column_name = 'game_id'
  ) THEN
    UPDATE app.deal_items di
    SET product_id = p.product_id
    FROM app.products p
    WHERE di.product_id IS NULL
      AND di.game_id IS NOT NULL
      AND p.legacy_game_id = di.game_id;
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'app' AND table_name = 'account_assets' AND column_name = 'game_id'
  ) THEN
    UPDATE app.account_assets aa
    SET product_id = p.product_id
    FROM app.products p
    WHERE aa.product_id IS NULL
      AND aa.game_id IS NOT NULL
      AND p.legacy_game_id = aa.game_id;
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'app' AND table_name = 'account_slot_assignments' AND column_name = 'game_id'
  ) THEN
    UPDATE app.account_slot_assignments asa
    SET product_id = p.product_id
    FROM app.products p
    WHERE asa.product_id IS NULL
      AND asa.game_id IS NOT NULL
      AND p.legacy_game_id = asa.game_id;
  END IF;
END $$;

COMMIT;
