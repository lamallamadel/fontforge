"""
Tests for aifont.agents.qa_agent and aifont.core.analyzer.

These tests use mock objects so they can run without a live FontForge
installation.  They validate:

- Detection of all problem types (open contours, wrong directions,
  overlaps, duplicate points).
- Automatic correction of auto-fixable issues.
- Suggestions generated for non-auto-fixable issues.
- QA report quality score calculation (0–100).
- ``QAReport.summary()`` and ``QAReport.to_dict()`` serialization.
"""

from __future__ import annotations

import sys
import types
import unittest
from dataclasses import dataclass, field
from typing import List
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Minimal fontforge stub so the SDK can be imported without the C extension.
# ---------------------------------------------------------------------------

_fontforge_stub = types.ModuleType("fontforge")
sys.modules.setdefault("fontforge", _fontforge_stub)


# ---------------------------------------------------------------------------
# Now we can safely import the SDK modules.
# ---------------------------------------------------------------------------

sys.path.insert(0, ".")  # ensure local aifont package is on the path

from aifont.core.analyzer import (  # noqa: E402
    GlyphIssue,
    FontReport,
    analyze,
    _FF_OPEN_CONTOUR,
    _FF_SELF_INTERSECT,
    _FF_WRONG_DIRECTION,
    _FF_DUPLICATE_POINT,
)
from aifont.agents.qa_agent import QAAgent, QAReport, CheckResult  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ff_glyph(name: str, unicode_val: int = -1, validate_mask: int = 0):
    """Return a minimal mock of a fontforge glyph object."""
    g = MagicMock()
    g.glyphname = name
    g.unicode = unicode_val
    g.validate.return_value = validate_mask
    g.width = 500
    g.left_side_bearing = 50
    g.right_side_bearing = 50
    g.foreground = []
    return g


def _make_ff_font(glyphs: list):
    """Return a minimal mock of a fontforge font object.

    Args:
        glyphs: list of fontforge glyph mocks.
    """
    ff = MagicMock()
    ff.fontname = "TestFont"
    glyph_map = {g.glyphname: g for g in glyphs}
    ff.__iter__ = lambda self: iter(glyph_map)
    ff.__getitem__ = lambda self, key: glyph_map[key]
    return ff


class _MockFont:
    """Minimal Font-like object backed by a mock fontforge font."""

    def __init__(self, ff_font):
        self._font = ff_font

    @property
    def _ff(self):
        return self._font

    def glyph(self, name):
        from aifont.core.glyph import Glyph
        return Glyph(self._font[name])


# ---------------------------------------------------------------------------
# Analyzer tests
# ---------------------------------------------------------------------------


class TestAnalyzerEmptyFont(unittest.TestCase):
    """analyze() on an empty font should return score 0 and no issues."""

    def test_empty_font_score(self):
        ff = MagicMock()
        ff.__iter__ = lambda self: iter([])
        font = _MockFont(ff)
        report = analyze(font)
        self.assertEqual(report.glyph_count, 0)
        self.assertEqual(report.total_issues, 0)
        self.assertEqual(report.score, 0.0)


class TestAnalyzerDetectsIssues(unittest.TestCase):
    """analyze() must detect every issue category."""

    def _report_for_mask(self, mask: int) -> FontReport:
        g = _make_ff_glyph("A", unicode_val=0x41, validate_mask=mask)
        ff = _make_ff_font([g])
        font = _MockFont(ff)
        return analyze(font)

    def test_detects_open_contour(self):
        report = self._report_for_mask(_FF_OPEN_CONTOUR)
        types_ = [i.issue_type for i in report.issues]
        self.assertIn("open_contour", types_)

    def test_detects_wrong_direction(self):
        report = self._report_for_mask(_FF_WRONG_DIRECTION)
        types_ = [i.issue_type for i in report.issues]
        self.assertIn("wrong_direction", types_)

    def test_detects_overlap(self):
        report = self._report_for_mask(_FF_SELF_INTERSECT)
        types_ = [i.issue_type for i in report.issues]
        self.assertIn("overlap", types_)

    def test_detects_duplicate_point(self):
        report = self._report_for_mask(_FF_DUPLICATE_POINT)
        types_ = [i.issue_type for i in report.issues]
        self.assertIn("duplicate_point", types_)

    def test_detects_all_combined(self):
        combined = _FF_OPEN_CONTOUR | _FF_SELF_INTERSECT | _FF_WRONG_DIRECTION | _FF_DUPLICATE_POINT
        report = self._report_for_mask(combined)
        types_ = {i.issue_type for i in report.issues}
        self.assertEqual(
            types_,
            {"open_contour", "overlap", "wrong_direction", "duplicate_point"},
        )

    def test_clean_glyph_produces_no_issues(self):
        report = self._report_for_mask(0)
        self.assertEqual(report.total_issues, 0)


class TestAnalyzerMissingUnicodes(unittest.TestCase):
    """analyze() should report missing Basic Latin glyphs."""

    def test_empty_font_has_missing_unicodes(self):
        ff = MagicMock()
        ff.__iter__ = lambda self: iter([])
        font = _MockFont(ff)
        report = analyze(font)
        self.assertGreater(len(report.missing_unicodes), 0)

    def test_full_ascii_no_missing(self):
        glyphs = [_make_ff_glyph(chr(cp), unicode_val=cp) for cp in range(0x21, 0x7F)]
        ff = _make_ff_font(glyphs)
        font = _MockFont(ff)
        report = analyze(font)
        self.assertEqual(report.missing_unicodes, [])


class TestAnalyzerScore(unittest.TestCase):
    """Quality score should decrease proportionally with issues."""

    def test_perfect_font_scores_100(self):
        glyphs = [_make_ff_glyph(chr(cp), unicode_val=cp, validate_mask=0) for cp in range(0x21, 0x7F)]
        ff = _make_ff_font(glyphs)
        font = _MockFont(ff)
        report = analyze(font)
        self.assertEqual(report.score, 100.0)

    def test_problematic_font_scores_below_100(self):
        mask = _FF_OPEN_CONTOUR | _FF_WRONG_DIRECTION
        glyphs = [_make_ff_glyph(chr(cp), unicode_val=cp, validate_mask=mask) for cp in range(0x21, 0x7F)]
        ff = _make_ff_font(glyphs)
        font = _MockFont(ff)
        report = analyze(font)
        self.assertLess(report.score, 100.0)

    def test_score_in_range(self):
        mask = _FF_OPEN_CONTOUR | _FF_SELF_INTERSECT | _FF_WRONG_DIRECTION | _FF_DUPLICATE_POINT
        glyphs = [_make_ff_glyph(chr(cp), unicode_val=cp, validate_mask=mask) for cp in range(0x21, 0x7F)]
        ff = _make_ff_font(glyphs)
        font = _MockFont(ff)
        report = analyze(font)
        self.assertGreaterEqual(report.score, 0.0)
        self.assertLessEqual(report.score, 100.0)


# ---------------------------------------------------------------------------
# QAAgent tests
# ---------------------------------------------------------------------------


class TestQAAgentNoIssues(unittest.TestCase):
    """QAAgent on a clean font should produce a passing report."""

    def _clean_font(self):
        glyphs = [_make_ff_glyph(chr(cp), unicode_val=cp, validate_mask=0) for cp in range(0x21, 0x7F)]
        ff = _make_ff_font(glyphs)
        return _MockFont(ff)

    def test_run_returns_qa_report(self):
        agent = QAAgent(self._clean_font(), auto_fix=False)
        report = agent.run()
        self.assertIsInstance(report, QAReport)

    def test_clean_font_passes_checks(self):
        agent = QAAgent(self._clean_font(), auto_fix=False)
        report = agent.run()
        self.assertTrue(report.passed)

    def test_clean_font_score_100(self):
        agent = QAAgent(self._clean_font(), auto_fix=False)
        report = agent.run()
        self.assertEqual(report.score, 100.0)


class TestQAAgentAutoFix(unittest.TestCase):
    """QAAgent auto-fix should call the corrective contour functions."""

    def test_auto_fix_wrong_direction(self):
        mask = _FF_WRONG_DIRECTION
        glyphs = [_make_ff_glyph("A", unicode_val=0x41, validate_mask=mask)]
        ff = _make_ff_font(glyphs)
        font = _MockFont(ff)

        with patch("aifont.agents.qa_agent.correct_directions") as mock_fix:
            agent = QAAgent(font, auto_fix=True)
            # Patch the second analyze call (after fix) to return a clean report.
            with patch("aifont.agents.qa_agent.analyze") as mock_analyze:
                initial = FontReport(
                    glyph_count=1,
                    issues=[
                        GlyphIssue("A", "wrong_direction", "desc", auto_fixable=True)
                    ],
                    score=80.0,
                )
                clean = FontReport(glyph_count=1, issues=[], score=100.0)
                mock_analyze.side_effect = [initial, clean]
                report = agent.run()

            # correct_directions should have been called once with ["A"].
            mock_fix.assert_called_once()
        self.assertEqual(report.corrections_applied, 1)

    def test_auto_fix_overlaps(self):
        mask = _FF_SELF_INTERSECT
        glyphs = [_make_ff_glyph("B", unicode_val=0x42, validate_mask=mask)]
        ff = _make_ff_font(glyphs)
        font = _MockFont(ff)

        with patch("aifont.agents.qa_agent.remove_overlap") as mock_fix:
            agent = QAAgent(font, auto_fix=True)
            with patch("aifont.agents.qa_agent.analyze") as mock_analyze:
                initial = FontReport(
                    glyph_count=1,
                    issues=[GlyphIssue("B", "overlap", "desc", auto_fixable=True)],
                    score=80.0,
                )
                clean = FontReport(glyph_count=1, issues=[], score=100.0)
                mock_analyze.side_effect = [initial, clean]
                report = agent.run()

            mock_fix.assert_called_once()
        self.assertEqual(report.corrections_applied, 1)

    def test_no_auto_fix_open_contours(self):
        """Open contours are NOT auto-fixable; no correction must be applied."""
        glyphs = [_make_ff_glyph("C", unicode_val=0x43, validate_mask=_FF_OPEN_CONTOUR)]
        ff = _make_ff_font(glyphs)
        font = _MockFont(ff)
        agent = QAAgent(font, auto_fix=True)
        with patch("aifont.agents.qa_agent.analyze") as mock_analyze:
            initial = FontReport(
                glyph_count=1,
                issues=[GlyphIssue("C", "open_contour", "desc", auto_fixable=False, suggestion="Close it.")],
                score=70.0,
            )
            mock_analyze.return_value = initial
            report = agent.run()
        self.assertEqual(report.corrections_applied, 0)
        self.assertFalse(report.passed)


class TestQAAgentSuggestions(unittest.TestCase):
    """QAAgent must provide suggestions for non-auto-fixable issues."""

    def test_suggestion_for_open_contour(self):
        glyphs = [_make_ff_glyph("D", unicode_val=0x44, validate_mask=_FF_OPEN_CONTOUR)]
        ff = _make_ff_font(glyphs)
        font = _MockFont(ff)
        agent = QAAgent(font, auto_fix=False)
        with patch("aifont.agents.qa_agent.analyze") as mock_analyze:
            mock_analyze.return_value = FontReport(
                glyph_count=1,
                issues=[GlyphIssue("D", "open_contour", "Open contour.", auto_fixable=False, suggestion="Close it.")],
                score=80.0,
            )
            report = agent.run()
        self.assertTrue(len(report.suggestions) > 0)

    def test_suggestion_for_missing_unicodes(self):
        glyphs = []  # empty → lots of missing unicode
        ff = _make_ff_font(glyphs)
        font = _MockFont(ff)
        agent = QAAgent(font, auto_fix=False)
        report = agent.run()
        # At least one suggestion about missing glyphs expected.
        missing_suggestions = [s for s in report.suggestions if "missing" in s.lower() or "U+" in s]
        self.assertTrue(len(missing_suggestions) > 0)


class TestQAReport(unittest.TestCase):
    """QAReport data structure tests."""

    def _make_report(self) -> QAReport:
        checks = {
            "open_contours": CheckResult(
                "Open Contours",
                passed=False,
                issues=[GlyphIssue("A", "open_contour", "Open contour.", auto_fixable=False, suggestion="Fix it.")],
            ),
            "wrong_directions": CheckResult("Contour Directions", passed=True),
            "overlaps": CheckResult("Overlapping Contours", passed=True),
            "duplicate_points": CheckResult("Duplicate Points", passed=True),
            "unicode_coverage": CheckResult("Unicode Coverage", passed=True),
        }
        return QAReport(
            font_name="TestFont",
            score=80.0,
            checks=checks,
            suggestions=["Fix open contour in A."],
            corrections_applied=0,
        )

    def test_total_issues(self):
        report = self._make_report()
        self.assertEqual(report.total_issues, 1)

    def test_passed_false_when_checks_fail(self):
        report = self._make_report()
        self.assertFalse(report.passed)

    def test_summary_contains_score(self):
        report = self._make_report()
        summary = report.summary()
        self.assertIn("80.0", summary)
        self.assertIn("TestFont", summary)

    def test_summary_contains_fail(self):
        report = self._make_report()
        self.assertIn("FAIL", report.summary())

    def test_to_dict_structure(self):
        report = self._make_report()
        d = report.to_dict()
        self.assertIn("font_name", d)
        self.assertIn("score", d)
        self.assertIn("checks", d)
        self.assertIn("suggestions", d)
        self.assertIn("corrections_applied", d)
        self.assertEqual(d["font_name"], "TestFont")
        self.assertEqual(d["score"], 80.0)

    def test_to_dict_checks_structure(self):
        report = self._make_report()
        d = report.to_dict()
        open_check = d["checks"]["open_contours"]
        self.assertFalse(open_check["passed"])
        self.assertEqual(len(open_check["issues"]), 1)
        issue = open_check["issues"][0]
        self.assertEqual(issue["glyph"], "A")
        self.assertEqual(issue["type"], "open_contour")

    def test_passing_report(self):
        checks = {
            k: CheckResult(k, passed=True)
            for k in ("open_contours", "wrong_directions", "overlaps", "duplicate_points", "unicode_coverage")
        }
        report = QAReport("Clean", 100.0, checks=checks)
        self.assertTrue(report.passed)
        self.assertIn("PASS", report.summary())


class TestQAAgentValidateFont(unittest.TestCase):
    """validate_font() tool should return a FontReport."""

    def test_returns_font_report(self):
        ff = MagicMock()
        ff.__iter__ = lambda self: iter([])
        font = _MockFont(ff)
        agent = QAAgent(font)
        result = agent.validate_font()
        self.assertIsInstance(result, FontReport)


class TestQAAgentIndividualTools(unittest.TestCase):
    """Individual tool methods should return lists of processed glyph names."""

    def _agent_with_single_glyph(self, name: str = "A") -> tuple:
        g = _make_ff_glyph(name, unicode_val=0x41)
        ff = _make_ff_font([g])
        font = _MockFont(ff)
        return QAAgent(font), name

    def test_fix_overlaps_returns_list(self):
        agent, name = self._agent_with_single_glyph()
        with patch("aifont.agents.qa_agent.remove_overlap"):
            result = agent.fix_overlaps()
        self.assertIsInstance(result, list)
        self.assertIn(name, result)

    def test_correct_directions_returns_list(self):
        agent, name = self._agent_with_single_glyph()
        with patch("aifont.agents.qa_agent.correct_directions"):
            result = agent.correct_directions()
        self.assertIsInstance(result, list)
        self.assertIn(name, result)

    def test_simplify_contours_returns_list(self):
        agent, name = self._agent_with_single_glyph()
        with patch("aifont.agents.qa_agent.simplify"):
            result = agent.simplify_contours()
        self.assertIsInstance(result, list)
        self.assertIn(name, result)

    def test_generate_qa_report_without_font_report(self):
        ff = MagicMock()
        ff.fontname = "X"
        ff.__iter__ = lambda self: iter([])
        font = _MockFont(ff)
        agent = QAAgent(font, auto_fix=False)
        report = agent.generate_qa_report()
        self.assertIsInstance(report, QAReport)
        self.assertEqual(report.font_name, "X")


if __name__ == "__main__":
    unittest.main()
