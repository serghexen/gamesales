BEGIN;

-- Переименовываем отображаемое имя типа сделки sale без изменения кода и логики.
UPDATE app.deal_types
SET name = 'Услуга'
WHERE code = 'sale';

COMMIT;
