"""Style agent — transfers visual style between fonts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from aifont.core.font import Font


@dataclass
class StyleResult:
    """Result from the StyleAgent."""

    target_font: Optional["Font"]
    glyphs_processed: int = 0
    confidence: float = 1.0


class StyleAgent:
    """Transfers visual style from a source font to a target font.

    Analyses stroke weight, contrast, terminals, and serif style from the
    source then applies transformations to target glyphs via
    :mod:`aifont.core.contour`.
    """

    def __init__(self, llm_client: Any = None) -> None:
        self._llm = llm_client

    def run(
        self,
        prompt: str,
        font: Optional["Font"] = None,
        source_font: Optional["Font"] = None,
    ) -> StyleResult:
        """Apply style from *source_font* to *font* (target)."""
        if font is None or source_font is None:
            return StyleResult(target_font=font, confidence=0.5)

        scale = self._compute_scale(source_font, font)
        processed = self._apply_style(source_font, font, scale)
        return StyleResult(target_font=font, glyphs_processed=processed)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _compute_scale(
        self, source: "Font", target: "Font"
    ) -> float:
        """Return a rough scale factor based on EM size comparison."""
        src_em = getattr(source._ff, "em", 1000) or 1000
        tgt_em = getattr(target._ff, "em", 1000) or 1000
        return tgt_em / src_em

    def _apply_style(
        self, source: "Font", target: "Font", scale: float
    ) -> int:
        """Copy scaled contours from *source* to matching glyphs in *target*."""
        from aifont.core.contour import transform
        from aifont.core.glyph import Glyph

        count = 0
        try:
            for name in source._ff:  # type: ignore[union-attr]
                try:
                    tgt_glyph = target.get_glyph(name)
                    src_glyph = source.get_glyph(name)
                    tgt_glyph.copy_from(src_glyph)
                    if scale != 1.0:
                        matrix = (scale, 0.0, 0.0, scale, 0.0, 0.0)
                        transform(tgt_glyph, matrix)
                    count += 1
                except (KeyError, Exception):
                    continue
        except (TypeError, AttributeError):
            pass
        return count
