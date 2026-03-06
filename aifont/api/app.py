"""FastAPI application factory for the AIFont REST API."""

from __future__ import annotations

from typing import Any


def create_app() -> Any:
    """Create and configure the FastAPI application.

    Returns:
        A configured :class:`fastapi.FastAPI` instance.

    The full route definitions live in :mod:`aifont.api.routes` which is
    imported lazily to keep this factory importable without FastAPI installed
    (e.g. during unit tests of the core SDK).
    """
    try:
        from fastapi import FastAPI  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "fastapi is required to run the AIFont API. Install it with: pip install aifont[api]"
        ) from exc

    app = FastAPI(
        title="AIFont API",
        description=(
            "REST API for the AIFont Python SDK — AI-powered font generation "
            "and manipulation built on FontForge."
        ),
        version="0.1.0",
    )

    # Register routers (imported lazily to avoid circular imports).
    from aifont.api.routes import router  # noqa: PLC0415

    app.include_router(router)

    return app
