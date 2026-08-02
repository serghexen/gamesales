-- Сохраняет нормализованный SKU товара отдельно от пользовательского артикула для единого каталога.
ALTER TABLE marketplace.catalog_items
  ADD COLUMN IF NOT EXISTS sku text NOT NULL DEFAULT '';
