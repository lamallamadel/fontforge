"""Agent-related API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class RunRequest(BaseModel):
    prompt: str
    font_id: str | None = None


class RunResponse(BaseModel):
    success: bool
    steps: list[dict[str, Any]]
    font_id: str | None = None
    errors: list[str] = []


@router.post("/run", response_model=RunResponse)
async def run_agents(request: RunRequest) -> RunResponse:
    """Run the full agent pipeline for a prompt."""
    from aifont.agents.orchestrator import Orchestrator
    from aifont.api.routes.fonts import _font_store

    font = None
    if request.font_id:
        font = _font_store.get(request.font_id)
        if font is None:
            raise HTTPException(
                status_code=404,
                detail=f"Font {request.font_id!r} not found.",
            )

    try:
        orch = Orchestrator()
        result = orch.run(request.prompt, font=font)
        if result.font is not None:
            font_id = str(id(result.font))
            _font_store[font_id] = result.font
        else:
            font_id = request.font_id
        return RunResponse(
            success=result.success,
            steps=[
                {
                    "agent": s.agent_name,
                    "success": s.success,
                    "confidence": s.confidence,
                    "error": s.error,
                }
                for s in result.steps
            ],
            font_id=font_id,
            errors=result.errors,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
