# TODO

## Текущий бэклог
- Добавить пароль и ограничить доступ к Redis (`requirepass`, `bind/network rules`, обновить `REDIS_URL`).
- Добавить серверный поиск/ленивую загрузку аккаунтов в селекторах сделок, чтобы не грузить все аккаунты сразу.
- Добавить частичный индекс активных слотов для ускорения `/accounts/for-deal/availability` (`WHERE released_at IS NULL`).
- Исправить лимит `loadAccountDeals`: пагинация/"Показать еще" или явное уведомление "первые N".
- Защититься от гонки при одновременном создании шеринга: уникальный индекс активного слота (`account_id + slot_type_code WHERE released_at IS NULL`) + обработка 409 на API и сообщение на фронте.
- Добавить CI (GitHub Actions): автоматический запуск `cd gamesales-web && npm run check` на каждый PR.
- Добавить PR-шаблон (`.github/pull_request_template.md`) с чеклистом: комментарии, тесты, локальные проверки.

## Архив
- Ветка миграции `product-first` завершена (`phase1`-`phase8`), post-migration smoke-check пройден.
- Импорт после удаления `game_titles/game_platforms` считаем успешным; дальнейшие правки только по факту падений.
