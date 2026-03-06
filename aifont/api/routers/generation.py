"""Async font generation router.

Endpoints
---------
POST /fonts/generate   — schedule an AI font generation task
GET  /tasks/{task_id}  — poll the status of any Celery task
"""

from __future__ import annotations

from fastapi import APIRouter, status

from aifont.api.dependencies import CurrentUser, DBSession
from aifont.api.schemas import GenerationRequest, TaskStatus
from aifont.api.tasks import celery_app
from aifont.api.tasks.font_tasks import generate_font as _generate_task

router = APIRouter(tags=["generation"])


@router.post("/fonts/generate", response_model=TaskStatus, status_code=status.HTTP_202_ACCEPTED)
async def generate_font(
    body: GenerationRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> TaskStatus:
    """Schedule an async AI font generation task.

    The heavy lifting is done by the Celery worker (``aifont.tasks.generate_font``).
    Use ``GET /tasks/{task_id}`` to poll for the result.
    """
    task = _generate_task.delay(
        body.prompt,
        str(body.font_id) if body.font_id else None,
        body.style_hints,
    )
    return TaskStatus(task_id=task.id, status="pending")


@router.get("/tasks/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str, current_user: CurrentUser) -> TaskStatus:
    """Return the current status and result of a Celery task."""
    result = celery_app.AsyncResult(task_id)
    status_str = result.status.lower()  # PENDING → pending etc.
    task_result = None
    error = None

    if result.successful():
        task_result = result.result if isinstance(result.result, dict) else {"value": result.result}
    elif result.failed():
        error = str(result.result)

    return TaskStatus(task_id=task_id, status=status_str, result=task_result, error=error)
