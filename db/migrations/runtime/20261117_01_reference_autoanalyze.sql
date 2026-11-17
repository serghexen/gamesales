-- Маленькие справочники анализируются после изменения, не дожидаясь 50 строк.
-- Данные не меняются; короткое ожидание блокировки защищает рабочие запросы.
SET LOCAL lock_timeout = '1s';
SET LOCAL statement_timeout = '15s';

ALTER TABLE app.account_statuses SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE app.asset_types SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE app.deal_flow_statuses SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE app.deal_statuses SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE app.deal_types SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE app.domains SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE app.messengers SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE app.platforms SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE app.product_types SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE app.regions SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE app.sources SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE app.subscription_products SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE app.user_roles SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE app.voucher_catalog_suppliers SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE app.slot_types SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE finance.dim_regions SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE finance.dim_sources SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE finance.entry_statuses SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE finance.projects SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE finance.section_types SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
ALTER TABLE finance.sections SET (autovacuum_analyze_threshold = 0, autovacuum_analyze_scale_factor = 0);
