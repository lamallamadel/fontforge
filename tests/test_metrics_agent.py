"""
tests/test_metrics_agent.py — unit tests for aifont.agents.MetricsAgent.

These tests exercise the full metrics pipeline using a minimal mock font
object so that fontforge is not required to run them in isolation.

A separate integration section (class TestMetricsAgentIntegration) exercises
the agent against a real fontforge font when fontforge is available.
"""

import sys
import unittest
from dataclasses import dataclass
from typing import Dict, List
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Minimal mock font that mimics the fontforge font API
# ---------------------------------------------------------------------------


@dataclass
class _MockGlyph:
    name: str
    width: int = 500
    left_side_bearing: int = 50
    right_side_bearing: int = 50

    def boundingBox(self):
        # xmin = lsb, xmax = width - rsb
        xmin = float(self.left_side_bearing)
        xmax = float(self.width - self.right_side_bearing)
        return (xmin, -200.0, xmax, 700.0)


class _MockFont:
    """Minimal font mock compatible with aifont.core.metrics internals."""

    def __init__(self):
        self.fontname = "MockFont-Regular"
        self.em = 1000
        self._glyphs: Dict[str, _MockGlyph] = {}
        self._gpos_lookups: List[str] = []
        self._pos_subs: Dict[str, List] = {}

        # Populate with a small Latin alphabet.
        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz":
            self._glyphs[ch] = _MockGlyph(name=ch)

    # Iteration
    def __iter__(self):
        return iter(self._glyphs)

    def __contains__(self, name):
        return name in self._glyphs

    def __getitem__(self, name):
        return self._glyphs[name]

    # Lookup API stubs
    @property
    def gpos_lookups(self):
        return self._gpos_lookups

    @property
    def gsub_lookups(self):
        return []

    def getLookupInfo(self, name):
        return ("gpos_pair",)

    def getLookupSubtables(self, lookup):
        return []

    def addLookup(self, name, *args, **kwargs):
        self._gpos_lookups.append(name)

    def addLookupSubtable(self, lookup, subtable):
        pass

    def autoKern(self, subtable, em):
        pass


# ---------------------------------------------------------------------------
# Unit tests — no fontforge dependency
# ---------------------------------------------------------------------------


class TestMetricsCore(unittest.TestCase):
    """Tests for aifont.core.metrics functions using the mock font."""

    def setUp(self):
        from aifont.core.metrics import (
            analyze_spacing,
            auto_kern,
            auto_space,
            get_kern_pairs,
            get_side_bearings,
            set_kern,
            set_side_bearings,
        )
        self.font = _MockFont()
        self.analyze_spacing = analyze_spacing
        self.auto_kern = auto_kern
        self.auto_space = auto_space
        self.get_kern_pairs = get_kern_pairs
        self.get_side_bearings = get_side_bearings
        self.set_kern = set_kern
        self.set_side_bearings = set_side_bearings

    # --- get_side_bearings ---

    def test_get_side_bearings_returns_correct_values(self):
        sb = self.get_side_bearings(self.font, "A")
        self.assertIsNotNone(sb)
        self.assertEqual(sb.glyph_name, "A")
        # bbox = (50, -200, 450, 700), width = 500  -> lsb=50, rsb=50
        self.assertEqual(sb.lsb, 50)
        self.assertEqual(sb.rsb, 50)

    def test_get_side_bearings_missing_glyph_returns_none(self):
        sb = self.get_side_bearings(self.font, "nonexistent_glyph_xyz")
        self.assertIsNone(sb)

    # --- set_side_bearings ---

    def test_set_side_bearings_updates_width(self):
        result = self.set_side_bearings(self.font, "A", lsb=80, rsb=80)
        self.assertTrue(result)
        glyph = self.font["A"]
        self.assertEqual(glyph.left_side_bearing, 80)
        self.assertEqual(glyph.right_side_bearing, 80)

    def test_set_side_bearings_only_rsb(self):
        result = self.set_side_bearings(self.font, "B", rsb=100)
        self.assertTrue(result)
        self.assertEqual(self.font["B"].right_side_bearing, 100)

    def test_set_side_bearings_missing_glyph_returns_false(self):
        result = self.set_side_bearings(self.font, "no_such_glyph", lsb=10)
        self.assertFalse(result)

    # --- auto_space ---

    def test_auto_space_returns_count(self):
        n = self.auto_space(self.font, target_ratio=0.15)
        self.assertGreater(n, 0)
        self.assertLessEqual(n, len(self.font._glyphs))

    # --- get_kern_pairs ---

    def test_get_kern_pairs_returns_list(self):
        pairs = self.get_kern_pairs(self.font)
        self.assertIsInstance(pairs, list)

    # --- set_kern ---

    def test_set_kern_creates_lookup(self):
        self.set_kern(self.font, "A", "V", -50)
        self.assertIn("aifont-kern-lookup", self.font._gpos_lookups)

    # --- analyze_spacing ---

    def test_analyze_spacing_returns_analysis(self):
        from aifont.core.metrics import SpacingAnalysis
        analysis = self.analyze_spacing(self.font)
        self.assertIsInstance(analysis, SpacingAnalysis)
        self.assertEqual(analysis.glyph_count, len(self.font._glyphs))
        self.assertGreater(analysis.avg_lsb, 0)

    def test_analyze_spacing_no_kern_suggestion(self):
        analysis = self.analyze_spacing(self.font)
        # Mock font has no kern pairs and >10 glyphs → should suggest AutoKern
        suggestions_combined = " ".join(analysis.suggestions).lower()
        self.assertIn("autokern", suggestions_combined)

    # --- auto_kern ---

    def test_auto_kern_returns_list(self):
        pairs = self.auto_kern(self.font, threshold=0)
        self.assertIsInstance(pairs, list)


# ---------------------------------------------------------------------------
# Unit tests for MetricsAgent
# ---------------------------------------------------------------------------


class TestMetricsAgent(unittest.TestCase):
    """Tests for aifont.agents.MetricsAgent using the mock font."""

    def setUp(self):
        from aifont.agents.metrics_agent import MetricsAgent
        self.MetricsAgent = MetricsAgent
        self.font = _MockFont()

    def test_default_instantiation(self):
        agent = self.MetricsAgent()
        self.assertEqual(agent.style_intent, "")
        self.assertTrue(agent.apply_autospace)
        self.assertTrue(agent.apply_autokern)

    def test_style_intent_airy(self):
        agent = self.MetricsAgent(style_intent="airy")
        self.assertAlmostEqual(agent._target_ratio, 0.20)

    def test_style_intent_tight(self):
        agent = self.MetricsAgent(style_intent="tight")
        self.assertAlmostEqual(agent._target_ratio, 0.08)

    def test_style_intent_unknown_uses_default(self):
        agent = self.MetricsAgent(style_intent="fancyunknown")
        self.assertAlmostEqual(agent._target_ratio, 0.15)

    def test_analyze_spacing_tool(self):
        from aifont.core.metrics import SpacingAnalysis
        agent = self.MetricsAgent()
        result = agent.analyze_spacing(self.font)
        self.assertIsInstance(result, SpacingAnalysis)

    def test_auto_space_tool(self):
        agent = self.MetricsAgent()
        n = agent.auto_space(self.font)
        self.assertIsInstance(n, int)

    def test_set_kern_pair_tool(self):
        agent = self.MetricsAgent()
        agent.set_kern_pair(self.font, "A", "V", -60)
        self.assertIn("aifont-kern-lookup", self.font._gpos_lookups)

    def test_set_side_bearings_tool(self):
        agent = self.MetricsAgent()
        result = agent.set_side_bearings(self.font, "C", lsb=60, rsb=60)
        self.assertTrue(result)

    def test_generate_report_structure(self):
        from aifont.agents.metrics_agent import GlyphMetricsSnapshot, MetricsReport
        from aifont.core.metrics import KernPair, SpacingAnalysis

        agent = self.MetricsAgent()
        before = SpacingAnalysis(glyph_count=52, kern_pair_count=0, avg_lsb=50.0, avg_rsb=50.0)
        after = SpacingAnalysis(glyph_count=52, kern_pair_count=10, avg_lsb=50.0, avg_rsb=50.0)
        kern_pairs = [KernPair("A", "V", -60)]
        snapshots = [GlyphMetricsSnapshot("A", 60, 60, 500)]
        corrections = ["AutoSpace applied", "AutoKern applied"]

        report = agent.generate_report(
            self.font,
            before=before,
            after=after,
            kern_pairs_added=kern_pairs,
            sidebearings_changed=snapshots,
            corrections_applied=corrections,
        )

        self.assertIsInstance(report, MetricsReport)
        self.assertEqual(report.font_name, "MockFont-Regular")
        self.assertEqual(len(report.kern_pairs_added), 1)
        self.assertEqual(len(report.corrections_applied), 2)
        self.assertIn("MockFont-Regular", report.summary)
        self.assertIn("+10", report.summary)

    def test_generate_report_to_dict(self):
        from aifont.agents.metrics_agent import MetricsReport
        from aifont.core.metrics import SpacingAnalysis

        agent = self.MetricsAgent()
        before = SpacingAnalysis(glyph_count=52)
        after = SpacingAnalysis(glyph_count=52, kern_pair_count=5)
        report = agent.generate_report(
            self.font,
            before=before,
            after=after,
            kern_pairs_added=[],
            sidebearings_changed=[],
            corrections_applied=["test correction"],
        )
        d = report.to_dict()
        self.assertIn("font_name", d)
        self.assertIn("before", d)
        self.assertIn("after", d)
        self.assertIn("corrections_applied", d)
        self.assertEqual(d["corrections_applied"], ["test correction"])

    def test_run_pipeline_returns_report(self):
        from aifont.agents.metrics_agent import MetricsReport

        agent = self.MetricsAgent()
        report = agent.run(self.font)
        self.assertIsInstance(report, MetricsReport)
        self.assertIsNotNone(report.before)
        self.assertIsNotNone(report.after)
        self.assertGreater(len(report.corrections_applied), 0)

    def test_run_pipeline_no_autospace(self):
        from aifont.agents.metrics_agent import MetricsReport

        agent = self.MetricsAgent(apply_autospace=False, apply_autokern=False)
        report = agent.run(self.font)
        self.assertIsInstance(report, MetricsReport)
        # No corrections should have been applied.
        self.assertEqual(len(report.corrections_applied), 0)

    def test_run_pipeline_applies_autospace_correction(self):
        agent = self.MetricsAgent(apply_autospace=True, apply_autokern=False)
        report = agent.run(self.font)
        autospace_corrections = [c for c in report.corrections_applied if "AutoSpace" in c]
        self.assertTrue(autospace_corrections)

    def test_run_pipeline_applies_autokern_correction(self):
        agent = self.MetricsAgent(apply_autospace=False, apply_autokern=True)
        report = agent.run(self.font)
        # AutoKern may produce 0 pairs on mock font — just check no exception raised
        self.assertIsNotNone(report)


# ---------------------------------------------------------------------------
# Integration tests — require fontforge Python bindings
# ---------------------------------------------------------------------------


class TestMetricsAgentIntegration(unittest.TestCase):
    """
    Integration tests that run against a real fontforge font.
    Skipped automatically when fontforge is not installed.
    """

    @classmethod
    def setUpClass(cls):
        try:
            import fontforge
            # Verify the Python bindings are functional (not just a stub module).
            if not hasattr(fontforge, "open"):
                raise unittest.SkipTest("fontforge Python bindings not fully available")
            cls.fontforge = fontforge
        except ImportError:
            raise unittest.SkipTest("fontforge Python bindings not available")

    def _open_reference_font(self, name: str):
        """Open a font from the tests/fonts directory."""
        import os
        fonts_dir = os.path.join(os.path.dirname(__file__), "fonts")
        path = os.path.join(fonts_dir, name)
        if not os.path.exists(path):
            self.skipTest(f"Reference font '{name}' not found at {path}")
        return self.fontforge.open(path)

    def test_integration_ambrosia(self):
        """Full pipeline on Ambrosia.sfd reference font."""
        from aifont.agents.metrics_agent import MetricsAgent, MetricsReport

        font = self._open_reference_font("Ambrosia.sfd")
        try:
            agent = MetricsAgent(style_intent="text", apply_autospace=True, apply_autokern=True)
            report = agent.run(font)
            self.assertIsInstance(report, MetricsReport)
            self.assertGreater(report.before.glyph_count, 0)
            self.assertIsNotNone(report.after)
            self.assertIsNotNone(report.summary)
        finally:
            font.close()

    def test_integration_analyze_only(self):
        """AnalyzeSpacing tool on Ambrosia.sfd — no modifications."""
        from aifont.agents.metrics_agent import MetricsAgent
        from aifont.core.metrics import SpacingAnalysis

        font = self._open_reference_font("Ambrosia.sfd")
        try:
            agent = MetricsAgent(apply_autospace=False, apply_autokern=False)
            analysis = agent.analyze_spacing(font)
            self.assertIsInstance(analysis, SpacingAnalysis)
            self.assertGreater(analysis.glyph_count, 0)
        finally:
            font.close()

    def test_integration_set_kern_pair(self):
        """SetKernPair tool on Ambrosia.sfd."""
        from aifont.agents.metrics_agent import MetricsAgent

        font = self._open_reference_font("Ambrosia.sfd")
        try:
            agent = MetricsAgent()
            agent.set_kern_pair(font, "A", "V", -80)
            # No exception should be raised.
        finally:
            font.close()

    def test_integration_report_to_dict_serialisable(self):
        """GenerateReport output must be JSON-serialisable."""
        import json
        from aifont.agents.metrics_agent import MetricsAgent

        font = self._open_reference_font("Ambrosia.sfd")
        try:
            agent = MetricsAgent(apply_autospace=True, apply_autokern=False)
            report = agent.run(font)
            d = report.to_dict()
            # Must not raise.
            serialized = json.dumps(d)
            self.assertIn("font_name", serialized)
        finally:
            font.close()


if __name__ == "__main__":
    unittest.main()
