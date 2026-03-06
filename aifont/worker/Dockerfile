# ── Worker service (Celery) ───────────────────────────────────────────────────
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# FontForge Python bindings require libfontforge; install via apt
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        python3-fontforge \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/worker.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY aifont/ aifont/

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD celery -A aifont.worker.celery_app inspect ping -d celery@$$HOSTNAME || exit 1

CMD ["celery", "-A", "aifont.worker.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
