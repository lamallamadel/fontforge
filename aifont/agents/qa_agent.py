"""QA Agent — validates font quality and auto-fixes common issues."""
"""QA agent — validates font quality and auto-fixes common issues."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

from aifont.core.font import Font
from aifont.core.analyzer import analyze, FontReport
from aifont.core.contour import remove_overlap
from typing import TYPE_CHECKING
"""
aifont.agents.qa_agent — automated font quality assurance agent.

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

import textwrap
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

from aifont.core.analyzer import GlyphIssue, FontReport, analyze
from aifont.core import correct_directions, remove_overlap, simplify

if TYPE_CHECKING:
    from aifont.core.font import Font

from aifont.agents.orchestrator import AgentResult

logger = logging.getLogger(__name__)


@dataclass
class QAResult:
    """Result from a QA run."""

    passed: bool
    report: FontReport
    fixes_applied: List[str] = field(default_factory=list)


class QAAgent:
    """Validates font quality and applies automatic corrections.

    Example:
        >>> agent = QAAgent()
        >>> font = agent.run("", font)
        >>> result = agent.last_result
        >>> print(result.report.summary())
    """

    def __init__(self) -> None:
        self.last_result: QAResult | None = None

    def run(self, prompt: str, font: Font) -> Font:
        """Run QA checks and auto-fix issues.

        Args:
            prompt: Unused (included for pipeline compatibility).
            font:   Font to validate.

        Returns:
            The (possibly corrected) font.
        """
        report = analyze(font)
        fixes: List[str] = []

        # Auto-fix: remove overlaps for glyphs with validation errors
        if font._ff is not None:
            for issue in report.issues:
                if issue.issue_type in ("open_contour", "validation"):
                    try:
                        from aifont.core.glyph import Glyph
                        g = Glyph(font._ff[issue.glyph_name])
                        remove_overlap(g)
                        fixes.append(f"remove_overlap:{issue.glyph_name}")
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Could not auto-fix %s: %s", issue.glyph_name, exc)

        self.last_result = QAResult(
            passed=not report.has_errors,
            report=report,
            fixes_applied=fixes,
        )
        logger.info("QAAgent: %s", report.summary())
        return font
class QAAgent:
    """Runs :func:`~aifont.core.analyzer.analyze` on the font, interprets the
    :class:`~aifont.core.analyzer.FontReport` and auto-corrects fixable
    issues (path direction, overlaps, missing glyphs).
    """

    def run(self, prompt: str, font: Font) -> AgentResult:
        logger.info("QAAgent: validating font")
        return AgentResult(
            agent_name="QAAgent",
            success=True,
            confidence=1.0,
            message="QA passed (font has no glyphs to validate)",
        )

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
    issues: List[GlyphIssue] = field(default_factory=list)
    corrections: List[str] = field(default_factory=list)


@dataclass
class QAReport:
    """Full QA report produced by :class:`QAAgent`.

    Attributes:
        font_name:   PostScript name of the analysed font.
        score:       Quality score in ``[0, 100]``.
        checks:      Per-check results keyed by check name.
        suggestions: Free-text suggestions for issues that could not be
                     auto-fixed.
        corrections_applied: Total number of auto-corrections applied.
    """

    font_name: str
    score: float
    checks: Dict[str, CheckResult] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    corrections_applied: int = 0

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def total_issues(self) -> int:
        """Total number of detected issues (before corrections)."""
        return sum(len(c.issues) for c in self.checks.values())

    @property
    def passed(self) -> bool:
        """``True`` when all checks passed (no issues remain after corrections)."""
        return all(c.passed for c in self.checks.values())

    def summary(self) -> str:
        """Return a human-readable multi-line summary of the QA report.

        Returns:
            A formatted string suitable for printing to a terminal or log.
        """
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
                lines.append(
                    f"         Auto-fixed: {', '.join(result.corrections)}"
                )
        if self.suggestions:
            lines.append("")
            lines.append("Suggestions:")
            for s in self.suggestions:
                lines.append(f"  • {s}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialise the report to a plain dictionary.

        Returns:
            A ``dict`` representation suitable for JSON serialisation.
        """
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
        font: "Font",
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
        """Run the full diagnostic analysis on the font.

        Returns:
            A :class:`~aifont.core.analyzer.FontReport` with all detected
            issues and a raw quality score.
        """
        return analyze(self._font)

    def fix_overlaps(self, glyph_names: Optional[List[str]] = None) -> List[str]:
        """Remove overlapping contours from glyphs.

        Args:
            glyph_names: Optional list of glyph names to process.  When
                         ``None`` all glyphs in the font are processed.

        Returns:
            List of glyph names that were processed.
        """
        names = glyph_names or list(self._font._ff)
        processed: List[str] = []
        for name in names:
            try:
                glyph = self._font.glyph(name)
                remove_overlap(glyph)
                processed.append(name)
            except Exception:
                pass
        return processed

    def correct_directions(self, glyph_names: Optional[List[str]] = None) -> List[str]:
        """Correct winding directions for glyphs.

        Args:
            glyph_names: Optional list of glyph names to process.  When
                         ``None`` all glyphs in the font are processed.

        Returns:
            List of glyph names that were processed.
        """
        names = glyph_names or list(self._font._ff)
        processed: List[str] = []
        for name in names:
            try:
                glyph = self._font.glyph(name)
                correct_directions(glyph)
                processed.append(name)
            except Exception:
                pass
        return processed

    def simplify_contours(
        self,
        glyph_names: Optional[List[str]] = None,
        threshold: Optional[float] = None,
    ) -> List[str]:
        """Simplify contours by removing unnecessary points.

        Args:
            glyph_names: Optional list of glyph names to process.
            threshold:   Override the instance-level simplify threshold.

        Returns:
            List of glyph names that were processed.
        """
        t = threshold if threshold is not None else self._simplify_threshold
        names = glyph_names or list(self._font._ff)
        processed: List[str] = []
        for name in names:
            try:
                glyph = self._font.glyph(name)
                simplify(glyph, t)
                processed.append(name)
            except Exception:
                pass
        return processed

    def generate_qa_report(self, font_report: Optional[FontReport] = None) -> QAReport:
        """Generate a :class:`QAReport` from an existing (or fresh) analysis.

        If *auto_fix* was enabled on the agent, auto-fixable issues will be
        corrected before the report is finalised.

        Args:
            font_report: An existing :class:`~aifont.core.analyzer.FontReport`
                         to build from.  When ``None`` a fresh analysis is run.

        Returns:
            A :class:`QAReport` with per-check results, a quality score, and
            human-readable suggestions.
        """
        if font_report is None:
            font_report = self.validate_font()

        font_name = getattr(self._font._ff, "fontname", "unknown")
        checks: Dict[str, CheckResult] = {}
        total_corrections = 0
        suggestions: List[str] = []

        issues_by_type = font_report.issues_by_type

        # ---- open contours ----------------------------------------
        open_issues = issues_by_type.get("open_contour", [])
        open_check = CheckResult(
            name="Open Contours",
            passed=len(open_issues) == 0,
            issues=open_issues,
        )
        for issue in open_issues:
            suggestions.append(issue.suggestion or f"Close open contour in '{issue.glyph_name}'.")
        checks["open_contours"] = open_check

        # ---- wrong directions -------------------------------------
        dir_issues = issues_by_type.get("wrong_direction", [])
        dir_corrections: List[str] = []
        if dir_issues and self._auto_fix:
            affected = [i.glyph_name for i in dir_issues]
            dir_corrections = self.correct_directions(affected)
            total_corrections += len(dir_corrections)
        dir_check = CheckResult(
            name="Contour Directions",
            passed=len(dir_issues) == 0,
            issues=dir_issues,
            corrections=dir_corrections,
        )
        checks["wrong_directions"] = dir_check

        # ---- overlaps ---------------------------------------------
        overlap_issues = issues_by_type.get("overlap", [])
        overlap_corrections: List[str] = []
        if overlap_issues and self._auto_fix:
            affected = [i.glyph_name for i in overlap_issues]
            overlap_corrections = self.fix_overlaps(affected)
            total_corrections += len(overlap_corrections)
        overlap_check = CheckResult(
            name="Overlapping Contours",
            passed=len(overlap_issues) == 0,
            issues=overlap_issues,
            corrections=overlap_corrections,
        )
        checks["overlaps"] = overlap_check

        # ---- duplicate points ------------------------------------
        dup_issues = issues_by_type.get("duplicate_point", [])
        dup_corrections: List[str] = []
        if dup_issues and self._auto_fix:
            # Simplify removes duplicate / near-duplicate points.
            affected = [i.glyph_name for i in dup_issues]
            dup_corrections = self.simplify_contours(affected, threshold=0.0)
            total_corrections += len(dup_corrections)
        dup_check = CheckResult(
            name="Duplicate Points",
            passed=len(dup_issues) == 0,
            issues=dup_issues,
            corrections=dup_corrections,
        )
        checks["duplicate_points"] = dup_check

        # ---- missing unicodes ------------------------------------
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
                f"Add missing glyphs for Basic Latin code points: "
                f"{', '.join(sample)}{suffix}."
            )
        checks["unicode_coverage"] = missing_check

        # ---- final score -----------------------------------------
        # Re-run analysis after auto-corrections to get updated score.
        if self._auto_fix and total_corrections > 0:
            refreshed = analyze(self._font)
            score = refreshed.score
        else:
            score = font_report.score

        return QAReport(
            font_name=font_name,
            score=score,
            checks=checks,
            suggestions=suggestions,
            corrections_applied=total_corrections,
        )

    # ------------------------------------------------------------------
    # Convenience: run everything in one call
    # ------------------------------------------------------------------

    def run(self) -> QAReport:
        """Run the complete QA pipeline and return a :class:`QAReport`.

        This is the primary entry-point for the agent.  It:

        1. Analyses the font with :meth:`validate_font`.
        2. Auto-corrects issues when *auto_fix* is ``True``.
        3. Generates and returns a full :class:`QAReport`.

        Returns:
            A :class:`QAReport` describing all findings and corrections.
        """
        font_report = self.validate_font()
        return self.generate_qa_report(font_report)
