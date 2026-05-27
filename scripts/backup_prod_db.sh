#!/usr/bin/env bash
set -euo pipefail

# Читает значение ключа из env-файла, чтобы не дублировать секреты в скрипте.
get_env_value() {
  local env_file="$1"
  local key="$2"
  awk -F= -v k="$key" '$1==k {sub(/^[[:space:]]+/, "", $2); print $2; exit}' "$env_file"
}

# Проверяет наличие файла и завершает работу с понятной ошибкой.
require_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "[ERROR] File not found: $file" >&2
    exit 1
  fi
}

# Проверяет наличие внешней команды, без которой бэкап невозможен.
require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "[ERROR] Command not found: $command_name" >&2
    exit 1
  fi
}

ENV_FILE="${ENV_FILE:-.env.prod}"
BACKUP_DIR="${BACKUP_DIR:-/apps/db_backup}"
DB_CONTAINER="${DB_CONTAINER:-gamesales-postgres}"
TMP_DUMP_PATH="/tmp/gamesales_backup.dump"

require_file "$ENV_FILE"
require_command docker
mkdir -p "$BACKUP_DIR"

DB_NAME="${DB_NAME:-$(get_env_value "$ENV_FILE" POSTGRES_DB)}"
DB_USER="${DB_USER:-$(get_env_value "$ENV_FILE" POSTGRES_USER)}"
DB_PASSWORD="${DB_PASSWORD:-$(get_env_value "$ENV_FILE" POSTGRES_PASSWORD)}"

if [[ -z "$DB_NAME" || -z "$DB_USER" || -z "$DB_PASSWORD" ]]; then
  echo "[ERROR] Missing DB_NAME/DB_USER/DB_PASSWORD. Check $ENV_FILE or env vars." >&2
  exit 1
fi

TS="$(date +%F_%H-%M-%S)"
OUT_FILE="backup_${TS}.dump"
OUT_PATH="${BACKUP_DIR%/}/$OUT_FILE"

# Удаляет временный дамп в контейнере при любом завершении скрипта.
cleanup() {
  docker exec "$DB_CONTAINER" rm -f "$TMP_DUMP_PATH" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Создает дамп внутри контейнера и копирует его на хост в отдельную папку.
docker exec -e "PGPASSWORD=$DB_PASSWORD" "$DB_CONTAINER" \
  pg_dump -U "$DB_USER" -d "$DB_NAME" -F c -f "$TMP_DUMP_PATH"
docker cp "${DB_CONTAINER}:${TMP_DUMP_PATH}" "$OUT_PATH"

echo "[OK] Backup created: $OUT_PATH"
