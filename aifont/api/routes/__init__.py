"""API routes package."""

from __future__ import annotations

from fastapi import APIRouter

from aifont.api.routes import agents, fonts

# Create a combined router that includes all sub-routers
router = APIRouter()

# Include the sub-routers
router.include_router(fonts.router, prefix="/fonts", tags=["fonts"])
router.include_router(agents.router, prefix="/agents", tags=["agents"])

# Add health check endpoint
@router.get("/health")
async def health() -> dict:
    """Liveness probe for the AIFont API."""
    return {"status": "ok"}

__all__ = ["router", "agents", "fonts"]
