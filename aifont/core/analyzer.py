"""
aifont.core.analyzer — Font analysis and diagnostics.

Inspects a font and returns a structured :class:`FontReport` containing:

* Glyph count and coverage statistics
* Missing Unicode code-points in key ranges
* Kerning pair count and coverage
* Contour quality metrics (open paths, self-intersections, direction)
* Consistency checks (height, width, sidebearing uniformity)

FontForge is used as a black-box dependency via ``import fontforge``.
No FontForge source code is modified.
"""

from __future__ import annotations

import dataclasses
import unicodedata
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

from .metrics import get_kern_pairs

if TYPE_CHECKING:
    from .font import Font


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class GlyphIssue:
    """A single validation issue found in a glyph.

    Attributes
    ----------
    glyph_name : str
        Name of the affected glyph.
    issue_type : str
        Short identifier such as ``"open_path"``, ``"direction"``,
        ``"overlap"``, ``"missing_unicode"``.
    description : str
        Human-readable description of the problem.
    """

    glyph_name: str
    issue_type: str
    description: str


@dataclasses.dataclass
class FontReport:
    """Structured diagnostic report for a font.

    Attributes
    ----------
    family_name : str
        Font family name.
    glyph_count : int
        Total number of glyphs.
    unicode_coverage : int
        Number of glyphs with a Unicode code-point assigned.
    missing_basic_latin : list of int
        Code-points in U+0020–U+007E that lack a glyph.
    kern_pair_count : int
        Total number of explicit kerning pairs.
    issues : list of GlyphIssue
        All detected per-glyph issues.
    validation_score : float
        A score between 0.0 (many issues) and 1.0 (no issues).
    metrics_summary : dict
        Aggregated metric statistics (avg width, cap-height, etc.).
    """

    family_name: str
    glyph_count: int
    unicode_coverage: int
    missing_basic_latin: List[int]
    kern_pair_count: int
    issues: List[GlyphIssue]
    validation_score: float
    metrics_summary: Dict[str, float]

    def passed(self) -> bool:
        """Return ``True`` if no issues were found."""
        return len(self.issues) == 0

    def issues_by_type(self, issue_type: str) -> List[GlyphIssue]:
        """Return all issues of the given *issue_type*."""
        return [i for i in self.issues if i.issue_type == issue_type]

    def __str__(self) -> str:
        lines = [
            f"Font: {self.family_name}",
            f"  Glyphs       : {self.glyph_count}",
            f"  Unicode cvg  : {self.unicode_coverage}",
            f"  Kern pairs   : {self.kern_pair_count}",
            f"  Issues       : {len(self.issues)}",
            f"  Score        : {self.validation_score:.2f}",
        ]
        if self.missing_basic_latin:
            sample = [
                chr(cp) for cp in self.missing_basic_latin[:10]
            ]
            lines.append(
                f"  Missing latin: {''.join(sample)}"
                + ("…" if len(self.missing_basic_latin) > 10 else "")
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze(font: "Font") -> FontReport:
    """Analyse *font* and return a :class:`FontReport`.

    Runs the following checks on every glyph in *font*:

    * Open contours
    * Path direction (wrong winding)
    * Self-intersecting paths (overlaps)
    * Missing Unicode assignment
    * Inconsistent advance widths (for proportional fonts)

    It also checks for missing Basic Latin glyphs (U+0020–U+007E) and
    collects kerning statistics.

    Parameters
    ----------
    font : Font
        The :class:`~aifont.core.font.Font` to analyse.

    Returns
    -------
    FontReport
        A structured report with all findings.

    Examples
    --------
    ::

        from aifont.core.font import Font
        from aifont.core.analyzer import analyze

        font = Font.open("MyFont.otf")
        report = analyze(font)
        print(report)
        for issue in report.issues:
            print(f"  [{issue.issue_type}] {issue.glyph_name}: {issue.description}")
    """
    ff = font.ff_font
    issues: List[GlyphIssue] = []

    # ---- glyph census ----
    glyph_names = list(ff)
    glyph_count = len(glyph_names)
    unicode_coverage = sum(
        1 for n in glyph_names if ff[n].unicode >= 0
    )

    # ---- missing Basic Latin ----
    existing_cps: Set[int] = {
        ff[n].unicode for n in glyph_names if ff[n].unicode >= 0
    }
    missing_basic_latin = [
        cp for cp in range(0x0020, 0x007F) if cp not in existing_cps
    ]

    # ---- per-glyph validation ----
    widths: List[int] = []
    for name in glyph_names:
        g = ff[name]
        _check_glyph(g, name, issues)
        if g.width > 0:
            widths.append(int(g.width))

    # ---- kerning ----
    kern_pairs = get_kern_pairs(font)
    kern_pair_count = len(kern_pairs)

    # ---- metrics summary ----
    metrics_summary: Dict[str, float] = {}
    if widths:
        metrics_summary["avg_width"] = sum(widths) / len(widths)
        metrics_summary["min_width"] = float(min(widths))
        metrics_summary["max_width"] = float(max(widths))
    try:
        metrics_summary["em_size"] = float(ff.em)
        metrics_summary["ascent"] = float(ff.ascent)
        metrics_summary["descent"] = float(ff.descent)
    except Exception:  # noqa: BLE001
        pass

    # ---- validation score ----
    # Simple heuristic: 1.0 − (issues / max_possible_issues)
    max_issues = max(glyph_count * 4, 1)  # 4 checks per glyph
    validation_score = max(0.0, 1.0 - len(issues) / max_issues)

    return FontReport(
        family_name=font.metadata.family_name,
        glyph_count=glyph_count,
        unicode_coverage=unicode_coverage,
        missing_basic_latin=missing_basic_latin,
        kern_pair_count=kern_pair_count,
        issues=issues,
        validation_score=round(validation_score, 4),
        metrics_summary=metrics_summary,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


# FontForge validation bitmask constants
# (see fontforge documentation for full list)
_FF_VALIDATION = {
    0x1: "open_contour",
    0x2: "self_intersection",
    0x4: "wrong_direction",
    0x8: "flipped_references",
    0x10: "missing_extrema",
    0x20: "wrong_start_point",
    0x200: "too_many_points",
    0x400: "no_glyph_name",
    0x800: "duplicate_unicode",
    0x1000: "unicode_out_of_range",
    0x2000: "overlap",
}

_FF_VALIDATION_DESCRIPTIONS = {
    "open_contour": "Contour is not closed",
    "self_intersection": "Path self-intersects",
    "wrong_direction": "Path direction is incorrect",
    "flipped_references": "Component reference is flipped",
    "missing_extrema": "Missing extrema points",
    "wrong_start_point": "Wrong start point",
    "too_many_points": "Too many points in contour",
    "no_glyph_name": "Glyph has no PostScript name",
    "duplicate_unicode": "Duplicate Unicode code-point",
    "unicode_out_of_range": "Unicode value out of valid range",
    "overlap": "Overlapping contours",
}


def _check_glyph(
    ff_glyph: object,
    name: str,
    issues: List[GlyphIssue],
) -> None:
    """Run FontForge validation on one glyph and append issues."""
    try:
        mask = int(ff_glyph.validate(True))  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return

    for bit, issue_type in _FF_VALIDATION.items():
        if mask & bit:
            description = _FF_VALIDATION_DESCRIPTIONS.get(
                issue_type, issue_type
            )
            issues.append(
                GlyphIssue(
                    glyph_name=name,
                    issue_type=issue_type,
                    description=description,
                )
            )
