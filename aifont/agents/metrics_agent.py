"""Metrics agent — auto-optimises spacing and kerning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

if TYPE_CHECKING:
    from aifont.core.font import Font


@dataclass
class MetricsResult:
    """Result from the MetricsAgent."""

    font: Optional["Font"]
    kern_pairs_updated: int = 0
    spacing_adjusted: bool = False
    confidence: float = 1.0


class MetricsAgent:
    """Analyses and auto-optimises font spacing and kerning.

    Uses :mod:`aifont.core.metrics` for all font operations.
    An optional LLM client can interpret style intent (e.g.
    "airy spacing" vs "tight display").
    """

    def __init__(self, llm_client: Any = None) -> None:
        self._llm = llm_client

    def run(
        self,
        prompt: str,
        font: Optional["Font"] = None,
    ) -> MetricsResult:
        """Analyse *font* and apply spacing/kerning corrections."""
        from aifont.core.metrics import auto_space, get_kern_pairs

        if font is None:
            return MetricsResult(font=None, confidence=0.5)

        target_ratio = self._interpret_ratio(prompt)
        auto_space(font, target_ratio=target_ratio)
        pairs = get_kern_pairs(font)
        return MetricsResult(
            font=font,
            kern_pairs_updated=len(pairs),
            spacing_adjusted=True,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _interpret_ratio(self, prompt: str) -> float:
        """Map style keywords in *prompt* to a side-bearing ratio."""
        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ("tight", "compact", "narrow")):
            return 0.08
        if any(w in prompt_lower for w in ("airy", "loose", "wide", "open")):
            return 0.22
        return 0.15
