-- Удаляем старый раздел "Аналитика": его сценарии перенесены в "Финансы".
DELETE FROM app.ui_sections
WHERE section_code = 'analytics';
