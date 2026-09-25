# Airpay: настройки первого запуска через Supplier Hub

Эта инструкция относится к Airpay в «Платежах». Первый запуск — с выключенной
оплатой. Проверку реального pay, его повтора (reconcile) и получения ваучера
выполняет только владелец вручную. Interhub API/worker и их настройки не менять.
Настройки внести **до запуска/пересоздания** новых контейнеров, а не после.

## 1. Отдельный env Airpay на сервере Hub

В каталоге checkout `homtech_hub` создать `.env.airpay`, ограничить права `600`.
Не копировать целиком основной env Interhub и не добавлять секреты в Git.
Ниже шаблон: значения в угловых скобках заменить своими.

```dotenv
DATABASE_URL='postgresql://<user>:<url-encoded-password>@<hub-db-host>:5432/<hub-db-name>'
SUPPLIER_HUB_DATA_SECRET='<отдельный случайный стабильный секрет, минимум 32 символа>'
SUPPLIER_HUB_CLIENTS_JSON='{"crm-airpay":"<случайный ключ CRM, минимум 32 символа>"}'

SUPPLIER_HUB_PURCHASES_ENABLED=false
AIRPAY_PAYMENTS_ENABLED=false
GAMESALES_LOCAL_UI=false
GAMESALES_SUPPLIER_OFFLINE=false

AIRPAY_USERNAME='<Basic-логин от Airpay>'
AIRPAY_PASSWORD='<Basic-пароль от Airpay>'
AIRPAY_API_URL=https://api.airpay.kz/AirPayService/api/v20
AIRPAY_VOUCHER_URL=https://partner.airpay.kz:9969/api/Payment/getVoucherCodeByPaymentId
AIRPAY_TIMEOUT_SEC=20
AIRPAY_SSL_VERIFY=true
AIRPAY_CA_CERT_PATH=
AIRPAY_PROXY_URL=
AIRPAY_TUNNEL_HOST=
```

- `DATABASE_URL` — существующая выбранная БД **Hub**, не CRM и не локальный
  staging-туннель. Проверить фактический контейнер/базу перед миграцией; имя сети
  само по себе не доказывает окружение. В ней появится отдельная схема
  `supplier_hub_airpay`. Учётной записи мигратора нужны права создания схемы/таблиц.
- Два секрета сгенерировать независимо, например двумя вызовами
  `openssl rand -hex 32` на доверенной машине. Сохранить в менеджере паролей.
  `SUPPLIER_HUB_DATA_SECRET` нужен для расшифровки сохранённых кодов: резервная
  копия БД должна сопровождаться сохранением этого ключа. Не менять ключ при
  обычной выкладке. Для уже существующей БД Airpay использовать прежний ключ.
- Логин и пароль вводятся отдельно: вручную кодировать их в Base64 не нужно.
  Значения с `$`/`#` заключать в одинарные кавычки согласно синтаксису dotenv;
  при наличии одинарной кавычки в самом пароле учитывать экранирование Compose.
- `AIRPAY_PROXY_URL` пустой при прямом выходе сервера к Airpay. Если требуется
  прокси, указать его реальный HTTP(S)-адрес, доступный **из контейнера**.
  `127.0.0.1:3129` локальной машины сюда не переносить. Согласовать исходящий IP
  с Airpay, если доступ ограничен списком IP.
- `AIRPAY_TUNNEL_HOST` относится к локальному SSH-сценарию; на сервере при
  `GAMESALES_LOCAL_UI=false` туннель не используется. `AIRPAY_SSL_VERIFY=true`
  сохранять; нестандартный CA требует файла, доступного внутри контейнера,
  и отдельного read-only mount, которого нет в базовом Compose.
- `SUPPLIER_HUB_PURCHASES_ENABLED=false` здесь задаётся **только в новом
  `.env.airpay`**. Одноимённую настройку работающего Interhub не менять.

## 2. Параметры отдельного Compose-проекта Hub

В shell на сервере Hub, из checkout `homtech_hub`:

```sh
export AIRPAY_ENV_FILE="$PWD/.env.airpay"
export AIRPAY_DOCKER_NETWORK='<существующая общая сеть CRM API и выбранной БД Hub>'
export AIRPAY_RELEASE_TAG='airpay-20260925'
export AIRPAY_DEPLOY_PAYMENTS_ENABLED=false
python api/scripts/airpay_deploy_preflight.py
```

Preflight читает конфигурацию и сеть, не запускает контейнеры, миграции или Airpay.
На хосте нужен Docker Compose v2 и Python 3. В исходниках CRM production API уже
подключён к external-сети `homtech-hub-staging_default`; **проверить её реальное
назначение на сервере**, не выбирать production-БД по названию вслепую.
При общей сети CRM сможет использовать `http://airpay-api:8011`.
Для разных серверов нужен отдельно настроенный защищённый внутренний маршрут;
порт 8011 базовый Compose публикует только на loopback хоста.

После проверки резервной копии Hub с ключом, ресурсов, точных Git-ревизий и
успешного preflight:

```sh
docker compose -f docker-compose.airpay.yml build airpay-api airpay-migrate
docker compose -f docker-compose.airpay.yml run --rm --no-deps airpay-migrate
docker compose -f docker-compose.airpay.yml up -d --no-deps --no-build airpay-api
curl --fail http://127.0.0.1:8011/live
curl --fail http://127.0.0.1:8011/ready
```

Использовать только самостоятельный `docker-compose.airpay.yml`, не объединять
с основным Compose и не выполнять общий `down/up`. Проверить шесть отметок
миграций в `supplier_hub_airpay.schema_migrations`, логи Airpay/PostgreSQL.
Ожидается `/ready`: `status=ready`, `payments_enabled=false`. Readiness проверяет
БД/основные настройки, но ещё не подтверждает правильность Basic-доступа Airpay.

## 3. Настройки CRM

В **существующий** `.env.prod` checkout `gamesales` добавить:

```dotenv
AIRPAY_BACKEND=hub
AIRPAY_HUB_URL=http://airpay-api:8011
AIRPAY_HUB_CLIENT_ID=crm-airpay
AIRPAY_HUB_CLIENT_KEY='<тот же ключ, что у crm-airpay в SUPPLIER_HUB_CLIENTS_JSON>'
AIRPAY_PAYMENTS_ENABLED=false
```

`AIRPAY_HUB_URL` выше подходит только при общей Docker-сети из предыдущего шага.
Это Airpay API на **8011**, а не существующий Interhub Hub на 8010.
`AIRPAY_USERNAME`/`AIRPAY_PASSWORD` в CRM для режима `hub` не нужны.
`AIRPAY_PAYMENTS_ENABLED=false` в CRM защищает прямой режим; в режиме `hub`
основной запрет оплаты действует на Hub. Поэтому флаги Hub обязательно оставить
выключенными. Не менять `SUPPLIER_HUB_BASE_URL`, операторские ключи, `INTERHUB_*`,
общие offline-флаги или `JWT_SECRET` CRM ради этой настройки.
Если CRM уже хранила коды Airpay, сохранить прежний `AIRPAY_DATA_SECRET`
(или прежний `JWT_SECRET`, когда использовался он) для чтения архива.

Перед переключением исключить новые прямые действия Airpay и проверить старый
журнал: `GET /integrations/airpay/cutover` под владельцем — `ready=true`, все
счётчики нулевые. На первой установке сначала подготовить таблицы CRM; отсутствие
таблиц не считается пустым журналом. Старые записи остаются архивом CRM.

CRM нужны также её шесть Airpay-миграций: Hub-прокси проверяет старый журнал
перед подготовкой. Перед миграцией проверить резервную копию **CRM** и весь
список pending: штатный мигратор применяет все runtime-файлы, а не только Airpay.
В исходниках есть также `20260923_01_supplier_catalog_change_details.sql`;
её нельзя молча включать в Airpay-выкладку, если на сервере она ещё не применена.
В таком случае сначала согласовать отдельный план миграций.

После проверки списка pending и резервной копии:

```sh
docker compose -f docker-compose.prod.yml --env-file .env.prod --profile maintenance run --rm --build migrate
docker compose -f docker-compose.prod.yml --env-file .env.prod build api web
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --no-deps api web
```

Проверить `app.schema_migrations`, `/health` CRM и логи API/PostgreSQL. Общий API
CRM при этом перезапускается, поэтому нужен обычный согласованный интервал
выкладки; существующий Hub Interhub и Seller не пересоздаются.

## 4. Проверка после запуска

Владелец вручную открывает «Платежи»: Interhub — баланс, каталог, форма подготовки;
Airpay — баланс/каталог, подготовка и check, количество, подтверждение с
выключенной оплатой, история/очередь/Excel. Проверить контракт `airpay.v1` с
`execution_backend=hub`, отсутствие незавершённых старых операций и ошибок.
Никаких pay/reconcile/получений ваучера для этого smoke-check не нужно.

Только после успешной проверки и отдельного решения владельца для реальных
покупок потребуются **все** разрешения: `SUPPLIER_HUB_PURCHASES_ENABLED=true`
в отдельном `.env.airpay` и `AIRPAY_DEPLOY_PAYMENTS_ENABLED=true` при пересоздании
только `airpay-api` (Compose перекрывает `AIRPAY_PAYMENTS_ENABLED` из env-файла).
До этого проверить queued-задания: включение оплаты может запустить ранее
подтверждённые задания. Это инструкция на будущее, не часть первого запуска.

Если Hub недоступен, не включать прямой fallback CRM. Восстанавливать Hub с его
БД/ключом и прежними идентификаторами. Подробнее: [эксплуатация](airpay-operations.md)
и [план внедрения](airpay-rollout-plan.md). Сам по себе push не подтверждает
готовность production: Docker build, backup и сеть проверяются на выбранном хосте.
