# AIFont — Quick Start Guide

AIFont is a Python SDK + AI agent layer built on top of [FontForge](https://fontforge.org).
This guide explains how to run every service locally with Docker Compose in under five minutes.

---

## Prerequisites

| Tool | Minimum version |
|------|----------------|
| Docker | 24.0+ |
| Docker Compose | v2.20+ (bundled with Docker Desktop) |

---

## 1 — Clone & configure environment variables

```bash
# Copy the example environment file
cp .env.example .env
```

Open `.env` and replace the placeholder values:

| Variable | Description |
|----------|-------------|
| `POSTGRES_PASSWORD` | PostgreSQL password (change from default) |
| `POSTGRES_USER` | PostgreSQL username |
| `POSTGRES_DB` | PostgreSQL database name |
| `SECRET_KEY` | Application secret — generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `REDIS_PASSWORD` | Redis password *(production only)* |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | LLM API key for AI agents *(optional)* |

> **Security note:** The `.env` file is listed in `.gitignore` and must never be committed to version control.

---

## 2 — Start all services (development)

```bash
docker compose up --build
```

Docker Compose starts six services:

| Service | Role | Local URL |
|---------|------|-----------|
| `db` | PostgreSQL 16 — persistent font metadata | `localhost:5432` |
| `cache` | Redis 7 — Celery broker + result backend | `localhost:6379` |
| `fontforge` | FontForge Python bindings service | internal |
| `api` | FastAPI REST server | http://localhost:8000 |
| `worker` | Celery async worker | internal |
| `frontend` | React app served by Nginx | http://localhost:3000 |

All services have **health checks** configured — Docker will automatically restart any service that fails its health check.

---

## 3 — Verify services are healthy

```bash
# Check the status of all containers
docker compose ps

# Verify the API is responding
curl http://localhost:8000/health
# → {"status":"ok"}

# View real-time logs from all services
docker compose logs -f

# View logs from a single service
docker compose logs -f api
```

---

## 4 — Run in production

> **Requirements:** Fill in all variables in `.env`, especially `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, and `SECRET_KEY`.

```bash
docker compose -f docker-compose.prod.yml up -d
```

Key differences from the development setup:

- No source-code hot-reload mounts.
- API runs with multiple Uvicorn workers (`API_WORKERS=4` by default).
- Worker scales to two replicas.
- Backend services (`db`, `cache`, `fontforge`, `api`, `worker`) are on an **internal** Docker network — only the frontend port 80/443 is exposed.
- Place TLS certificates in `./ssl/` and mount them into the frontend container.

---

## 5 — Stop services

```bash
# Stop and remove containers (data volumes are preserved)
docker compose down

# Stop and also remove all persistent volumes (⚠ destroys database)
docker compose down -v
```

---

## Service architecture

```
                ┌──────────────────────────────┐
 Browser ──────▶│  frontend  (Nginx / React)   │
                │  port 80 / 3000              │
                └──────────────┬───────────────┘
                               │ /api/*
                ┌──────────────▼───────────────┐
                │  api  (FastAPI · Uvicorn)     │
                │  port 8000                   │
                └────┬─────────────┬───────────┘
                     │             │
          ┌──────────▼──┐   ┌──────▼──────────┐
          │  db          │   │  cache (Redis)  │
          │  PostgreSQL  │   │  broker+results │
          └─────────────┘   └────────┬────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  worker  (Celery)   │
                          │  + fontforge SDK    │
                          └─────────────────────┘
```

---

## Persistent data

| Volume | Contents |
|--------|----------|
| `postgres_data` | PostgreSQL database files |
| `redis_data` | Redis RDB snapshot |
| `font_storage` | Generated / uploaded font files |

---

## Troubleshooting

**Port already in use**

```bash
# Change the host port in docker-compose.yml, e.g.:
ports:
  - "8080:8000"   # maps host:8080 → container:8000
```

**FontForge Python bindings not found**

The `fontforge` and `worker` images install `python3-fontforge` from Debian packages at build time.
If the apt repository is unavailable, the build will fail — ensure network access from the Docker build context.

**Database migration**

After the first `docker compose up`, run Alembic migrations:

```bash
docker compose exec api alembic upgrade head
```
