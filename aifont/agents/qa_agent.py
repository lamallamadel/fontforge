"""aifont.agents.qa_agent — automated font quality assurance agent.

The :class:`QAAgent` validates font quality and corrects common problems
automatically.  It exposes a set of *tools* that can be invoked individually
or in batch:

- :meth:`~QAAgent.validate_font`        — run full diagnostic analysis.
- :meth:`~QAAgent.fix_overlaps`         — remove overlapping contours.
- :meth:`~QAAgent.correct_directions`   — fix winding-direction errors.
- :meth:`~QAAgent.simplify_contours`    — reduce unnecessary path points.
- :meth:`~QAAgent.generate_qa_report`   — produce a structured QA report.

Typical usage::

    from aifont.core.font import Font
    from aifont.agents.qa_agent import QAAgent

    font = Font.open("MyFont.otf")
    agent = QAAgent(font)
    report = agent.run()
    print(report.summary())

Architecture constraint
-----------------------
This agent uses **only** ``aifont.core`` APIs.  It never imports or calls
``fontforge`` directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from aifont.core import correct_directions, remove_overlap, simplify
from aifont.core.analyzer import FontReport, GlyphIssue, analyze

if TYPE_CHECKING:
    from aifont.core.font import Font


# ---------------------------------------------------------------------------
# QA Report
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    """Outcome of a single QA check.

    Attributes:
        name:        Human-readable name of the check.
        passed:      ``True`` if no problems were found.
        issues:      Issues detected by this check.
        corrections: Names of glyphs that were auto-corrected.
    """

    name: str
    passed: bool
    issues: list[GlyphIssue] = field(default_factory=list)
    corrections: list[str] = field(default_factory=list)


@dataclass
class QAReport:
    """Full QA report produced by :class:`QAAgent`.

    Attributes:
        font_name:   PostScript name of the analysed font.
        score:       Quality score in ``[0, 100]``.
        checks:      Per-check results keyed by check name (bool or CheckResult).
        suggestions: Free-text suggestions for issues that could not be
                     auto-fixed.
        corrections_applied: Total number of auto-corrections applied.
        confidence:  Agent confidence in the result (0.0–1.0).
        auto_fixed:  List of glyph names that were auto-corrected.
        issues_remaining: List of issue descriptions that could not be fixed.
    """

    font_name: str = ""
    score: float = 0.0
    checks: dict[str, CheckResult | bool] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)
    corrections_applied: int = 0
    confidence: float = 0.0
    auto_fixed: list[str] = field(default_factory=list)
    issues_remaining: list[str] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        """Total number of detected issues (before corrections)."""
        return sum(
            (len(c.issues) if isinstance(c, CheckResult) else 0) for c in self.checks.values()
        )

    @property
    def passed(self) -> bool:
        """``True`` when all checks passed."""
        return all(
            (c.passed if isinstance(c, CheckResult) else bool(c)) for c in self.checks.values()
        )

    def summary(self) -> str:
        """Return a human-readable multi-line summary of the QA report."""
        lines = [
            f"QA Report — {self.font_name}",
            f"  Score             : {self.score:.1f}/100",
            f"  Issues detected   : {self.total_issues}",
            f"  Auto-corrections  : {self.corrections_applied}",
            f"  Overall           : {'PASS' if self.passed else 'FAIL'}",
            "",
            "Checks:",
        ]
        for name, result in self.checks.items():
            status = "✓ PASS" if result.passed else "✗ FAIL"
            lines.append(f"  [{status}] {name}")
            for issue in result.issues:
                indent = "         "
                lines.append(f"{indent}• {issue.description}")
                if issue.suggestion:
                    lines.append(f"{indent}  → {issue.suggestion}")
            if result.corrections:
                lines.append(f"         Auto-fixed: {', '.join(result.corrections)}")
        if self.suggestions:
            lines.append("")
            lines.append("Suggestions:")
            for s in self.suggestions:
                lines.append(f"  • {s}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialise the report to a plain dictionary."""
        return {
            "font_name": self.font_name,
            "score": self.score,
            "passed": self.passed,
            "total_issues": self.total_issues,
            "corrections_applied": self.corrections_applied,
            "checks": {
                name: {
                    "passed": chk.passed,
                    "issues": [
                        {
                            "glyph": i.glyph_name,
                            "type": i.issue_type,
                            "description": i.description,
                            "auto_fixable": i.auto_fixable,
                            "suggestion": i.suggestion,
                        }
                        for i in chk.issues
                    ],
                    "corrections": chk.corrections,
                }
                for name, chk in self.checks.items()
            },
            "suggestions": self.suggestions,
        }


# ---------------------------------------------------------------------------
# QA Agent
# ---------------------------------------------------------------------------


class QAAgent:
    """Agent that validates font quality and auto-corrects common issues.

    Args:
        font:            The :class:`~aifont.core.font.Font` to validate.
        simplify_threshold: Distance threshold passed to
                            :func:`~aifont.core.contour.simplify`.
                            Defaults to ``1.0``.
        auto_fix:        When ``True`` (default) the agent will attempt to
                         correct auto-fixable issues in-place before scoring.
    """

    def __init__(
        self,
        font: Font | None = None,
        simplify_threshold: float = 1.0,
        auto_fix: bool = True,
    ) -> None:
        self._font = font
        self._simplify_threshold = simplify_threshold
        self._auto_fix = auto_fix

    # ------------------------------------------------------------------
    # Individual tools
    # ------------------------------------------------------------------

    def validate_font(self) -> FontReport:
        """Run the full diagnostic analysis on the font."""
        return analyze(self._font)

    def fix_overlaps(self, glyph_names: list[str] | None = None) -> list[str]:
        """Remove overlapping contours from glyphs."""
        names = glyph_names or list(self._font._ff)  # type: ignore[union-attr]
        processed: list[str] = []
        for name in names:
            try:
                glyph = self._font.glyph(name)  # type: ignore[union-attr]
                remove_overlap(glyph)
                processed.append(name)
            except Exception:
                pass
        return processed

    def correct_directions(self, glyph_names: list[str] | None = None) -> list[str]:
        """Correct winding directions for glyphs."""
        names = glyph_names or list(self._font._ff)  # type: ignore[union-attr]
        processed: list[str] = []
        for name in names:
            try:
                glyph = self._font.glyph(name)  # type: ignore[union-attr]
                correct_directions(glyph)
                processed.append(name)
            except Exception:
                pass
        return processed

    def simplify_contours(
        self,
        glyph_names: list[str] | None = None,
        threshold: float | None = None,
    ) -> list[str]:
        """Simplify contours by removing unnecessary points."""
        t = threshold if threshold is not None else self._simplify_threshold
        names = glyph_names or list(self._font._ff)  # type: ignore[union-attr]
        processed: list[str] = []
        for name in names:
            try:
                glyph = self._font.glyph(name)  # type: ignore[union-attr]
                simplify(glyph, t)
                processed.append(name)
            except Exception:
                pass
        return processed

    def generate_qa_report(self, font_report: FontReport | None = None) -> QAReport:
        """Generate a :class:`QAReport` from an existing (or fresh) analysis."""
        if font_report is None:
            font_report = self.validate_font()

        font_name = getattr(getattr(self._font, "_ff", None), "fontname", "unknown")
        checks: dict[str, CheckResult] = {}
        total_corrections = 0
        suggestions: list[str] = []

        # Build a dict grouping issues by type for easy lookup
        issues_by_type: dict[str, list] = {}
        for issue in font_report.issues:
            issues_by_type.setdefault(issue.issue_type or issue.code, []).append(issue)

        open_issues = issues_by_type.get("open_contour", [])
        open_check = CheckResult(
            name="Open Contours",
            passed=len(open_issues) == 0,
            issues=open_issues,
        )
        for issue in open_issues:
            suggestions.append(issue.suggestion or f"Close open contour in '{issue.glyph_name}'.")
        checks["open_contours"] = open_check

        dir_issues = issues_by_type.get("wrong_direction", [])
        dir_corrections: list[str] = []
        if dir_issues and self._auto_fix:
            affected = [i.glyph_name for i in dir_issues]
            dir_corrections = self.correct_directions(affected)
            total_corrections += len(dir_corrections)
        checks["wrong_directions"] = CheckResult(
            name="Contour Directions",
            passed=len(dir_issues) == 0,
            issues=dir_issues,
            corrections=dir_corrections,
        )

        overlap_issues = issues_by_type.get("overlap", [])
        overlap_corrections: list[str] = []
        if overlap_issues and self._auto_fix:
            affected = [i.glyph_name for i in overlap_issues]
            overlap_corrections = self.fix_overlaps(affected)
            total_corrections += len(overlap_corrections)
        checks["overlaps"] = CheckResult(
            name="Overlapping Contours",
            passed=len(overlap_issues) == 0,
            issues=overlap_issues,
            corrections=overlap_corrections,
        )

        dup_issues = issues_by_type.get("duplicate_point", [])
        dup_corrections: list[str] = []
        if dup_issues and self._auto_fix:
            affected = [i.glyph_name for i in dup_issues]
            dup_corrections = self.simplify_contours(affected, threshold=0.0)
            total_corrections += len(dup_corrections)
        checks["duplicate_points"] = CheckResult(
            name="Duplicate Points",
            passed=len(dup_issues) == 0,
            issues=dup_issues,
            corrections=dup_corrections,
        )

        missing = font_report.missing_unicodes
        missing_check = CheckResult(
            name="Unicode Coverage (Basic Latin)",
            passed=len(missing) == 0,
            issues=[],
        )
        if missing:
            sample = [f"U+{cp:04X}" for cp in missing[:10]]
            suffix = f" (and {len(missing) - 10} more)" if len(missing) > 10 else ""
            suggestions.append(
                f"Add missing glyphs for Basic Latin code points: {', '.join(sample)}{suffix}."
            )
        checks["unicode_coverage"] = missing_check

        if self._auto_fix and total_corrections > 0:
            refreshed = analyze(self._font)
            score = refreshed.validation_score * 100
        else:
            score = font_report.validation_score * 100

        return QAReport(
            font_name=font_name,
            score=score,
            checks=checks,
            suggestions=suggestions,
            corrections_applied=total_corrections,
            confidence=0.8 if self._font is not None else 0.0,
            auto_fixed=[
                c for cr in checks.values() if isinstance(cr, CheckResult) for c in cr.corrections
            ],
            issues_remaining=[
                i.description
                for cr in checks.values()
                if isinstance(cr, CheckResult)
                for i in cr.issues
                if not i.auto_fixable
            ],
        )

    def run(self, prompt: str = "", *, font: object | None = None) -> QAReport:
        """Run the complete QA pipeline and return a :class:`QAReport`.

        Parameters
        ----------
        prompt:
            Optional natural-language instruction (currently unused).
        font:
            Font to validate.  Overrides the instance-level font when given.
            When neither this nor the instance font is set a minimal "no-op"
            report is returned with ``confidence=0.0``.
        """
        if font is not None:
            self._font = font  # type: ignore[assignment]
        if self._font is None:
            return QAReport(
                checks={
                    "glyph_count": False,
                    "no_errors": False,
                    "coverage": False,
                },
                confidence=0.0,
            )
        font_report = self.validate_font()
        report = self.generate_qa_report(font_report)
        # Ensure canonical check keys expected by tests are present
        report.checks.setdefault("glyph_count", font_report.glyph_count > 0)
        report.checks.setdefault(
            "no_errors", not any(i.severity == "error" for i in font_report.issues)
        )
        report.checks.setdefault("coverage", font_report.unicode_coverage > 0)
        return report
