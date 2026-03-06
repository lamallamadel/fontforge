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

    return app


# Module-level singleton for ASGI servers
app = create_app()
