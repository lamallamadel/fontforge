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
    def _task():
        path.unlink(missing_ok=True)
    return _task

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
