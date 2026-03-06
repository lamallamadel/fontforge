# ── FontForge service (Python bindings + SDK) ─────────────────────────────────
#
# This image installs the FontForge Python bindings and the aifont SDK so that
# both the API and Worker services can use it as a base layer when needed.
# It is also a standalone service that can run the FontForge Python REPL.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install FontForge and its Python bindings from Debian/Ubuntu packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        fontforge \
        python3-fontforge \
        libfontforge4 \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY aifont/ aifont/

# Verify fontforge Python bindings are importable
RUN python3 -c "import fontforge; print('FontForge', fontforge.version())"

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python3 -c "import fontforge" || exit 1

CMD ["python3", "-c", "import fontforge; print('FontForge service ready')"]
