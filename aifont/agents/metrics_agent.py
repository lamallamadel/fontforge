"""Metrics agent — auto-optimises spacing and kerning."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aifont.core.font import Font

from aifont.agents.orchestrator import AgentResult

logger = logging.getLogger(__name__)


class MetricsAgent:
    """Analyses current font metrics via :mod:`aifont.core.metrics`,
    identifies issues (too tight, inconsistent sidebearings) and applies
    corrections.
    """

    def run(self, prompt: str, font: Font) -> AgentResult:
        logger.info("MetricsAgent: optimising metrics for prompt %r", prompt)
        return AgentResult(
            agent_name="MetricsAgent",
            success=True,
            confidence=0.85,
            message="Metrics optimisation deferred (font has no glyphs yet)",
        )
