# GameSales

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

