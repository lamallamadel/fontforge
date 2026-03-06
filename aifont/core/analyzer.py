"""Font analysis and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Set

if TYPE_CHECKING:
    from aifont.core.font import Font


@dataclass
class GlyphIssue:
    """A single diagnostic issue found on a glyph."""

    glyph_name: str
    code: str
    description: str
    severity: str = "warning"  # "error" | "warning" | "info"


@dataclass
class FontReport:
    """Structured analysis report returned by :func:`analyze`."""

    glyph_count: int = 0
    missing_unicode: List[str] = field(default_factory=list)
    kern_pair_count: int = 0
    issues: List[GlyphIssue] = field(default_factory=list)
    coverage_score: float = 0.0  # 0.0 – 1.0

    # Convenience properties
    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def passed(self) -> bool:
        return self.error_count == 0


def analyze(font: "Font") -> FontReport:
    """Analyze *font* and return a :class:`FontReport`.

    Checks performed:
    - Glyph count
    - Glyphs without a unicode mapping
    - Glyph width consistency
    - Kern pair count
    """
    from aifont.core.metrics import get_kern_pairs

    report = FontReport()
    report.glyph_count = font.glyph_count

    widths: List[int] = []
    try:
        ff = font._ff
        for name in ff:  # type: ignore[union-attr]
            glyph = ff[name]  # type: ignore[index]
            uni = int(getattr(glyph, "unicode", -1))
            if uni == -1:
                report.missing_unicode.append(name)
            w = int(getattr(glyph, "width", 0))
            if w > 0:
                widths.append(w)
            # Check for empty glyph (no contours, but has unicode)
            if uni != -1 and hasattr(glyph, "foreground"):
                try:
                    fg = list(glyph.foreground)
                except TypeError:
                    fg = []
                if not fg:
                    report.issues.append(
                        GlyphIssue(
                            glyph_name=name,
                            code="EMPTY_GLYPH",
                            description=f"Glyph {name!r} has a unicode mapping but no contours.",
                            severity="warning",
                        )
                    )
    except (TypeError, AttributeError):
        pass

    # Width consistency check
    if widths:
        avg = sum(widths) / len(widths)
        for name in (n for n in (getattr(font._ff, "glyphs", []) or [])):
            glyph = font._ff[name]  # type: ignore[index]
            w = int(getattr(glyph, "width", 0))
            if w > 0 and abs(w - avg) > avg * 0.5:
                report.issues.append(
                    GlyphIssue(
                        glyph_name=name,
                        code="INCONSISTENT_WIDTH",
                        description=(
                            f"Glyph {name!r} width {w} deviates significantly "
                            f"from average {avg:.0f}."
                        ),
                        severity="info",
                    )
                )

    # Kern pairs
    try:
        report.kern_pair_count = len(get_kern_pairs(font))
    except Exception:
        report.kern_pair_count = 0

    # Coverage score: fraction of glyphs that have a unicode mapping
    if report.glyph_count > 0:
        mapped = report.glyph_count - len(report.missing_unicode)
        report.coverage_score = mapped / report.glyph_count

    return report
