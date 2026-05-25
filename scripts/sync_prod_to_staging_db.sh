#!/usr/bin/env bash
set -euo pipefail

# Читает значение переменной из env-файла, чтобы не дублировать секреты в командах.
get_env_value() {
  local env_file="$1"
  local key="$2"
  awk -F= -v k="$key" '$1==k {sub(/^[[:space:]]+/, "", $2); print $2; exit}' "$env_file"
}

# Проверяет обязательные входные файлы и сообщает понятную ошибку.
require_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "[ERROR] File not found: $file" >&2
    exit 1
  fi
}

PROD_COMPOSE_FILE="${PROD_COMPOSE_FILE:-docker-compose.prod.yml}"
PROD_ENV_FILE="${PROD_ENV_FILE:-.env.prod}"
STAGING_COMPOSE_FILE="${STAGING_COMPOSE_FILE:-docker-compose.staging.yml}"
STAGING_ENV_FILE="${STAGING_ENV_FILE:-.env.staging}"

require_file "$PROD_COMPOSE_FILE"
require_file "$PROD_ENV_FILE"
require_file "$STAGING_COMPOSE_FILE"
require_file "$STAGING_ENV_FILE"

PROD_DB_NAME="$(get_env_value "$PROD_ENV_FILE" POSTGRES_DB)"
PROD_DB_USER="$(get_env_value "$PROD_ENV_FILE" POSTGRES_USER)"
STAGING_DB_NAME="$(get_env_value "$STAGING_ENV_FILE" POSTGRES_DB)"
STAGING_DB_USER="$(get_env_value "$STAGING_ENV_FILE" POSTGRES_USER)"

if [[ -z "$PROD_DB_NAME" || -z "$PROD_DB_USER" || -z "$STAGING_DB_NAME" || -z "$STAGING_DB_USER" ]]; then
  echo "[ERROR] Missing required DB vars in env files." >&2
  exit 1
fi

if [[ "$PROD_DB_NAME" == "$STAGING_DB_NAME" ]]; then
  echo "[ERROR] PROD and STAGING DB names are identical ($PROD_DB_NAME). Abort for safety." >&2
  exit 1
fi

# Показывает параметры операции до запуска, чтобы исключить ошибку окружения.
echo "[INFO] Source DB:  $PROD_DB_NAME ($PROD_DB_USER)"
echo "[INFO] Target DB:  $STAGING_DB_NAME ($STAGING_DB_USER)"
echo "[INFO] Compose prod:    $PROD_COMPOSE_FILE"
echo "[INFO] Compose staging: $STAGING_COMPOSE_FILE"
echo
read -r -p "Type YES to continue syncing prod -> staging: " CONFIRM
if [[ "$CONFIRM" != "YES" ]]; then
  echo "[INFO] Cancelled."
  exit 0
fi

PROD_DB_CONTAINER="$(docker compose -f "$PROD_COMPOSE_FILE" --env-file "$PROD_ENV_FILE" ps -q postgres)"
STAGING_DB_CONTAINER="$(docker compose -f "$STAGING_COMPOSE_FILE" --env-file "$STAGING_ENV_FILE" ps -q postgres)"

if [[ -z "$PROD_DB_CONTAINER" || -z "$STAGING_DB_CONTAINER" ]]; then
  echo "[ERROR] Could not resolve postgres container IDs. Are stacks up?" >&2
  exit 1
fi

# Завершает сессии и пересоздает staging БД, чтобы импорт был чистым и повторяемым.
docker exec -i "$STAGING_DB_CONTAINER" psql -v ON_ERROR_STOP=1 -U "$STAGING_DB_USER" -d postgres <<SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '$STAGING_DB_NAME' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "$STAGING_DB_NAME";
CREATE DATABASE "$STAGING_DB_NAME" OWNER "$STAGING_DB_USER";
SQL

# Переливает дамп потоком напрямую из prod в staging без временных файлов.
docker exec -i "$PROD_DB_CONTAINER" pg_dump -U "$PROD_DB_USER" -d "$PROD_DB_NAME" --no-owner --no-privileges \
  | docker exec -i "$STAGING_DB_CONTAINER" psql -v ON_ERROR_STOP=1 -U "$STAGING_DB_USER" -d "$STAGING_DB_NAME"

echo "[OK] Sync completed: $PROD_DB_NAME -> $STAGING_DB_NAME"
