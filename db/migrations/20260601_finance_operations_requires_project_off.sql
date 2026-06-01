-- Проект временно исключен из UI ввода, поэтому снимаем обязательность проекта у операций.
UPDATE finance.operations
SET requires_project = false,
    updated_at = now()
WHERE requires_project IS TRUE;
