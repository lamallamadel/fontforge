"""Design Agent — generates glyph outlines from natural language prompts."""

from __future__ import annotations

import logging
from typing import Optional

from aifont.core.font import Font

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
