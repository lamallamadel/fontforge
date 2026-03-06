"""
tests/test_style_agent.py — unit tests for aifont.agents.StyleAgent.

These tests use mock fontforge objects so that no real FontForge
installation is required.  All tests exercise the StyleAgent tools through
the aifont.core layer.

Test coverage
-------------
- StyleProfile dataclass / summary()
- analyze_style() with mock font
- _detect_intent() prompt dispatcher
- StyleAgent.apply_stroke()
- StyleAgent.apply_slant() (with and without optical corrections)
- StyleAgent.transform_glyph()
- StyleAgent.interpolate_style()
- StyleAgent.transfer_style()
- StyleAgent.run() prompt-based dispatch
- StyleTransferResult.summary()
- Contour helpers: apply_stroke, apply_slant, transform, scale, translate,
  simplify, remove_overlap
"""

from __future__ import annotations

import math
import unittest
from typing import List, Optional, Tuple
from unittest.mock import MagicMock, call, patch


# ---------------------------------------------------------------------------
# Mock helpers — replace fontforge glyph / font without installing fontforge
# ---------------------------------------------------------------------------


class _MockGlyphRaw:
    """Minimal stand-in for a ``fontforge.glyph``."""

    def __init__(self, name: str = "A", width: int = 600) -> None:
        self.glyphname = name
        self.unicode = ord(name[0]) if name else -1
        self.width = width
        self.left_side_bearing = 50
        self.right_side_bearing = 50
        self._transform_calls: List[tuple] = []
        self._change_weight_calls: List[tuple] = []
        self._remove_overlap_count = 0
        self._simplify_calls: List[tuple] = []

    def boundingBox(self):
        return (50.0, 0.0, 550.0, 700.0)

    def transform(self, matrix):
        self._transform_calls.append(matrix)

    def changeWeight(self, *args):
        self._change_weight_calls.append(args)

    def removeOverlap(self):
        self._remove_overlap_count += 1

    def simplify(self, threshold=1.0):
        self._simplify_calls.append((threshold,))


class _MockFontRaw:
    """Minimal stand-in for a ``fontforge.font``."""

    def __init__(self, family: str = "TestFont") -> None:
        self.familyname = family
        self.fontname = family.replace(" ", "-")
        self.em = 1000
        self.italicangle = 0.0
        self.ascent = 800
        self.descent = 200
        self._glyphs: dict = {}

    def __iter__(self):
        return iter(self._glyphs)

    def __getitem__(self, key):
        return self._glyphs[key]

    def add_glyph(self, name: str, width: int = 600):
        self._glyphs[name] = _MockGlyphRaw(name, width)
        return self._glyphs[name]


def _make_font(family: str = "TestFont", add_glyphs: bool = True) -> "Font":
    """Return a :class:`Font` wrapping a :class:`_MockFontRaw`."""
    from aifont.core.font import Font

    ff = _MockFontRaw(family)
    if add_glyphs:
        for name in "AaBbCcDdEeHhIiOoXx":
            ff.add_glyph(name)
    return Font(ff)


# ---------------------------------------------------------------------------
# Tests: StyleProfile
# ---------------------------------------------------------------------------


class TestStyleProfile(unittest.TestCase):
    def test_defaults(self):
        from aifont.core.analyzer import StyleProfile

        sp = StyleProfile()
        self.assertEqual(sp.stroke_width, 0.0)
        self.assertEqual(sp.weight_class, 400)
        self.assertFalse(sp.has_serifs)
        self.assertEqual(sp.glyph_count, 0)
        self.assertEqual(sp.notes, [])

    def test_summary_upright(self):
        from aifont.core.analyzer import StyleProfile

        sp = StyleProfile(
            weight_class=700,
            has_serifs=False,
            italic_angle=0.0,
            stroke_width=130.0,
            stroke_contrast=0.4,
            x_height=500.0,
        )
        s = sp.summary()
        self.assertIn("700", s)
        self.assertIn("sans-serif", s)
        self.assertNotIn("italic", s)

    def test_summary_italic(self):
        from aifont.core.analyzer import StyleProfile

        sp = StyleProfile(
            weight_class=400,
            has_serifs=True,
            italic_angle=12.0,
            stroke_width=80.0,
            stroke_contrast=0.6,
            x_height=450.0,
        )
        s = sp.summary()
        self.assertIn("serif", s)
        self.assertIn("italic", s)
        self.assertIn("12.0", s)


# ---------------------------------------------------------------------------
# Tests: analyze_style
# ---------------------------------------------------------------------------


class TestAnalyzeStyle(unittest.TestCase):
    def test_basic_analysis(self):
        from aifont.core.analyzer import analyze_style

        font = _make_font("TestSans")
        profile = analyze_style(font)

        self.assertIsInstance(profile.stroke_width, float)
        self.assertGreater(profile.stroke_width, 0)
        self.assertEqual(profile.em_size, 1000)
        self.assertEqual(profile.italic_angle, 0.0)
        self.assertFalse(profile.has_serifs)

    def test_glyph_count(self):
        from aifont.core.analyzer import analyze_style

        font = _make_font("TestSans", add_glyphs=True)
        profile = analyze_style(font)
        # Our mock font adds 18 glyph names (len("AaBbCcDdEeHhIiOoXx"))
        self.assertEqual(profile.glyph_count, 18)

    def test_italic_font_detected(self):
        from aifont.core.analyzer import analyze_style

        font = _make_font("TestSans")
        font.raw.italicangle = 12.0
        profile = analyze_style(font)
        self.assertAlmostEqual(profile.italic_angle, 12.0)
        self.assertTrue(any("italic" in n.lower() for n in profile.notes))

    def test_serif_detection_by_name(self):
        from aifont.core.analyzer import analyze_style

        serif_font = _make_font("Times Roman")
        profile = analyze_style(serif_font)
        self.assertTrue(profile.has_serifs)

    def test_sans_detection_by_name(self):
        from aifont.core.analyzer import analyze_style

        sans_font = _make_font("Helvetica Sans")
        profile = analyze_style(sans_font)
        self.assertFalse(profile.has_serifs)

    def test_weight_class_range(self):
        from aifont.core.analyzer import StyleProfile, analyze_style

        font = _make_font("TestFont")
        profile = analyze_style(font)
        self.assertIn(profile.weight_class, range(100, 1000, 100))

    def test_empty_font(self):
        from aifont.core.analyzer import analyze_style

        font = _make_font("Empty", add_glyphs=False)
        profile = analyze_style(font)
        self.assertEqual(profile.glyph_count, 0)
        # Should still return a valid profile with em-based fallbacks
        self.assertGreater(profile.x_height, 0)
        self.assertGreater(profile.stroke_width, 0)


# ---------------------------------------------------------------------------
# Tests: _detect_intent
# ---------------------------------------------------------------------------


class TestDetectIntent(unittest.TestCase):
    def _detect(self, prompt):
        from aifont.agents.style_agent import _detect_intent

        return _detect_intent(prompt)

    def test_bold_english(self):
        self.assertEqual(self._detect("Make this font more bold"), "bold")

    def test_bold_french(self):
        self.assertEqual(self._detect("Rends ça plus gras"), "bold")

    def test_bold_heavy(self):
        self.assertEqual(self._detect("I want a heavy typeface"), "bold")

    def test_light_english(self):
        self.assertEqual(self._detect("Make this thinner"), "light")

    def test_light_french(self):
        self.assertEqual(self._detect("Rends ça plus léger"), "light")

    def test_italic_english(self):
        self.assertEqual(self._detect("Apply an italic style"), "italic")

    def test_italic_slant(self):
        self.assertEqual(self._detect("Slant this font by 12 degrees"), "italic")

    def test_vintage(self):
        self.assertEqual(self._detect("Make it more vintage"), "vintage")

    def test_retro(self):
        self.assertEqual(self._detect("I want a retro look"), "vintage")

    def test_transfer(self):
        self.assertEqual(self._detect("Inspire from the style of Futura"), "transfer")

    def test_unknown(self):
        self.assertEqual(self._detect("Something completely different"), "unknown")

    def test_case_insensitive(self):
        self.assertEqual(self._detect("MAKE IT BOLD"), "bold")


# ---------------------------------------------------------------------------
# Tests: contour helpers
# ---------------------------------------------------------------------------


class TestContourHelpers(unittest.TestCase):
    def _make_glyph(self, name="A") -> "Glyph":
        from aifont.core.glyph import Glyph

        return Glyph(_MockGlyphRaw(name))

    def test_transform_called(self):
        from aifont.core import contour

        g = self._make_glyph()
        matrix = (1.0, 0.0, 0.0, 1.0, 10.0, 20.0)
        contour.transform(g, matrix)
        self.assertEqual(g.raw._transform_calls, [matrix])

    def test_remove_overlap(self):
        from aifont.core import contour

        g = self._make_glyph()
        contour.remove_overlap(g)
        self.assertEqual(g.raw._remove_overlap_count, 1)

    def test_simplify(self):
        from aifont.core import contour

        g = self._make_glyph()
        contour.simplify(g, threshold=2.0)
        self.assertEqual(g.raw._simplify_calls, [(2.0,)])

    def test_apply_stroke(self):
        from aifont.core import contour

        g = self._make_glyph()
        contour.apply_stroke(g, 30.0)
        self.assertTrue(len(g.raw._change_weight_calls) > 0)
        # First arg of first call should be the stroke width
        self.assertEqual(g.raw._change_weight_calls[0][0], 30.0)

    def test_apply_stroke_fallback_one_arg(self):
        """changeWeight with join_type raising TypeError → fallback to 1-arg."""
        from aifont.core import contour
        from aifont.core.glyph import Glyph

        raw = _MockGlyphRaw()

        call_log = []

        def change_weight_strict(*args):
            if len(args) > 1:
                raise TypeError("only 1 arg allowed")
            call_log.append(args)

        raw.changeWeight = change_weight_strict
        g = Glyph(raw)
        contour.apply_stroke(g, 40.0)
        # The fallback (1-arg) path should have been used
        self.assertEqual(call_log, [(40.0,)])

    def test_apply_slant_matrix(self):
        """apply_slant should produce a shear transform with tan(angle)."""
        from aifont.core import contour

        g = self._make_glyph()
        angle = 12.0
        contour.apply_slant(g, angle_deg=angle)
        self.assertEqual(len(g.raw._transform_calls), 1)
        matrix = g.raw._transform_calls[0]
        # xx=1, xy=0, yx=tan(12°), yy=1, dx=0, dy=0
        expected_shear = math.tan(math.radians(angle))
        self.assertAlmostEqual(matrix[0], 1.0, places=6)
        self.assertAlmostEqual(matrix[1], 0.0, places=6)
        self.assertAlmostEqual(matrix[2], expected_shear, places=6)
        self.assertAlmostEqual(matrix[3], 1.0, places=6)
        self.assertAlmostEqual(matrix[4], 0.0, places=6)
        self.assertAlmostEqual(matrix[5], 0.0, places=6)

    def test_apply_slant_x_origin(self):
        """Non-zero x_origin should produce a non-zero dx component."""
        from aifont.core import contour

        g = self._make_glyph()
        contour.apply_slant(g, angle_deg=10.0, x_origin=100.0)
        matrix = g.raw._transform_calls[0]
        shear = math.tan(math.radians(10.0))
        self.assertAlmostEqual(matrix[4], -100.0 * shear, places=5)

    def test_scale(self):
        from aifont.core import contour

        g = self._make_glyph()
        contour.scale(g, 0.8, 0.9)
        self.assertEqual(g.raw._transform_calls, [(0.8, 0.0, 0.0, 0.9, 0.0, 0.0)])

    def test_translate(self):
        from aifont.core import contour

        g = self._make_glyph()
        contour.translate(g, 50.0, -30.0)
        self.assertEqual(g.raw._transform_calls, [(1.0, 0.0, 0.0, 1.0, 50.0, -30.0)])


# ---------------------------------------------------------------------------
# Tests: StyleAgent
# ---------------------------------------------------------------------------


class TestStyleAgentInit(unittest.TestCase):
    def test_defaults(self):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        self.assertEqual(agent.default_stroke_delta, 30.0)
        self.assertEqual(agent.default_slant_angle, 12.0)
        self.assertTrue(agent.optical_corrections)

    def test_custom_params(self):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent(
            default_stroke_delta=50.0,
            default_slant_angle=8.0,
            optical_corrections=False,
        )
        self.assertEqual(agent.default_stroke_delta, 50.0)
        self.assertEqual(agent.default_slant_angle, 8.0)
        self.assertFalse(agent.optical_corrections)


class TestStyleAgentAnalyzeStyle(unittest.TestCase):
    def test_returns_profile(self):
        from aifont.agents.style_agent import StyleAgent
        from aifont.core.analyzer import StyleProfile

        agent = StyleAgent()
        font = _make_font()
        profile = agent.analyze_style(font)
        self.assertIsInstance(profile, StyleProfile)
        self.assertEqual(profile.em_size, 1000)


class TestStyleAgentApplyStroke(unittest.TestCase):
    def test_bold_applies_stroke(self):
        from aifont.agents.style_agent import StyleAgent, StyleTransferResult

        agent = StyleAgent()
        font = _make_font()
        result = agent.apply_stroke(font, stroke_width=40.0)

        self.assertIsInstance(result, StyleTransferResult)
        self.assertIs(result.font, font)
        self.assertIsNotNone(result.before_profile)
        self.assertIsNotNone(result.after_profile)
        # Check that at least one glyph had changeWeight called
        changed = [
            g
            for g in font.raw._glyphs.values()
            if len(g._change_weight_calls) > 0
        ]
        self.assertGreater(len(changed), 0)

    def test_change_log_contains_direction(self):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.apply_stroke(_make_font(), stroke_width=30.0)
        self.assertTrue(any("expanded" in c for c in result.changes_applied))

    def test_light_applies_negative_stroke(self):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        font = _make_font()
        result = agent.apply_stroke(font, stroke_width=-20.0)
        self.assertTrue(any("contracted" in c for c in result.changes_applied))

    def test_selective_glyphs(self):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        font = _make_font()
        result = agent.apply_stroke(font, stroke_width=30.0, glyph_names=["A", "B"])
        changed = [
            name
            for name, g in font.raw._glyphs.items()
            if len(g._change_weight_calls) > 0
        ]
        # Only "A" and "B" (if present) should be changed
        for name in changed:
            self.assertIn(name, ["A", "B"])


class TestStyleAgentApplySlant(unittest.TestCase):
    def test_slant_applies_transform(self):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        font = _make_font()
        result = agent.apply_slant(font, angle=12.0)

        slanted = [
            g
            for g in font.raw._glyphs.values()
            if len(g._transform_calls) > 0
        ]
        self.assertGreater(len(slanted), 0)

    def test_slant_updates_font_metadata(self):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        font = _make_font()
        agent.apply_slant(font, angle=12.0)
        self.assertAlmostEqual(font.italic_angle, 12.0)

    def test_slant_log_contains_angle(self):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.apply_slant(_make_font(), angle=10.0)
        self.assertTrue(any("10.0" in c for c in result.changes_applied))

    def test_optical_corrections_add_extra_transform(self):
        """With optical corrections each glyph gets 2 transforms: shear + scale."""
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent(optical_corrections=True)
        font = _make_font()
        agent.apply_slant(font, angle=12.0, optical_corrections=True)

        for g in font.raw._glyphs.values():
            # shear transform + optical correction transform = 2
            self.assertEqual(len(g._transform_calls), 2)

    def test_no_optical_corrections(self):
        """Without optical corrections each glyph gets exactly 1 transform."""
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent(optical_corrections=False)
        font = _make_font()
        agent.apply_slant(font, angle=12.0, optical_corrections=False)

        for g in font.raw._glyphs.values():
            self.assertEqual(len(g._transform_calls), 1)


class TestStyleAgentTransformGlyph(unittest.TestCase):
    def test_transform_applied_to_all(self):
        from aifont.agents.style_agent import StyleAgent

        matrix = (0.9, 0.0, 0.0, 1.0, 0.0, 0.0)
        agent = StyleAgent()
        font = _make_font()
        result = agent.transform_glyph(font, matrix)
        for g in font.raw._glyphs.values():
            self.assertIn(matrix, g._transform_calls)

    def test_transform_selective(self):
        from aifont.agents.style_agent import StyleAgent

        matrix = (0.9, 0.0, 0.0, 1.0, 0.0, 0.0)
        agent = StyleAgent()
        font = _make_font()
        agent.transform_glyph(font, matrix, glyph_names=["A"])
        # "A" should be transformed
        self.assertIn(matrix, font.raw._glyphs["A"]._transform_calls)
        # "B" (if present) should not be transformed
        if "B" in font.raw._glyphs:
            self.assertNotIn(matrix, font.raw._glyphs["B"]._transform_calls)

    def test_result_log(self):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        result = agent.transform_glyph(_make_font(), matrix)
        self.assertTrue(any("TransformGlyph" in c for c in result.changes_applied))


class TestStyleAgentInterpolate(unittest.TestCase):
    def test_factor_clamped(self):
        """Factor > 1 should be clamped to 1.0."""
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        target = _make_font("TargetFont")
        reference = _make_font("BoldFont")
        # Increase reference stroke to force interpolation
        reference.raw._glyphs.setdefault("o", _MockGlyphRaw("o"))
        # Should not raise
        result = agent.interpolate_style(target, reference, factor=2.0)
        self.assertIsNotNone(result)

    def test_zero_factor_unchanged(self):
        """With factor=0 no stroke changes should be applied."""
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        target = _make_font("TargetFont")
        reference = _make_font("ReferenceFont")
        result = agent.interpolate_style(target, reference, factor=0.0)
        self.assertIsNotNone(result)
        # No stroke expansion should have occurred (delta = 0 * something)
        for g in target.raw._glyphs.values():
            self.assertEqual(len(g._change_weight_calls), 0)

    def test_result_header(self):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.interpolate_style(_make_font(), _make_font("Ref"), factor=0.5)
        self.assertTrue(any("InterpolateStyle" in c for c in result.changes_applied))


class TestStyleAgentTransferStyle(unittest.TestCase):
    def test_transfer_returns_result(self):
        from aifont.agents.style_agent import StyleAgent, StyleTransferResult

        agent = StyleAgent()
        target = _make_font("Target")
        reference = _make_font("Reference")
        result = agent.transfer_style(target, reference)
        self.assertIsInstance(result, StyleTransferResult)
        self.assertTrue(any("TransferStyle" in c for c in result.changes_applied))


# ---------------------------------------------------------------------------
# Tests: StyleAgent.run() prompt dispatcher
# ---------------------------------------------------------------------------


class TestStyleAgentRun(unittest.TestCase):
    def test_run_bold(self):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        font = _make_font()
        result = agent.run("Make this font more bold", font)
        self.assertTrue(any("expanded" in c for c in result.changes_applied))

    def test_run_light(self):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        font = _make_font()
        result = agent.run("Make this font thinner", font)
        self.assertTrue(any("contracted" in c for c in result.changes_applied))

    def test_run_italic(self):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        font = _make_font()
        result = agent.run("Apply italic style", font)
        self.assertTrue(any("ApplySlant" in c for c in result.changes_applied))

    def test_run_vintage(self):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        font = _make_font()
        result = agent.run("Make it more vintage", font)
        self.assertTrue(any("Vintage" in c or "vintage" in c for c in result.changes_applied))

    def test_run_transfer_requires_reference(self):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        font = _make_font()
        with self.assertRaises(ValueError):
            agent.run("Inspire from Futura style", font)

    def test_run_transfer_with_reference(self):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        target = _make_font("Target")
        ref = _make_font("Futura")
        result = agent.run("Inspire from Futura style", target, reference_font=ref)
        self.assertIsNotNone(result)

    def test_run_unknown_prompt(self):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        font = _make_font()
        result = agent.run("Do something totally unrecognized", font)
        self.assertTrue(
            any("Unknown" in c or "unknown" in c or "No changes" in c
                for c in result.changes_applied)
        )

    def test_run_stroke_width_override(self):
        """Custom stroke_width in run() should override agent default."""
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent(default_stroke_delta=30.0)
        font = _make_font()
        agent.run("Bold", font, stroke_width=80.0)
        # First glyph should have been expanded by 80, not 30
        for g in font.raw._glyphs.values():
            if g._change_weight_calls:
                self.assertEqual(g._change_weight_calls[0][0], 80.0)
                break

    def test_run_returns_before_after_profiles(self):
        from aifont.agents.style_agent import StyleAgent
        from aifont.core.analyzer import StyleProfile

        agent = StyleAgent()
        font = _make_font()
        result = agent.run("Make this font more bold", font)
        self.assertIsInstance(result.before_profile, StyleProfile)
        self.assertIsInstance(result.after_profile, StyleProfile)


# ---------------------------------------------------------------------------
# Tests: StyleTransferResult
# ---------------------------------------------------------------------------


class TestStyleTransferResult(unittest.TestCase):
    def test_summary_contains_changes(self):
        from aifont.agents.style_agent import StyleTransferResult
        from aifont.core.analyzer import StyleProfile

        result = StyleTransferResult(
            font=_make_font(),
            changes_applied=["ApplyStroke: expanded 5 glyph(s)", "  ⚠ Skipped X"],
            before_profile=StyleProfile(weight_class=400),
            after_profile=StyleProfile(weight_class=700),
        )
        s = result.summary()
        self.assertIn("ApplyStroke", s)
        self.assertIn("Before", s)
        self.assertIn("After", s)

    def test_summary_no_profiles(self):
        from aifont.agents.style_agent import StyleTransferResult

        result = StyleTransferResult(
            font=_make_font(),
            changes_applied=["some change"],
        )
        s = result.summary()
        self.assertIn("some change", s)
        self.assertNotIn("Before", s)


# ---------------------------------------------------------------------------
# Tests: before/after comparison
# ---------------------------------------------------------------------------


class TestBeforeAfterComparison(unittest.TestCase):
    """Verify that after applying a stroke the weight class can increase."""

    def test_bold_increases_weight_estimate(self):
        """After a large boldification the weight_class should not decrease."""
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        font = _make_font()
        # We patch analyze_style to simulate the before/after difference
        # because our mock doesn't actually change point coordinates.
        from aifont.core import analyzer as _analyzer
        from aifont.core.analyzer import StyleProfile

        call_count = [0]
        profiles = [
            StyleProfile(stroke_width=80.0, weight_class=400),
            StyleProfile(stroke_width=130.0, weight_class=700),
        ]

        original_analyze = _analyzer.analyze_style

        def fake_analyze(f):
            idx = min(call_count[0], len(profiles) - 1)
            call_count[0] += 1
            return profiles[idx]

        _analyzer.analyze_style = fake_analyze
        try:
            result = agent.apply_stroke(font, stroke_width=50.0)
        finally:
            _analyzer.analyze_style = original_analyze

        self.assertLessEqual(
            result.before_profile.weight_class,
            result.after_profile.weight_class,
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
