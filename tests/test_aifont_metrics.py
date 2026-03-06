"""
tests/test_aifont_metrics.py — unit tests for aifont.core.metrics.

These tests exercise the full metrics API using a minimal mock font so
that a compiled fontforge extension is NOT required to run them.

Run with::

    python -m pytest tests/test_aifont_metrics.py -v
"""

import sys
import unittest
from typing import Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Minimal mock glyph / font objects that mimic fontforge's Python API
# ---------------------------------------------------------------------------


class _MockGlyph:
    """Minimal fontforge glyph mock."""

    def __init__(self, name: str, lsb: int = 50, rsb: int = 50, width: int = 500):
        self.glyphname = name
        self.left_side_bearing = lsb
        self.right_side_bearing = rsb
        self.width = width
        # Simulated position substitution storage: list of tuples
        # (subtable, right_name, dx1, dy1, dwidth1, dheight1, dx2, dy2, dwidth2, dheight2)
        self._pos_subs: Dict[str, List[tuple]] = {}

    def addPosSub(self, subtable, partner, dx1, dy1, dwidth1, dheight1, dx2, dy2, dwidth2, dheight2):
        if subtable not in self._pos_subs:
            self._pos_subs[subtable] = []
        self._pos_subs[subtable].append(
            (subtable, partner, dx1, dy1, dwidth1, dheight1, dx2, dy2, dwidth2, dheight2)
        )

    def getPosSub(self, subtable):
        return self._pos_subs.get(subtable, [])

    def removePosSub(self, subtable, partner):
        if subtable in self._pos_subs:
            self._pos_subs[subtable] = [
                e for e in self._pos_subs[subtable] if e[1] != partner
            ]

    def autoWidth(self, separation, min_side=0, max_side=0):
        pass


class _MockFont:
    """Minimal fontforge font mock compatible with aifont.core.metrics."""

    def __init__(self):
        self.ascent = 800
        self.descent = 200
        self.os2_typolinegap = 0
        self._glyphs: Dict[str, _MockGlyph] = {}
        self._lookups: List[str] = []
        self._subtables: Dict[str, List[str]] = {}

    # --- glyph access ---

    def __contains__(self, name):
        return name in self._glyphs

    def __getitem__(self, name):
        return self._glyphs[name]

    def __iter__(self):
        return iter(self._glyphs)

    def add_glyph(self, name, **kwargs):
        self._glyphs[name] = _MockGlyph(name, **kwargs)
        return self._glyphs[name]

    # --- lookup management ---

    @property
    def lookups(self):
        return tuple(self._lookups)

    def addLookup(self, name, kind, flags, features):
        if name not in self._lookups:
            self._lookups.append(name)
            self._subtables[name] = []

    def addLookupSubtable(self, lookup, subtable):
        if lookup in self._subtables:
            if subtable not in self._subtables[lookup]:
                self._subtables[lookup].append(subtable)

    # --- auto operations ---

    def autoKern(self, subtable, separation, left=(), right=(), min_kern=-200, touching=False):
        pass

    def autoWidth(self, separation, min_side=0, max_side=0):
        pass


# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------

from aifont.core.metrics import (  # noqa: E402
    Metrics,
    _KERN_LOOKUP_NAME,
    _KERN_SUBTABLE_NAME,
    _ensure_kern_lookup,
    _unwrap,
)


# ---------------------------------------------------------------------------
# Tests: internal helpers
# ---------------------------------------------------------------------------


class TestUnwrap(unittest.TestCase):
    """Tests for the _unwrap helper."""

    def test_unwrap_plain_object(self):
        """Non-wrapper objects are returned as-is."""
        obj = object()
        self.assertIs(_unwrap(obj), obj)

    def test_unwrap_wrapper(self):
        """Objects with _ff_font attribute are unwrapped."""
        inner = MagicMock()
        wrapper = MagicMock()
        wrapper._ff_font = inner
        self.assertIs(_unwrap(wrapper), inner)


class TestEnsureKernLookup(unittest.TestCase):
    """Tests for _ensure_kern_lookup."""

    def test_creates_lookup_and_subtable(self):
        font = _MockFont()
        _ensure_kern_lookup(font)
        self.assertIn(_KERN_LOOKUP_NAME, font.lookups)
        self.assertIn(_KERN_SUBTABLE_NAME, font._subtables.get(_KERN_LOOKUP_NAME, []))

    def test_idempotent(self):
        """Calling twice must not raise or duplicate the lookup."""
        font = _MockFont()
        _ensure_kern_lookup(font)
        _ensure_kern_lookup(font)
        self.assertEqual(font.lookups.count(_KERN_LOOKUP_NAME), 1)


# ---------------------------------------------------------------------------
# Tests: Metrics class — kern pair management
# ---------------------------------------------------------------------------


class TestKernPairs(unittest.TestCase):
    """Tests for set_kern / get_kern / kern_pairs."""

    def setUp(self):
        self.font = _MockFont()
        self.font.add_glyph("A")
        self.font.add_glyph("V")
        self.font.add_glyph("W")
        self.metrics = Metrics(self.font)

    def test_set_and_get_kern(self):
        self.metrics.set_kern("A", "V", -80)
        self.assertEqual(self.metrics.get_kern("A", "V"), -80)

    def test_set_kern_positive_value(self):
        self.metrics.set_kern("V", "A", 20)
        self.assertEqual(self.metrics.get_kern("V", "A"), 20)

    def test_get_kern_missing_pair_returns_none(self):
        result = self.metrics.get_kern("A", "W")
        self.assertIsNone(result)

    def test_get_kern_missing_glyph_returns_none(self):
        result = self.metrics.get_kern("X", "A")
        self.assertIsNone(result)

    def test_set_kern_overrides_existing(self):
        self.metrics.set_kern("A", "V", -80)
        self.metrics.set_kern("A", "V", -50)
        self.assertEqual(self.metrics.get_kern("A", "V"), -50)

    def test_set_kern_missing_left_glyph_raises(self):
        with self.assertRaises(KeyError):
            self.metrics.set_kern("Z", "A", -10)

    def test_set_kern_missing_right_glyph_raises(self):
        with self.assertRaises(KeyError):
            self.metrics.set_kern("A", "Z", -10)

    def test_kern_pairs_empty_initially(self):
        self.assertEqual(self.metrics.kern_pairs(), {})

    def test_kern_pairs_returns_all(self):
        self.metrics.set_kern("A", "V", -80)
        self.metrics.set_kern("V", "A", -30)
        pairs = self.metrics.kern_pairs()
        self.assertEqual(pairs[("A", "V")], -80)
        self.assertEqual(pairs[("V", "A")], -30)

    def test_zero_kern_value(self):
        self.metrics.set_kern("A", "V", 0)
        self.assertEqual(self.metrics.get_kern("A", "V"), 0)

    def test_set_kern_creates_lookup(self):
        self.metrics.set_kern("A", "V", -10)
        self.assertIn(_KERN_LOOKUP_NAME, self.font.lookups)


# ---------------------------------------------------------------------------
# Tests: auto operations
# ---------------------------------------------------------------------------


class TestAutoOperations(unittest.TestCase):
    """Tests for auto_kern and auto_space."""

    def setUp(self):
        self.font = _MockFont()
        self.font.add_glyph("A")
        self.font.add_glyph("V")
        self.metrics = Metrics(self.font)

    def test_auto_kern_does_not_raise(self):
        self.metrics.auto_kern()

    def test_auto_kern_with_custom_separation(self):
        self.metrics.auto_kern(separation=10, min_kern=-100)

    def test_auto_space_does_not_raise(self):
        self.metrics.auto_space()

    def test_auto_space_with_params(self):
        self.metrics.auto_space(separation=80, min_side=10, max_side=200)


# ---------------------------------------------------------------------------
# Tests: side bearings
# ---------------------------------------------------------------------------


class TestSideBearings(unittest.TestCase):
    """Tests for set_sidebearings / get_sidebearings."""

    def setUp(self):
        self.font = _MockFont()
        self.font.add_glyph("A", lsb=50, rsb=50)
        self.metrics = Metrics(self.font)

    def test_get_sidebearings(self):
        lsb, rsb = self.metrics.get_sidebearings("A")
        self.assertEqual(lsb, 50)
        self.assertEqual(rsb, 50)

    def test_set_left_bearing(self):
        self.metrics.set_sidebearings("A", left=30)
        lsb, rsb = self.metrics.get_sidebearings("A")
        self.assertEqual(lsb, 30)
        self.assertEqual(rsb, 50)  # unchanged

    def test_set_right_bearing(self):
        self.metrics.set_sidebearings("A", right=70)
        lsb, rsb = self.metrics.get_sidebearings("A")
        self.assertEqual(lsb, 50)  # unchanged
        self.assertEqual(rsb, 70)

    def test_set_both_bearings(self):
        self.metrics.set_sidebearings("A", left=20, right=80)
        lsb, rsb = self.metrics.get_sidebearings("A")
        self.assertEqual(lsb, 20)
        self.assertEqual(rsb, 80)

    def test_set_sidebearings_missing_glyph_raises(self):
        with self.assertRaises(KeyError):
            self.metrics.set_sidebearings("Z", left=10)

    def test_get_sidebearings_missing_glyph_raises(self):
        with self.assertRaises(KeyError):
            self.metrics.get_sidebearings("Z")

    def test_set_zero_bearing(self):
        self.metrics.set_sidebearings("A", left=0, right=0)
        lsb, rsb = self.metrics.get_sidebearings("A")
        self.assertEqual(lsb, 0)
        self.assertEqual(rsb, 0)


# ---------------------------------------------------------------------------
# Tests: line metrics
# ---------------------------------------------------------------------------


class TestLineMetrics(unittest.TestCase):
    """Tests for ascent, descent, and line_gap properties."""

    def setUp(self):
        self.font = _MockFont()
        self.metrics = Metrics(self.font)

    def test_ascent_read(self):
        self.assertEqual(self.metrics.ascent, 800)

    def test_descent_read(self):
        self.assertEqual(self.metrics.descent, 200)

    def test_line_gap_read(self):
        self.assertEqual(self.metrics.line_gap, 0)

    def test_ascent_write(self):
        self.metrics.ascent = 900
        self.assertEqual(self.font.ascent, 900)
        self.assertEqual(self.metrics.ascent, 900)

    def test_descent_write(self):
        self.metrics.descent = 300
        self.assertEqual(self.font.descent, 300)
        self.assertEqual(self.metrics.descent, 300)

    def test_line_gap_write(self):
        self.metrics.line_gap = 50
        self.assertEqual(self.font.os2_typolinegap, 50)
        self.assertEqual(self.metrics.line_gap, 50)

    def test_line_gap_fallback_attribute(self):
        """line_gap falls back to os2_linegap when os2_typolinegap absent."""
        del self.font.os2_typolinegap
        self.font.os2_linegap = 100
        self.assertEqual(self.metrics.line_gap, 100)

    def test_line_gap_no_attribute_returns_zero(self):
        """line_gap returns 0 when neither OS/2 attribute exists."""
        del self.font.os2_typolinegap
        self.assertEqual(self.metrics.line_gap, 0)


# ---------------------------------------------------------------------------
# Tests: report()
# ---------------------------------------------------------------------------


class TestReport(unittest.TestCase):
    """Tests for Metrics.report()."""

    def setUp(self):
        self.font = _MockFont()
        self.font.add_glyph("A", lsb=40, rsb=60)
        self.font.add_glyph("V", lsb=30, rsb=30)
        self.metrics = Metrics(self.font)

    def test_report_returns_dict(self):
        report = self.metrics.report()
        self.assertIsInstance(report, dict)

    def test_report_has_required_keys(self):
        report = self.metrics.report()
        self.assertIn("line_metrics", report)
        self.assertIn("kern_pairs", report)
        self.assertIn("glyph_sidebearings", report)

    def test_report_line_metrics_values(self):
        report = self.metrics.report()
        lm = report["line_metrics"]
        self.assertEqual(lm["ascent"], 800)
        self.assertEqual(lm["descent"], 200)
        self.assertEqual(lm["units_per_em"], 1000)
        self.assertEqual(lm["line_gap"], 0)

    def test_report_kern_pairs_empty(self):
        report = self.metrics.report()
        self.assertEqual(report["kern_pairs"], [])

    def test_report_kern_pairs_after_set(self):
        self.metrics.set_kern("A", "V", -80)
        report = self.metrics.report()
        pairs = report["kern_pairs"]
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["left"], "A")
        self.assertEqual(pairs[0]["right"], "V")
        self.assertEqual(pairs[0]["value"], -80)

    def test_report_glyph_sidebearings(self):
        report = self.metrics.report()
        bearings = report["glyph_sidebearings"]
        self.assertIn("A", bearings)
        self.assertEqual(bearings["A"]["left"], 40)
        self.assertEqual(bearings["A"]["right"], 60)
        self.assertIn("V", bearings)
        self.assertEqual(bearings["V"]["left"], 30)
        self.assertEqual(bearings["V"]["right"], 30)

    def test_report_updated_line_metrics(self):
        self.metrics.ascent = 900
        self.metrics.descent = 100
        self.metrics.line_gap = 20
        report = self.metrics.report()
        lm = report["line_metrics"]
        self.assertEqual(lm["ascent"], 900)
        self.assertEqual(lm["descent"], 100)
        self.assertEqual(lm["units_per_em"], 1000)
        self.assertEqual(lm["line_gap"], 20)


# ---------------------------------------------------------------------------
# Tests: wrapper unwrapping
# ---------------------------------------------------------------------------


class TestFontWrapper(unittest.TestCase):
    """Metrics must accept both raw fontforge fonts and aifont wrappers."""

    def test_accepts_wrapper_with_ff_font(self):
        inner = _MockFont()
        inner.add_glyph("A")
        wrapper = MagicMock()
        wrapper._ff_font = inner
        metrics = Metrics(wrapper)
        self.assertEqual(metrics.ascent, 800)

    def test_accepts_raw_font(self):
        raw = _MockFont()
        raw.add_glyph("A")
        metrics = Metrics(raw)
        self.assertEqual(metrics.ascent, 800)


# ---------------------------------------------------------------------------
# Tests: auto_kern fallback (older fontforge API)
# ---------------------------------------------------------------------------


class TestAutoKernFallback(unittest.TestCase):
    """auto_kern must degrade gracefully on older fontforge builds."""

    def test_auto_kern_short_signature_fallback(self):
        font = _MockFont()

        def short_autoKern(subtable, separation):
            pass  # old-style API

        font.autoKern = short_autoKern
        metrics = Metrics(font)
        # Should not raise even though the full signature is not supported.
        metrics.auto_kern()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
