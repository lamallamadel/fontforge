"""
Unit tests for aifont.core.glyph.
"""

import pytest

_fontforge = pytest.importorskip("fontforge")
if not hasattr(_fontforge, "font"):
    pytest.skip("fontforge C extension not available", allow_module_level=True)

from aifont.core.font import Font  # noqa: E402
from aifont.core.glyph import Glyph  # noqa: E402


def _make_glyph(unicode_val: int = 65, name: str = "A") -> Glyph:
    """Helper: create a fresh font and return a single Glyph."""
    font = Font.new()
    return font.create_glyph(unicode_val, name)


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


class TestGlyphIdentity:
    def test_name(self):
        g = _make_glyph(65, "A")
        assert g.name == "A"

    def test_set_name(self):
        g = _make_glyph(65, "A")
        g.name = "A.alt"
        assert g.name == "A.alt"

    def test_unicode_value(self):
        g = _make_glyph(65, "A")
        assert g.unicode_value == 65

    def test_set_unicode_value(self):
        g = _make_glyph(65, "A")
        g.unicode_value = 97  # 'a'
        assert g.unicode_value == 97

    def test_unassigned_unicode_is_negative(self):
        font = Font.new()
        g = font.create_glyph(-1, "noUnicode")
        assert g.unicode_value < 0


# ---------------------------------------------------------------------------
# Width & bearings
# ---------------------------------------------------------------------------


class TestGlyphMetrics:
    def test_width_default_non_negative(self):
        g = _make_glyph()
        assert g.width >= 0

    def test_set_width(self):
        g = _make_glyph()
        g.set_width(600)
        assert g.width == 600

    def test_width_setter(self):
        g = _make_glyph()
        g.width = 700
        assert g.width == 700

    def test_left_side_bearing_readable(self):
        g = _make_glyph()
        # Empty glyph: lsb may be 0
        assert isinstance(g.left_side_bearing, int)

    def test_right_side_bearing_readable(self):
        g = _make_glyph()
        assert isinstance(g.right_side_bearing, int)

    def test_vwidth_readable(self):
        g = _make_glyph()
        assert isinstance(g.vwidth, int)


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------


class TestGlyphBoundingBox:
    def test_bounding_box_returns_four_floats(self):
        g = _make_glyph()
        bb = g.bounding_box
        assert len(bb) == 4
        assert all(isinstance(v, float) for v in bb)

    def test_empty_glyph_bounding_box_zeros(self):
        g = _make_glyph()
        bb = g.bounding_box
        # Empty glyph has no outline → all zeros
        assert bb == (0.0, 0.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# Contour access
# ---------------------------------------------------------------------------


class TestGlyphContours:
    def test_contours_property_accessible(self):
        g = _make_glyph()
        # Should not raise
        _ = g.contours

    def test_background_property_accessible(self):
        g = _make_glyph()
        _ = g.background


# ---------------------------------------------------------------------------
# Convenience operations
# ---------------------------------------------------------------------------


class TestGlyphOperations:
    def test_clear_does_not_raise(self):
        g = _make_glyph()
        g.clear()  # Should not raise

    def test_validate_returns_int(self):
        g = _make_glyph()
        result = g.validate()
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# ff_glyph
# ---------------------------------------------------------------------------


class TestGlyphFFAccess:
    def test_ff_glyph_not_none(self):
        g = _make_glyph()
        assert g.ff_glyph is not None


# ---------------------------------------------------------------------------
# Equality and hashing
# ---------------------------------------------------------------------------


class TestGlyphEquality:
    def test_same_ff_object_equal(self):
        font = Font.new()
        font.create_glyph(65, "A")
        g1 = font["A"]
        g2 = font["A"]
        assert g1 == g2

    def test_different_glyphs_not_equal(self):
        font = Font.new()
        font.create_glyph(65, "A")
        font.create_glyph(66, "B")
        assert font["A"] != font["B"]

    def test_glyph_hashable(self):
        g = _make_glyph()
        s = {g}
        assert g in s

    def test_not_equal_to_non_glyph(self):
        g = _make_glyph()
        assert g.__eq__("A") is NotImplemented
