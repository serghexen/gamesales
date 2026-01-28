CREATE SCHEMA IF NOT EXISTS app;
COMMENT ON SCHEMA app IS 'Схема приложения GameSales';

CREATE TABLE IF NOT EXISTS app.platforms (
  platform_id  smallserial PRIMARY KEY,
  code         text NOT NULL UNIQUE,
  name         text NOT NULL
);
COMMENT ON TABLE app.platforms IS 'Справочник платформ';
COMMENT ON COLUMN app.platforms.platform_id IS 'Идентификатор платформы';
COMMENT ON COLUMN app.platforms.code IS 'Код платформы (steam/psn/xbox/epic)';
COMMENT ON COLUMN app.platforms.name IS 'Название платформы';

CREATE TABLE IF NOT EXISTS app.regions (
  region_id smallserial PRIMARY KEY,
  code      text NOT NULL UNIQUE,
  name      text NOT NULL
);
COMMENT ON TABLE app.regions IS 'Справочник регионов';
COMMENT ON COLUMN app.regions.region_id IS 'Идентификатор региона';
COMMENT ON COLUMN app.regions.code IS 'Код региона (RU/TR/US/EU)';
COMMENT ON COLUMN app.regions.name IS 'Название региона';

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

CREATE TABLE IF NOT EXISTS app.sources (
  code text PRIMARY KEY,
  name text NOT NULL
);

CREATE TABLE IF NOT EXISTS app.domains (
  domain_id smallserial PRIMARY KEY,
  name text NOT NULL UNIQUE
);
COMMENT ON TABLE app.deal_statuses IS 'Справочник статусов сделок';
COMMENT ON COLUMN app.deal_statuses.code IS 'Код статуса сделки';
COMMENT ON COLUMN app.deal_statuses.name IS 'Название статуса сделки';
COMMENT ON TABLE app.sources IS 'Справочник источников клиентов';
COMMENT ON COLUMN app.sources.code IS 'Код источника';
COMMENT ON COLUMN app.sources.name IS 'Название источника';
COMMENT ON TABLE app.domains IS 'Справочник доменов аккаунтов';
COMMENT ON COLUMN app.domains.domain_id IS 'Идентификатор домена';
COMMENT ON COLUMN app.domains.name IS 'Домен (например, example.com)';

CREATE TABLE IF NOT EXISTS app.game_titles (
  game_id      bigserial PRIMARY KEY,
  title        text NOT NULL,
  platform_id  smallint REFERENCES app.platforms(platform_id),
  region_id    smallint REFERENCES app.regions(region_id),
  created_at   timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE app.game_titles IS 'Справочник игровых тайтлов';
COMMENT ON COLUMN app.game_titles.game_id IS 'Идентификатор тайтла';
COMMENT ON COLUMN app.game_titles.title IS 'Название игры';
COMMENT ON COLUMN app.game_titles.platform_id IS 'Платформа игры';
COMMENT ON COLUMN app.game_titles.region_id IS 'Регион игры';
COMMENT ON COLUMN app.game_titles.created_at IS 'Дата создания записи';
CREATE INDEX IF NOT EXISTS ix_game_titles_title ON app.game_titles (title);

CREATE TABLE IF NOT EXISTS app.accounts (
  account_id     bigserial PRIMARY KEY,
  login_name     text,
  domain_id      smallint REFERENCES app.domains(domain_id),
  platform_id    smallint NOT NULL REFERENCES app.platforms(platform_id),
  region_id      smallint REFERENCES app.regions(region_id),
  status_code    text NOT NULL DEFAULT 'active' REFERENCES app.account_statuses(code),
  created_at     timestamptz NOT NULL DEFAULT now(),
  notes          text,
  slot_capacity  integer NOT NULL DEFAULT 1,
  slot_reserved  integer NOT NULL DEFAULT 0,
  CONSTRAINT ck_slots_nonneg CHECK (slot_capacity >= 0 AND slot_reserved >= 0),
  CONSTRAINT ck_slots_capacity CHECK (slot_capacity >= slot_reserved),
  CONSTRAINT uq_account_login UNIQUE (login_name, domain_id)
);
COMMENT ON TABLE app.accounts IS 'Аккаунты для продаж/аренд';
COMMENT ON COLUMN app.accounts.account_id IS 'Идентификатор аккаунта';
COMMENT ON COLUMN app.accounts.login_name IS 'Логин аккаунта (без домена)';
COMMENT ON COLUMN app.accounts.domain_id IS 'Домен аккаунта';
COMMENT ON COLUMN app.accounts.platform_id IS 'Платформа аккаунта';
COMMENT ON COLUMN app.accounts.region_id IS 'Регион аккаунта';
COMMENT ON COLUMN app.accounts.status_code IS 'Статус аккаунта';
COMMENT ON COLUMN app.accounts.created_at IS 'Дата создания аккаунта';
COMMENT ON COLUMN app.accounts.notes IS 'Заметки';
COMMENT ON COLUMN app.accounts.slot_capacity IS 'Всего слотов';
COMMENT ON COLUMN app.accounts.slot_reserved IS 'Зарезервировано слотов';

CREATE TABLE IF NOT EXISTS app.account_assets (
  account_asset_id bigserial PRIMARY KEY,
  account_id       bigint NOT NULL REFERENCES app.accounts(account_id) ON DELETE CASCADE,
  game_id          bigint NOT NULL REFERENCES app.game_titles(game_id) ON DELETE RESTRICT,
  asset_type_code  text NOT NULL DEFAULT 'game' REFERENCES app.asset_types(code),
  notes            text,
  UNIQUE (account_id, game_id, asset_type_code)
);

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
COMMENT ON COLUMN app.account_assets.game_id IS 'Игра/тайтл';
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
  source_code text REFERENCES app.sources(code),
  contacts    text,
  notes       text,
  created_at  timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE app.customers IS 'Клиенты';
COMMENT ON COLUMN app.customers.customer_id IS 'Идентификатор клиента';
COMMENT ON COLUMN app.customers.nickname IS 'Имя/ник клиента';
COMMENT ON COLUMN app.customers.source_code IS 'Источник привлечения';
COMMENT ON COLUMN app.customers.contacts IS 'Контакты клиента';
COMMENT ON COLUMN app.customers.notes IS 'Заметки';
COMMENT ON COLUMN app.customers.created_at IS 'Дата создания записи';

CREATE TABLE IF NOT EXISTS app.deals (
  deal_id      bigserial PRIMARY KEY,
  deal_type_code text NOT NULL REFERENCES app.deal_types(code),
  status_code    text NOT NULL DEFAULT 'confirmed' REFERENCES app.deal_statuses(code),
  customer_id  bigint REFERENCES app.customers(customer_id),
  currency     text NOT NULL DEFAULT 'RUB',
  total_amount numeric(14,2),
  notes        text,
  created_at   timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE app.deals IS 'Сделки (продажа/аренда/расход и т.д.)';
COMMENT ON COLUMN app.deals.deal_id IS 'Идентификатор сделки';
COMMENT ON COLUMN app.deals.deal_type_code IS 'Тип сделки';
COMMENT ON COLUMN app.deals.status_code IS 'Статус сделки';
COMMENT ON COLUMN app.deals.customer_id IS 'Клиент';
COMMENT ON COLUMN app.deals.currency IS 'Валюта';
COMMENT ON COLUMN app.deals.total_amount IS 'Сумма сделки';
COMMENT ON COLUMN app.deals.notes IS 'Заметки';
COMMENT ON COLUMN app.deals.created_at IS 'Дата создания сделки';

CREATE TABLE IF NOT EXISTS app.deal_items (
  deal_item_id     bigserial PRIMARY KEY,
  deal_id          bigint NOT NULL REFERENCES app.deals(deal_id) ON DELETE CASCADE,
  account_id       bigint REFERENCES app.accounts(account_id) ON DELETE RESTRICT,
  game_id          bigint REFERENCES app.game_titles(game_id) ON DELETE RESTRICT,
  platform_id      smallint REFERENCES app.platforms(platform_id),
  account_asset_id bigint REFERENCES app.account_assets(account_asset_id) ON DELETE RESTRICT,
  qty              integer NOT NULL DEFAULT 1,
  price            numeric(14,2) NOT NULL DEFAULT 0,
  fee              numeric(14,2) NOT NULL DEFAULT 0,
  purchase_at      timestamptz,
  start_at         timestamptz,
  end_at           timestamptz,
  returned_at      timestamptz,
  slots_used       integer NOT NULL DEFAULT 1,
  notes            text,
  CONSTRAINT ck_qty_positive CHECK (qty > 0),
  CONSTRAINT ck_slots_used_nonneg CHECK (slots_used >= 0),
  CONSTRAINT ck_lease_window CHECK (end_at IS NULL OR start_at IS NULL OR end_at >= start_at),
  CONSTRAINT ck_one_target CHECK (
    (account_id IS NOT NULL)::int +
    (account_asset_id IS NOT NULL)::int +
    (game_id IS NOT NULL)::int >= 1
  )
);
COMMENT ON TABLE app.deal_items IS 'Позиции сделки';
COMMENT ON COLUMN app.deal_items.deal_item_id IS 'Идентификатор позиции';
COMMENT ON COLUMN app.deal_items.deal_id IS 'Сделка';
COMMENT ON COLUMN app.deal_items.account_id IS 'Аккаунт (если применимо)';
COMMENT ON COLUMN app.deal_items.game_id IS 'Игра (если применимо)';
COMMENT ON COLUMN app.deal_items.platform_id IS 'Платформа (если применимо)';
COMMENT ON COLUMN app.deal_items.account_asset_id IS 'Ассет аккаунта (если применимо)';
COMMENT ON COLUMN app.deal_items.qty IS 'Количество';
COMMENT ON COLUMN app.deal_items.price IS 'Цена';
COMMENT ON COLUMN app.deal_items.fee IS 'Комиссия/расход';
COMMENT ON COLUMN app.deal_items.purchase_at IS 'Дата покупки';
COMMENT ON COLUMN app.deal_items.start_at IS 'Дата начала';
COMMENT ON COLUMN app.deal_items.end_at IS 'Дата окончания';
COMMENT ON COLUMN app.deal_items.returned_at IS 'Факт возврата';
COMMENT ON COLUMN app.deal_items.slots_used IS 'Количество занятых слотов';
COMMENT ON COLUMN app.deal_items.notes IS 'Заметки';

CREATE OR REPLACE VIEW app.v_account_slots AS
SELECT
  a.account_id,
  a.slot_capacity,
  a.slot_reserved,
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
    a.slot_capacity - a.slot_reserved - COALESCE(SUM(
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
FROM app.accounts a
LEFT JOIN app.deal_items di ON di.account_id = a.account_id
LEFT JOIN app.deals d ON d.deal_id = di.deal_id
GROUP BY a.account_id, a.slot_capacity, a.slot_reserved;

INSERT INTO app.platforms(code, name)
VALUES ('steam','Steam'),('xbox','Xbox'),('epic','Epic Games')
ON CONFLICT (code) DO NOTHING;

INSERT INTO app.regions(code, name)
VALUES ('RU','Russia'),('TR','Turkey'),('US','USA'),('EU','Europe')
ON CONFLICT (code) DO NOTHING;

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

INSERT INTO app.deal_types(code, name)
VALUES
  ('sale','Продажа'),
  ('rental','Аренда'),
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
