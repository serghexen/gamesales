BEGIN;

-- Для игровых П2 держим два места, но второе открывается бизнес-правилом после 2 месяцев.
UPDATE app.slot_types
SET capacity = 2
WHERE code IN ('activate_ps4', 'activate_ps5');

COMMIT;
