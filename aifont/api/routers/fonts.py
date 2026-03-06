"""Font CRUD router.

Endpoints
---------
POST   /fonts              — create a font record (with optional file upload)
GET    /fonts              — list fonts (paginated)
GET    /fonts/{id}         — get a single font
PATCH  /fonts/{id}         — update font metadata
DELETE /fonts/{id}         — delete a font
POST   /fonts/{id}/upload  — upload a font file to an existing record
GET    /fonts/{id}/export  — download the stored font file
POST   /fonts/analyze      — trigger async analysis of an uploaded font
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select

from aifont.api.config import get_settings
from aifont.api.dependencies import CurrentUser, DBSession
from aifont.api.models import AnalysisResult, Font
from aifont.api.schemas import (
    FontCreate,
    FontList,
    FontRead,
    FontUpdate,
    TaskStatus,
)
from aifont.api.tasks.font_tasks import analyze_font as _analyze_font_task

router = APIRouter(prefix="/fonts", tags=["fonts"])

_UPLOAD_DIR = Path(os.environ.get("AIFONT_UPLOAD_DIR", "/tmp/aifont_uploads"))
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _allowed_extension(filename: str) -> bool:
    settings = get_settings()
    ext = Path(filename).suffix.lower()
    return ext in settings.allowed_font_extensions or ext in settings.allowed_svg_extensions


# ------------------------------------------------------------------ #
# CRUD                                                                 #
# ------------------------------------------------------------------ #


@router.post("", response_model=FontRead, status_code=status.HTTP_201_CREATED)
async def create_font(
    body: FontCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> FontRead:
    """Create a new font metadata record."""
    font = Font(
        name=body.name,
        family=body.family,
        style=body.style,
        version=body.version,
        description=body.description,
        owner_id=current_user.id,
    )
    db.add(font)
    await db.flush()
    await db.refresh(font)
    return FontRead.model_validate(font)


@router.get("", response_model=FontList)
async def list_fonts(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    name: str | None = Query(None, max_length=256),
) -> FontList:
    """Return a paginated list of fonts owned by the current user."""
    base_q = select(Font).where(Font.owner_id == current_user.id)
    if name:
        base_q = base_q.where(Font.name.ilike(f"%{name}%"))

    total_result = await db.execute(select(func.count()).select_from(base_q.subquery()))
    total = total_result.scalar_one()

    items_result = await db.execute(
        base_q.offset((page - 1) * page_size).limit(page_size).order_by(Font.created_at.desc())
    )
    items = [FontRead.model_validate(f) for f in items_result.scalars().all()]
    return FontList(items=items, total=total, page=page, page_size=page_size)


@router.get("/{font_id}", response_model=FontRead)
async def get_font(font_id: uuid.UUID, db: DBSession, current_user: CurrentUser) -> FontRead:
    """Get a single font by ID."""
    font = await _get_owned_font(font_id, current_user.id, db)
    return FontRead.model_validate(font)


@router.patch("/{font_id}", response_model=FontRead)
async def update_font(
    font_id: uuid.UUID,
    body: FontUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> FontRead:
    """Partially update font metadata."""
    font = await _get_owned_font(font_id, current_user.id, db)
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(font, field, value)
    await db.flush()
    await db.refresh(font)
    return FontRead.model_validate(font)


@router.delete("/{font_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_font(
    font_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Delete a font record (and associated file if present)."""
    font = await _get_owned_font(font_id, current_user.id, db)
    if font.file_path and Path(font.file_path).exists():
        Path(font.file_path).unlink(missing_ok=True)
    await db.delete(font)


# ------------------------------------------------------------------ #
# File upload / download                                               #
# ------------------------------------------------------------------ #


@router.post("/{font_id}/upload", response_model=FontRead)
async def upload_font_file(
    font_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    file: UploadFile = File(...),
) -> FontRead:
    """Upload a font file (.otf/.ttf/.woff/.woff2/.sfd/.svg) to an existing record."""
    settings = get_settings()

    if not file.filename or not _allowed_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type. Allowed: "
            f"{settings.allowed_font_extensions + settings.allowed_svg_extensions}",
        )

    font = await _get_owned_font(font_id, current_user.id, db)

    # Stream file to disk with size guard
    dest = _UPLOAD_DIR / f"{font_id}{Path(file.filename).suffix.lower()}"
    bytes_written = 0
    with dest.open("wb") as fh:
        while chunk := await file.read(65536):
            bytes_written += len(chunk)
            if bytes_written > settings.max_upload_size_bytes:
                fh.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds max size of {settings.max_upload_size_bytes} bytes",
                )
            fh.write(chunk)

    font.file_path = str(dest)
    await db.flush()
    await db.refresh(font)
    return FontRead.model_validate(font)


from fastapi.responses import FileResponse  # noqa: E402  (avoids circular imports at module level)


@router.get("/{font_id}/export")
async def export_font_file(
    font_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> FileResponse:
    """Download the stored font file for *font_id*."""
    font = await _get_owned_font(font_id, current_user.id, db)
    if not font.file_path or not Path(font.file_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No file associated with this font",
        )
    return FileResponse(
        path=font.file_path,
        filename=Path(font.file_path).name,
        media_type="application/octet-stream",
    )


# ------------------------------------------------------------------ #
# Analysis                                                             #
# ------------------------------------------------------------------ #


@router.post("/analyze", response_model=TaskStatus, status_code=status.HTTP_202_ACCEPTED)
async def analyze_font(
    db: DBSession,
    current_user: CurrentUser,
    file: UploadFile = File(...),
) -> TaskStatus:
    """Upload a font file and schedule an async analysis task.

    Returns a *task_id* that can be polled via ``GET /tasks/{task_id}``.
    """
    settings = get_settings()
    if not file.filename or not _allowed_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported file type for analysis",
        )

    # Persist a temporary font record to anchor the analysis result
    font = Font(
        name=Path(file.filename).stem,
        owner_id=current_user.id,
    )
    db.add(font)
    await db.flush()

    dest = _UPLOAD_DIR / f"analyze_{font.id}{Path(file.filename).suffix.lower()}"
    bytes_written = 0
    with dest.open("wb") as fh:
        while chunk := await file.read(65536):
            bytes_written += len(chunk)
            if bytes_written > settings.max_upload_size_bytes:
                fh.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="File too large",
                )
            fh.write(chunk)

    font.file_path = str(dest)

    # Dispatch Celery task
    task = _analyze_font_task.delay(str(font.id), str(dest))

    # Persist an analysis result record
    ar = AnalysisResult(font_id=font.id, task_id=task.id, status="pending")
    db.add(ar)
    await db.flush()

    return TaskStatus(task_id=task.id, status="pending")


# ------------------------------------------------------------------ #
# Internal helpers                                                     #
# ------------------------------------------------------------------ #


async def _get_owned_font(font_id: uuid.UUID, owner_id: uuid.UUID, db: DBSession) -> Font:
    result = await db.execute(select(Font).where(Font.id == font_id, Font.owner_id == owner_id))
    font = result.scalar_one_or_none()
    if font is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Font not found")
    return font
