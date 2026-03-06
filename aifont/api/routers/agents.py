"""AI Agent execution router.

Endpoints
---------
POST /agents/run   — dispatch a named AI agent as a Celery task
"""

from __future__ import annotations

from fastapi import APIRouter, status

from aifont.api.dependencies import CurrentUser, DBSession
from aifont.api.schemas import AgentRunRequest, AgentRunResponse
from aifont.api.tasks.font_tasks import run_agent as _run_agent_task

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/run", response_model=AgentRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_agent(
    body: AgentRunRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> AgentRunResponse:
    """Dispatch a named AI agent task asynchronously.

    Supported agents: ``design``, ``style``, ``metrics``, ``qa``,
    ``export``, ``orchestrator``.

    Returns a *task_id* that can be polled via ``GET /tasks/{task_id}``.
    """
    task = _run_agent_task.delay(
        body.agent,
        body.prompt,
        str(body.font_id) if body.font_id else None,
        body.parameters,
    )
    return AgentRunResponse(task_id=task.id, agent=body.agent, status="pending")
