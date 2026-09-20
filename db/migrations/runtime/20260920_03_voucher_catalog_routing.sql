-- Порядок задаётся для собственного номинала; отключение выдачи не удаляет связку и снимки.
ALTER TABLE app.voucher_catalog_offers
  ADD COLUMN fulfillment_priority integer NOT NULL DEFAULT 1 CHECK (fulfillment_priority > 0),
  ADD COLUMN fulfillment_enabled boolean NOT NULL DEFAULT true;

-- Сохраняем прежний порядок существующих предложений, включая временно отвязанные.
WITH ranked AS (
  SELECT offer_id, row_number() OVER (PARTITION BY catalog_nominal_id ORDER BY offer_id) AS priority
  FROM app.voucher_catalog_offers
)
UPDATE app.voucher_catalog_offers o SET fulfillment_priority=r.priority
FROM ranked r WHERE r.offer_id=o.offer_id;

-- Версия защищает настройки от перезаписи устаревшей карточкой другого редактора.
ALTER TABLE app.voucher_catalog_nominals
  ADD COLUMN fulfillment_revision bigint NOT NULL DEFAULT 0 CHECK (fulfillment_revision >= 0);
