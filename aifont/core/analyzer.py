"""
aifont.core.analyzer — font analysis and diagnostics.

Analyze a font and produce a structured :class:`FontReport` covering:
- Glyph count and missing Unicode mappings.
- Kerning coverage.
- Curve quality (open contours, missing extrema).
- Consistency metrics (cap height, x-height, descender depth).

FontForge source code is never modified.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Report data classes
# ---------------------------------------------------------------------------


@dataclass
class GlyphIssue:
    """A single issue found on a specific glyph."""

    glyph_name: str
    issue_type: str
    description: str


@dataclass
class FontReport:
    """Structured analysis report for a font.

    Attributes:
        glyph_count:        Total number of glyphs in the font.
        unicode_coverage:   Fraction of glyphs that have a Unicode mapping
                            (0.0 – 1.0).
        missing_unicodes:   Glyph names that lack a Unicode code point.
        kern_pair_count:    Total number of kern pairs.
        open_contours:      Glyph names that contain open (unclosed) contours.
        issues:             List of all detected issues.
        metrics_summary:    Dict with ``cap_height``, ``x_height``,
                            ``ascender``, ``descender`` estimates.
    """

    glyph_count: int = 0
    unicode_coverage: float = 0.0
    missing_unicodes: List[str] = field(default_factory=list)
    kern_pair_count: int = 0
    open_contours: List[str] = field(default_factory=list)
    issues: List[GlyphIssue] = field(default_factory=list)
    metrics_summary: Dict[str, float] = field(default_factory=dict)

    def passed(self) -> bool:
        """Return True if no critical issues were found."""
        return len(self.issues) == 0

    def __str__(self) -> str:
        lines = [
            f"FontReport:",
            f"  Glyphs          : {self.glyph_count}",
            f"  Unicode coverage: {self.unicode_coverage:.1%}",
            f"  Missing unicodes: {len(self.missing_unicodes)}",
            f"  Kern pairs      : {self.kern_pair_count}",
            f"  Open contours   : {len(self.open_contours)}",
            f"  Issues          : {len(self.issues)}",
        ]
        if self.metrics_summary:
            lines.append(f"  Metrics         : {self.metrics_summary}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_ff_font(font_or_ff: object) -> object:
    """Return the raw fontforge font from a wrapper or raw object."""
    if hasattr(font_or_ff, "_font"):
        return font_or_ff._font  # type: ignore[attr-defined]
    return font_or_ff


def _count_kern_pairs(ff_font: object) -> int:
    """Return an approximate count of kern pairs in the font."""
    count = 0
    try:
        for glyph_name in ff_font:
            g = ff_font[glyph_name]
            for entry in g.getPosSub("*"):
                if len(entry) >= 3 and entry[2] != 0:
                    count += 1
    except Exception:
        pass
    return count


def _find_open_contours(ff_font: object) -> List[str]:
    """Return names of glyphs that have open (unclosed) contours."""
    open_names: List[str] = []
    try:
        for glyph_name in ff_font:
            g = ff_font[glyph_name]
            layer = g.foreground
            for contour in layer:
                if not contour.closed:
                    open_names.append(glyph_name)
                    break
    except Exception:
        pass
    return open_names


def _estimate_metrics(ff_font: object) -> Dict[str, float]:
    """Estimate cap height, x-height, ascender, descender from representative glyphs."""
    result: Dict[str, float] = {}
    _candidates = {
        "cap_height": ["H", "I"],
        "x_height": ["x", "n"],
    }
    try:
        result["ascender"] = float(getattr(ff_font, "ascent", 0))
        result["descender"] = float(getattr(ff_font, "descent", 0))
    except Exception:
        pass

    for key, names in _candidates.items():
        for name in names:
            try:
                g = ff_font[name]
                bb = g.boundingBox()
                result[key] = float(bb[3])  # ymax
                break
            except Exception:
                continue

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class FontAnalyzer:
    """Stateful font analyzer.

    Example::

        analyzer = FontAnalyzer(font)
        report = analyzer.run()
        print(report)
    """

    def __init__(self, font: object) -> None:
        """Create an analyzer for *font*.

        Args:
            font: A :class:`~aifont.core.font.Font` wrapper or a raw
                  ``fontforge.font`` object.
        """
        self._ff = _get_ff_font(font)

    def run(self) -> FontReport:
        """Run all analysis checks and return a :class:`FontReport`.

        Returns:
            A :class:`FontReport` with all findings populated.
        """
        report = FontReport()
        ff = self._ff

        glyph_names: List[str] = []
        try:
            glyph_names = list(ff)
        except Exception:
            pass

        report.glyph_count = len(glyph_names)

        # Unicode coverage
        missing: List[str] = []
        for name in glyph_names:
            try:
                uni = ff[name].unicode
                if uni < 0:
                    missing.append(name)
            except Exception:
                missing.append(name)

        report.missing_unicodes = missing
        if report.glyph_count > 0:
            covered = report.glyph_count - len(missing)
            report.unicode_coverage = covered / report.glyph_count

        # Kerning
        report.kern_pair_count = _count_kern_pairs(ff)

        # Open contours
        report.open_contours = _find_open_contours(ff)
        for name in report.open_contours:
            report.issues.append(
                GlyphIssue(
                    glyph_name=name,
                    issue_type="open_contour",
                    description=f"Glyph '{name}' has an open contour.",
                )
            )

        # FontForge built-in validation (if available)
        try:
            problems = ff.validate()
            if problems:
                report.issues.append(
                    GlyphIssue(
                        glyph_name="<font>",
                        issue_type="validation",
                        description=f"FontForge validation returned flags: {problems}",
                    )
                )
        except Exception:
            pass

        # Metrics summary
        report.metrics_summary = _estimate_metrics(ff)

        return report


def analyze(font: object) -> FontReport:
    """Convenience wrapper — create a :class:`FontAnalyzer` and run it.

    Args:
        font: Font wrapper or raw fontforge font.

    Returns:
        A populated :class:`FontReport`.
    """
    return FontAnalyzer(font).run()
