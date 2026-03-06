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

from __future__ import annotations

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


@dataclass
class FontReport:
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
