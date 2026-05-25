# GameSales

Development rules and quality checklist: `CONTRIBUTING.md`.

Local development is intended to run **frontend + backend on your machine**
while **PostgreSQL lives on the VDS**.

## Prereqs
- Python 3.12+ (for API)
- Node 20.19+ or 22.12+ (for Vite)
- Access to the VDS Postgres (port 5432 + pg_hba.conf)

## Local API (FastAPI)
Create a venv and install deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt
```

Run API (from repo root):

```bash
export DATABASE_URL='postgresql://gamesales_app:<PASSWORD>@45.144.29.26:5432/gamesales'
uvicorn app:app --reload --host 0.0.0.0 --port 8000 --app-dir api
```

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
