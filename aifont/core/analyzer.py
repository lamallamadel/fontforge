"""Font analysis and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aifont.core.font import Font


@dataclass
class FontReport:
    """Structured analysis report returned by :func:`analyze`."""

    glyph_count: int = 0
    missing_unicodes: list[str] = field(default_factory=list)
    kerning_pairs: int = 0
    validation_errors: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)

    # Derived convenience properties -----------------------------------

    @property
    def passed(self) -> bool:
        """``True`` if no validation errors were found."""
        return len(self.validation_errors) == 0

    def __str__(self) -> str:  # pragma: no cover
        lines = [
            f"Glyphs         : {self.glyph_count}",
            f"Missing unicode: {len(self.missing_unicodes)}",
            f"Kerning pairs  : {self.kerning_pairs}",
            f"Errors         : {len(self.validation_errors)}",
        ]
        return "\n".join(lines)


def analyze(font: Font) -> FontReport:
    """Analyze *font* and return a :class:`FontReport`.

    Checks performed:
    * Glyph count
    * Glyphs without a unicode assignment
    * Number of kern pairs across all GPOS kern lookups
    * FontForge's built-in validation (path direction, open paths, etc.)

    Args:
        font: The :class:`~aifont.core.font.Font` to analyze.

    Returns:
        A :class:`FontReport` with the analysis results.
    """
    from aifont.core.metrics import get_kern_pairs  # noqa: PLC0415

    ff = font._raw
    report = FontReport()

    # Glyph count & missing unicodes.
    for name in ff:
        report.glyph_count += 1
        if ff[name].unicode < 0:
            report.missing_unicodes.append(name)

    # Kerning pairs.
    report.kerning_pairs = len(get_kern_pairs(font))

    # FontForge validation.
    errors = ff.validate()
    if errors:
        # validate() returns an integer bitmask; convert to human-readable list.
        report.validation_errors = _decode_validation_mask(errors)

    # Basic metrics.
    report.metrics = {
        "em_size": float(getattr(ff, "em", 1000)),
        "ascent": float(getattr(ff, "ascent", 800)),
        "descent": float(getattr(ff, "descent", 200)),
    }

    return report


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_VALIDATION_BITS: dict[int, str] = {
    0x1: "open_paths",
    0x2: "self_intersecting",
    0x4: "wrong_direction",
    0x8: "flipped_refs",
    0x10: "missing_extrema",
    0x20: "missing_anchors",
    0x40: "duplicate_glyphs",
    0x80: "more_points_than_spiro",
}


def _decode_validation_mask(mask: int) -> list[str]:
    return [label for bit, label in _VALIDATION_BITS.items() if mask & bit]
