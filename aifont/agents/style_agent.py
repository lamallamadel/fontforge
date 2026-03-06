"""Style Agent — transfers visual style between fonts."""

from __future__ import annotations

import logging
from typing import Optional

from aifont.core.font import Font

logger = logging.getLogger(__name__)


class StyleAgent:
    """Transfers visual style (stroke weight, contrast, terminals) from a source font.

    Example:
        >>> agent = StyleAgent(source_font=reference_font)
        >>> font = agent.run("match the style of the reference", target_font)
    """

    def __init__(self, source_font: Optional[Font] = None) -> None:
        self.source_font = source_font

    def run(self, prompt: str, font: Font) -> Font:
        """Apply style transfer.

        Args:
            prompt: Style description or instruction.
            font:   Target font to apply style to.

        Returns:
            The styled font.
        """
        logger.info("StyleAgent: applying style from prompt %r", prompt)
        # In production: analyse source font metrics, apply transformations via contour module
        return font
