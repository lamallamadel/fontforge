"""
Unit tests for aifont.core.analyzer.
"""

import pytest

_fontforge = pytest.importorskip("fontforge")
if not hasattr(_fontforge, "font"):
    pytest.skip("fontforge C extension not available", allow_module_level=True)

from aifont.core.analyzer import FontReport, GlyphIssue, analyze  # noqa: E402
from aifont.core.font import Font  # noqa: E402


def _minimal_font() -> Font:
    """Return a minimal font with a few glyphs."""
    font = Font.new()
    font.metadata.family_name = "AnalyzerTest"
    font.create_glyph(32, "space").set_width(250)
    font.create_glyph(65, "A").set_width(700)
    font.create_glyph(66, "B").set_width(700)
    return font


# ---------------------------------------------------------------------------
# FontReport dataclass
# ---------------------------------------------------------------------------


class TestFontReport:
    def test_passed_when_no_issues(self):
        report = FontReport(
            family_name="Test",
            glyph_count=1,
            unicode_coverage=1,
            missing_basic_latin=[],
            kern_pair_count=0,
            issues=[],
            validation_score=1.0,
            metrics_summary={},
        )
        assert report.passed() is True

    def test_not_passed_when_issues(self):
        issue = GlyphIssue("A", "open_contour", "Contour is not closed")
        report = FontReport(
            family_name="Test",
            glyph_count=1,
            unicode_coverage=1,
            missing_basic_latin=[],
            kern_pair_count=0,
            issues=[issue],
            validation_score=0.9,
            metrics_summary={},
        )
        assert report.passed() is False

    def test_issues_by_type(self):
        i1 = GlyphIssue("A", "open_contour", "msg")
        i2 = GlyphIssue("B", "wrong_direction", "msg")
        report = FontReport(
            family_name="Test",
            glyph_count=2,
            unicode_coverage=2,
            missing_basic_latin=[],
            kern_pair_count=0,
            issues=[i1, i2],
            validation_score=0.8,
            metrics_summary={},
        )
        assert report.issues_by_type("open_contour") == [i1]
        assert report.issues_by_type("wrong_direction") == [i2]
        assert report.issues_by_type("overlap") == []

    def test_str_representation(self):
        report = FontReport(
            family_name="MyFont",
            glyph_count=10,
            unicode_coverage=8,
            missing_basic_latin=[65, 66],
            kern_pair_count=5,
            issues=[],
            validation_score=1.0,
            metrics_summary={},
        )
        text = str(report)
        assert "MyFont" in text
        assert "10" in text


# ---------------------------------------------------------------------------
# analyze() function
# ---------------------------------------------------------------------------


class TestAnalyze:
    def test_returns_font_report(self):
        font = _minimal_font()
        report = analyze(font)
        assert isinstance(report, FontReport)

    def test_glyph_count_matches(self):
        font = _minimal_font()
        report = analyze(font)
        assert report.glyph_count == len(font)

    def test_family_name_matches(self):
        font = _minimal_font()
        report = analyze(font)
        assert report.family_name == "AnalyzerTest"

    def test_unicode_coverage_non_negative(self):
        font = _minimal_font()
        report = analyze(font)
        assert report.unicode_coverage >= 0

    def test_missing_basic_latin_is_list(self):
        font = _minimal_font()
        report = analyze(font)
        assert isinstance(report.missing_basic_latin, list)

    def test_missing_basic_latin_populated_for_minimal_font(self):
        font = _minimal_font()
        report = analyze(font)
        # Minimal font only has 3 glyphs → many Basic Latin chars missing
        assert len(report.missing_basic_latin) > 0

    def test_validation_score_between_0_and_1(self):
        font = _minimal_font()
        report = analyze(font)
        assert 0.0 <= report.validation_score <= 1.0

    def test_issues_is_list(self):
        font = _minimal_font()
        report = analyze(font)
        assert isinstance(report.issues, list)

    def test_metrics_summary_has_em_size(self):
        font = _minimal_font()
        report = analyze(font)
        assert "em_size" in report.metrics_summary

    def test_empty_font_glyph_count_zero(self):
        font = Font.new()
        report = analyze(font)
        assert report.glyph_count == 0

    def test_kern_pair_count_non_negative(self):
        font = _minimal_font()
        report = analyze(font)
        assert report.kern_pair_count >= 0
