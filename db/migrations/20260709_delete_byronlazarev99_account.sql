BEGIN;

-- Удаляем игровой аккаунт byronlazarev99@outlook.com и данные, которые прямо на него ссылаются.
CREATE TEMP TABLE tmp_delete_byron_accounts (
  account_id bigint PRIMARY KEY
) ON COMMIT DROP;

INSERT INTO tmp_delete_byron_accounts(account_id)
SELECT a.account_id
FROM app.accounts a
JOIN app.domains d ON d.domain_id = a.domain_id
WHERE lower(btrim(coalesce(a.login_name, ''))) = 'byronlazarev99'
  AND lower(btrim(coalesce(d.name, ''))) = 'outlook.com';

DO $$
DECLARE
  v_accounts_count integer;
BEGIN
  SELECT count(*) INTO v_accounts_count FROM tmp_delete_byron_accounts;

  IF v_accounts_count = 0 THEN
    RAISE NOTICE 'Аккаунт byronlazarev99@outlook.com не найден, накат будет no-op';
  ELSIF v_accounts_count > 1 THEN
    RAISE EXCEPTION 'Найдено % нормальных аккаунтов byronlazarev99@outlook.com, удаление остановлено', v_accounts_count;
  ELSE
    RAISE NOTICE 'Найден аккаунт byronlazarev99@outlook.com, будет удален';
  END IF;
END $$;

-- Фиксируем связанные сущности до удаления, чтобы порядок FK был управляемым.
CREATE TEMP TABLE tmp_delete_byron_subscription_terms (
  term_id bigint PRIMARY KEY
) ON COMMIT DROP;

INSERT INTO tmp_delete_byron_subscription_terms(term_id)
SELECT st.term_id
FROM app.subscription_terms st
JOIN tmp_delete_byron_accounts ta ON ta.account_id = st.account_id;

CREATE TEMP TABLE tmp_delete_byron_account_assets (
  account_asset_id bigint PRIMARY KEY
) ON COMMIT DROP;

INSERT INTO tmp_delete_byron_account_assets(account_asset_id)
SELECT aa.account_asset_id
FROM app.account_assets aa
JOIN tmp_delete_byron_accounts ta ON ta.account_id = aa.account_id;

CREATE TEMP TABLE tmp_delete_byron_deal_items (
  deal_item_id bigint PRIMARY KEY,
  deal_id bigint NOT NULL
) ON COMMIT DROP;

INSERT INTO tmp_delete_byron_deal_items(deal_item_id, deal_id)
SELECT DISTINCT di.deal_item_id, di.deal_id
FROM app.deal_items di
WHERE EXISTS (
    SELECT 1 FROM tmp_delete_byron_accounts ta WHERE ta.account_id = di.account_id
  )
  OR EXISTS (
    SELECT 1 FROM tmp_delete_byron_account_assets taa WHERE taa.account_asset_id = di.account_asset_id
  )
  OR EXISTS (
    SELECT 1 FROM tmp_delete_byron_subscription_terms tst WHERE tst.term_id = di.subscription_term_id
  );

CREATE TEMP TABLE tmp_delete_byron_deals (
  deal_id bigint PRIMARY KEY
) ON COMMIT DROP;

INSERT INTO tmp_delete_byron_deals(deal_id)
SELECT DISTINCT deal_id
FROM tmp_delete_byron_deal_items;

CREATE TEMP TABLE tmp_delete_byron_deals_to_delete (
  deal_id bigint PRIMARY KEY
) ON COMMIT DROP;

-- Сделку удаляем целиком только если в ней нет позиций, не относящихся к этому аккаунту.
INSERT INTO tmp_delete_byron_deals_to_delete(deal_id)
SELECT td.deal_id
FROM tmp_delete_byron_deals td
WHERE NOT EXISTS (
  SELECT 1
  FROM app.deal_items di
  WHERE di.deal_id = td.deal_id
    AND NOT EXISTS (
      SELECT 1
      FROM tmp_delete_byron_deal_items tdi
      WHERE tdi.deal_item_id = di.deal_item_id
    )
);

CREATE TEMP TABLE tmp_delete_byron_finance_entries (
  entry_id bigint NOT NULL,
  biz_date date NOT NULL,
  PRIMARY KEY (entry_id, biz_date)
) ON COMMIT DROP;

-- Удаляем finance-записи по аккаунту, позициям и тем сделкам, которые будут удалены полностью.
INSERT INTO tmp_delete_byron_finance_entries(entry_id, biz_date)
SELECT DISTINCT e.entry_id, e.biz_date
FROM finance.entries e
WHERE EXISTS (
    SELECT 1
    FROM tmp_delete_byron_accounts ta
    WHERE e.external_key = 'account-' || ta.account_id::text
  )
  OR EXISTS (
    SELECT 1
    FROM tmp_delete_byron_deal_items tdi
    WHERE tdi.deal_item_id = e.app_deal_item_id
  )
  OR EXISTS (
    SELECT 1
    FROM tmp_delete_byron_deals_to_delete tdd
    WHERE tdd.deal_id = e.app_deal_id
  );

DO $$
DECLARE
  v_accounts_count integer;
  v_terms_count integer;
  v_assets_count integer;
  v_items_count integer;
  v_deals_count integer;
  v_finance_count integer;
BEGIN
  SELECT count(*) INTO v_accounts_count FROM tmp_delete_byron_accounts;
  SELECT count(*) INTO v_terms_count FROM tmp_delete_byron_subscription_terms;
  SELECT count(*) INTO v_assets_count FROM tmp_delete_byron_account_assets;
  SELECT count(*) INTO v_items_count FROM tmp_delete_byron_deal_items;
  SELECT count(*) INTO v_deals_count FROM tmp_delete_byron_deals_to_delete;
  SELECT count(*) INTO v_finance_count FROM tmp_delete_byron_finance_entries;

  RAISE NOTICE
    'План удаления byronlazarev99@outlook.com: accounts=%, subscription_terms=%, account_assets=%, deal_items=%, deals=%, finance_entries=%',
    v_accounts_count, v_terms_count, v_assets_count, v_items_count, v_deals_count, v_finance_count;
END $$;

-- Claims резервов могли быть созданы startup-логикой, поэтому проверяем наличие таблицы.
DO $$
BEGIN
  IF to_regclass('app.account_reserve_claims') IS NOT NULL THEN
    EXECUTE '
      DELETE FROM app.account_reserve_claims arc
      USING pg_temp.tmp_delete_byron_accounts ta
      WHERE arc.account_id = ta.account_id
    ';
  END IF;
END $$;

DELETE FROM finance.entry_audit a
USING tmp_delete_byron_finance_entries tfe
WHERE a.entry_id = tfe.entry_id
  AND a.entry_biz_date = tfe.biz_date;

DELETE FROM finance.import_batch_rows r
USING tmp_delete_byron_finance_entries tfe
WHERE r.created_entry_id = tfe.entry_id
  AND r.created_entry_biz_date = tfe.biz_date;

DELETE FROM finance.entries e
USING tmp_delete_byron_finance_entries tfe
WHERE e.entry_id = tfe.entry_id
  AND e.biz_date = tfe.biz_date;

DELETE FROM app.account_slot_assignments asa
WHERE EXISTS (
    SELECT 1 FROM tmp_delete_byron_accounts ta WHERE ta.account_id = asa.account_id
  )
  OR EXISTS (
    SELECT 1 FROM tmp_delete_byron_deal_items tdi WHERE tdi.deal_item_id = asa.deal_item_id
  )
  OR EXISTS (
    SELECT 1 FROM tmp_delete_byron_deals_to_delete tdd WHERE tdd.deal_id = asa.deal_id
  )
  OR EXISTS (
    SELECT 1 FROM tmp_delete_byron_subscription_terms tst WHERE tst.term_id = asa.subscription_term_id
  );

DELETE FROM app.deal_audit da
WHERE EXISTS (
    SELECT 1 FROM tmp_delete_byron_deal_items tdi WHERE tdi.deal_item_id = da.deal_item_id
  )
  OR EXISTS (
    SELECT 1 FROM tmp_delete_byron_deals_to_delete tdd WHERE tdd.deal_id = da.deal_id
  );

DELETE FROM app.deal_items di
USING tmp_delete_byron_deal_items tdi
WHERE di.deal_item_id = tdi.deal_item_id;

DELETE FROM app.deals d
USING tmp_delete_byron_deals_to_delete tdd
WHERE d.deal_id = tdd.deal_id;

DELETE FROM app.subscription_terms st
USING tmp_delete_byron_subscription_terms tst
WHERE st.term_id = tst.term_id;

DELETE FROM app.account_assets aa
USING tmp_delete_byron_account_assets taa
WHERE aa.account_asset_id = taa.account_asset_id;

DELETE FROM app.account_secrets s
USING tmp_delete_byron_accounts ta
WHERE s.account_id = ta.account_id;

DELETE FROM app.account_platforms ap
USING tmp_delete_byron_accounts ta
WHERE ap.account_id = ta.account_id;

DELETE FROM app.accounts a
USING tmp_delete_byron_accounts ta
WHERE a.account_id = ta.account_id;

COMMIT;
