-- Сохраняет единый статус заказа независимо от технических статусов конкретного маркетплейса.
ALTER TABLE marketplace.order_items
  ADD COLUMN IF NOT EXISTS normalized_status text NOT NULL DEFAULT 'problem';
