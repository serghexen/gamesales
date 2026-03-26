-- Для сроков подписки разрешаем несколько активных назначений,
-- а ограничения по слотам считаются на уровне бизнес-логики.
DROP INDEX IF EXISTS app.uq_slot_assignments_active_subscription_term;
