BEGIN;

UPDATE app.slot_types
SET capacity = 2
WHERE code IN ('play_ps4', 'play_ps5');

COMMIT;
