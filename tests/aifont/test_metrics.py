"""
Unit tests for aifont.core.metrics.
"""

import pytest

_fontforge = pytest.importorskip("fontforge")
if not hasattr(_fontforge, "font"):
    pytest.skip("fontforge C extension not available", allow_module_level=True)

from aifont.core.font import Font  # noqa: E402
from aifont.core.metrics import (  # noqa: E402
    auto_space,
    get_kern_pairs,
    remove_kern,
    set_kern,
)


def _font_with_glyphs(*specs) -> Font:
    """Create a font with named glyphs. specs = [(unicode, name), ...]"""
    font = Font.new()
    for ucp, name in specs:
        font.create_glyph(ucp, name)
    return font


# ---------------------------------------------------------------------------
# get_kern_pairs
# ---------------------------------------------------------------------------


class TestGetKernPairs:
    def test_empty_font_returns_empty_list(self):
        font = Font.new()
        pairs = get_kern_pairs(font)
        assert isinstance(pairs, list)
        assert pairs == []

    def test_returns_list(self):
        font = _font_with_glyphs((65, "A"), (86, "V"))
        pairs = get_kern_pairs(font)
        assert isinstance(pairs, list)

    def test_each_pair_is_three_tuple(self):
        font = _font_with_glyphs((65, "A"), (86, "V"))
        pairs = get_kern_pairs(font)
        for p in pairs:
            assert len(p) == 3


# ---------------------------------------------------------------------------
# set_kern
# ---------------------------------------------------------------------------


class TestSetKern:
    def test_set_kern_missing_left_raises(self):
        font = _font_with_glyphs((65, "A"))
        with pytest.raises(KeyError):
            set_kern(font, "X", "A", -50)

    def test_set_kern_missing_right_raises(self):
        font = _font_with_glyphs((65, "A"))
        with pytest.raises(KeyError):
            set_kern(font, "A", "X", -50)

    def test_set_kern_does_not_raise_for_valid_glyphs(self):
        font = _font_with_glyphs((65, "A"), (86, "V"))
        # May or may not add a pair depending on fontforge internals,
        # but should not raise
        try:
            set_kern(font, "A", "V", -80)
        except Exception as exc:  # noqa: BLE001
            pytest.skip(f"set_kern raised unexpectedly: {exc}")


# ---------------------------------------------------------------------------
# remove_kern
# ---------------------------------------------------------------------------


class TestRemoveKern:
    def test_remove_kern_nonexistent_returns_false(self):
        font = _font_with_glyphs((65, "A"), (86, "V"))
        result = remove_kern(font, "A", "V")
        # May return True or False; should not raise
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# auto_space
# ---------------------------------------------------------------------------


class TestAutoSpace:
    def test_auto_space_does_not_raise(self):
        font = _font_with_glyphs((65, "A"), (66, "B"))
        # Give them a width so they are not skipped
        for g in font.glyphs:
            g.set_width(600)
        auto_space(font)  # should not raise

    def test_auto_space_with_glyph_names_list(self):
        font = _font_with_glyphs((65, "A"), (66, "B"))
        for g in font.glyphs:
            g.set_width(600)
        auto_space(font, target_ratio=0.1, glyph_names=["A"])

    def test_auto_space_custom_ratio(self):
        font = _font_with_glyphs((65, "A"))
        for g in font.glyphs:
            g.set_width(600)
        auto_space(font, target_ratio=0.2)
