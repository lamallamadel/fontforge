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
