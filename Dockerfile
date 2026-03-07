# ============================================================================
# AIFont — multi-stage Docker image
# ============================================================================
# Architecture constraint: FontForge is the underlying engine; AIFont is the
# Python SDK + AI agent layer built ON TOP of it via `import fontforge`.
# ============================================================================

# ---------------------------------------------------------------------------
# Stage 1 — Builder
# ---------------------------------------------------------------------------
FROM ubuntu:22.04 AS builder

ARG DEBIAN_FRONTEND=noninteractive

# Install FontForge and Python build toolchain.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.11 \
        python3.11-dev \
        python3.11-venv \
        python3-pip \
        fontforge \
        python3-fontforge \
        # Build tools
        build-essential \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment for isolation.
RUN python3.11 -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Make system fontforge bindings visible inside the venv.
RUN SITE=$(python3.11 -c "import sysconfig; print(sysconfig.get_path('platlib'))") && \
    VENV_SITE=$(/venv/bin/python -c "import sysconfig; print(sysconfig.get_path('platlib'))") && \
    ln -sf "$SITE/fontforge" "$VENV_SITE/fontforge" 2>/dev/null || true && \
    ln -sf "$SITE/psMat.so" "$VENV_SITE/psMat.so" 2>/dev/null || true

WORKDIR /build
COPY aifont/pyproject.toml ./

# Install runtime dependencies (no extras, API extras handled separately).
RUN pip install --no-cache-dir ".[api]"

# ---------------------------------------------------------------------------
# Stage 2 — Runtime
# ---------------------------------------------------------------------------
FROM ubuntu:22.04 AS runtime

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.11 \
        python3.11-distutils \
        python3-fontforge \
        fontforge \
        libfontforge4 \
        ca-certificates \
        # Health-check tooling
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the populated venv from builder.
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy AIFont source code.
WORKDIR /app
COPY aifont/ ./aifont/

# Make system fontforge bindings visible to the copied venv.
RUN SITE=$(python3.11 -c "import sysconfig; print(sysconfig.get_path('platlib'))") && \
    VENV_SITE=$(/venv/bin/python -c "import sysconfig; print(sysconfig.get_path('platlib'))") && \
    ln -sf "$SITE/fontforge" "$VENV_SITE/fontforge" 2>/dev/null || true && \
    ln -sf "$SITE/psMat.so" "$VENV_SITE/psMat.so" 2>/dev/null || true

# Install aifont itself in editable mode so changes are picked up.
RUN pip install --no-cache-dir -e "./aifont[api]"

# Non-root user for security.
RUN groupadd -r aifont && useradd -r -g aifont aifont
USER aifont

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "aifont.api.app:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8000"]
