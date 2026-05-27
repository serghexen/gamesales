# Матрица прав по формам

Актуально по коду на 5 марта 2026.

## Роли
- `admin`
- `owner`
- `manager`
- `operator`

## Важно
- Доступ к самим страницам (`Сделки`, `Аккаунты`, `Товары`) сначала проверяется ролевой моделью разделов (RBAC sections).
- Если ролью раздел скрыт, форма этого раздела недоступна независимо от прав на поля.
- Ограничение с резервами у `owner` было из-за старого `require_role` на secret-endpoint'ах аккаунтов; 5 марта 2026 это исправлено.

## Сделки (Шеринг и Услуга)

| Поле / действие | admin / owner | manager | operator | Где проверяется |
|---|---|---|---|---|
| Открыть и редактировать обычную сделку (не `completed`) | Да | Да | Да | `deals_api.py`, `WorkDealEditorForm.vue` |
| Редактировать сделку в `completed` | Да | Нет | Нет | `deals_api.py` (`editing completed... only for admin/owner`) + `useDealModalFlow.js` |
| Ручная правка `created_at` / `completed_at` | Да | Нет | Нет | `useDealsActions.js`, `WorkDealEditorForm.vue`, `deals_api.py` |
| Менять `is_refund` в форме редактирования | Да (для `completed`) | Нет | Нет | UI: `WorkDealEditorForm.vue` (`canEditRefundFlag`) |
| Менять `is_refund` на backend в `pending` | Да | Да | Да | `deals_api.py` (`is_refund can be changed only for pending deals`) |
| Завершить сделку с возвратом | Да | Нет | Нет | `useDealsActions.js` + backend проверка |
| Кнопка `Возврат` (перевод `completed -> pending`, назначение на owner) | Да | Да | Да | `POST /deals/{id}/return` в `deals_api.py` |
| Удалить сделку | Только если `draft` | Только если `draft` | Только если `draft` | `DELETE /deals/{id}` |
| Создать продажу/шеринг (общие поля формы) | Да | Да | Да | `POST /deals` |
| Видеть `admin/owner` в списке «Ответственный» | Да | Нет (скрыты) | Нет (скрыты) | `auth_api.py` (`/users`) |

### Бизнес-валидации полей сделок (для всех ролей)
- `rental`: обязательны `account_id`, `product_id`, `slot_type_code` (если не черновик).
- `sale`: обязательны `region_code`, `source_id` (если не черновик).
- `created_at/completed_at` в ручной правке: `completed_at >= created_at`.
- `order_number` должен быть уникален для источников типа `market`.

## Аккаунты

| Поле / действие | admin / owner | manager | operator | Где проверяется |
|---|---|---|---|---|
| Создание аккаунта | Да | Да | Да | `POST /accounts` |
| Редактирование карточки | Да | Да | Да | `PUT /accounts/{id}` |
| Менять `status_code` | Да | Нет | Нет | `accounts_api.py` |
| Менять `is_deactivated` | Да | Да | Нет | UI: `canToggleAccountDeactivation`, backend: запрет для operator |
| Видеть статус деактивации | Да | Да | Да | `WorkAccountEditorModal.vue` |
| Чтение/запись секретов (`account_password`, `email_password`, `auth_code`, `reserveN`) | Да | Да | Да | `/accounts/{id}/secrets`, `/accounts/secrets/batch` |
| Привязка товаров к аккаунту | Да | Да | Да | `PUT /accounts/{id}/products` |
| Архивация аккаунта | Да | Да | Да | `DELETE /accounts/{id}` (soft archive) |

### Обязательные и валидируемые поля аккаунта
- Backend `POST /accounts`: обязательны `region_code`, `login_name`, `domain_code`, `account_date`.
- `account_date` не может быть из будущего (`validate_date_not_future`).
- Уникальность аккаунта: `(login_name, domain)`.
- Frontend форма создания дополнительно требует: `account_password`, `email_password`, `auth_code`.
- Резервы сохраняются как `reserve1`, `reserve2`, ... (из строки `reserve_text` по пробелам).

## Товары

| Поле / действие | admin / owner | manager | operator | Где проверяется |
|---|---|---|---|---|
| Создание товара | Да | Да | Да | `POST /products` (`get_current_user`) |
| Редактирование товара | Да | Да | Да | `PUT /products/{id}` |
| Архивация товара | Да | Да | Да | `DELETE /products/{id}` |
| Ограничения по ролям на поля формы товара | Нет отдельных | Нет отдельных | Нет отдельных | Роль не влияет на поля в форме |

### Обязательные и валидируемые поля товара
- Обязательны: `type_code`, `title`.
- `type_code` должен существовать в справочнике типов.
- Для `game` проверяется конфликт по названию+платформам.
- На `update` смена `type_code` запрещена.

## Управление ролевой моделью
- Настраивать видимость разделов и прав может только `admin/owner`.
- Это не field-level ACL, а доступ к разделам UI (`Сделки`, `Аккаунты`, `Товары`, и т.д.).
