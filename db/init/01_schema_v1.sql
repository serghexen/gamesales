CREATE SCHEMA IF NOT EXISTS app;
COMMENT ON SCHEMA app IS 'Схема приложения GameSales';

CREATE TABLE IF NOT EXISTS app.platforms (
  platform_id  smallserial PRIMARY KEY,
  code         text NOT NULL UNIQUE,
  name         text NOT NULL,
  slot_capacity integer NOT NULL DEFAULT 0
);
COMMENT ON TABLE app.platforms IS 'Справочник платформ';
COMMENT ON COLUMN app.platforms.platform_id IS 'Идентификатор платформы';
COMMENT ON COLUMN app.platforms.code IS 'Код платформы (steam/psn/xbox/epic)';
COMMENT ON COLUMN app.platforms.name IS 'Название платформы';
COMMENT ON COLUMN app.platforms.slot_capacity IS 'Слотов на аккаунт для платформы';

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

CREATE TABLE IF NOT EXISTS app.deal_flow_statuses (
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
COMMENT ON TABLE app.deal_flow_statuses IS 'Справочник статусов процесса сделки';
COMMENT ON COLUMN app.deal_flow_statuses.code IS 'Код статуса процесса сделки';
COMMENT ON COLUMN app.deal_flow_statuses.name IS 'Название статуса процесса сделки';
COMMENT ON TABLE app.sources IS 'Справочник источников клиентов';
COMMENT ON COLUMN app.sources.code IS 'Код источника';
COMMENT ON COLUMN app.sources.name IS 'Название источника';
COMMENT ON TABLE app.domains IS 'Справочник доменов аккаунтов';
COMMENT ON COLUMN app.domains.domain_id IS 'Идентификатор домена';
COMMENT ON COLUMN app.domains.name IS 'Домен (например, example.com)';

CREATE TABLE IF NOT EXISTS app.game_titles (
  game_id      bigserial PRIMARY KEY,
  title        text NOT NULL,
  short_title  text,
  link         text,
  logo_url     text,
  logo_blob    bytea,
  logo_mime    text,
  text_lang    text,
  audio_lang   text,
  vr_support   text,
  region_id    smallint REFERENCES app.regions(region_id),
  created_at   timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE app.game_titles IS 'Справочник игровых тайтлов';
COMMENT ON COLUMN app.game_titles.game_id IS 'Идентификатор тайтла';
COMMENT ON COLUMN app.game_titles.title IS 'Название игры';
COMMENT ON COLUMN app.game_titles.short_title IS 'Короткое название игры';
COMMENT ON COLUMN app.game_titles.link IS 'Ссылка на игру';
COMMENT ON COLUMN app.game_titles.logo_url IS 'Обложка игры';
COMMENT ON COLUMN app.game_titles.logo_blob IS 'Обложка игры (файл)';
COMMENT ON COLUMN app.game_titles.logo_mime IS 'MIME обложки';
COMMENT ON COLUMN app.game_titles.text_lang IS 'Язык текста';
COMMENT ON COLUMN app.game_titles.audio_lang IS 'Язык озвучки';
COMMENT ON COLUMN app.game_titles.vr_support IS 'Поддержка VR';
COMMENT ON COLUMN app.game_titles.region_id IS 'Регион игры';
COMMENT ON COLUMN app.game_titles.created_at IS 'Дата создания записи';
CREATE INDEX IF NOT EXISTS ix_game_titles_title ON app.game_titles (title);

CREATE TABLE IF NOT EXISTS app.game_platforms (
  game_id     bigint NOT NULL REFERENCES app.game_titles(game_id) ON DELETE CASCADE,
  platform_id smallint NOT NULL REFERENCES app.platforms(platform_id),
  CONSTRAINT pk_game_platforms PRIMARY KEY (game_id, platform_id)
);
COMMENT ON TABLE app.game_platforms IS 'Платформы тайтлов (многие-ко-многим)';
COMMENT ON COLUMN app.game_platforms.game_id IS 'Игра/тайтл';
COMMENT ON COLUMN app.game_platforms.platform_id IS 'Платформа';

CREATE TABLE IF NOT EXISTS app.accounts (
  account_id     bigserial PRIMARY KEY,
  login_name     text,
  domain_id      smallint REFERENCES app.domains(domain_id),
  region_id      smallint REFERENCES app.regions(region_id),
  status_code    text NOT NULL DEFAULT 'active' REFERENCES app.account_statuses(code),
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
COMMENT ON COLUMN app.accounts.created_at IS 'Дата создания аккаунта';
COMMENT ON COLUMN app.accounts.account_date IS 'Дата аккаунта';
COMMENT ON COLUMN app.accounts.notes IS 'Заметки';

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

CREATE TABLE IF NOT EXISTS app.account_assets (
  account_asset_id bigserial PRIMARY KEY,
  account_id       bigint NOT NULL REFERENCES app.accounts(account_id) ON DELETE CASCADE,
  game_id          bigint REFERENCES app.game_titles(game_id) ON DELETE RESTRICT,
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
  flow_status_code text NOT NULL DEFAULT 'pending' REFERENCES app.deal_flow_statuses(code),
  region_id    smallint REFERENCES app.regions(region_id),
  customer_id  bigint REFERENCES app.customers(customer_id),
  currency     text NOT NULL DEFAULT 'RUB',
  total_amount numeric(14,2),
  notes        text,
  created_at   timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE app.deals IS 'Сделки (продажа/шеринг/расход и т.д.)';
COMMENT ON COLUMN app.deals.deal_id IS 'Идентификатор сделки';
COMMENT ON COLUMN app.deals.deal_type_code IS 'Тип сделки';
COMMENT ON COLUMN app.deals.status_code IS 'Статус сделки';
COMMENT ON COLUMN app.deals.flow_status_code IS 'Статус процесса сделки';
COMMENT ON COLUMN app.deals.region_id IS 'Регион сделки';
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
  purchase_cost    numeric(14,2) NOT NULL DEFAULT 0,
  fee              numeric(14,2) NOT NULL DEFAULT 0,
  purchase_at      timestamptz,
  start_at         timestamptz,
  end_at           timestamptz,
  returned_at      timestamptz,
  slots_used       integer NOT NULL DEFAULT 1,
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
COMMENT ON COLUMN app.deal_items.game_id IS 'Игра (если применимо)';
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
COMMENT ON COLUMN app.deal_items.game_link IS 'Ссылка на игру';
COMMENT ON COLUMN app.deal_items.notes IS 'Заметки';

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
      CASE WHEN TG_TABLE_NAME = 'deal_items' THEN NEW.deal_item_id ELSE NULL END,
      TG_TABLE_NAME,
      TG_OP,
      v_user,
      to_jsonb(OLD),
      to_jsonb(NEW)
    );
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

INSERT INTO app.platforms(code, name, slot_capacity)
VALUES ('ps4','PlayStation 4', 6),('ps5','PlayStation 5', 3)
ON CONFLICT (code) DO UPDATE SET name=excluded.name, slot_capacity=excluded.slot_capacity;

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
  ('pending','В ожидании'),
  ('completed','Завершен')
ON CONFLICT (code) DO NOTHING;
