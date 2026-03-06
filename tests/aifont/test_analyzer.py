"""
Unit tests for aifont.core.analyzer.
"""

from __future__ import annotations

import pytest

try:
    import fontforge as _ff
    _FF = hasattr(_ff, "font")
except ImportError:
    _FF = False

from aifont.core.analyzer import FontAnalyzer, FontReport, GlyphIssue, analyze
from aifont.core.font import Font


def test_analyzer_module_importable():
    assert FontAnalyzer is not None
    assert FontReport is not None
    assert analyze is not None


def test_font_report_defaults():
    report = FontReport()
    assert report.glyph_count == 0
    assert report.unicode_coverage == 0.0
    assert report.missing_unicodes == []
    assert report.kern_pair_count == 0
    assert report.open_contours == []
    assert report.issues == []
    assert report.passed is True


def test_font_report_str():
    report = FontReport(glyph_count=26, unicode_coverage=1.0)
    text = str(report)
    assert "26" in text
    assert "FontReport" in text


def test_glyph_issue_fields():
    issue = GlyphIssue(glyph_name="A", issue_type="open_contour", description="open")
    assert issue.glyph_name == "A"
    assert issue.issue_type == "open_contour"


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_analyze_empty_font():
    font = Font.new()
    report = analyze(font)
    assert isinstance(report, FontReport)
    assert report.glyph_count == 0
    assert report.unicode_coverage == 0.0
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_analyze_font_with_glyphs():
    font = Font.new()
    font.create_glyph("A", 0x0041)
    font.create_glyph("B", 0x0042)
    font.create_glyph("nomap", -1)

    report = analyze(font)
    assert report.glyph_count >= 2
    # "nomap" should show up as missing a unicode
    assert "nomap" in report.missing_unicodes
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_font_analyzer_run():
    font = Font.new()
    analyzer = FontAnalyzer(font)
    report = analyzer.run()
    assert isinstance(report, FontReport)
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_analyze_returns_font_report():
    font = Font.new()
    result = analyze(font)
    assert isinstance(result, FontReport)
    font.close()
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
        assert report.passed is True

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
        assert report.passed is False

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
