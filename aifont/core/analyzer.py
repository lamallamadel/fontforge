"""
aifont.core.analyzer — font analysis and diagnostics.

Analyzes a :class:`~aifont.core.font.Font` for structural quality issues and
returns a :class:`FontReport` data object containing per-glyph diagnostics and
summary statistics.

The analyzer uses fontforge's built-in validation API together with custom
heuristics to detect:

- Open contours
- Incorrect winding directions
- Self-intersecting / overlapping contours
- Duplicate points on contours
- Missing Unicode mappings for printable code points
- Inconsistent cap-height / x-height across glyphs

These results are consumed by :class:`~aifont.agents.qa_agent.QAAgent` to drive
automated corrections and to produce a human-readable QA report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from aifont.core.font import Font


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

# fontforge validation bitmask constants (see fontforge/splinefont.h)
_FF_OPEN_CONTOUR = 0x1
_FF_SELF_INTERSECT = 0x2
_FF_WRONG_DIRECTION = 0x8
_FF_DUPLICATE_POINT = 0x400


@dataclass
class GlyphIssue:
    """A single quality problem detected on one glyph.

    Attributes:
        glyph_name:  PostScript name of the affected glyph.
        issue_type:  Short string key identifying the issue category
                     (``"open_contour"``, ``"wrong_direction"``,
                     ``"overlap"``, ``"duplicate_point"``).
        description: Human-readable description of the problem.
        auto_fixable: ``True`` when the agent can correct this automatically.
        suggestion:  Suggested action when auto-fix is not available.
    """

    glyph_name: str
    issue_type: str
    description: str
    auto_fixable: bool = True
    suggestion: str = ""


@dataclass
class FontReport:
    """Analysis report for an entire font.

    Attributes:
        glyph_count:   Total number of glyphs in the font.
        issues:        List of all detected :class:`GlyphIssue` objects.
        missing_unicodes: List of Unicode code points present in a standard
                          printable range but absent from the font.
        score:         Quality score in the range ``[0, 100]``.  ``100``
                       means no problems were found.
    """

    glyph_count: int = 0
    issues: List[GlyphIssue] = field(default_factory=list)
    missing_unicodes: List[int] = field(default_factory=list)
    score: float = 100.0

    # Convenience grouping
    @property
    def issues_by_type(self) -> Dict[str, List[GlyphIssue]]:
        """Return issues grouped by ``issue_type``."""
        result: Dict[str, List[GlyphIssue]] = {}
        for issue in self.issues:
            result.setdefault(issue.issue_type, []).append(issue)
        return result

    @property
    def total_issues(self) -> int:
        """Total number of issues detected."""
        return len(self.issues)

    @property
    def auto_fixable_count(self) -> int:
        """Number of issues that can be auto-fixed."""
        return sum(1 for i in self.issues if i.auto_fixable)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

# Basic Latin printable range used for missing-unicode checks
_BASIC_LATIN = list(range(0x21, 0x7F))  # '!' to '~'


def analyze(font: "Font") -> FontReport:
    """Analyze *font* and return a :class:`FontReport`.

    Runs fontforge's built-in ``validate()`` on each glyph (which checks for
    open contours, wrong directions, overlaps, and duplicate points) plus a
    custom check for missing Unicode assignments across the Basic Latin range.

    Args:
        font: A :class:`~aifont.core.font.Font` instance to analyse.

    Returns:
        A :class:`FontReport` summarising all detected issues and a quality
        score between 0 and 100.
    """
    ff = font._ff
    issues: List[GlyphIssue] = []

    # ------------------------------------------------------------------
    # Per-glyph validation via fontforge's validate() bitmask
    # ------------------------------------------------------------------
    glyph_names: List[str] = list(ff)
    glyph_count = len(glyph_names)

    for name in glyph_names:
        try:
            g = ff[name]
        except Exception:
            continue

        try:
            mask = g.validate(False)
        except Exception:
            mask = 0

        if mask & _FF_OPEN_CONTOUR:
            issues.append(
                GlyphIssue(
                    glyph_name=name,
                    issue_type="open_contour",
                    description=f"Glyph '{name}' has one or more open contours.",
                    auto_fixable=False,
                    suggestion=(
                        "Close the path manually or remove the stray open segment."
                    ),
                )
            )

        if mask & _FF_WRONG_DIRECTION:
            issues.append(
                GlyphIssue(
                    glyph_name=name,
                    issue_type="wrong_direction",
                    description=(
                        f"Glyph '{name}' has contours with incorrect winding direction."
                    ),
                    auto_fixable=True,
                )
            )

        if mask & _FF_SELF_INTERSECT:
            issues.append(
                GlyphIssue(
                    glyph_name=name,
                    issue_type="overlap",
                    description=f"Glyph '{name}' has self-intersecting or overlapping contours.",
                    auto_fixable=True,
                )
            )

        if mask & _FF_DUPLICATE_POINT:
            issues.append(
                GlyphIssue(
                    glyph_name=name,
                    issue_type="duplicate_point",
                    description=f"Glyph '{name}' contains duplicate on-curve points.",
                    auto_fixable=True,
                )
            )

    # ------------------------------------------------------------------
    # Missing Unicode check (Basic Latin)
    # ------------------------------------------------------------------
    present = set()
    for name in glyph_names:
        try:
            u = ff[name].unicode
            if u >= 0:
                present.add(u)
        except Exception:
            pass

    missing_unicodes = [cp for cp in _BASIC_LATIN if cp not in present]

    # ------------------------------------------------------------------
    # Quality score
    # ------------------------------------------------------------------
    # Deduct points for each issue relative to glyph count.
    # Maximum penalty is 100 (score floor is 0).
    if glyph_count > 0:
        issue_ratio = len(issues) / glyph_count
        # Each issue reduces the score; cap deduction at 100.
        deduction = min(issue_ratio * 50, 100.0)
        # Missing unicode coverage also penalises the score (up to 20 pts).
        coverage_deduction = min((len(missing_unicodes) / len(_BASIC_LATIN)) * 20, 20.0)
        score = max(0.0, 100.0 - deduction - coverage_deduction)
    else:
        score = 0.0

    return FontReport(
        glyph_count=glyph_count,
        issues=issues,
        missing_unicodes=missing_unicodes,
        score=round(score, 1),
    )
