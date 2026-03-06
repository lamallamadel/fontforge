"""Tests for aifont.core.analyzer.

These tests use open-source reference fonts that ship with the FontForge test
suite (located in tests/fonts/).  They validate every acceptance criterion
listed in the Font Analyzer issue:

  - Global metrics (ascent, descent, units_per_em)
  - Glyph count and glyph list
  - Unicode coverage (percentage of Basic Latin, etc.)
  - Basic problem detection
  - Simple quality score (0–100)
  - Exportable report (dict / JSON)
"""

import json
import os
import unittest

# ---------------------------------------------------------------------------
# Resolve the path to the test font directory relative to this file.
# The tests/ directory lives one level above aifont/.
# ---------------------------------------------------------------------------

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))
_FONTS_DIR = os.path.join(_REPO_ROOT, "tests", "fonts")
_AMBROSIA_SFD = os.path.join(_FONTS_DIR, "Ambrosia.sfd")
_DEJAVU_SFD = os.path.join(_FONTS_DIR, "DejaVuSerif.sfd")
_NOTO_TTF = os.path.join(_FONTS_DIR, "NotoSerifTibetan-Regular.ttf")


def _fontforge_available() -> bool:
    """Return True only when the fontforge C extension is fully loaded."""
    try:
        import fontforge as _ff

        return callable(getattr(_ff, "open", None))
    except Exception:
        return False


def _skip_if_missing(path: str):
    """Return a skip decorator when *path* does not exist or fontforge is unavailable."""
    font_present = os.path.exists(path)
    ff_present = _fontforge_available()
    if not font_present:
        return unittest.skip(f"Font not found: {path}")
    if not ff_present:
        return unittest.skip("fontforge C extension not available (bindings not compiled)")
    return lambda fn: fn  # no-op decorator


class TestAnalyzerWithAmbrosia(unittest.TestCase):
    """Full analysis pipeline tested against Ambrosia.sfd (open-source)."""

    @classmethod
    @_skip_if_missing(_AMBROSIA_SFD)
    def setUpClass(cls):
        from aifont.core.analyzer import analyze

        cls.report = analyze(_AMBROSIA_SFD)

    # ------------------------------------------------------------------
    # Global metrics
    # ------------------------------------------------------------------

    def test_global_metrics_ascent_positive(self):
        self.assertGreater(self.report.global_metrics.ascent, 0)

    def test_global_metrics_units_per_em_positive(self):
        upm = self.report.global_metrics.units_per_em
        self.assertGreater(upm, 0)

    def test_global_metrics_descent_stored(self):
        # descent may be positive or zero (FontForge stores it as positive)
        self.assertIsInstance(self.report.global_metrics.descent, int)

    def test_global_metrics_family_name_string(self):
        self.assertIsInstance(self.report.global_metrics.family_name, str)

    # ------------------------------------------------------------------
    # Glyph count and list
    # ------------------------------------------------------------------

    def test_glyph_count_positive(self):
        self.assertGreater(self.report.glyph_count, 0)

    def test_glyphs_list_length_matches_count(self):
        self.assertEqual(len(self.report.glyphs), self.report.glyph_count)

    def test_each_glyph_has_name(self):
        for glyph in self.report.glyphs:
            self.assertIsInstance(glyph.name, str)
            self.assertTrue(len(glyph.name) > 0)

    def test_each_glyph_has_width(self):
        for glyph in self.report.glyphs:
            self.assertIsInstance(glyph.width, int)

    # ------------------------------------------------------------------
    # Unicode coverage
    # ------------------------------------------------------------------

    def test_unicode_coverage_list_not_empty(self):
        self.assertGreater(len(self.report.unicode_coverage), 0)

    def test_unicode_coverage_basic_latin_present(self):
        names = [c.block_name for c in self.report.unicode_coverage]
        self.assertIn("Basic Latin", names)

    def test_unicode_coverage_percent_in_range(self):
        for block in self.report.unicode_coverage:
            self.assertGreaterEqual(block.coverage_percent, 0.0)
            self.assertLessEqual(block.coverage_percent, 100.0)

    def test_unicode_coverage_covered_le_block_size(self):
        for block in self.report.unicode_coverage:
            self.assertLessEqual(block.covered, block.block_size)

    # ------------------------------------------------------------------
    # Problem detection
    # ------------------------------------------------------------------

    def test_problems_is_list(self):
        self.assertIsInstance(self.report.problems, list)

    def test_each_problem_has_severity(self):
        for problem in self.report.problems:
            self.assertIn(problem.severity, ("error", "warning", "info"))

    def test_each_problem_has_description(self):
        for problem in self.report.problems:
            self.assertIsInstance(problem.description, str)
            self.assertTrue(len(problem.description) > 0)

    # ------------------------------------------------------------------
    # Quality score
    # ------------------------------------------------------------------

    def test_quality_score_in_range(self):
        self.assertGreaterEqual(self.report.quality_score, 0.0)
        self.assertLessEqual(self.report.quality_score, 100.0)

    def test_quality_score_is_float(self):
        self.assertIsInstance(self.report.quality_score, float)

    # ------------------------------------------------------------------
    # Exportable report — dict / JSON
    # ------------------------------------------------------------------

    def test_to_dict_returns_dict(self):
        d = self.report.to_dict()
        self.assertIsInstance(d, dict)

    def test_to_dict_contains_required_keys(self):
        d = self.report.to_dict()
        for key in (
            "font_path",
            "global_metrics",
            "glyph_count",
            "glyphs",
            "unicode_coverage",
            "problems",
            "quality_score",
        ):
            self.assertIn(key, d)

    def test_to_dict_global_metrics_keys(self):
        m = self.report.to_dict()["global_metrics"]
        for key in ("ascent", "descent", "units_per_em", "family_name"):
            self.assertIn(key, m)

    def test_to_json_valid_json(self):
        j = self.report.to_json()
        parsed = json.loads(j)
        self.assertIsInstance(parsed, dict)

    def test_to_json_roundtrip(self):
        d1 = self.report.to_dict()
        d2 = json.loads(self.report.to_json())
        self.assertEqual(d1, d2)

    def test_save_json(self):
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as fh:
            tmp_path = fh.name
        try:
            self.report.save_json(tmp_path)
            self.assertTrue(os.path.exists(tmp_path))
            with open(tmp_path, encoding="utf-8") as fh:
                parsed = json.load(fh)
            self.assertIsInstance(parsed, dict)
            self.assertIn("quality_score", parsed)
        finally:
            os.unlink(tmp_path)


class TestAnalyzerWithDejaVu(unittest.TestCase):
    """Sanity checks against DejaVuSerif.sfd (open-source reference font)."""

    @classmethod
    @_skip_if_missing(_DEJAVU_SFD)
    def setUpClass(cls):
        from aifont.core.analyzer import analyze

        cls.report = analyze(_DEJAVU_SFD)

    def test_glyph_count_reasonable(self):
        # DejaVu Serif has hundreds of glyphs
        self.assertGreater(self.report.glyph_count, 10)

    def test_quality_score_non_zero(self):
        self.assertGreater(self.report.quality_score, 0.0)

    def test_latin_coverage_non_zero(self):
        basic_latin = next(
            (c for c in self.report.unicode_coverage if c.block_name == "Basic Latin"),
            None,
        )
        self.assertIsNotNone(basic_latin)
        self.assertGreater(basic_latin.coverage_percent, 0.0)


class TestAnalyzerWithNotoTTF(unittest.TestCase):
    """Verify the analyzer works with a binary TTF (NotoSerifTibetan)."""

    @classmethod
    @_skip_if_missing(_NOTO_TTF)
    def setUpClass(cls):
        from aifont.core.analyzer import analyze

        cls.report = analyze(_NOTO_TTF)

    def test_glyph_count_positive(self):
        self.assertGreater(self.report.glyph_count, 0)

    def test_report_serializes_to_json(self):
        j = self.report.to_json()
        self.assertIsInstance(json.loads(j), dict)


class TestAnalyzerUnitMetrics(unittest.TestCase):
    """Unit tests for quality score calculation logic (no font file needed)."""

    def _make_report(
        self,
        ascent=800,
        descent=200,
        cap_height=700,
        x_height=500,
        latin_coverage_fraction=1.0,
        problems=None,
    ):
        """Build a minimal FontReport programmatically for score testing."""
        from aifont.core.analyzer import (
            FontAnalyzer,
            GlobalMetrics,
            GlyphInfo,
        )

        metrics = GlobalMetrics(
            ascent=ascent,
            descent=descent,
            units_per_em=ascent + descent,
            cap_height=cap_height,
            x_height=x_height,
            italic_angle=0.0,
            underline_position=-100,
            underline_width=50,
            family_name="Test",
            full_name="Test Regular",
            weight="Regular",
            version="1.0",
            copyright="",
            is_fixed_pitch=False,
            sf_version="",
        )

        # Build a synthetic glyph list covering exactly `latin_coverage_fraction`
        # of the printable Basic Latin block (U+0020–U+007E).
        basic_latin = list(range(0x0020, 0x007F))
        n = int(len(basic_latin) * latin_coverage_fraction)
        glyphs = [
            GlyphInfo(name=f"uni{cp:04X}", unicode_value=cp, width=600, has_contours=True)
            for cp in basic_latin[:n]
        ]

        # Compute coverage using the same logic as the real analyser.
        analyzer = FontAnalyzer.__new__(FontAnalyzer)
        analyzer._compute_unicode_coverage(glyphs)

        probs = problems or []
        score = analyzer._compute_quality_score(metrics, glyphs, probs)
        return score

    def test_perfect_latin_coverage_gives_high_score(self):
        score = self._make_report(latin_coverage_fraction=1.0, problems=[])
        # Full coverage + sane metrics + no problems → expect ≥ 90
        self.assertGreaterEqual(score, 90.0)

    def test_no_latin_coverage_reduces_score(self):
        score_full = self._make_report(latin_coverage_fraction=1.0, problems=[])
        score_empty = self._make_report(latin_coverage_fraction=0.0, problems=[])
        self.assertGreater(score_full, score_empty)

    def test_errors_reduce_score(self):
        from aifont.core.analyzer import BasicProblem

        score_clean = self._make_report(problems=[])
        errors = [
            BasicProblem(severity="error", glyph_name=None, description="x") for _ in range(5)
        ]
        score_with_errors = self._make_report(problems=errors)
        self.assertGreater(score_clean, score_with_errors)

    def test_score_capped_at_100(self):
        score = self._make_report(
            latin_coverage_fraction=1.0,
            problems=[],
        )
        self.assertLessEqual(score, 100.0)

    def test_score_not_negative(self):
        from aifont.core.analyzer import BasicProblem

        many_errors = [
            BasicProblem(severity="error", glyph_name=None, description="x") for _ in range(100)
        ]
        score = self._make_report(problems=many_errors)
        self.assertGreaterEqual(score, 0.0)


if __name__ == "__main__":
    unittest.main()
