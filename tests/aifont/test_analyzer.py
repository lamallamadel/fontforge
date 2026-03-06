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
    assert report.passed() is True


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
