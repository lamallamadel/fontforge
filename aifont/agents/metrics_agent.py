"""Metrics Agent — auto-optimizes spacing and kerning."""

from __future__ import annotations

import logging

from aifont.core.font import Font
from aifont.core import auto_space

logger = logging.getLogger(__name__)


class MetricsAgent:
    """Automatically optimises spacing and kerning for a font.

    Example:
        >>> agent = MetricsAgent()
        >>> font = agent.run("airy spacing", font)
    """

    _SPACING_PRESETS = {
        "tight": 0.08,
        "normal": 0.12,
        "airy": 0.18,
        "display": 0.10,
    }

    def run(self, prompt: str, font: Font) -> Font:
        """Optimise metrics based on a style prompt.

        Args:
            prompt: Style hint (e.g. ``"airy spacing"``).
            font:   Font to optimise.

        Returns:
            The font with updated spacing.
        """
        logger.info("MetricsAgent: optimising metrics for prompt %r", prompt)
        ratio = 0.12  # default
        for keyword, preset_ratio in self._SPACING_PRESETS.items():
            if keyword in prompt.lower():
                ratio = preset_ratio
                break
        auto_space(font, target_ratio=ratio)
        return font
