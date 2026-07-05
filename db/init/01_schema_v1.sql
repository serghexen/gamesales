CREATE SCHEMA IF NOT EXISTS app;
COMMENT ON SCHEMA app IS 'Схема приложения GameSales';

CREATE TABLE IF NOT EXISTS app.platforms (
  platform_id  smallserial PRIMARY KEY,
  code         text NOT NULL UNIQUE,
  name         text NOT NULL,
  slot_capacity integer NOT NULL DEFAULT 0,
  is_archived  boolean NOT NULL DEFAULT false
);
COMMENT ON TABLE app.platforms IS 'Справочник платформ';
COMMENT ON COLUMN app.platforms.platform_id IS 'Идентификатор платформы';
COMMENT ON COLUMN app.platforms.code IS 'Код платформы (steam/psn/xbox/epic)';
COMMENT ON COLUMN app.platforms.name IS 'Название платформы';
COMMENT ON COLUMN app.platforms.slot_capacity IS 'Слотов на аккаунт для платформы';
COMMENT ON COLUMN app.platforms.is_archived IS 'Архивная запись';
CREATE INDEX IF NOT EXISTS ix_platforms_archived ON app.platforms (is_archived);

CREATE TABLE IF NOT EXISTS app.regions (
  region_id smallserial PRIMARY KEY,
  code      text NOT NULL UNIQUE,
  name      text NOT NULL,
  purchase_cost_rate numeric(12,6) NOT NULL DEFAULT 1.0,
  is_archived  boolean NOT NULL DEFAULT false
);
COMMENT ON TABLE app.regions IS 'Справочник регионов';
COMMENT ON COLUMN app.regions.region_id IS 'Идентификатор региона';
COMMENT ON COLUMN app.regions.code IS 'Код региона (RU/TR/US/EU)';
COMMENT ON COLUMN app.regions.name IS 'Название региона';
COMMENT ON COLUMN app.regions.purchase_cost_rate IS 'Коэффициент пересчета закупа в RUB';
COMMENT ON COLUMN app.regions.is_archived IS 'Архивная запись';
CREATE INDEX IF NOT EXISTS ix_regions_archived ON app.regions (is_archived);

CREATE TABLE IF NOT EXISTS app.account_statuses (
  code text PRIMARY KEY,
  name text NOT NULL
);
COMMENT ON TABLE app.account_statuses IS 'Справочник статусов аккаунтов';
COMMENT ON COLUMN app.account_statuses.code IS 'Код статуса';
COMMENT ON COLUMN app.account_statuses.name IS 'Название статуса';

CREATE TABLE IF NOT EXISTS app.asset_types (
  code text PRIMARY KEY,
  name text NOT NULL
);
COMMENT ON TABLE app.asset_types IS 'Справочник типов ассетов';
COMMENT ON COLUMN app.asset_types.code IS 'Код типа ассета';
COMMENT ON COLUMN app.asset_types.name IS 'Название типа ассета';

CREATE TABLE IF NOT EXISTS app.deal_types (
  code text PRIMARY KEY,
  name text NOT NULL
);
COMMENT ON TABLE app.deal_types IS 'Справочник типов сделок';
COMMENT ON COLUMN app.deal_types.code IS 'Код типа сделки';
COMMENT ON COLUMN app.deal_types.name IS 'Название типа сделки';

CREATE TABLE IF NOT EXISTS app.deal_statuses (
  code text PRIMARY KEY,
  name text NOT NULL
);

CREATE TABLE IF NOT EXISTS app.deal_flow_statuses (
  code text PRIMARY KEY,
  name text NOT NULL
);

CREATE TABLE IF NOT EXISTS app.sources (
  source_id bigserial PRIMARY KEY,
  code text NOT NULL,
  name text NOT NULL,
  is_archived  boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS app.messengers (
  messenger_id bigserial PRIMARY KEY,
  code text NOT NULL,
  name text NOT NULL,
  is_archived boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS app.domains (
  domain_id smallserial PRIMARY KEY,
  name text NOT NULL UNIQUE,
  is_archived  boolean NOT NULL DEFAULT false
);
COMMENT ON TABLE app.deal_statuses IS 'Справочник статусов сделок';
COMMENT ON COLUMN app.deal_statuses.code IS 'Код статуса сделки';
COMMENT ON COLUMN app.deal_statuses.name IS 'Название статуса сделки';
COMMENT ON TABLE app.deal_flow_statuses IS 'Справочник статусов процесса сделки';
COMMENT ON COLUMN app.deal_flow_statuses.code IS 'Код статуса процесса сделки';
COMMENT ON COLUMN app.deal_flow_statuses.name IS 'Название статуса процесса сделки';
COMMENT ON TABLE app.sources IS 'Справочник источников клиентов';
COMMENT ON COLUMN app.sources.source_id IS 'Идентификатор источника';
COMMENT ON COLUMN app.sources.code IS 'Код источника';
COMMENT ON COLUMN app.sources.name IS 'Название источника';
COMMENT ON COLUMN app.sources.is_archived IS 'Архивная запись';
CREATE INDEX IF NOT EXISTS ix_sources_archived ON app.sources (is_archived);
CREATE INDEX IF NOT EXISTS ix_sources_code ON app.sources (code);
COMMENT ON TABLE app.messengers IS 'Справочник мессенджеров';
COMMENT ON COLUMN app.messengers.messenger_id IS 'Идентификатор мессенджера';
COMMENT ON COLUMN app.messengers.code IS 'Код мессенджера';
COMMENT ON COLUMN app.messengers.name IS 'Название мессенджера';
COMMENT ON COLUMN app.messengers.is_archived IS 'Архивная запись';
CREATE INDEX IF NOT EXISTS ix_messengers_archived ON app.messengers (is_archived);
CREATE INDEX IF NOT EXISTS ix_messengers_code ON app.messengers (code);
COMMENT ON TABLE app.domains IS 'Справочник доменов аккаунтов';
COMMENT ON COLUMN app.domains.domain_id IS 'Идентификатор домена';
COMMENT ON COLUMN app.domains.name IS 'Домен (например, example.com)';
COMMENT ON COLUMN app.domains.is_archived IS 'Архивная запись';
CREATE INDEX IF NOT EXISTS ix_domains_archived ON app.domains (is_archived);

CREATE TABLE IF NOT EXISTS app.product_types (
  code text PRIMARY KEY,
  name text NOT NULL,
  is_archived boolean NOT NULL DEFAULT false
);
COMMENT ON TABLE app.product_types IS 'Справочник типов товаров';
COMMENT ON COLUMN app.product_types.code IS 'Код типа товара (game/subscription/...)';
COMMENT ON COLUMN app.product_types.name IS 'Название типа товара';
COMMENT ON COLUMN app.product_types.is_archived IS 'Архивная запись';

CREATE TABLE IF NOT EXISTS app.products (
  product_id bigserial PRIMARY KEY,
  type_code text NOT NULL REFERENCES app.product_types(code),
  title text NOT NULL,
  short_title text,
  region_id smallint REFERENCES app.regions(region_id),
  is_archived boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  legacy_game_id bigint UNIQUE
);
COMMENT ON TABLE app.products IS 'Единый справочник товаров';
COMMENT ON COLUMN app.products.product_id IS 'Идентификатор товара';
COMMENT ON COLUMN app.products.type_code IS 'Тип товара';
COMMENT ON COLUMN app.products.title IS 'Название товара';
COMMENT ON COLUMN app.products.short_title IS 'Короткое название товара';
COMMENT ON COLUMN app.products.region_id IS 'Регион товара';
COMMENT ON COLUMN app.products.is_archived IS 'Архивная запись';
COMMENT ON COLUMN app.products.created_at IS 'Дата создания записи';
COMMENT ON COLUMN app.products.legacy_game_id IS 'Ссылка на legacy game_id для поэтапной миграции';
CREATE INDEX IF NOT EXISTS ix_products_type ON app.products (type_code);
CREATE INDEX IF NOT EXISTS ix_products_title ON app.products (title);
CREATE INDEX IF NOT EXISTS ix_products_archived ON app.products (is_archived);

CREATE TABLE IF NOT EXISTS app.game_products (
  product_id bigint PRIMARY KEY REFERENCES app.products(product_id) ON DELETE CASCADE,
  link text,
  logo_url text,
  logo_blob bytea,
  logo_mime text,
  text_lang text,
  audio_lang text,
  vr_support text
);
COMMENT ON TABLE app.game_products IS 'Игровые атрибуты товара';
COMMENT ON COLUMN app.game_products.product_id IS 'Ссылка на товар типа game';

CREATE TABLE IF NOT EXISTS app.subscription_products (
  product_id bigint PRIMARY KEY REFERENCES app.products(product_id) ON DELETE CASCADE,
  provider text,
  billing_period text,
  notes text
);
COMMENT ON TABLE app.subscription_products IS 'Атрибуты товара типа subscription';
COMMENT ON COLUMN app.subscription_products.product_id IS 'Ссылка на товар типа subscription';

CREATE TABLE IF NOT EXISTS app.subscription_plans (
  plan_id bigserial PRIMARY KEY,
  product_id bigint NOT NULL REFERENCES app.subscription_products(product_id) ON DELETE CASCADE,
  name text,
  duration_months integer,
  is_active boolean NOT NULL DEFAULT true,
  price numeric(14,2),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_subscription_plans_duration_nonneg CHECK (duration_months IS NULL OR duration_months >= 0),
  CONSTRAINT ck_subscription_plans_price_nonneg CHECK (price IS NULL OR price >= 0)
);
CREATE INDEX IF NOT EXISTS ix_subscription_plans_product ON app.subscription_plans (product_id);
COMMENT ON TABLE app.subscription_plans IS 'Дочерние тарифы/планы подписки';
COMMENT ON COLUMN app.subscription_plans.product_id IS 'Товар подписки';

CREATE TABLE IF NOT EXISTS app.product_platforms (
  product_id bigint NOT NULL REFERENCES app.products(product_id) ON DELETE CASCADE,
  platform_id smallint NOT NULL REFERENCES app.platforms(platform_id),
  CONSTRAINT pk_product_platforms PRIMARY KEY (product_id, platform_id)
);
COMMENT ON TABLE app.product_platforms IS 'Связь товаров и платформ';
COMMENT ON COLUMN app.product_platforms.product_id IS 'Товар';
COMMENT ON COLUMN app.product_platforms.platform_id IS 'Платформа';
CREATE INDEX IF NOT EXISTS ix_product_platforms_platform_id
  ON app.product_platforms(platform_id);

CREATE TABLE IF NOT EXISTS app.accounts (
  account_id     bigserial PRIMARY KEY,
  login_name     text,
  domain_id      smallint REFERENCES app.domains(domain_id),
  region_id      smallint REFERENCES app.regions(region_id),
  status_code    text NOT NULL DEFAULT 'active' REFERENCES app.account_statuses(code),
  is_deactivated boolean NOT NULL DEFAULT false,
  deactivated_at timestamptz,
  next_activation_at timestamptz,
  created_at     timestamptz NOT NULL DEFAULT now(),
  account_date   date,
  notes          text,
  CONSTRAINT uq_account_login UNIQUE (login_name, domain_id)
);
COMMENT ON TABLE app.accounts IS 'Аккаунты для продаж/аренд';
COMMENT ON COLUMN app.accounts.account_id IS 'Идентификатор аккаунта';
COMMENT ON COLUMN app.accounts.login_name IS 'Логин аккаунта (без домена)';
COMMENT ON COLUMN app.accounts.domain_id IS 'Домен аккаунта';
COMMENT ON COLUMN app.accounts.region_id IS 'Регион аккаунта';
COMMENT ON COLUMN app.accounts.status_code IS 'Статус аккаунта';
COMMENT ON COLUMN app.accounts.is_deactivated IS 'Признак деактивации аккаунта';
COMMENT ON COLUMN app.accounts.deactivated_at IS 'Когда аккаунт был деактивирован';
COMMENT ON COLUMN app.accounts.next_activation_at IS 'Когда аккаунт можно повторно активировать';
COMMENT ON COLUMN app.accounts.created_at IS 'Дата создания аккаунта';
COMMENT ON COLUMN app.accounts.account_date IS 'Дата аккаунта';
COMMENT ON COLUMN app.accounts.notes IS 'Заметки';
CREATE INDEX IF NOT EXISTS ix_accounts_is_deactivated ON app.accounts (is_deactivated);

CREATE TABLE IF NOT EXISTS app.subscription_terms (
  term_id bigserial PRIMARY KEY,
  product_id bigint NOT NULL REFERENCES app.subscription_products(product_id) ON DELETE CASCADE,
  account_id bigint NOT NULL REFERENCES app.accounts(account_id) ON DELETE RESTRICT,
  valid_until date NOT NULL,
  notes text,
  is_archived boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE app.subscription_terms IS 'Сроки подписок по базовому товару';
COMMENT ON COLUMN app.subscription_terms.product_id IS 'Базовый товар типа subscription';
COMMENT ON COLUMN app.subscription_terms.account_id IS 'Аккаунт, на котором действует срок подписки';
COMMENT ON COLUMN app.subscription_terms.valid_until IS 'Дата окончания срока';
CREATE INDEX IF NOT EXISTS idx_subscription_terms_product ON app.subscription_terms(product_id, valid_until);
CREATE INDEX IF NOT EXISTS idx_subscription_terms_account ON app.subscription_terms(account_id);
CREATE INDEX IF NOT EXISTS idx_subscription_terms_archived ON app.subscription_terms(is_archived);
CREATE INDEX IF NOT EXISTS idx_subscription_terms_active_account_product_valid_until
  ON app.subscription_terms(account_id, product_id, valid_until)
  WHERE is_archived IS NOT TRUE;

CREATE TABLE IF NOT EXISTS app.account_platforms (
  account_id     bigint NOT NULL REFERENCES app.accounts(account_id) ON DELETE CASCADE,
  platform_id    smallint NOT NULL REFERENCES app.platforms(platform_id),
  slot_capacity  integer NOT NULL DEFAULT 0,
  CONSTRAINT pk_account_platforms PRIMARY KEY (account_id, platform_id),
  CONSTRAINT ck_account_platform_slots CHECK (slot_capacity >= 0)
);
COMMENT ON TABLE app.account_platforms IS 'Слоты аккаунтов по платформам';
COMMENT ON COLUMN app.account_platforms.account_id IS 'Аккаунт';
COMMENT ON COLUMN app.account_platforms.platform_id IS 'Платформа';
COMMENT ON COLUMN app.account_platforms.slot_capacity IS 'Всего слотов на платформе';

CREATE TABLE IF NOT EXISTS app.slot_types (
  code text PRIMARY KEY,
  name text NOT NULL,
  platform_code text NOT NULL,
  mode text NOT NULL,
  capacity integer NOT NULL DEFAULT 0,
  CONSTRAINT ck_slot_type_mode CHECK (mode IN ('play', 'activate')),
  CONSTRAINT ck_slot_type_capacity CHECK (capacity >= 0)
);

INSERT INTO app.slot_types(code, name, platform_code, mode, capacity)
VALUES
  ('play_ps4', 'П3 (PS4)', 'ps4', 'play', 2),
  ('play_ps5', 'П3 (PS5)', 'ps5', 'play', 2),
  ('activate_ps4', 'П2 (PS4)', 'ps4', 'activate', 2),
  ('activate_ps5', 'П2 (PS5)', 'ps5', 'activate', 2)
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS app.account_assets (
  account_asset_id bigserial PRIMARY KEY,
  account_id       bigint NOT NULL REFERENCES app.accounts(account_id) ON DELETE CASCADE,
  product_id       bigint REFERENCES app.products(product_id) ON DELETE RESTRICT,
  asset_type_code  text NOT NULL DEFAULT 'game' REFERENCES app.asset_types(code),
  notes            text,
  UNIQUE (account_id, product_id, asset_type_code)
);

CREATE INDEX IF NOT EXISTS idx_account_assets_product
  ON app.account_assets (product_id, account_id)
  WHERE asset_type_code = 'game';

CREATE INDEX IF NOT EXISTS idx_account_assets_account_product
  ON app.account_assets (account_id, product_id)
  WHERE asset_type_code = 'game';
CREATE INDEX IF NOT EXISTS idx_account_assets_product_account_live
  ON app.account_assets (product_id, account_id)
  WHERE asset_type_code IN ('game', 'subscription');
CREATE INDEX IF NOT EXISTS idx_account_assets_account_product_live
  ON app.account_assets (account_id, product_id)
  WHERE asset_type_code IN ('game', 'subscription');
CREATE INDEX IF NOT EXISTS idx_account_assets_product_id
  ON app.account_assets (product_id);

CREATE TABLE IF NOT EXISTS app.account_secrets (
  account_secret_id bigserial PRIMARY KEY,
  account_id        bigint NOT NULL REFERENCES app.accounts(account_id) ON DELETE CASCADE,
  secret_key        text NOT NULL,
  secret_value      text NOT NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (account_id, secret_key)
);
COMMENT ON TABLE app.account_assets IS 'Ассеты, привязанные к аккаунтам';
COMMENT ON COLUMN app.account_assets.account_asset_id IS 'Идентификатор связи';
COMMENT ON COLUMN app.account_assets.account_id IS 'Аккаунт';
COMMENT ON COLUMN app.account_assets.product_id IS 'Товар';
COMMENT ON COLUMN app.account_assets.asset_type_code IS 'Тип ассета';
COMMENT ON COLUMN app.account_assets.notes IS 'Заметки';
COMMENT ON TABLE app.account_secrets IS 'Секреты аккаунтов (пароли, резервы)';
COMMENT ON COLUMN app.account_secrets.account_secret_id IS 'Идентификатор секрета';
COMMENT ON COLUMN app.account_secrets.account_id IS 'Аккаунт';
COMMENT ON COLUMN app.account_secrets.secret_key IS 'Ключ секрета (password/reserve1/...)';
COMMENT ON COLUMN app.account_secrets.secret_value IS 'Значение секрета (base64)';
COMMENT ON COLUMN app.account_secrets.created_at IS 'Дата создания секрета';

CREATE TABLE IF NOT EXISTS app.customers (
  customer_id bigserial PRIMARY KEY,
  nickname    text NOT NULL,
  customer_login text,
  customer_password text,
  source_id   bigint REFERENCES app.sources(source_id),
  contacts    text,
  notes       text,
  created_at  timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE app.customers IS 'Клиенты';
COMMENT ON COLUMN app.customers.customer_id IS 'Идентификатор клиента';
COMMENT ON COLUMN app.customers.nickname IS 'Имя/ник клиента';
COMMENT ON COLUMN app.customers.customer_login IS 'Логин клиента';
COMMENT ON COLUMN app.customers.customer_password IS 'Пароль клиента';
COMMENT ON COLUMN app.customers.source_id IS 'Источник привлечения';
COMMENT ON COLUMN app.customers.contacts IS 'Контакты клиента';
COMMENT ON COLUMN app.customers.notes IS 'Заметки';
COMMENT ON COLUMN app.customers.created_at IS 'Дата создания записи';

CREATE TABLE IF NOT EXISTS app.deals (
  deal_id      bigserial PRIMARY KEY,
  deal_type_code text NOT NULL REFERENCES app.deal_types(code),
  status_code    text NOT NULL DEFAULT 'confirmed' REFERENCES app.deal_statuses(code),
  flow_status_code text NOT NULL DEFAULT 'pending' REFERENCES app.deal_flow_statuses(code),
  region_id    smallint REFERENCES app.regions(region_id),
  customer_id  bigint REFERENCES app.customers(customer_id),
  messenger_id bigint REFERENCES app.messengers(messenger_id),
  order_number text,
  responsible_username text,
  currency     text NOT NULL DEFAULT 'RUB',
  total_amount numeric(14,2),
  notes        text,
  lock_version integer NOT NULL DEFAULT 1,
  created_at   timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);
COMMENT ON TABLE app.deals IS 'Сделки (услуга/шеринг/расход и т.д.)';
COMMENT ON COLUMN app.deals.deal_id IS 'Идентификатор сделки';
COMMENT ON COLUMN app.deals.deal_type_code IS 'Тип сделки';
COMMENT ON COLUMN app.deals.status_code IS 'Статус сделки';
COMMENT ON COLUMN app.deals.flow_status_code IS 'Статус процесса сделки';
COMMENT ON COLUMN app.deals.region_id IS 'Регион сделки';
COMMENT ON COLUMN app.deals.customer_id IS 'Клиент';
COMMENT ON COLUMN app.deals.messenger_id IS 'Мессенджер коммуникации с клиентом';
COMMENT ON COLUMN app.deals.order_number IS 'Номер заказа/заявки';
COMMENT ON COLUMN app.deals.responsible_username IS 'Ответственный менеджер';
COMMENT ON COLUMN app.deals.currency IS 'Валюта';
COMMENT ON COLUMN app.deals.total_amount IS 'Сумма сделки';
COMMENT ON COLUMN app.deals.notes IS 'Заметки';
COMMENT ON COLUMN app.deals.lock_version IS 'Версия записи для optimistic locking';
COMMENT ON COLUMN app.deals.created_at IS 'Дата создания сделки';
COMMENT ON COLUMN app.deals.completed_at IS 'Дата завершения сделки';
CREATE INDEX IF NOT EXISTS ix_deals_messenger_id ON app.deals (messenger_id);

CREATE TABLE IF NOT EXISTS app.deal_items (
  deal_item_id     bigserial PRIMARY KEY,
  deal_id          bigint NOT NULL REFERENCES app.deals(deal_id) ON DELETE CASCADE,
  account_id       bigint REFERENCES app.accounts(account_id) ON DELETE RESTRICT,
  product_id       bigint REFERENCES app.products(product_id) ON DELETE RESTRICT,
  platform_id      smallint REFERENCES app.platforms(platform_id),
  account_asset_id bigint REFERENCES app.account_assets(account_asset_id) ON DELETE RESTRICT,
  qty              integer NOT NULL DEFAULT 1,
  price            numeric(14,2) NOT NULL DEFAULT 0,
  purchase_cost    numeric(14,2) NOT NULL DEFAULT 0,
  fee              numeric(14,2) NOT NULL DEFAULT 0,
  purchase_at      timestamptz,
  start_at         timestamptz,
  end_at           timestamptz,
  returned_at      timestamptz,
  slots_used       integer NOT NULL DEFAULT 1,
  slot_type_code   text REFERENCES app.slot_types(code),
  subscription_term_id bigint REFERENCES app.subscription_terms(term_id) ON DELETE RESTRICT,
  reserve_key      text,
  game_link        text,
  notes            text,
  CONSTRAINT ck_qty_positive CHECK (qty > 0),
  CONSTRAINT ck_slots_used_nonneg CHECK (slots_used >= 0),
  CONSTRAINT ck_lease_window CHECK (end_at IS NULL OR start_at IS NULL OR end_at >= start_at)
);
COMMENT ON TABLE app.deal_items IS 'Позиции сделки';
COMMENT ON COLUMN app.deal_items.deal_item_id IS 'Идентификатор позиции';
COMMENT ON COLUMN app.deal_items.deal_id IS 'Сделка';
COMMENT ON COLUMN app.deal_items.account_id IS 'Аккаунт (если применимо)';
COMMENT ON COLUMN app.deal_items.product_id IS 'Товар (если применимо)';
COMMENT ON COLUMN app.deal_items.platform_id IS 'Платформа (если применимо)';
COMMENT ON COLUMN app.deal_items.account_asset_id IS 'Ассет аккаунта (если применимо)';
COMMENT ON COLUMN app.deal_items.qty IS 'Количество';
COMMENT ON COLUMN app.deal_items.price IS 'Цена';
COMMENT ON COLUMN app.deal_items.purchase_cost IS 'Закупочная цена';
COMMENT ON COLUMN app.deal_items.fee IS 'Комиссия/расход';
COMMENT ON COLUMN app.deal_items.purchase_at IS 'Дата покупки';
COMMENT ON COLUMN app.deal_items.start_at IS 'Дата начала';
COMMENT ON COLUMN app.deal_items.end_at IS 'Дата окончания';
COMMENT ON COLUMN app.deal_items.returned_at IS 'Факт возврата';
COMMENT ON COLUMN app.deal_items.slots_used IS 'Количество занятых слотов';
COMMENT ON COLUMN app.deal_items.slot_type_code IS 'Тип слота';
COMMENT ON COLUMN app.deal_items.subscription_term_id IS 'Срок подписки, выбранный для аренды';
COMMENT ON COLUMN app.deal_items.reserve_key IS 'Ключ резерва аккаунта (reserveN), закрепленный за шеринговой сделкой';
COMMENT ON COLUMN app.deal_items.game_link IS 'Ссылка на игру';
COMMENT ON COLUMN app.deal_items.notes IS 'Заметки';
CREATE INDEX IF NOT EXISTS idx_deal_items_product_id
  ON app.deal_items (product_id);
CREATE INDEX IF NOT EXISTS idx_deal_items_subscription_term_id
  ON app.deal_items (subscription_term_id);
CREATE INDEX IF NOT EXISTS idx_deal_items_deal_id
  ON app.deal_items (deal_id);
CREATE INDEX IF NOT EXISTS idx_deal_items_account_id
  ON app.deal_items (account_id);

CREATE TABLE IF NOT EXISTS app.account_slot_assignments (
  assignment_id bigserial PRIMARY KEY,
  account_id bigint NOT NULL REFERENCES app.accounts(account_id) ON DELETE CASCADE,
  slot_type_code text NOT NULL REFERENCES app.slot_types(code),
  customer_id bigint REFERENCES app.customers(customer_id),
  product_id bigint REFERENCES app.products(product_id),
  subscription_term_id bigint REFERENCES app.subscription_terms(term_id) ON DELETE RESTRICT,
  deal_id bigint REFERENCES app.deals(deal_id),
  deal_item_id bigint REFERENCES app.deal_items(deal_item_id),
  assigned_at timestamptz NOT NULL DEFAULT now(),
  released_at timestamptz,
  assigned_by text,
  released_by text,
  notes text
);

CREATE INDEX IF NOT EXISTS idx_account_slot_assignments_active
  ON app.account_slot_assignments(account_id, slot_type_code)
  WHERE released_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_account_slot_assignments_product_id
  ON app.account_slot_assignments(product_id);
CREATE INDEX IF NOT EXISTS idx_slot_assignments_subscription_term_id
  ON app.account_slot_assignments(subscription_term_id);
CREATE INDEX IF NOT EXISTS idx_asa_deal_item_active
  ON app.account_slot_assignments(deal_item_id)
  WHERE released_at IS NULL;

-- Индексы для ускорения поиска/фильтрации по сделкам и клиентам.
CREATE INDEX IF NOT EXISTS idx_customers_nickname
  ON app.customers(nickname);
CREATE INDEX IF NOT EXISTS idx_deals_status_flow_created_deal
  ON app.deals(status_code, flow_status_code, created_at, deal_id);

CREATE TABLE IF NOT EXISTS app.deal_audit (
  audit_id bigserial PRIMARY KEY,
  deal_id bigint,
  deal_item_id bigint,
  table_name text NOT NULL,
  action text NOT NULL,
  changed_at timestamptz NOT NULL DEFAULT now(),
  changed_by text,
  old_data jsonb,
  new_data jsonb
);

CREATE OR REPLACE FUNCTION app.log_deal_audit()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  v_user text;
BEGIN
  v_user := current_setting('app.user', true);
  IF TG_OP = 'UPDATE' THEN
    IF to_jsonb(OLD) IS DISTINCT FROM to_jsonb(NEW) THEN
      IF TG_TABLE_NAME = 'deal_items' THEN
        INSERT INTO app.deal_audit(
          deal_id,
          deal_item_id,
          table_name,
          action,
          changed_by,
          old_data,
          new_data
        )
        VALUES (
          NEW.deal_id,
          NEW.deal_item_id,
          TG_TABLE_NAME,
          TG_OP,
          v_user,
          to_jsonb(OLD),
          to_jsonb(NEW)
        );
      ELSE
        INSERT INTO app.deal_audit(
          deal_id,
          deal_item_id,
          table_name,
          action,
          changed_by,
          old_data,
          new_data
        )
        VALUES (
          NEW.deal_id,
          NULL,
          TG_TABLE_NAME,
          TG_OP,
          v_user,
          to_jsonb(OLD),
          to_jsonb(NEW)
        );
      END IF;
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_deals_audit ON app.deals;
CREATE TRIGGER trg_deals_audit
AFTER UPDATE ON app.deals
FOR EACH ROW EXECUTE FUNCTION app.log_deal_audit();

DROP TRIGGER IF EXISTS trg_deal_items_audit ON app.deal_items;
CREATE TRIGGER trg_deal_items_audit
AFTER UPDATE ON app.deal_items
FOR EACH ROW EXECUTE FUNCTION app.log_deal_audit();

CREATE OR REPLACE VIEW app.v_account_platform_slots AS
SELECT
  ap.account_id,
  ap.platform_id,
  ap.slot_capacity,
  COALESCE(SUM(
    CASE
      WHEN d.deal_type_code = 'rental'
       AND d.status_code = 'confirmed'
       AND di.returned_at IS NULL
       AND (di.start_at IS NULL OR di.start_at <= now())
       AND (di.end_at   IS NULL OR di.end_at   >= now())
      THEN di.slots_used
      ELSE 0
    END
  ), 0) AS occupied_slots,
  GREATEST(
    ap.slot_capacity - COALESCE(SUM(
    CASE
      WHEN d.deal_type_code = 'rental'
       AND d.status_code = 'confirmed'
       AND di.returned_at IS NULL
       AND (di.start_at IS NULL OR di.start_at <= now())
       AND (di.end_at   IS NULL OR di.end_at   >= now())
        THEN di.slots_used
        ELSE 0
      END
    ), 0),
    0
  ) AS free_slots
FROM app.account_platforms ap
LEFT JOIN app.deal_items di ON di.account_id = ap.account_id AND di.platform_id = ap.platform_id
LEFT JOIN app.deals d ON d.deal_id = di.deal_id
GROUP BY ap.account_id, ap.platform_id, ap.slot_capacity;

CREATE OR REPLACE VIEW app.v_account_slot_status AS
SELECT
  a.account_id,
  st.code AS slot_type_code,
  st.platform_code,
  st.mode,
  st.capacity,
  COALESCE(
    SUM(
      CASE
        WHEN asa.assignment_id IS NOT NULL AND asa.released_at IS NULL THEN 1
        ELSE 0
      END
    ),
    0
  ) AS occupied,
  GREATEST(
    st.capacity - COALESCE(
      SUM(
        CASE
          WHEN asa.assignment_id IS NOT NULL AND asa.released_at IS NULL THEN 1
          ELSE 0
        END
      ),
      0
    ),
    0
  ) AS free
FROM app.accounts a
CROSS JOIN app.slot_types st
LEFT JOIN app.account_slot_assignments asa
  ON asa.account_id = a.account_id AND asa.slot_type_code = st.code
GROUP BY a.account_id, st.code, st.platform_code, st.mode, st.capacity;

INSERT INTO app.platforms(code, name, slot_capacity)
VALUES ('ps4','PlayStation 4', 6),('ps5','PlayStation 5', 3)
ON CONFLICT (code) DO UPDATE SET name=excluded.name, slot_capacity=excluded.slot_capacity;

INSERT INTO app.regions(code, name, purchase_cost_rate)
VALUES
  ('RU','Russia', 1.0),
  ('TR','Turkey', 2.8),
  ('US','USA', 1.0),
  ('EU','Europe', 1.0)
ON CONFLICT (code) DO UPDATE SET
  name=excluded.name,
  purchase_cost_rate=excluded.purchase_cost_rate;

INSERT INTO app.account_statuses(code, name)
VALUES
  ('active','Активный'),
  ('banned','Бан'),
  ('archived','Архив'),
  ('problem','Проблемный')
ON CONFLICT (code) DO NOTHING;

INSERT INTO app.asset_types(code, name)
VALUES
  ('game','Игра'),
  ('subscription','Подписка'),
  ('dlc','DLC'),
  ('other','Другое')
ON CONFLICT (code) DO NOTHING;

INSERT INTO app.product_types(code, name)
VALUES
  ('game', 'Игра'),
  ('subscription', 'Подписка')
ON CONFLICT (code) DO NOTHING;

INSERT INTO app.deal_types(code, name)
VALUES
  ('sale','Услуга'),
  ('rental','Шеринг'),
  ('expense','Расходы'),
  ('adjustment','Корректирование')
ON CONFLICT (code) DO NOTHING;

INSERT INTO app.deal_statuses(code, name)
VALUES
  ('draft','Черновик'),
  ('confirmed','Подтвержден'),
  ('cancelled','Отменен'),
  ('closed','Закрыт')
ON CONFLICT (code) DO NOTHING;

INSERT INTO app.deal_flow_statuses(code, name)
VALUES
  ('draft','Черновик'),
  ('pending','В ожидании'),
  ('completed','Завершен')
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS app.user_roles (
  code text PRIMARY KEY,
  name text NOT NULL
);

CREATE TABLE IF NOT EXISTS app.users (
  user_id bigserial PRIMARY KEY,
  username text NOT NULL UNIQUE,
  name text NOT NULL DEFAULT '',
  password_hash text NOT NULL,
  role_code text NOT NULL DEFAULT 'manager' REFERENCES app.user_roles(code),
  created_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO app.user_roles(code, name)
VALUES ('operator','Оператор'),('owner','Управляющий'),('admin','Администратор'),('manager','Менеджер')
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS app.ui_sections (
  section_code text PRIMARY KEY,
  section_name text NOT NULL,
  sort_order integer NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS app.role_ui_sections (
  role_code text NOT NULL REFERENCES app.user_roles(code) ON DELETE CASCADE,
  section_code text NOT NULL REFERENCES app.ui_sections(section_code) ON DELETE CASCADE,
  can_view boolean NOT NULL DEFAULT true,
  updated_at timestamptz NOT NULL DEFAULT now(),
  updated_by text NOT NULL DEFAULT '',
  PRIMARY KEY (role_code, section_code)
);

INSERT INTO app.ui_sections(section_code, section_name, sort_order)
VALUES
  ('deals', 'Сделки', 10),
  ('accounts', 'Аккаунты', 20),
  ('products', 'Товары', 30),
  ('ns-gift', 'NS Gift', 40),
  ('telegram', 'Чаты', 50),
  ('analytics', 'Аналитика', 60),
  ('catalogs', 'Справочники', 70),
  ('users', 'Пользователи', 80),
  ('profile', 'Профиль', 90),
  ('dashboard', 'Дашборд', 100)
ON CONFLICT (section_code) DO UPDATE
SET section_name = EXCLUDED.section_name,
    sort_order = EXCLUDED.sort_order;

INSERT INTO app.role_ui_sections(role_code, section_code, can_view, updated_by)
SELECT
  r.code,
  s.section_code,
  CASE
    WHEN lower(r.code) IN ('admin', 'owner') THEN true
    WHEN s.section_code IN ('analytics', 'catalogs', 'users', 'dashboard') THEN false
    ELSE true
  END AS can_view,
  'system'
FROM app.user_roles r
CROSS JOIN app.ui_sections s
ON CONFLICT (role_code, section_code) DO NOTHING;

CREATE SCHEMA IF NOT EXISTS tg;

CREATE TABLE IF NOT EXISTS tg.sessions (
  user_id         bigint PRIMARY KEY REFERENCES app.users(user_id) ON DELETE CASCADE,
  phone           text NOT NULL,
  session_string  text NOT NULL DEFAULT '',
  phone_code_hash text,
  status          text NOT NULL DEFAULT 'pending',
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  last_used_at    timestamptz
);

CREATE TABLE IF NOT EXISTS tg.contact_notes (
  user_id    bigint NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
  sender_id  bigint NOT NULL,
  title      text NOT NULL DEFAULT '',
  info       text NOT NULL DEFAULT '',
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, sender_id)
);

CREATE TABLE IF NOT EXISTS tg.shared_session (
  id              smallint PRIMARY KEY DEFAULT 1,
  phone           text NOT NULL DEFAULT '',
  session_string  text NOT NULL DEFAULT '',
  phone_code_hash text,
  status          text NOT NULL DEFAULT 'pending',
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  last_used_at    timestamptz,
  updated_by_user_id bigint REFERENCES app.users(user_id)
);

CREATE TABLE IF NOT EXISTS tg.contact_notes_shared (
  sender_id  bigint PRIMARY KEY,
  title      text NOT NULL DEFAULT '',
  info       text NOT NULL DEFAULT '',
  updated_at timestamptz NOT NULL DEFAULT now(),
  updated_by_user_id bigint REFERENCES app.users(user_id)
);

CREATE TABLE IF NOT EXISTS tg.sent_messages (
  message_id bigint NOT NULL,
  chat_id    bigint NOT NULL,
  sent_by_user_id bigint NOT NULL REFERENCES app.users(user_id),
  sent_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (message_id, chat_id)
);

CREATE TABLE IF NOT EXISTS tg.dialog_states (
  chat_id bigint PRIMARY KEY,
  status text NOT NULL DEFAULT 'new',
  updated_at timestamptz NOT NULL DEFAULT now(),
  updated_by_user_id bigint REFERENCES app.users(user_id),
  CONSTRAINT ck_tg_dialog_states_status CHECK (status IN ('new', 'accepted', 'archived'))
);

CREATE TABLE IF NOT EXISTS tg.dialog_snapshot (
  chat_id       bigint PRIMARY KEY,
  title         text NOT NULL DEFAULT '',
  unread_count  integer NOT NULL DEFAULT 0,
  is_group      boolean NOT NULL DEFAULT false,
  is_channel    boolean NOT NULL DEFAULT false,
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tg_dialog_snapshot_updated_at
  ON tg.dialog_snapshot(updated_at DESC);
