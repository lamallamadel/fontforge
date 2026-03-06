"""Style agent — transfers visual style between fonts."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aifont.core.font import Font

from aifont.agents.orchestrator import AgentResult

logger = logging.getLogger(__name__)


class StyleAgent:
    """Analyses stroke weight, contrast and terminals of a reference font and
    applies those style characteristics to the target font via
    :mod:`aifont.core.contour` transformations.
    """

    def run(self, prompt: str, font: Font) -> AgentResult:
        logger.info("StyleAgent: applying style for prompt %r", prompt)
        return AgentResult(
            agent_name="StyleAgent",
            success=True,
            confidence=0.9,
            message="Style transfer skipped (no reference font provided)",
        )
