"""
aifont.core.analyzer — font analysis and diagnostics.

Analyze a font and produce a structured :class:`FontReport` covering:
- Glyph count and missing Unicode mappings.
- Kerning coverage.
- Curve quality (open contours, missing extrema).
- Consistency metrics (cap height, x-height, descender depth).

FontForge source code is never modified.
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
aifont.core.analyzer — font analysis and style diagnostics.

This module provides functions to extract stylistic metrics from a font,
including stroke weight, contrast, serif detection, italic angle, and
key vertical proportions.  Results are returned as a :class:`StyleProfile`
dataclass that is consumed by :mod:`aifont.agents.style_agent`.

Architecture constraint
-----------------------
DO NOT modify FontForge source code.  All font access goes through
:class:`~aifont.core.font.Font` wrappers.

Typical usage
-------------
>>> from aifont.core.font import Font
>>> from aifont.core.analyzer import analyze_style
>>>
>>> font = Font.open("MyFont.otf")
>>> profile = analyze_style(font)
>>> print(profile.weight_class, profile.italic_angle)
"""Font analysis and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Set
from typing import TYPE_CHECKING
"""Font Analyzer — rapid analysis of existing fonts to extract metrics.

This module wraps FontForge's Python bindings (``import fontforge``) as a
black-box dependency.  It NEVER modifies FontForge source code.

Usage::

    from aifont.core.analyzer import analyze

    report = analyze("MyFont.otf")
    print(report.quality_score)
    print(report.to_dict())

    import json
    with open("report.json", "w") as fh:
        json.dump(report.to_dict(), fh, indent=2)
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
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Report data classes
# ---------------------------------------------------------------------------


@dataclass
class GlyphIssue:
    """A single issue found on a specific glyph."""
import math
from dataclasses import dataclass, field
from typing import List, Optional

from aifont.core.font import Font


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
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

import fontforge  # FontForge Python binding — black-box dependency


# ---------------------------------------------------------------------------
# Unicode range definitions used for coverage analysis
# ---------------------------------------------------------------------------

# Each entry is (range_name, first_codepoint, last_codepoint_inclusive)
UNICODE_RANGES: List[Tuple[str, int, int]] = [
    ("Basic Latin", 0x0000, 0x007F),
    ("Latin-1 Supplement", 0x0080, 0x00FF),
    ("Latin Extended-A", 0x0100, 0x017F),
    ("Latin Extended-B", 0x0180, 0x024F),
    ("Greek and Coptic", 0x0370, 0x03FF),
    ("Cyrillic", 0x0400, 0x04FF),
    ("Arabic", 0x0600, 0x06FF),
    ("Devanagari", 0x0900, 0x097F),
    ("CJK Unified Ideographs", 0x4E00, 0x9FFF),
    ("Hangul Syllables", 0xAC00, 0xD7AF),
    ("Letterlike Symbols", 0x2100, 0x214F),
    ("Mathematical Operators", 0x2200, 0x22FF),
    ("General Punctuation", 0x2000, 0x206F),
    ("Currency Symbols", 0x20A0, 0x20CF),
    ("Combining Diacritical Marks", 0x0300, 0x036F),
    ("IPA Extensions", 0x0250, 0x02AF),
    ("Spacing Modifier Letters", 0x02B0, 0x02FF),
    ("Number Forms", 0x2150, 0x218F),
    ("Arrows", 0x2190, 0x21FF),
    ("Box Drawing", 0x2500, 0x257F),
    ("Block Elements", 0x2580, 0x259F),
    ("Geometric Shapes", 0x25A0, 0x25FF),
    ("Miscellaneous Symbols", 0x2600, 0x26FF),
    ("Dingbats", 0x2700, 0x27BF),
    ("Private Use Area", 0xE000, 0xF8FF),
    ("Alphabetic Presentation Forms", 0xFB00, 0xFB4F),
]


# ---------------------------------------------------------------------------
# FontReport — structured result of an analysis run
# ---------------------------------------------------------------------------


@dataclass
class StyleProfile:
    """Stylistic metrics extracted from a font.

    All measurements are in font units unless stated otherwise.

    Attributes
    ----------
    stroke_width:
        Estimated average stroke width (thin stems for high-contrast fonts).
    stroke_contrast:
        Ratio of thick to thin stroke: 0.0 = monolinear, approaching 1.0 =
        extreme contrast.
    italic_angle:
        Italic slant angle in degrees (0 = upright).
    x_height:
        Estimated x-height in font units.
    cap_height:
        Estimated cap-height in font units.
    ascender:
        Font ascender value in font units.
    descender:
        Font descender value in font units (positive number).
    em_size:
        Units-per-em for the font.
    has_serifs:
        Heuristic serif detection flag.
    weight_class:
        Estimated CSS weight class (100–900).
    glyph_count:
        Total number of glyphs analysed.
    notes:
        Free-text observations generated during analysis.
    """

    stroke_width: float = 0.0
    stroke_contrast: float = 0.0
    italic_angle: float = 0.0
    x_height: float = 0.0
    cap_height: float = 0.0
    ascender: float = 800.0
    descender: float = 200.0
    em_size: int = 1000
    has_serifs: bool = False
    weight_class: int = 400
    glyph_count: int = 0
    notes: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def summary(self) -> str:
        """Return a human-readable one-line summary."""
        serif_label = "serif" if self.has_serifs else "sans-serif"
        angle_label = f", italic {self.italic_angle:.1f}°" if self.italic_angle else ""
        return (
            f"Weight {self.weight_class}, {serif_label}{angle_label}, "
            f"stroke {self.stroke_width:.0f}u, "
            f"contrast {self.stroke_contrast:.2f}, "
            f"x-height {self.x_height:.0f}u"
        )


# ---------------------------------------------------------------------------
# Glyph helpers
# ---------------------------------------------------------------------------


def _bounding_box(ff_glyph: object):
    """Return the bounding box of a raw fontforge glyph or None."""
    bb = getattr(ff_glyph, "boundingBox", None)
    if callable(bb):
        try:
            return bb()
        except Exception:
            return None
    return None


def _glyph_width(ff_glyph: object) -> Optional[int]:
    """Return the advance width of a raw fontforge glyph or None."""
    w = getattr(ff_glyph, "width", None)
    if w is None:
        return None
    return int(w)


# ---------------------------------------------------------------------------
# Heuristic estimators
# ---------------------------------------------------------------------------


def _estimate_stroke_width(font: Font) -> float:
    """Estimate average stroke width from glyph bounding-box height ratios.

    We sample vertical extents for lowercase glyphs (a–z) and use the
    assumption that stroke width ≈ 10–15 % of cap-height for regular weight.
    """
    em = max(font.em_size, 1)
    # Use the 'o' glyph as a proxy: its inner counter height vs outer height
    # gives an approximation of stroke weight.
    for glyph_name in ("o", "O", "n", "H"):
        try:
            ff_g = font.raw[glyph_name]
        except (KeyError, TypeError):
            continue
        bb = _bounding_box(ff_g)
        if bb is None:
            continue
        xmin, ymin, xmax, ymax = bb
        height = ymax - ymin
        width = xmax - xmin
        if height > 0 and width > 0:
            # Stroke width heuristic: ~12 % of the smaller dimension
            return min(height, width) * 0.12
    # Fallback: estimate from em size
    return em * 0.08


def _estimate_x_height(font: Font) -> float:
    """Estimate x-height from the bounding box of lowercase 'x' or 'o'."""
    for glyph_name in ("x", "o", "n", "e"):
        try:
            ff_g = font.raw[glyph_name]
        except (KeyError, TypeError):
            continue
        bb = _bounding_box(ff_g)
        if bb is None:
            continue
        _, ymin, _, ymax = bb
        height = ymax - ymin
        if height > 0:
            return float(height)
    return font.em_size * 0.50


def _estimate_cap_height(font: Font) -> float:
    """Estimate cap-height from the bounding box of uppercase 'H' or 'I'."""
    for glyph_name in ("H", "I", "A", "E"):
        try:
            ff_g = font.raw[glyph_name]
        except (KeyError, TypeError):
            continue
        bb = _bounding_box(ff_g)
        if bb is None:
            continue
        _, ymin, _, ymax = bb
        height = ymax - ymin
        if height > 0:
            return float(height)
    return font.em_size * 0.70


def _estimate_stroke_contrast(font: Font, stroke_width: float) -> float:
    """Estimate stroke contrast ratio from thick/thin proportions.

    Uses the diagonal strokes of 'O' as a proxy: a monolinear font has
    nearly equal horizontal and vertical stroke widths; a high-contrast
    font has a much larger vertical stem.
    """
    em = max(font.em_size, 1)
    try:
        ff_g = font.raw["O"]
    except (KeyError, TypeError):
        ff_g = None

    if ff_g is not None:
        bb = _bounding_box(ff_g)
        if bb is not None:
            xmin, ymin, xmax, ymax = bb
            w = xmax - xmin
            h = ymax - ymin
            if w > 0 and h > 0:
                # Ratio of thin (horizontal) to thick (vertical) stems.
                # This is a rough heuristic based on counter proportions.
                ratio = abs(w - h) / max(w, h)
                return min(ratio, 1.0)
    # Fallback heuristic
    thick = stroke_width
    thin = thick * 0.4
    if thick > 0:
        return max(0.0, min(1.0, 1.0 - thin / thick))
    return 0.0


def _detect_serifs(font: Font) -> bool:
    """Heuristic serif detection.

    Serif fonts tend to have a font name or family name containing "serif",
    "times", "garamond", "palatino", "georgia" etc.  This is a simple
    name-based heuristic; point-level analysis would require much more code.
    """
    serif_keywords = {
        "serif", "times", "garamond", "palatino", "georgia", "roman",
        "caslon", "baskerville", "didot", "bodoni", "minion",
    }
    sans_keywords = {
        "sans", "gothic", "grotesque", "grotesk", "futura", "helvetica",
        "arial", "verdana", "trebuchet",
    }
    name = (font.family_name + " " + font.font_name).lower()
    if any(k in name for k in serif_keywords):
        return True
    if any(k in name for k in sans_keywords):
        return False
    # Default: assume sans-serif
    return False


def _weight_class_from_stroke(stroke_width: float, em_size: int) -> int:
    """Map a stroke width to the nearest CSS weight class (100–900)."""
    if em_size <= 0:
        return 400
    ratio = stroke_width / em_size
    # Approximate boundaries
    thresholds = [
        (0.04, 100),   # Thin
        (0.055, 200),  # ExtraLight
        (0.07, 300),   # Light
        (0.09, 400),   # Regular
        (0.11, 500),   # Medium
        (0.13, 600),   # SemiBold
        (0.16, 700),   # Bold
        (0.20, 800),   # ExtraBold
    ]
    for threshold, weight in thresholds:
        if ratio < threshold:
            return weight
    return 900  # Black


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_style(font: Font) -> StyleProfile:
    """Analyse the visual style of *font* and return a :class:`StyleProfile`.

    The analysis uses heuristics based on glyph bounding boxes and font
    metadata.  It does not perform point-level Bézier analysis.

    Parameters
    ----------
    font:
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
    StyleProfile
        A dataclass containing the extracted stylistic metrics.

    Examples
    --------
    >>> from aifont.core.font import Font
    >>> from aifont.core.analyzer import analyze_style
    >>> profile = analyze_style(Font.open("Helvetica.otf"))
    >>> print(profile.summary())
    """
    notes: List[str] = []

    em = font.em_size
    italic_angle = font.italic_angle
    ascender = float(font.ascent)
    descender = float(font.descent)

    stroke_width = _estimate_stroke_width(font)
    x_height = _estimate_x_height(font)
    cap_height = _estimate_cap_height(font)
    stroke_contrast = _estimate_stroke_contrast(font, stroke_width)
    has_serifs = _detect_serifs(font)
    weight_class = _weight_class_from_stroke(stroke_width, em)

    # Count glyphs
    glyph_count = 0
    try:
        for _ in font.raw:
            glyph_count += 1
    except Exception:
        pass

    if italic_angle != 0.0:
        notes.append(f"Font is italic (angle={italic_angle:.1f}°)")
    if has_serifs:
        notes.append("Serif font detected (name heuristic)")
    else:
        notes.append("Sans-serif font detected (name heuristic)")

    return StyleProfile(
        stroke_width=stroke_width,
        stroke_contrast=stroke_contrast,
        italic_angle=italic_angle,
        x_height=x_height,
        cap_height=cap_height,
        ascender=ascender,
        descender=descender,
        em_size=em,
        has_serifs=has_serifs,
        weight_class=weight_class,
        glyph_count=glyph_count,
        notes=notes,
class GlobalMetrics:
    """Core typographic metrics extracted from the font."""

    ascent: int
    descent: int
    units_per_em: int
    cap_height: int
    x_height: int
    italic_angle: float
    underline_position: int
    underline_width: int
    family_name: str
    full_name: str
    weight: str
    version: str
    copyright: str
    is_fixed_pitch: bool
    sf_version: str


@dataclass
class GlyphInfo:
    """Lightweight summary of a single glyph."""

    name: str
    unicode_value: int
    width: int
    has_contours: bool


@dataclass
class UnicodeCoverage:
    """Coverage statistics for a Unicode block."""

    block_name: str
    first_codepoint: int
    last_codepoint: int
    block_size: int
    covered: int
    coverage_percent: float


@dataclass
class BasicProblem:
    """A detected quality issue in the font."""

    severity: str  # "error" | "warning" | "info"
    glyph_name: Optional[str]
    description: str
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from aifont.core.font import Font


@dataclass
class GlyphIssue:
    """A single diagnostic issue found on a glyph."""

    glyph_name: str
    code: str
    description: str
    severity: str = "warning"  # "error" | "warning" | "info"
    """A single issue found in a glyph."""
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
    severity: str = "warning"  # "info" | "warning" | "error"
    auto_fixable: bool = True
    suggestion: str = ""


@dataclass
class FontReport:
    """Structured analysis report returned by :func:`analyze`."""

    glyph_count: int = 0
    missing_unicode: List[str] = field(default_factory=list)
    kern_pair_count: int = 0
    issues: List[GlyphIssue] = field(default_factory=list)
    coverage_score: float = 0.0  # 0.0 – 1.0

    # Convenience properties
    """Structured analysis report for a font."""

    glyph_count: int = 0
    missing_unicodes: List[int] = field(default_factory=list)
    kern_pair_count: int = 0
    issues: List[GlyphIssue] = field(default_factory=list)
    score: float = 0.0  # 0.0 – 100.0

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

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
    def summary(self) -> str:
        return (
            f"FontReport: {self.glyph_count} glyphs, "
            f"{self.error_count} errors, {self.warning_count} warnings, "
            f"score={self.score:.1f}/100"
        )


def analyze(font: "Font") -> FontReport:
    """Analyze a font and return a structured :class:`FontReport`.

    Checks performed:
    - Glyph count
    - Missing Unicode mappings
    - Kerning coverage
    - Path direction issues
    - Open contours

    Args:
        font: The font to analyze.

    Returns:
        A :class:`FontReport` with all findings.
    """
    report = FontReport()
    ff = font._ff
    if ff is None:
        return report

    report.glyph_count = len(list(ff.glyphs()))

    issues: List[GlyphIssue] = []

    for glyph in ff.glyphs():
        # Check for open contours
        for contour in glyph.foreground:
            if not contour.closed:
                issues.append(
                    GlyphIssue(
                        glyph_name=glyph.glyphname,
                        issue_type="open_contour",
                        description="Glyph has an open contour.",
                        severity="error",
                    )
                )

        # Check unicode mapping
        if glyph.unicode == -1 and not glyph.glyphname.startswith("."):
            issues.append(
                GlyphIssue(
                    glyph_name=glyph.glyphname,
                    issue_type="missing_unicode",
                    description="Glyph has no Unicode mapping.",
                    severity="warning",
                )
            )
            report.missing_unicodes.append(-1)

        # FontForge validation
        ff_issues = glyph.validate(True)
        if ff_issues != 0:
            issues.append(
                GlyphIssue(
                    glyph_name=glyph.glyphname,
                    issue_type="validation",
                    description=f"FontForge validation flags: {ff_issues:#010x}",
                    severity="warning",
                )
            )

    report.issues = issues

    # Score: start at 100, deduct per issue
    deductions = sum(5 if i.severity == "error" else 1 for i in issues)
    report.score = max(0.0, 100.0 - deductions)

    return report
    """Complete analysis report for a font file.

    All fields are plain Python types so the report can be serialised to JSON
    without any special encoder.
    """

    font_path: str
    global_metrics: GlobalMetrics
    glyph_count: int
    glyphs: List[GlyphInfo]
    unicode_coverage: List[UnicodeCoverage]
    problems: List[BasicProblem]
    quality_score: float  # 0.0 – 100.0

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain :class:`dict` representation of the report.

        The returned dictionary contains only JSON-serializable types so it
        can be passed directly to :func:`json.dump`.
        """
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Return a JSON string representation of the report."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save_json(self, path: str, indent: int = 2) -> None:
        """Write the report as a JSON file at *path*."""
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_json(indent=indent))


# ---------------------------------------------------------------------------
# FontAnalyzer
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
    """Analyzes an existing font and produces a :class:`FontReport`.

    The analyser uses FontForge's Python bindings exclusively — it never
    modifies the font on disk.

    Parameters
    ----------
    font_path:
        Absolute or relative path to the font file (.otf, .ttf, .sfd, …).
    """

    def __init__(self, font_path: str) -> None:
        self.font_path = os.path.abspath(font_path)
        self._ff_font: Optional[fontforge.font] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def analyze(self) -> FontReport:
        """Run the full analysis pipeline and return a :class:`FontReport`."""
        self._ff_font = fontforge.open(self.font_path)
        try:
            global_metrics = self._extract_global_metrics()
            glyphs = self._extract_glyphs()
            glyph_count = len(glyphs)
            unicode_coverage = self._compute_unicode_coverage(glyphs)
            problems = self._detect_problems(glyphs)
            quality_score = self._compute_quality_score(
                global_metrics, glyphs, problems
            )
        finally:
            self._ff_font.close()
            self._ff_font = None

        return FontReport(
            font_path=self.font_path,
            global_metrics=global_metrics,
            glyph_count=glyph_count,
            glyphs=glyphs,
            unicode_coverage=unicode_coverage,
            problems=problems,
            quality_score=quality_score,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_global_metrics(self) -> GlobalMetrics:
        ff = self._ff_font
        return GlobalMetrics(
            ascent=ff.ascent,
            descent=ff.descent,
            units_per_em=ff.ascent + ff.descent,
            cap_height=ff.capHeight,
            x_height=ff.xHeight,
            italic_angle=float(ff.italicangle),
            underline_position=ff.upos,
            underline_width=ff.uwidth,
            family_name=ff.familyname or "",
            full_name=ff.fullname or "",
            weight=ff.weight or "",
            version=ff.version or "",
            copyright=ff.copyright or "",
            is_fixed_pitch=bool(ff.is_fixed_pitch),
            sf_version=ff.sfversion or "",
        )

    def _extract_glyphs(self) -> List[GlyphInfo]:
        ff = self._ff_font
        glyphs: List[GlyphInfo] = []
        for name in ff:
            g = ff[name]
            has_contours = g.layer_cnt > 0 and len(g.layers[ff.activeLayer]) > 0
            glyphs.append(
                GlyphInfo(
                    name=name,
                    unicode_value=g.unicode if g.unicode >= 0 else -1,
                    width=g.width,
                    has_contours=has_contours,
                )
            )
        return glyphs

    def _compute_unicode_coverage(
        self, glyphs: List[GlyphInfo]
    ) -> List[UnicodeCoverage]:
        covered_codepoints = {
            g.unicode_value for g in glyphs if g.unicode_value >= 0
        }
        result: List[UnicodeCoverage] = []
        for block_name, first, last in UNICODE_RANGES:
            block_size = last - first + 1
            covered = sum(
                1 for cp in range(first, last + 1) if cp in covered_codepoints
            )
            coverage_percent = round(covered / block_size * 100, 2) if block_size else 0.0
            result.append(
                UnicodeCoverage(
                    block_name=block_name,
                    first_codepoint=first,
                    last_codepoint=last,
                    block_size=block_size,
                    covered=covered,
                    coverage_percent=coverage_percent,
                )
            )
        return result

    def _detect_problems(self, glyphs: List[GlyphInfo]) -> List[BasicProblem]:
        """Detect basic font problems using FontForge's validation APIs."""
        ff = self._ff_font
        problems: List[BasicProblem] = []

        # --- Global metric sanity checks ---
        if ff.ascent <= 0:
            problems.append(
                BasicProblem(
                    severity="error",
                    glyph_name=None,
                    description="Font ascent is zero or negative.",
                )
            )
        if ff.descent < 0:
            problems.append(
                BasicProblem(
                    severity="warning",
                    glyph_name=None,
                    description=(
                        "Font descent is stored as a negative value; "
                        "some tools expect a non-negative value."
                    ),
                )
            )
        upm = ff.ascent + ff.descent
        if upm not in (1000, 2048):
            problems.append(
                BasicProblem(
                    severity="info",
                    glyph_name=None,
                    description=(
                        f"Units per em is {upm}. "
                        "Common values are 1000 (OTF/CFF) and 2048 (TTF)."
                    ),
                )
            )

        # --- Missing essential glyphs ---
        essential_unicodes = {
            0x0020: "space",
            0x002E: "period",
            0x0041: "A",
            0x0061: "a",
            0x0030: "zero",
        }
        covered = {g.unicode_value for g in glyphs}
        for cp, label in essential_unicodes.items():
            if cp not in covered:
                problems.append(
                    BasicProblem(
                        severity="warning",
                        glyph_name=None,
                        description=f"Missing essential glyph: {label} (U+{cp:04X}).",
                    )
                )

        # --- Per-glyph validation via fontforge ---
        for name in ff:
            g = ff[name]
            if g.unicode < 0:
                continue  # skip un-encoded glyphs for this check
            errors = g.validate(True)
            if errors != 0:
                # FontForge validation flags are bit-masked; report any non-zero result
                problems.append(
                    BasicProblem(
                        severity="warning",
                        glyph_name=name,
                        description=(
                            f"Glyph '{name}' failed FontForge validation "
                            f"(error flags: {errors:#010x})."
                        ),
                    )
                )

        return problems

    def _compute_quality_score(
        self,
        metrics: GlobalMetrics,
        glyphs: List[GlyphInfo],
        problems: List[BasicProblem],
    ) -> float:
        """Compute a simple quality score in the range 0.0 – 100.0.

        The score is composed of:

        * **Glyph coverage** (40 pts): proportion of the Basic Latin block
          (U+0020–U+007E, 95 printable code points) that is present.
        * **Metric soundness** (30 pts): basic sanity of ascent/descent/UPM.
        * **Problem penalty** (30 pts): deducted proportionally based on the
          number and severity of detected problems.
        """
        score = 0.0

        # 1. Basic Latin coverage (40 pts)
        basic_latin_printable = set(range(0x0020, 0x007F))  # 95 code points
        covered = {g.unicode_value for g in glyphs if g.unicode_value >= 0}
        latin_covered = len(basic_latin_printable & covered)
        score += 40.0 * (latin_covered / len(basic_latin_printable))

        # 2. Metric soundness (30 pts)
        metric_score = 30.0
        if metrics.ascent <= 0:
            metric_score -= 15.0
        if metrics.units_per_em <= 0:
            metric_score -= 15.0
        if metrics.cap_height <= 0:
            metric_score -= 5.0
        if metrics.x_height <= 0:
            metric_score -= 5.0
        score += max(0.0, metric_score)

        # 3. Problem penalty (30 pts)
        error_count = sum(1 for p in problems if p.severity == "error")
        warning_count = sum(1 for p in problems if p.severity == "warning")
        penalty = min(30.0, error_count * 5.0 + warning_count * 1.0)
        score += max(0.0, 30.0 - penalty)

        return round(min(100.0, max(0.0, score)), 2)


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------


def analyze(font_path: str) -> FontReport:
    """Convenience wrapper: open *font_path*, analyse it, and return the report.

    Parameters
    ----------
    font_path:
        Path to the font file to analyse.

    Returns
    -------
    FontReport
        A structured report containing global metrics, glyph list, Unicode
        coverage, detected problems, and a quality score.
    """
    return FontAnalyzer(font_path).analyze()
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
