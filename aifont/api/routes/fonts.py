"""Font-related API endpoints."""

from __future__ import annotations

import os
import tempfile
from typing import Any

from fastapi import APIRouter, File, HTTPException, Path, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter()

# In-memory store keyed by font id (for demo purposes)
_font_store: dict[str, Any] = {}


class AnalyzeResponse(BaseModel):
    font_id: str
    glyph_count: int
    missing_unicode: list
    kern_pair_count: int
    coverage_score: float
    error_count: int
    warning_count: int
    passed: bool


class GenerateRequest(BaseModel):
    prompt: str
    font_name: str = "GeneratedFont"


class GenerateResponse(BaseModel):
    font_id: str
    message: str


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_font(file: UploadFile = File(...)) -> AnalyzeResponse:
    """Upload a font file and return an analysis report."""
    # Save upload to a temp file
    suffix = os.path.splitext(file.filename or ".otf")[1] or ".otf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        from aifont.core.analyzer import analyze
        from aifont.core.font import Font

        font = Font.open(tmp_path)
        report = analyze(font)
        font_id = str(id(font))
        _font_store[font_id] = font
        return AnalyzeResponse(
            font_id=font_id,
            glyph_count=report.glyph_count,
            missing_unicode=report.missing_unicode,
            kern_pair_count=report.kern_pair_count,
            coverage_score=report.coverage_score,
            error_count=report.error_count,
            warning_count=report.warning_count,
            passed=report.passed,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        os.unlink(tmp_path)


@router.post("/generate", response_model=GenerateResponse)
async def generate_font(request: GenerateRequest) -> GenerateResponse:
    """Generate a new font from a natural language prompt."""
    try:
        from aifont.agents.design_agent import DesignAgent
        from aifont.core.font import Font

        font = Font.new(request.font_name)
        agent = DesignAgent()
        agent.run(prompt=request.prompt, font=font)
        font_id = str(id(font))
        _font_store[font_id] = font
        return GenerateResponse(
            font_id=font_id,
            message=f"Font generated from prompt: {request.prompt!r}",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{font_id}/export")
async def export_font(
    font_id: str = Path(..., description="Font ID returned by /analyze or /generate"),
    fmt: str = "otf",
) -> FileResponse:
    """Export a previously loaded/generated font by ID."""
    font = _font_store.get(font_id)
    if font is None:
        raise HTTPException(status_code=404, detail=f"Font {font_id!r} not found.")

    suffix_map = {"otf": ".otf", "ttf": ".ttf", "woff2": ".woff2"}
    suffix = suffix_map.get(fmt, ".otf")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        out_path = tmp.name

    try:
        from aifont.core.export import export_otf, export_ttf, export_woff2

        if fmt == "woff2":
            export_woff2(font, out_path)
        elif fmt == "ttf":
            export_ttf(font, out_path)
        else:
            export_otf(font, out_path)
    except Exception as exc:
        os.unlink(out_path)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return FileResponse(out_path, media_type="application/octet-stream")
