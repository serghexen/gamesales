BEGIN;

-- Current naming mapping:
--   P2 -> activate_*
--   P3 -> play_*
-- Required capacities:
--   P2 = 1
--   P3 = 2
UPDATE app.slot_types
SET capacity = 1
WHERE code IN ('activate_ps4', 'activate_ps5');

UPDATE app.slot_types
SET capacity = 2
WHERE code IN ('play_ps4', 'play_ps5');

COMMIT;
