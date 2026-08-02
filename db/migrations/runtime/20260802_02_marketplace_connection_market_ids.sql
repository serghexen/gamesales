-- migrate:no-transaction
-- Добавляет внешние идентификаторы Яндекс Маркета, получаемые после проверки API-Key.
ALTER TABLE marketplace.connections ADD COLUMN IF NOT EXISTS business_id bigint;
ALTER TABLE marketplace.connections ADD COLUMN IF NOT EXISTS campaign_id bigint;

ALTER TABLE marketplace.connections
  DROP CONSTRAINT IF EXISTS connections_workspace_id_provider_code_client_id_key;

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_marketplace_connections_workspace_ozon_client
  ON marketplace.connections(workspace_id, provider_code, client_id)
  WHERE provider_code='ozon';

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_marketplace_connections_workspace_campaign
  ON marketplace.connections(workspace_id, provider_code, campaign_id)
  WHERE campaign_id IS NOT NULL;
