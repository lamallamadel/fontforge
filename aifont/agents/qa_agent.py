"""QA agent — validates font quality and auto-fixes common issues."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from aifont.core.font import Font
    from aifont.core.analyzer import GlyphIssue


@dataclass
class QAReport:
    """Validation report produced by the QAAgent."""

    passed: bool = True
    checks: Dict[str, bool] = field(default_factory=dict)
    auto_fixed: List[str] = field(default_factory=list)
    issues_remaining: List["GlyphIssue"] = field(default_factory=list)
    confidence: float = 1.0


class QAAgent:
    """Runs font quality checks and applies auto-fixes.

    Uses :func:`aifont.core.analyzer.analyze` for diagnostics and
    :mod:`aifont.core.contour` for auto-corrections.
    """

    def __init__(self) -> None:
        pass

    def run(
        self,
        prompt: str,
        font: Optional["Font"] = None,
    ) -> QAReport:
        """Validate *font* and return a :class:`QAReport`."""
        if font is None:
            return QAReport(passed=False, confidence=0.0)

        from aifont.core.analyzer import analyze
        from aifont.core.contour import remove_overlap
        from aifont.core.glyph import Glyph

        report_data = analyze(font)
        checks: Dict[str, bool] = {
            "glyph_count": report_data.glyph_count > 0,
            "no_errors": report_data.error_count == 0,
            "coverage": report_data.coverage_score > 0,
        }
        auto_fixed: List[str] = []

        # Auto-fix: remove overlaps from glyphs that have issues
        for issue in report_data.issues:
            if issue.code == "EMPTY_GLYPH":
                continue  # cannot auto-fix
            try:
                glyph = font.get_glyph(issue.glyph_name)
                remove_overlap(glyph)
                auto_fixed.append(issue.glyph_name)
            except (KeyError, Exception):
                pass

        remaining = [
            i for i in report_data.issues
            if i.glyph_name not in auto_fixed
        ]
        return QAReport(
            passed=all(checks.values()),
            checks=checks,
            auto_fixed=auto_fixed,
            issues_remaining=remaining,
        )
