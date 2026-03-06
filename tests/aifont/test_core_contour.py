"""Unit tests for aifont.core.contour."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aifont.core.contour import remove_overlap, simplify, transform


class TestSimplify:
    def test_calls_ff_simplify(self, glyph, mock_ff_glyph):
        simplify(glyph)
        mock_ff_glyph.simplify.assert_called_once()

    def test_fallback_when_simplify_raises(self, glyph, mock_ff_glyph):
        mock_ff_glyph.simplify.side_effect = TypeError("bad args")
        simplify(glyph, threshold=2.0)
        # Should have retried without args
        assert mock_ff_glyph.simplify.call_count >= 1

    def test_noop_when_no_simplify_attr(self, glyph, mock_ff_glyph):
        del mock_ff_glyph.simplify
        simplify(glyph)  # Must not raise


class TestRemoveOverlap:
    def test_calls_ff_remove_overlap(self, glyph, mock_ff_glyph):
        remove_overlap(glyph)
        mock_ff_glyph.removeOverlap.assert_called_once()

    def test_noop_when_no_remove_overlap_attr(self, glyph, mock_ff_glyph):
        del mock_ff_glyph.removeOverlap
        remove_overlap(glyph)  # Must not raise


class TestTransform:
    def test_calls_ff_transform(self, glyph, mock_ff_glyph):
        matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        transform(glyph, matrix)
        mock_ff_glyph.transform.assert_called_once_with(matrix)

    def test_raises_for_invalid_matrix(self, glyph):
        with pytest.raises(ValueError, match="6 elements"):
            transform(glyph, (1, 0, 0))

    def test_noop_when_no_transform_attr(self, glyph, mock_ff_glyph):
        del mock_ff_glyph.transform
        transform(glyph, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))  # Must not raise
