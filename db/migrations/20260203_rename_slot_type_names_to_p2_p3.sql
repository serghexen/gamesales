BEGIN;

UPDATE app.slot_types
SET name = 'П2 (PS4)'
WHERE code = 'play_ps4';

UPDATE app.slot_types
SET name = 'П2 (PS5)'
WHERE code = 'play_ps5';

UPDATE app.slot_types
SET name = 'П3 (PS4)'
WHERE code = 'activate_ps4';

UPDATE app.slot_types
SET name = 'П3 (PS5)'
WHERE code = 'activate_ps5';

COMMIT;
