"""Unit tests for aifont.core.analyzer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aifont.core.analyzer import FontReport, GlyphIssue, analyze


class TestGlyphIssue:
    def test_defaults(self):
        issue = GlyphIssue(glyph_name="A", code="TEST", description="desc")
        assert issue.severity == "warning"

    def test_custom_severity(self):
        issue = GlyphIssue(
            glyph_name="A", code="X", description="d", severity="error"
        )
        assert issue.severity == "error"


class TestFontReport:
    def test_defaults(self):
        r = FontReport()
        assert r.glyph_count == 0
        assert r.missing_unicode == []
        assert r.issues == []
        assert r.coverage_score == 0.0

    def test_error_count(self):
        r = FontReport(
            issues=[
                GlyphIssue("A", "E", "d", "error"),
                GlyphIssue("B", "W", "d", "warning"),
            ]
        )
        assert r.error_count == 1
        assert r.warning_count == 1

    def test_passed_no_errors(self):
        r = FontReport(issues=[GlyphIssue("A", "W", "d", "warning")])
        assert r.passed is True

    def test_passed_with_errors(self):
        r = FontReport(issues=[GlyphIssue("A", "E", "d", "error")])
        assert r.passed is False


class TestAnalyze:
    def test_returns_font_report(self, font):
        result = analyze(font)
        assert isinstance(result, FontReport)

    def test_glyph_count_set(self, font):
        result = analyze(font)
        assert result.glyph_count == 3

    def test_coverage_score_full_unicode(self, font):
        # All mock glyphs have unicode values
        result = analyze(font)
        assert result.coverage_score > 0

    def test_missing_unicode_detected(self, font, mock_ff_font):
        # Make glyph "B" have no unicode
        mock_ff_font["B"].unicode = -1
        result = analyze(font)
        assert "B" in result.missing_unicode

    def test_empty_glyph_warning(self, font, mock_ff_font):
        # Give glyph "A" a unicode but empty foreground
        glyph_a = mock_ff_font["A"]
        glyph_a.foreground.__iter__ = MagicMock(return_value=iter([]))
        result = analyze(font)
        codes = [i.code for i in result.issues]
        assert "EMPTY_GLYPH" in codes

    def test_kern_pair_count(self, font):
        result = analyze(font)
        assert result.kern_pair_count >= 0

    def test_zero_glyph_count_coverage(self, mock_ff_font):
        from aifont.core.font import Font

        mock_ff_font.__iter__ = MagicMock(return_value=iter([]))
        font_empty = Font(mock_ff_font)
        result = analyze(font_empty)
        assert result.coverage_score == 0.0
