"""FastAPI application factory for AIFont API."""

from __future__ import annotations

from fastapi import FastAPI

from aifont.api.routes import fonts, agents


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="AIFont API",
        description="REST API exposing the AIFont SDK and AI agents.",
        version="0.1.0",
    )

    app.include_router(fonts.router, prefix="/fonts", tags=["fonts"])
    app.include_router(agents.router, prefix="/agents", tags=["agents"])

    @app.get("/health", tags=["health"])
    async def health() -> dict:
        return {"status": "ok", "version": "0.1.0"}
"""AIFont REST API — FastAPI application exposing the SDK and agents."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.background import BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from aifont.core.font import Font
from aifont.core.analyzer import analyze


def _delete_after_send(path: Path):
    """Return a background task callable that deletes *path*."""
    def delete_file():
        path.unlink(missing_ok=True)
    return delete_file

app = FastAPI(
    title="AIFont API",
    description=(
        "REST API for the AIFont SDK — AI-powered font design built on FontForge.\n\n"
        "All endpoints operate on font files (OTF/TTF/SFD) or return structured JSON reports."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    prompt: str
    family_name: str = "AIFont"


class MetadataResponse(BaseModel):
    family_name: str
    full_name: str
    weight: str
    version: str
    glyph_count: int


class AnalysisResponse(BaseModel):
    glyph_count: int
    missing_unicodes: list[int]
    kern_pair_count: int
    error_count: int
    warning_count: int
    score: float
    summary: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "AIFont API is running. Visit /docs for interactive documentation."}


@app.post("/fonts/analyze", response_model=AnalysisResponse, tags=["Fonts"])
async def analyze_font(file: UploadFile = File(...)):
    """Analyze an uploaded font file and return a quality report.

    Upload an OTF or TTF font file and receive a detailed analysis including
    glyph count, missing unicodes, kerning coverage, and a quality score.
    """
    suffix = Path(file.filename or "font.otf").suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        font = Font.open(tmp_path)
        report = analyze(font)
        font.close()
        return AnalysisResponse(
            glyph_count=report.glyph_count,
            missing_unicodes=report.missing_unicodes,
            kern_pair_count=report.kern_pair_count,
            error_count=report.error_count,
            warning_count=report.warning_count,
            score=report.score,
            summary=report.summary(),
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/fonts/generate", tags=["Fonts"])
async def generate_font(request: GenerateRequest):
    """Generate a new font from a natural language prompt.

    This endpoint runs the full AIFont agent pipeline:
    DesignAgent → StyleAgent → MetricsAgent → QAAgent.

    Returns metadata about the generated font.
    """
    try:
        from aifont.agents.orchestrator import Orchestrator

        orch = Orchestrator()
        font = orch.run(request.prompt)
        meta = font.metadata
        font.close()
        return {
            "status": "success",
            "family_name": meta.family_name,
            "prompt": request.prompt,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/fonts/export", tags=["Fonts"])
async def export_font(
    file: UploadFile = File(...),
    format: str = "otf",
):
    """Export an uploaded font in the specified format.

    Supported formats: ``otf``, ``ttf``, ``woff2``.
    """
    allowed = {"otf", "ttf", "woff2"}
    if format not in allowed:
        raise HTTPException(status_code=400, detail=f"Format must be one of {allowed}.")

    suffix = Path(file.filename or "font.sfd").suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        in_path = Path(tmp.name)

    out_path = in_path.with_suffix(f".{format}")

    try:
        font = Font.open(in_path)
        if format == "woff2":
            from aifont.core.export import export_woff2
            export_woff2(font, out_path)
        elif format == "ttf":
            from aifont.core.export import export_ttf
            export_ttf(font, out_path)
        else:
            from aifont.core.export import export_otf
            export_otf(font, out_path)
        font.close()
        return FileResponse(
            str(out_path),
            media_type="application/octet-stream",
            filename=out_path.name,
            background=_delete_after_send(out_path),
        )
    except Exception as exc:
        out_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        in_path.unlink(missing_ok=True)
"""AIFont FastAPI application entry point.

Start the server
----------------
    uvicorn aifont.api.main:app --reload --host 0.0.0.0 --port 8000

Or with the Celery worker (separate terminal):
    celery -A aifont.api.tasks.celery_app worker --loglevel=info
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from aifont.api.config import get_settings
from aifont.api.database import init_db
from aifont.api.routers import agents, auth, fonts, generation

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Rate limiter                                                         #
# ------------------------------------------------------------------ #

settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


# ------------------------------------------------------------------ #
# Application lifecycle                                                #
# ------------------------------------------------------------------ #


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialise the database schema on startup (dev/test only)."""
    try:
        await init_db()
        logger.info("Database tables created/verified.")
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not initialise database: %s", exc)
    yield


# ------------------------------------------------------------------ #
# Application factory                                                  #
# ------------------------------------------------------------------ #


def create_app() -> FastAPI:
    cfg = get_settings()
    app = FastAPI(
        title=cfg.app_title,
        version=cfg.app_version,
        description=(
            "AIFont REST API — generate, analyse and manage fonts "
            "powered by FontForge and AI agents."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ---- CORS --------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Rate limiting -----------------------------------------------
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # ---- Routers -----------------------------------------------------
    app.include_router(auth.router)
    app.include_router(fonts.router)
    app.include_router(generation.router)
    app.include_router(agents.router)

    # ---- Health check ------------------------------------------------
    @app.get("/health", tags=["health"])
    async def health() -> dict:
        return {"status": "ok", "version": cfg.app_version}

    return app


app = create_app()
Creates and wires up the FastAPI application with:
- Prometheus metrics middleware + /metrics scrape endpoint
- Sentry error tracking
- Structured JSON logging

Environment variables
---------------------
APP_VERSION
    Application version included in ``aifont_app_info`` metric.
ENVIRONMENT
    Deployment environment (default: ``"production"``).
SENTRY_DSN
    Sentry Data Source Name.  Error tracking is disabled when empty.
LOG_LEVEL
    Minimum log level (default: ``"INFO"``).
JSON_LOGS
    Emit JSON logs when ``"true"`` (default: ``"true"``).
"""
"""AIFont FastAPI application entry point."""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from aifont.monitoring.logging import get_logger, setup_logging
from aifont.monitoring.metrics import setup_metrics
from aifont.monitoring.middleware import PrometheusMiddleware
from aifont.monitoring.sentry import setup_sentry

log = get_logger(__name__)


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application.

    Call this function from your ASGI server entry point::

        # gunicorn.conf.py / uvicorn
        from aifont.api.main import create_app
        app = create_app()
    """
    environment = os.getenv("ENVIRONMENT", "production")
    app_version = os.getenv("APP_VERSION", "unknown")
    sentry_dsn = os.getenv("SENTRY_DSN", "")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    json_logs = os.getenv("JSON_LOGS", "true").lower() == "true"

    # ------------------------------------------------------------------
    # Logging — must be configured before anything that logs
    # ------------------------------------------------------------------
    setup_logging(level=log_level, environment=environment, json_logs=json_logs)
    log.info("Starting AIFont API", version=app_version, environment=environment)

    # ------------------------------------------------------------------
    # Prometheus
    # ------------------------------------------------------------------
    setup_metrics(app_version=app_version, environment=environment)

    # ------------------------------------------------------------------
    # Sentry
    # ------------------------------------------------------------------
    setup_sentry(dsn=sentry_dsn, environment=environment, release=app_version)

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    app = FastAPI(
        title="AIFont API",
        description="Python SDK + AI agent layer built on top of FontForge.",
        version=app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Prometheus metrics middleware — wraps every route automatically
    app.add_middleware(PrometheusMiddleware)

    # Mount the Prometheus scrape endpoint at /metrics
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # ------------------------------------------------------------------
    # Health endpoints
    # ------------------------------------------------------------------

    @app.get("/healthz", tags=["health"], summary="Liveness probe")
    async def healthz() -> dict:
        """Returns HTTP 200 when the service is alive."""
        return {"status": "ok"}

    @app.get("/readyz", tags=["health"], summary="Readiness probe")
    async def readyz() -> dict:
        """Returns HTTP 200 when the service is ready to accept traffic."""
        return {"status": "ready"}

    # ------------------------------------------------------------------
    # Global error handler — ensures unhandled errors are captured in
    # Sentry and return a JSON body rather than a 500 HTML page.
    # ------------------------------------------------------------------

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        from aifont.monitoring.sentry import capture_exception

        event_id = capture_exception(
            exc,
            url=str(request.url),
            method=request.method,
        )
        log.exception(
            "Unhandled exception",
            path=str(request.url.path),
            method=request.method,
            sentry_event_id=event_id,
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "sentry_event_id": event_id,
            },
        )

    return app


# Module-level singleton for ASGI servers
app = create_app()
# Convenience module-level instance for ``uvicorn aifont.api.main:app``
app = create_app()
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from aifont.auth.router import router as auth_router
from aifont.db import Base, engine

# ---------------------------------------------------------------------------
# Settings from environment variables
# ---------------------------------------------------------------------------

# Comma-separated list of allowed CORS origins.
# Example: ALLOWED_ORIGINS="https://app.example.com,https://www.example.com"
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS: list[str] = (
    [o.strip() for o in _raw_origins.split(",") if o.strip()]
    if _raw_origins
    else ["http://localhost:3000", "http://localhost:8000"]
)

# Comma-separated list of trusted hostnames (prevents HTTP Host header injection).
# Example: ALLOWED_HOSTS="api.example.com,www.example.com"
_raw_hosts = os.environ.get("ALLOWED_HOSTS", "")
ALLOWED_HOSTS: list[str] = (
    [h.strip() for h in _raw_hosts.split(",") if h.strip()]
    if _raw_hosts
    else ["localhost", "127.0.0.1"]
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create all database tables on startup (dev convenience)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="AIFont API",
    description="AI-powered font creation platform built on top of FontForge.",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Security middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
"""FastAPI application for the AIFont REST API."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AIFont API",
    description="REST API for AI-powered font generation and analysis",
    version="0.1.0",
)

# Restrict CORS to explicitly configured origins.
# In production set CORS_ORIGINS to a comma-separated list, e.g.:
#   CORS_ORIGINS=https://app.example.com,https://admin.example.com
_cors_origins_raw = os.getenv("CORS_ORIGINS", "")
cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prevent HTTP host header injection (OWASP A05)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS,
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth_router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"message": "AIFont API", "version": "0.1.0"}
