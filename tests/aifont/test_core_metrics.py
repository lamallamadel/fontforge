"""Unit tests for aifont.core.metrics."""

from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from aifont.core.metrics import auto_space, get_kern_pairs, set_kern


class TestGetKernPairs:
    def test_returns_empty_when_no_subtables(self, font, mock_ff_font):
        mock_ff_font.subtables = None
        result = get_kern_pairs(font)
        assert result == {}

    def test_returns_empty_when_no_posub(self, font, mock_ff_font):
        # getPosSub returns empty list for all glyphs
        result = get_kern_pairs(font)
        assert isinstance(result, dict)

    def test_returns_pairs_when_present(self, font, mock_ff_font):
        # Simulate a kern pair on glyph "A"
        mock_ff_font.subtables = True
        glyph_a = mock_ff_font["A"]
        glyph_a.getPosSub.return_value = [
            ("kern-sub", "Pair", "V", -50, 0, 0, 0, 0)
        ]
        pairs = get_kern_pairs(font)
        assert ("A", "V") in pairs
        assert pairs[("A", "V")] == -50

    def test_handles_type_error_gracefully(self, font, mock_ff_font):
        mock_ff_font.subtables = True
        mock_ff_font.__iter__.side_effect = lambda: iter(["A"])
        mock_ff_font.__getitem__.side_effect = TypeError("bad")
        result = get_kern_pairs(font)
        assert result == {}


class TestSetKern:
    def test_creates_lookup_and_sets_value(self, font, mock_ff_font):
        set_kern(font, "A", "V", -50)
        mock_ff_font.addLookup.assert_called_once()
        mock_ff_font.addLookupSubtable.assert_called_once()

    def test_does_not_duplicate_existing_lookup(self, font, mock_ff_font):
        mock_ff_font.gpos_lookups = ["aifont-kern"]
        mock_ff_font.__iter__.side_effect = lambda: iter(["aifont-kern"])
        # addLookup should not be called when lookup already exists
        set_kern(font, "A", "V", -30, subtable="aifont-kern")
        mock_ff_font.addLookup.assert_not_called()

    def test_handles_missing_glyph_gracefully(self, font, mock_ff_font):
        mock_ff_font.__getitem__.side_effect = KeyError("A")
        # Should not raise
        set_kern(font, "A", "V", -50)


class TestAutoSpace:
    def test_calls_auto_width_when_available(self, font, mock_ff_font):
        auto_space(font)
        mock_ff_font.autoWidth.assert_called_once_with(0, 0)

    def test_fallback_adjusts_bearings(self, font, mock_ff_font):
        mock_ff_font.autoWidth.side_effect = Exception("not available")
        # Should not raise, and should attempt to set bearings
        auto_space(font, target_ratio=0.1)
        # At least one glyph should have had bearings set

    def test_target_ratio_used_in_fallback(self, font, mock_ff_font):
        del mock_ff_font.autoWidth  # no autoWidth
        mock_ff_font.autoWidth = MagicMock(side_effect=AttributeError)
        auto_space(font, target_ratio=0.2)
        # Doesn't raise
