ALTER TABLE app.deal_items
  ADD COLUMN IF NOT EXISTS reserve_key text;

COMMENT ON COLUMN app.deal_items.reserve_key IS 'Ключ резерва аккаунта (reserveN), закрепленный за шеринговой сделкой';
