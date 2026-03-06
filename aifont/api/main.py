"""AIFont FastAPI application entry point.

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


# Convenience module-level instance for ``uvicorn aifont.api.main:app``
app = create_app()
