ALTER TABLE app.customers
  ADD COLUMN IF NOT EXISTS customer_login text,
  ADD COLUMN IF NOT EXISTS customer_password text;
