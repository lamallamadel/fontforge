"""Celery tasks for long-running font operations."""

from __future__ import annotations

import json
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="aifont.tasks.analyze_font")
def analyze_font(self, font_id: str, file_path: str) -> dict:
    """Analyse a font file and return a structured report.

    This task runs in a Celery worker process.  It wraps the
    ``aifont.core`` SDK so that FontForge is never called directly from
    the API server process.
    """
    try:
        # Lazy import to avoid loading fontforge in the API server process.
        from aifont.core.font import Font  # noqa: PLC0415

        font = Font.open(file_path)
        report = {
            "font_id": font_id,
            "name": font.metadata.get("name", ""),
            "family": font.metadata.get("family", ""),
            "glyph_count": len(list(font.glyphs)),
            "status": "completed",
        }
        font.close()
        return report
    except Exception as exc:  # pragma: no cover
        logger.exception("analyze_font task failed for font_id=%s", font_id)
        raise self.retry(exc=exc, countdown=5, max_retries=3) from exc


@shared_task(bind=True, name="aifont.tasks.generate_font")
def generate_font(self, prompt: str, font_id: str | None, style_hints: dict | None) -> dict:
    """Generate or modify a font using the AI agent pipeline.

    Long-running; intended to be executed asynchronously via Celery.
    """
    try:
        # Lazy import — orchestrator depends on optional AI libraries.
        from aifont.agents.orchestrator import Orchestrator  # noqa: PLC0415

        orchestrator = Orchestrator()
        result_font = orchestrator.run(prompt=prompt, font_id=font_id, style_hints=style_hints)
        return {
            "font_id": str(result_font.id) if result_font else None,
            "status": "completed",
        }
    except ImportError:
        # Agents layer not yet installed — return stub result.
        logger.warning("generate_font: aifont.agents not available, returning stub")
        return {"font_id": font_id, "status": "stub", "prompt": prompt}
    except Exception as exc:  # pragma: no cover
        logger.exception("generate_font task failed")
        raise self.retry(exc=exc, countdown=10, max_retries=2) from exc


@shared_task(bind=True, name="aifont.tasks.run_agent")
def run_agent(
    self,
    agent_name: str,
    prompt: str,
    font_id: str | None,
    parameters: dict | None,
) -> dict:
    """Dispatch a named AI agent task."""
    try:
        from aifont.agents import get_agent  # noqa: PLC0415

        agent = get_agent(agent_name)
        result = agent.run(prompt=prompt, font_id=font_id, **(parameters or {}))
        return {"agent": agent_name, "result": result, "status": "completed"}
    except ImportError:
        logger.warning("run_agent: aifont.agents not available, returning stub")
        return {"agent": agent_name, "font_id": font_id, "status": "stub", "prompt": prompt}
    except Exception as exc:  # pragma: no cover
        logger.exception("run_agent task failed for agent=%s", agent_name)
        raise self.retry(exc=exc, countdown=10, max_retries=2) from exc
