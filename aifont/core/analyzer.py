"""aifont.core.analyzer — font analysis and diagnostics.

Analyzes a font and produces a structured :class:`FontReport`.
FontForge source code is never modified.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aifont.core.font import Font


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class GlyphIssue:
    """A single validation issue found in a glyph.

    Both ``issue_type`` and ``code`` refer to the same value.
    Either keyword can be used at construction time.

    Attributes:
        glyph_name:  PostScript name of the affected glyph.
        issue_type:  Short identifier such as ``"open_contour"`` (alias: ``code``).
        description: Human-readable description of the problem.
        severity:    One of ``"info"``, ``"warning"``, ``"error"``.
        code:        Alias for ``issue_type``.
        suggestion:  Optional suggestion for fixing the issue.
        auto_fixable: Whether the issue can be auto-fixed.
    """

    glyph_name: str
    issue_type: str = ""
    description: str = ""
    severity: str = "warning"
    code: str = ""
    suggestion: str = ""
    auto_fixable: bool = False

    def __post_init__(self) -> None:
        if self.code and not self.issue_type:
            self.issue_type = self.code
        elif self.issue_type and not self.code:
            self.code = self.issue_type


@dataclass
class FontReport:
    """Structured analysis report returned by :func:`analyze`.

    All fields have sensible defaults so ``FontReport()`` works with no args.

    Note:
        ``coverage_score`` is an alias for ``unicode_coverage``.
        ``missing_unicode`` is an alias for ``missing_unicodes``.
        ``passed`` is a property that returns ``True`` if no *error*-severity
        issues are present.
    """

    glyph_count: int = 0
    unicode_coverage: float = 0.0
    missing_unicodes: list[str] = field(default_factory=list)
    kern_pair_count: int = 0
    open_contours: list[str] = field(default_factory=list)
    issues: list[GlyphIssue] = field(default_factory=list)
    metrics_summary: dict[str, float] = field(default_factory=dict)
    family_name: str = ""
    missing_basic_latin: list[int] = field(default_factory=list)
    validation_score: float = 0.0
    # Alias fields accepted in __init__ for backward compatibility
    coverage_score: float | None = field(default=None, repr=False)
    missing_unicode: list[str] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        # Apply alias → primary field mapping
        if self.coverage_score is not None:
            self.unicode_coverage = self.coverage_score
        else:
            self.coverage_score = self.unicode_coverage
        if self.missing_unicode is not None:
            self.missing_unicodes = self.missing_unicode
        else:
            self.missing_unicode = self.missing_unicodes

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def passed(self) -> bool:
        """``True`` if no *error*-severity issues are present."""
        return not any(i.severity == "error" for i in self.issues)

    @property
    def error_count(self) -> int:
        """Number of issues with ``severity == "error"``."""
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        """Number of issues with ``severity == "warning"``."""
        return sum(1 for i in self.issues if i.severity == "warning")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def issues_by_type(self, issue_type: str) -> list[GlyphIssue]:
        """Return all issues of the given *issue_type* (or *code*)."""
        return [i for i in self.issues if i.issue_type == issue_type or i.code == issue_type]

    def __str__(self) -> str:
        lines = ["FontReport:"]
        if self.family_name:
            lines.append(f"  Family          : {self.family_name}")
        lines += [
            f"  Glyphs          : {self.glyph_count}",
            f"  Unicode coverage: {self.unicode_coverage}",
            f"  Missing unicodes: {len(self.missing_unicodes)}",
            f"  Kern pairs      : {self.kern_pair_count}",
            f"  Open contours   : {len(self.open_contours)}",
            f"  Issues          : {len(self.issues)}",
        ]
        if self.validation_score:
            lines.append(f"  Score           : {self.validation_score:.2f}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# StyleProfile — lightweight font style snapshot
# ---------------------------------------------------------------------------


@dataclass
class StyleProfile:
    """A lightweight snapshot of a font's visual style attributes.

    Used by :class:`~aifont.agents.style_agent.StyleAgent` to capture the
    style *before* and *after* a transfer operation.

    Attributes:
        stroke_width:  Estimated average stroke width in font units.
        italic_angle:  Italic angle in degrees (0 = upright).
        weight:        Estimated weight value (100–900).
        x_height:      x-height in font units (0 if unknown).
        cap_height:    Cap-height in font units (0 if unknown).
        style_name:    Descriptive style label derived from the font metadata.
    """

    stroke_width: float = 0.0
    italic_angle: float = 0.0
    weight: float = 400.0
    x_height: float = 0.0
    cap_height: float = 0.0
    style_name: str = ""

    def summary(self) -> str:
        """Return a one-line human-readable summary."""
        return (
            f"style={self.style_name!r} weight={self.weight:.0f}"
            f" stroke={self.stroke_width:.1f} angle={self.italic_angle:.1f}°"
        )


def analyze_style(font: object) -> StyleProfile:
    """Extract a :class:`StyleProfile` from *font*.

    Reads italic angle, weight, and typographic metrics from the font's
    ``fontforge`` object.  Falls back gracefully when attributes are absent.

    Args:
        font: A :class:`~aifont.core.font.Font` wrapper or raw fontforge font.

    Returns:
        A :class:`StyleProfile` populated from the font's metadata.
    """
    ff = _get_ff_font(font)

    italic_angle: float = 0.0
    with contextlib.suppress(Exception):
        italic_angle = float(getattr(ff, "italicangle", 0) or 0)

    weight: float = 400.0
    with contextlib.suppress(Exception):
        os2 = getattr(ff, "os2_weight", None)
        if os2:
            weight = float(os2)

    x_height: float = 0.0
    cap_height: float = 0.0
    metrics = _estimate_metrics(ff)
    x_height = float(metrics.get("x_height", 0.0))
    cap_height = float(metrics.get("cap_height", 0.0))

    # Estimate stroke width from the 'I' or 'l' glyph
    stroke_width: float = 0.0
    with contextlib.suppress(Exception):
        for gname in ("I", "l", "H"):
            g = ff[gname]  # type: ignore[index]
            bb = g.boundingBox()
            if bb and bb[2] > bb[0]:
                stroke_width = float(bb[2] - bb[0])
                break

    style_name: str = ""
    with contextlib.suppress(Exception):
        style_name = str(getattr(ff, "weight", "") or "")

    return StyleProfile(
        stroke_width=stroke_width,
        italic_angle=italic_angle,
        weight=weight,
        x_height=x_height,
        cap_height=cap_height,
        style_name=style_name,
    )


# ---------------------------------------------------------------------------
# FontAnalyzer class
# ---------------------------------------------------------------------------


class FontAnalyzer:
    """Class-based interface to font analysis.

    Example::

        analyzer = FontAnalyzer(font)
        report = analyzer.run()
    """

    def __init__(self, font: Font) -> None:
        self._font = font

    def run(self) -> FontReport:
        """Run the full analysis and return a :class:`FontReport`."""
        return analyze(self._font)


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
        for glyph_name in ff_font:  # type: ignore[union-attr]
            g = ff_font[glyph_name]  # type: ignore[index]
            for entry in g.getPosSub("*"):
                if len(entry) >= 4 and entry[1] == "Pair":
                    count += 1
    except Exception:  # noqa: BLE001
        pass
    return count


def _find_open_contours(ff_font: object) -> list[str]:
    """Return names of glyphs that have open (unclosed) contours."""
    open_names: list[str] = []
    try:
        for glyph_name in ff_font:  # type: ignore[union-attr]
            g = ff_font[glyph_name]  # type: ignore[index]
            layer = g.foreground
            for contour in layer:
                if not contour.closed:
                    open_names.append(glyph_name)
                    break
    except Exception:  # noqa: BLE001
        pass
    return open_names


def _estimate_metrics(ff_font: object) -> dict[str, float]:
    """Estimate typographic metrics from the font."""
    result: dict[str, float] = {}
    _candidates = {
        "cap_height": ["H", "I"],
        "x_height": ["x", "n"],
    }
    try:
        result["ascender"] = float(getattr(ff_font, "ascent", 0))
        result["descender"] = float(getattr(ff_font, "descent", 0))
        result["em_size"] = float(getattr(ff_font, "em", 1000))
    except Exception:  # noqa: BLE001
        pass
    for key, names in _candidates.items():
        for name in names:
            try:
                g = ff_font[name]  # type: ignore[index]
                bb = g.boundingBox()
                result[key] = float(bb[3])
                break
            except Exception:  # noqa: BLE001
                continue
    return result


def _check_glyph(
    ff_glyph: object,
    name: str,
    issues: list[GlyphIssue],
) -> None:
    """Run validation checks on one glyph and append any issues found."""
    _ff_validation = {
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
    _descriptions = {
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
    try:
        mask_raw = ff_glyph.validate(True)  # type: ignore[attr-defined]
        mask = int(mask_raw) if mask_raw is not None else 0
    except Exception:  # noqa: BLE001
        mask = 0
    for bit, issue_type in _ff_validation.items():
        if mask & bit:
            description = _descriptions.get(issue_type, issue_type)
            issues.append(
                GlyphIssue(
                    glyph_name=name,
                    issue_type=issue_type,
                    description=description,
                )
            )

    # Check for empty glyph (no contours in foreground)
    try:
        uni = int(getattr(ff_glyph, "unicode", -1))
        if uni >= 0:  # only mapped glyphs are expected to have contours
            has_contours = any(True for _ in ff_glyph.foreground)  # type: ignore[attr-defined]
            if not has_contours:
                issues.append(
                    GlyphIssue(
                        glyph_name=name,
                        code="EMPTY_GLYPH",
                        description="Glyph has no contours",
                        severity="warning",
                    )
                )
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze(font: Font) -> FontReport:
    """Analyse *font* and return a :class:`FontReport`.

    Args:
        font: The :class:`~aifont.core.font.Font` to analyse.

    Returns:
        A :class:`FontReport` with the analysis results.
    """
    try:
        from aifont.core.metrics import get_kern_pairs  # noqa: PLC0415
    except ImportError:
        get_kern_pairs = None  # type: ignore[assignment]

    ff = font._font  # type: ignore[attr-defined]

    # Family name
    try:
        family_name = font.metadata.family_name  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        family_name = str(getattr(ff, "familyname", "") or "")

    # Glyph census
    glyph_names: list[str] = []
    with contextlib.suppress(Exception):
        glyph_names = list(ff)  # type: ignore[arg-type]
    glyph_count = len(glyph_names)

    # Unicode coverage
    unicode_with_mapping = 0
    missing_unicodes: list[str] = []
    existing_cps: set[int] = set()
    for name in glyph_names:
        try:
            g = ff[name]  # type: ignore[index]
            uni = int(getattr(g, "unicode", -1))
            if uni >= 0:
                unicode_with_mapping += 1
                existing_cps.add(uni)
            else:
                missing_unicodes.append(name)
        except Exception:  # noqa: BLE001
            pass

    if glyph_count > 0:
        unicode_coverage: float = unicode_with_mapping / glyph_count
    else:
        unicode_coverage = 0.0

    # Missing Basic Latin glyphs (U+0020–U+007E)
    missing_basic_latin = [cp for cp in range(0x0020, 0x007F) if cp not in existing_cps]

    # Per-glyph validation
    issues: list[GlyphIssue] = []
    open_contours: list[str] = []
    for name in glyph_names:
        try:
            g = ff[name]  # type: ignore[index]
            _check_glyph(g, name, issues)
            # Track open contours separately
            try:
                layer = g.foreground
                for contour in layer:
                    if not contour.closed:
                        open_contours.append(name)
                        break
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001
            pass

    # Kerning
    kern_pair_count = 0
    if get_kern_pairs is not None:
        try:
            kern_pairs = get_kern_pairs(font)
            kern_pair_count = len(kern_pairs)
        except Exception:  # noqa: BLE001
            pass

    # Metrics summary
    metrics_summary = _estimate_metrics(ff)
    if "em_size" not in metrics_summary:
        try:
            metrics_summary["em_size"] = float(getattr(ff, "em", 1000))
        except Exception:  # noqa: BLE001
            metrics_summary["em_size"] = 1000.0

    # Validation score
    max_issues = max(glyph_count * 4, 1)
    validation_score = max(0.0, 1.0 - len(issues) / max_issues)

    return FontReport(
        glyph_count=glyph_count,
        unicode_coverage=unicode_coverage,
        missing_unicodes=missing_unicodes,
        kern_pair_count=kern_pair_count,
        open_contours=open_contours,
        issues=issues,
        metrics_summary=metrics_summary,
        family_name=family_name,
        missing_basic_latin=missing_basic_latin,
        validation_score=round(validation_score, 4),
    )
