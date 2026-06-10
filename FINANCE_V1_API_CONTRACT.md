# Finance v1: контур управленческой аналитики

## 1) Цель v1
- Запустить отдельный контур учета `finance.*`, который не ломает текущий операционный контур `app.*`.
- Получать `P&L` по периоду и разрезам: регион, источник, проект, операция.
- Поддержать ввод данных вручную, через API и импортом.

## 2) Что считаем в v1
- `revenue` — выручка.
- `direct_expense` — прямые расходы.
- `indirect_expense` — косвенные расходы.
- `gross_profit` = `revenue - direct_expense`.
- `operating_profit` = `revenue - direct_expense - indirect_expense`.
- `margin` = `operating_profit / revenue` (если `revenue > 0`, иначе `0`).

## 3) Какие данные вносятся
- Первичные записи в `finance.entries`:
  - дата учета (`biz_date`);
  - операция (`operation_id`);
  - сумма (`amount`) и количество (`qty`);
  - измерения (`region_id`, `source_id`, `project_id`);
  - служебные поля (`input_channel`, `external_key`, `status_code`, `comment`, `payload_json`).
- Формулы по операциям в `finance.operation_formulas` (версии + период действия).
- Справочники: `sections`, `operations`, `projects`, `dim_regions`, `dim_sources`.

## 4) Принципы расчета
- Первичка хранится в `finance.entries`, формулы раскладывают запись в `finance.entry_postings`.
- Отчеты строятся по `entry_postings` и витрине `finance.mv_pnl_daily`.
- Для повторного импорта используется идемпотентность: уникальность `(input_channel, external_key)`.
- Учетные исправления делаются корректирующими записями, а не перезаписью истории.

## 5) Контракты API (v1)

### 5.1 Справочники

`GET /finance/catalogs/bootstrap`
- Возвращает все справочники для формы ввода и фильтров.

Пример ответа:
```json
{
  "types": [{"type_id": 1, "code": "revenue", "name": "Выручка"}],
  "sections": [{"section_id": 1, "code": "revenue", "name": "Выручка", "kind": "revenue"}],
  "operations": [{"operation_id": 10, "type_id": 1, "code": "sale_tr", "name": "Продажа TR", "requires_region": true}],
  "projects": [{"project_id": 100, "code": "asat_m", "name": "ASAT-M"}],
  "regions": [{"region_id": 1, "code": "TR", "name": "Turkey"}],
  "sources": [{"source_id": 1, "code": "ym", "name": "Yandex Market"}]
}
```

`POST /finance/catalogs/sections`
`POST /finance/catalogs/operations`
`POST /finance/catalogs/projects`
- CRUD для справочников `finance`.
- Реализованные v1 ручки:
  - `POST /finance/catalogs/sync-from-app`
  - `POST /finance/catalogs/seed-defaults`
  - `POST|PUT|DELETE /finance/catalogs/sections`
  - `POST|PUT|DELETE /finance/catalogs/operations`
  - `POST|PUT|DELETE /finance/catalogs/projects`

### 5.2 Ввод и журнал

`POST /finance/entries`
- Создание одной записи.

Тело запроса:
```json
{
  "biz_date": "2026-05-28",
  "operation_id": 10,
  "region_id": 1,
  "source_id": 1,
  "project_id": 100,
  "qty": 1,
  "amount": 3500.00,
  "currency": "RUB",
  "input_channel": "manual",
  "external_key": "manual-20260528-1",
  "comment": "Ручной ввод",
  "payload_json": {"raw": "опционально"}
}
```

Ответ:
```json
{
  "entry_id": 501,
  "biz_date": "2026-05-28",
  "status_code": "confirmed"
}
```

`POST /finance/entries/bulk`
- Массовая загрузка (CSV/JSON), возвращает `batch_id`.
- Реализован JSON-bulk формат:
  - `items[]` + `stop_on_error` + `file_name`
  - результат: `batch_id`, `success_rows`, `failed_rows`, список ошибок.

`POST /finance/integrations/yandex/sync`
- Старт ручной синхронизации Yandex Market за период `date_from/date_to`, возвращает `job_id`.
- В теле можно передать `store_code`: `asat`, `sps` или `mds`; по нему backend выбирает env-настройки магазина и finance-источник.
- Загружает отчет `united-orders`, берет доставленные строки с `incomeWithoutServices`.
- Создает дневную gross-запись поступления и, если комиссия больше нуля, дневную запись расхода по комиссиям.
- В отчете это дает `Поступления = gross_amount`, `Расходы = commission_amount`, `Итог = income_without_services`.
- В `payload_json` дневной записи сохраняет контрольные суммы: `rows_count`, `orders_count`, `gross_amount`, `commission_amount`, `income_without_services`.
- Идемпотентность: `external_key` вида `yandex-market:united-orders:{campaignId}:daily:{biz_date}:gross|commission`.

`GET /finance/integrations/yandex/sync/{job_id}`
- Возвращает статус ручной синхронизации: `queued/running/done/failed`, сообщение, ошибку или итоговую статистику.

`POST /finance/integrations/wildberries/sync`
- Старт ручной синхронизации Wildberries за период `date_from/date_to`, возвращает `job_id`.
- В теле передается `store_code`: `asat` или `sps`; backend выбирает отдельный токен и finance-источник `ASAT / wb` либо `SPS / wb`.
- Использует новый Finance API `POST /api/finance/v1/sales-reports/detailed` и пагинацию по `rrdId`.
- Для Basic-токена с многочасовым лимитом автоматически использует старый `reportDetailByPeriod` до его отключения 15 июля 2026 года.
- Сворачивает строки по `rrDate` в дневную gross-запись продаж и дневную запись прямых расходов.
- Расходы включают возвраты, разницу между продажами и `forPay`, логистику, хранение, приемку, удержания и штрафы за вычетом дополнительных начислений.
- В `payload_json` сохраняются суммы `gross_sales`, `returns`, `for_pay`, `delivery`, `storage`, `acceptance`, `deduction`, `penalty`, `additional_payment`, `payout_amount`.
- Идемпотентность: `external_key` вида `wildberries:{store_code}:sales-reports:daily:{biz_date}:gross|expense`.

`GET /finance/integrations/wildberries/sync/{job_id}`
- Возвращает статус ручной синхронизации WB: `queued/running/done/failed`, сообщение, ошибку или итоговую статистику.
- При лимите API задача остается в `running`, показывает обратный отсчет в `message` и автоматически продолжает запрос.

`GET /finance/entries`
- Журнал записей с фильтрами: `date_from`, `date_to`, `project_id`, `region_id`, `source_id`, `operation_id`, `status_code`, `limit`, `offset`.

`PATCH /finance/entries/{entry_id}`
- Изменение только разрешенных полей + аудит.

`POST /finance/entries/{entry_id}/status`
- Перевод статуса (`draft/confirmed/cancelled`).

### 5.3 Формулы

`POST /finance/formulas/preview`
- Превью расчета без записи в БД.

`POST /finance/formulas/rebuild`
- Перерасчет `entry_postings` для диапазона дат/операций (service endpoint для админа).

Реализованные v1 ручки:
- `GET /finance/formulas`
- `POST /finance/formulas`

### 5.4 Отчеты

`GET /finance/reports/pnl`
- Главный отчет P&L.
- Фильтры: `date_from`, `date_to`, `region_id`, `source_id`, `project_id`, `group_by` (`day|week|month|project|operation|source|region`).

Пример ответа:
```json
{
  "totals": {
    "revenue": 1200000.00,
    "direct_expense": 700000.00,
    "indirect_expense": 150000.00,
    "gross_profit": 500000.00,
    "operating_profit": 350000.00,
    "margin": 0.2917
  },
  "series": [
    {"bucket": "2026-05-01", "revenue": 100000.00, "direct_expense": 60000.00, "indirect_expense": 10000.00, "operating_profit": 30000.00}
  ]
}
```

`GET /finance/reports/projects`
- Таблица по проектам: выручка/расходы/прибыль/маржа.
- Реализован параметр `split_by_source` для режима:
  - `false` -> без источника (итог по проекту);
  - `true` -> каждый источник отдельной строкой внутри проекта.

`GET /finance/reports/drilldown`
- Проваливание до первички по выбранной ячейке отчета.

## 6) Что берем из `app.*`
- Для начальной синхронизации измерений:
  - `app.regions` -> `finance.dim_regions`;
  - `app.sources` -> `finance.dim_sources`;
  - `app.users` -> авторы действий.
- Источники из `app.sources` синхронизируются как отдельные записи по `app_source_id`
  (дубли `code` допустимы, например `ym` для разных направлений).
- Опционально для автозагрузки фактов:
  - `app.deals` + `app.deal_items` через ETL/джобу.
- Внешних ключей на `app.*` не делаем: связь только логическая через `app_*_id` поля.

## 7) Порядок реализации
- Шаг 1: применить миграцию `db/migrations/20260528_finance_schema_v1.sql`.
- Шаг 2: сделать backend-домен `api/domains/finance_*` (модели, API, сервис формул).
- Шаг 3: добавить bootstrap-ручки и CRUD справочников.
- Шаг 4: добавить ввод `entries` и bulk import.
- Шаг 5: добавить отчеты `pnl/projects/drilldown`.
- Шаг 6: подключить вкладку в `WorkView` и формы в `work/sections`.

## 8) Что увидит пользователь в UI
- `Общее окно`: KPI + динамика + waterfall.
- `Отчет по проектам`: таблица с переключателем "по источникам/без источника".
- `Операции`: форма ввода + журнал + статусы.
- `Справочники`: разделы, операции, формулы.
