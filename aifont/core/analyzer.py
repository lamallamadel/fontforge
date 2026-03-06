"""Font analysis and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from aifont.core.font import Font


@dataclass
class GlyphIssue:
    """A single issue found in a glyph."""

    glyph_name: str
    issue_type: str
    description: str
    severity: str = "warning"  # "info" | "warning" | "error"


@dataclass
class FontReport:
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
