CREATE TABLE IF NOT EXISTS finance.cash_flow_opening_balances (
  balance_month date PRIMARY KEY,
  amount numeric(16,2) NOT NULL DEFAULT 0,
  comment text,
  created_by text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_finance_cash_flow_opening_month CHECK (date_trunc('month', balance_month)::date = balance_month)
);

COMMENT ON TABLE finance.cash_flow_opening_balances IS 'Ручные начальные остатки Cash Flow по месяцам';
COMMENT ON COLUMN finance.cash_flow_opening_balances.balance_month IS 'Первое число месяца, к которому относится остаток';
