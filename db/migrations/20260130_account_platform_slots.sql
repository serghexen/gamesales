BEGIN;

-- Ensure PS4/PS5 platforms and capacities are up to date
INSERT INTO app.platforms(code, name, slot_capacity)
VALUES ('ps4','PlayStation 4', 6),('ps5','PlayStation 5', 3)
ON CONFLICT (code) DO UPDATE SET name=excluded.name, slot_capacity=excluded.slot_capacity;

-- Account-platform slot capacities
CREATE TABLE IF NOT EXISTS app.account_platforms (
  account_id     bigint NOT NULL REFERENCES app.accounts(account_id) ON DELETE CASCADE,
  platform_id    smallint NOT NULL REFERENCES app.platforms(platform_id),
  slot_capacity  integer NOT NULL DEFAULT 0,
  CONSTRAINT pk_account_platforms PRIMARY KEY (account_id, platform_id),
  CONSTRAINT ck_account_platform_slots CHECK (slot_capacity >= 0)
);

-- Backfill PS4/PS5 slots for all accounts
INSERT INTO app.account_platforms(account_id, platform_id, slot_capacity)
SELECT a.account_id, p.platform_id, p.slot_capacity
FROM app.accounts a
JOIN app.platforms p ON p.code IN ('ps4', 'ps5')
ON CONFLICT (account_id, platform_id) DO UPDATE SET slot_capacity=excluded.slot_capacity;

-- Replace old aggregated view with platform-specific one
DROP VIEW IF EXISTS app.v_account_slots;

CREATE OR REPLACE VIEW app.v_account_platform_slots AS
SELECT
  ap.account_id,
  ap.platform_id,
  ap.slot_capacity,
  COALESCE(SUM(
    CASE
      WHEN d.deal_type_code = 'rental'
       AND d.status_code = 'confirmed'
       AND di.returned_at IS NULL
       AND (di.start_at IS NULL OR di.start_at <= now())
       AND (di.end_at   IS NULL OR di.end_at   >= now())
      THEN di.slots_used
      ELSE 0
    END
  ), 0) AS occupied_slots,
  GREATEST(
    ap.slot_capacity - COALESCE(SUM(
    CASE
      WHEN d.deal_type_code = 'rental'
       AND d.status_code = 'confirmed'
       AND di.returned_at IS NULL
       AND (di.start_at IS NULL OR di.start_at <= now())
       AND (di.end_at   IS NULL OR di.end_at   >= now())
        THEN di.slots_used
        ELSE 0
      END
    ), 0),
    0
  ) AS free_slots
FROM app.account_platforms ap
LEFT JOIN app.deal_items di ON di.account_id = ap.account_id AND di.platform_id = ap.platform_id
LEFT JOIN app.deals d ON d.deal_id = di.deal_id
GROUP BY ap.account_id, ap.platform_id, ap.slot_capacity;

COMMIT;
