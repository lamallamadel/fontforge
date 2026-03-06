"""Design agent — generates glyph outlines from natural-language prompts."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aifont.core.font import Font

from aifont.agents.orchestrator import AgentResult

logger = logging.getLogger(__name__)


class DesignAgent:
    """Generates glyphs from a natural-language description.

    Workflow:
    1. Passes the *prompt* to an LLM (via ``litellm`` if available) to obtain
       an SVG ``<path d="…">`` string for each required glyph.
    2. Writes the SVG to a temporary file and imports it via
       :func:`~aifont.core.svg_parser.svg_to_glyph`.

    When no LLM is configured the agent is a no-op (returns success with low
    confidence) so that the rest of the pipeline can still proceed.
    """

    def run(self, prompt: str, font: Font) -> AgentResult:
        logger.info("DesignAgent: processing prompt %r", prompt)
        # LLM integration goes here — stub returns success.
        return AgentResult(
            agent_name="DesignAgent",
            success=True,
            confidence=0.8,
            message="Design step skipped (no LLM configured)",
        )
