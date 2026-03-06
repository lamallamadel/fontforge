"""API route definitions for AIFont."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

router = APIRouter()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@router.get("/health")
async def health() -> dict:
    """Liveness probe for the AIFont API."""
    return {"status": "ok"}


class RunAgentRequest(BaseModel):
    prompt: str
    target: str = "web"


class AnalyzeResponse(BaseModel):
    glyph_count: int
    missing_unicodes: list[str]
    kerning_pairs: int
    errors: list[str]
    passed: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/agents/run")
async def run_agents(body: RunAgentRequest) -> dict:
    """Run the full AIFont agent pipeline for the given *prompt*.

    Creates a blank font, passes it through the orchestrator pipeline,
    and returns a summary of the result.
    """
    from aifont.agents.orchestrator import Orchestrator  # noqa: PLC0415

    try:
        orch = Orchestrator()
        font = orch.run(body.prompt)
        meta = font.metadata
        return {"status": "ok", "metadata": meta}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/fonts/analyze")
async def analyze_font(file: UploadFile) -> AnalyzeResponse:
    """Upload a font file and return an analysis report."""
    import tempfile  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    from aifont.core.analyzer import analyze  # noqa: PLC0415
    from aifont.core.font import Font  # noqa: PLC0415

    suffix = Path(file.filename or "upload.otf").suffix or ".otf"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        font = Font.open(tmp_path)
        report = analyze(font)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return AnalyzeResponse(
        glyph_count=report.glyph_count,
        missing_unicodes=report.missing_unicodes,
        kerning_pairs=report.kerning_pairs,
        errors=report.validation_errors,
        passed=report.passed,
    )
