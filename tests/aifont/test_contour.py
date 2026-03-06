"""
Unit tests for aifont.core.contour.
"""

import pytest

_fontforge = pytest.importorskip("fontforge")
if not hasattr(_fontforge, "font"):
    pytest.skip("fontforge C extension not available", allow_module_level=True)

from aifont.core.contour import (  # noqa: E402
    add_extrema,
    auto_hint,
    correct_direction,
    remove_overlap,
    reverse_direction,
    round_to_int,
    simplify,
    transform,
)
from aifont.core.font import Font  # noqa: E402


def _empty_glyph(unicode_val: int = 65, name: str = "A"):
    font = Font.new()
    return font.create_glyph(unicode_val, name)


# ---------------------------------------------------------------------------
# simplify
# ---------------------------------------------------------------------------


class TestSimplify:
    def test_does_not_raise_on_empty_glyph(self):
        g = _empty_glyph()
        simplify(g)  # should not raise

    def test_does_not_raise_with_threshold(self):
        g = _empty_glyph()
        simplify(g, threshold=2.0)


# ---------------------------------------------------------------------------
# remove_overlap
# ---------------------------------------------------------------------------


class TestRemoveOverlap:
    def test_does_not_raise_on_empty_glyph(self):
        g = _empty_glyph()
        remove_overlap(g)


# ---------------------------------------------------------------------------
# transform
# ---------------------------------------------------------------------------


class TestTransform:
    def test_identity_transform_does_not_raise(self):
        g = _empty_glyph()
        identity = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        transform(g, identity)

    def test_translation_transform_does_not_raise(self):
        g = _empty_glyph()
        translate_50 = (1.0, 0.0, 0.0, 1.0, 50.0, 0.0)
        transform(g, translate_50)

    def test_invalid_matrix_length_raises_value_error(self):
        g = _empty_glyph()
        with pytest.raises(ValueError):
            transform(g, (1.0, 0.0, 0.0))  # type: ignore[arg-type]

    def test_scale_matrix_does_not_raise(self):
        g = _empty_glyph()
        scale_half = (0.5, 0.0, 0.0, 0.5, 0.0, 0.0)
        transform(g, scale_half)


# ---------------------------------------------------------------------------
# reverse_direction
# ---------------------------------------------------------------------------


class TestReverseDirection:
    def test_does_not_raise(self):
        g = _empty_glyph()
        reverse_direction(g)


# ---------------------------------------------------------------------------
# correct_direction
# ---------------------------------------------------------------------------


class TestCorrectDirection:
    def test_does_not_raise(self):
        g = _empty_glyph()
        correct_direction(g)


# ---------------------------------------------------------------------------
# add_extrema
# ---------------------------------------------------------------------------


class TestAddExtrema:
    def test_does_not_raise(self):
        g = _empty_glyph()
        add_extrema(g)


# ---------------------------------------------------------------------------
# round_to_int
# ---------------------------------------------------------------------------


class TestRoundToInt:
    def test_does_not_raise(self):
        g = _empty_glyph()
        round_to_int(g)


# ---------------------------------------------------------------------------
# auto_hint
# ---------------------------------------------------------------------------


class TestAutoHint:
    def test_does_not_raise(self):
        g = _empty_glyph()
        auto_hint(g)
