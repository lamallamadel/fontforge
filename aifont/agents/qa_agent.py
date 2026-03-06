"""QA Agent — validates font quality and auto-fixes common issues."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

from aifont.core.font import Font
from aifont.core.analyzer import analyze, FontReport
from aifont.core.contour import remove_overlap

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
