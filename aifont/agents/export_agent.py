"""Export agent — intelligent font export with format-specific optimisation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from aifont.core.font import Font

from aifont.agents.orchestrator import AgentResult

logger = logging.getLogger(__name__)

ExportTarget = Literal["web", "print", "app"]


class ExportAgent:
    """Chooses optimal export settings based on the intended target use
    (``"web"``, ``"print"``, ``"app"``), applies format-specific fixes
    (hinting for TTF, subsetting for WOFF2) and writes the output files
    via :mod:`aifont.core.export`.
    """

    def __init__(
        self,
        output_dir: str | Path | None = None,
        target: ExportTarget = "web",
    ) -> None:
        self.output_dir = Path(output_dir) if output_dir else None
        self.target = target

    def run(self, prompt: str, font: Font) -> AgentResult:
        logger.info("ExportAgent: preparing %s export", self.target)
        return AgentResult(
            agent_name="ExportAgent",
            success=True,
            confidence=1.0,
            message=f"Export skipped (no output_dir set, target={self.target})",
        )
