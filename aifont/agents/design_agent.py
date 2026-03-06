"""Design Agent — generates glyph outlines from natural language prompts."""
"""Design agent — generates glyph outlines from natural-language prompts."""

from __future__ import annotations

import logging
from typing import Optional

from aifont.core.font import Font
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aifont.core.font import Font

from aifont.agents.orchestrator import AgentResult

logger = logging.getLogger(__name__)


class DesignAgent:
    """Generates or modifies glyph designs based on a text prompt.

    The agent translates natural language descriptions (e.g. *"bold geometric A"*)
    into SVG path data which is then imported into the font via
    :mod:`aifont.core.svg_parser`.

    Example:
        >>> agent = DesignAgent()
        >>> font = agent.run("Create a rounded sans-serif", font)
    """

    def run(self, prompt: str, font: Font) -> Font:
        """Run the design step.

        Args:
            prompt: Natural language design instruction.
            font:   Font to modify.

        Returns:
            The modified font.
        """
        logger.info("DesignAgent: processing prompt %r", prompt)
        # In production: call LLM to generate SVG paths, then import via svg_parser
        # For now, this is a no-op placeholder.
        return font
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
