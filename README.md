# GameSales

Development rules and quality checklist: `CONTRIBUTING.md`.

Local development is intended to run **frontend + backend on your machine**
while **PostgreSQL lives on the VDS**.

## Prereqs
- Python 3.12+ (for API)
- Node 20.19+ or 22.12+ (for Vite)
- SSH access to the staging DB tunnel and the InterHub proxy

## Local API (FastAPI)
Create a venv and install deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt
```

For local UI checks, use VS Code → **Tasks: Run Task** → **Local UI + InterHub (no workers)**.
Stop any existing local API on port 8000 first. This task starts the staging DB tunnel,
the InterHub HTTPS tunnel, the API without background polling, and Vite against the local API.
It does not start Docker services, queues, or server workers.

Manual startup (four separate terminals, from the repository root):

```bash
# 1. Staging DB tunnel; keep this terminal open.
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 127.0.0.1:5433:127.0.0.1:5433 adminops@138.16.162.73

# 2. Direct HTTPS tunnel to InterHub through the server configured in .env.dev.
.venv/bin/python api/scripts/run_interhub_tunnel.py

# 3. API with all lifespan background polling disabled.
GAMESALES_LOCAL_UI=1 .venv/bin/uvicorn app:app --reload --host 127.0.0.1 --port 8000 --app-dir api

# 4. Frontend pointing explicitly at the local API.
cd gamesales-web
VITE_API_BASE=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

The API reads `.env.dev`. Local UI mode requires the DB endpoint
`127.0.0.1:5433/gamesales_staging` and forces InterHub through
the SSH forward at `127.0.0.1:3128` (or `INTERHUB_TUNNEL_LOCAL_PORT`). SSH connects
to the hostname from `INTERHUB_API_URL` on port 443 using the server’s allowed IP.
No HTTP proxy service is needed on the server; TLS still verifies the InterHub hostname.
It never falls back to a direct
InterHub connection if the tunnel is unavailable. It keeps the DB pool running;
do not use `--lifespan off`.

This is not a read-only mode: explicit saves still change staging data and buttons can
call integrations. The automatic payment reconciliation, marketplace polling and voucher
catalog schedule stay disabled on the local API. Server workers are unaffected.
New catalog UI requires the runtime migrations through `20260920_03_voucher_catalog_routing.sql`
to have been applied to staging before the API starts; apply migrations as a separate deployment step.
The nominal card stores supplier priority and eligibility for future automatic fulfillment;
it does not change seller delivery yet. See [catalog routing](docs/voucher-catalog-routing.md).

When finished, stop the API and frontend, then stop both tunnel tasks (or Ctrl+C in their
terminals). Check that the tunnels you started no longer listen on 5433 and 3128.

Health check:

```bash
curl http://localhost:8000/health
```

## Local frontend (Vite)
From `gamesales-web`:

```bash
npm install
VITE_API_BASE=http://localhost:8000 npm run dev
```

Open: http://localhost:5173

## Docker (server)
Docker Compose files are for server usage (DB + API + web).
See `docker-compose.prod.yml` and `.env.example`.

### Deploy on VDS
Make sure `.env.prod` exists on the server, then:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml --profile maintenance run --rm migrate
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

## Staging on the same server
Staging is isolated from production and runs on separate ports.

Files:
- `docker-compose.staging.yml`
- `.env.staging.example` (template only, no secrets)
- `scripts/sync_prod_to_staging_db.sh`

### 1) Prepare staging env
On server:

```bash
cp .env.prod .env.staging
```

Then update `.env.staging`:
- `POSTGRES_DB=gamesales_staging`
- `DATABASE_URL=postgresql://...@postgres:5432/gamesales_staging`

### 2) Run staging stack

```bash
docker compose --env-file .env.staging -f docker-compose.staging.yml up -d --build
```

Ports:
- web: `18080`
- api: `18081`
- postgres: `127.0.0.1:5433` (SSH tunnel only)

### 3) Connect from local machine to staging DB
Open SSH tunnel from your computer:

```bash
ssh -N -L 5433:127.0.0.1:5433 adminops@138.16.162.73
```

Then connect in DB client to:
- host: `127.0.0.1`
- port: `5433`
- db/user/password: from `.env.staging`

### 4) Refresh staging DB from prod
Run on server in repo root:

```bash
./scripts/sync_prod_to_staging_db.sh
```

The script has safety checks:
- refuses if prod/staging DB names are equal;
- asks explicit confirmation (`YES`);
- recreates staging DB and streams dump from prod.

## Daily production DB backup
Use a separate directory for dumps:

```bash
mkdir -p /apps/db_backup
```

Manual backup run from server repo root:

```bash
./scripts/backup_prod_db.sh
```

The script:
- reads DB credentials from `.env.prod` (can be overridden via env vars);
- creates dump in PostgreSQL custom format;
- saves file to `/apps/db_backup/backup_YYYY-MM-DD_HH-MM-SS.dump`.

Schedule daily backup at `23:00` (server local time):

```bash
crontab -e
```

```cron
0 23 * * * cd /apps/gamesales && ./scripts/backup_prod_db.sh >> /apps/db_backup/backup.log 2>&1
```

# Миграции БД

Структура БД обновляется отдельной одноразовой задачей до перезапуска API. Она не запускается автоматически вместе с API и не выполняет исторические файлы из `db/migrations` повторно: при первом запуске они только фиксируются как базовая линия. Новые миграции добавляются в `db/migrations/runtime`.

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml --profile maintenance run --rm migrate
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build api
```

Мигратор берёт блокировку на одного исполнителя и прекращает работу, если не смог получить DDL-блокировку за пять секунд. Перед первым production-запуском обязательно сделать и проверить восстановление резервной копии БД.
