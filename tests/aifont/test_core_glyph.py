"""Unit tests for aifont.core.glyph (Glyph)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aifont.core.glyph import Glyph


class TestGlyph:
    def test_name(self, glyph):
        assert glyph.name == "A"

    def test_unicode(self, glyph):
        assert glyph.unicode == 0x0041

    def test_unicode_setter(self, glyph, mock_ff_glyph):
        glyph.unicode = 0x0042
        assert mock_ff_glyph.unicode == 0x0042

    def test_width(self, glyph):
        assert glyph.width == 600

    def test_width_setter(self, glyph, mock_ff_glyph):
        glyph.width = 700
        assert mock_ff_glyph.width == 700

    def test_set_width_fluent(self, glyph, mock_ff_glyph):
        glyph.set_width(800)
        assert mock_ff_glyph.width == 800

    def test_left_side_bearing(self, glyph):
        assert glyph.left_side_bearing == 60

    def test_left_side_bearing_setter(self, glyph, mock_ff_glyph):
        glyph.left_side_bearing = 80
        assert mock_ff_glyph.left_side_bearing == 80

    def test_right_side_bearing(self, glyph):
        assert glyph.right_side_bearing == 60

    def test_right_side_bearing_setter(self, glyph, mock_ff_glyph):
        glyph.right_side_bearing = 90
        assert mock_ff_glyph.right_side_bearing == 90

    def test_contours_empty_by_default(self, glyph):
        assert glyph.contours == []

    def test_contours_with_items(self, mock_ff_glyph):
        contour = MagicMock()
        mock_ff_glyph.foreground.__iter__ = MagicMock(
            return_value=iter([contour])
        )
        g = Glyph(mock_ff_glyph)
        assert len(g.contours) == 1

    def test_contours_no_foreground(self):
        ff = MagicMock(spec=[])  # no attributes
        g = Glyph(ff)
        assert g.contours == []

    def test_copy_from(self, mock_ff_glyph):
        src_ff = MagicMock()
        src_ff.glyphname = "B"
        src_ff.unicode = 0x0042
        src_ff.width = 700
        src_ff.foreground = MagicMock()
        src_glyph = Glyph(src_ff)

        dst_glyph = Glyph(mock_ff_glyph)
        dst_glyph.copy_from(src_glyph)

        mock_ff_glyph.clear.assert_called_once()
        assert mock_ff_glyph.width == 700

    def test_clear(self, glyph, mock_ff_glyph):
        glyph.clear()
        mock_ff_glyph.clear.assert_called_once()

    def test_auto_hint(self, glyph, mock_ff_glyph):
        glyph.auto_hint()
        mock_ff_glyph.autoHint.assert_called_once()

    def test_repr(self, glyph):
        r = repr(glyph)
        assert "Glyph(" in r
        assert "A" in r

    def test_unicode_missing(self):
        ff = MagicMock()
        ff.glyphname = "notdef"
        del ff.unicode  # simulate missing attribute
        ff.unicode = -1
        g = Glyph(ff)
        assert g.unicode == -1

    def test_width_negative_raises(self):
        ff = MagicMock()
        ff.width = 600
        g = Glyph(ff)
        with pytest.raises(ValueError):
            g.width = -1

    def test_has_open_contours_false_when_no_foreground(self):
        ff = MagicMock(spec=[])  # no attributes at all
        g = Glyph(ff)
        assert g.has_open_contours is False

    def test_has_open_contours_all_closed(self, mock_ff_glyph):
        c1 = MagicMock()
        c1.closed = True
        c2 = MagicMock()
        c2.closed = True
        mock_ff_glyph.foreground.__iter__ = MagicMock(return_value=iter([c1, c2]))
        g = Glyph(mock_ff_glyph)
        assert g.has_open_contours is False

    def test_has_open_contours_one_open(self, mock_ff_glyph):
        c1 = MagicMock()
        c1.closed = True
        c2 = MagicMock()
        c2.closed = False
        mock_ff_glyph.foreground.__iter__ = MagicMock(return_value=iter([c1, c2]))
        g = Glyph(mock_ff_glyph)
        assert g.has_open_contours is True

    def test_has_open_contours_exception_returns_false(self, mock_ff_glyph):
        mock_ff_glyph.foreground.__iter__ = MagicMock(side_effect=RuntimeError("boom"))
        g = Glyph(mock_ff_glyph)
        assert g.has_open_contours is False

    def test_simplify_with_flags(self, glyph, mock_ff_glyph):
        result = glyph.simplify(error_bound=2.0, flags=("removeextranodes",))
        assert result is glyph
        mock_ff_glyph.simplify.assert_called_with(2.0, ("removeextranodes",))

    def test_remove_overlap(self, glyph, mock_ff_glyph):
        result = glyph.remove_overlap()
        assert result is glyph
        mock_ff_glyph.removeOverlap.assert_called_once()

    def test_correct_direction(self, glyph, mock_ff_glyph):
        result = glyph.correct_direction()
        assert result is glyph
        mock_ff_glyph.correctDirection.assert_called_once()

    def test_round_to_int(self, glyph, mock_ff_glyph):
        result = glyph.round_to_int()
        assert result is glyph
        mock_ff_glyph.round.assert_called_once()

    def test_transform(self, glyph, mock_ff_glyph):
        matrix = (1, 0, 0, 1, 10, 20)
        result = glyph.transform(matrix)
        assert result is glyph
        mock_ff_glyph.transform.assert_called_with(matrix)
