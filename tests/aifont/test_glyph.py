"""
Unit tests for aifont.core.glyph.
"""

from __future__ import annotations

import pytest

try:
    import fontforge as _ff
    _FF = hasattr(_ff, "font")
except ImportError:
    _FF = False

from aifont.core.font import Font
from aifont.core.glyph import Glyph


def test_glyph_module_importable():
    assert Glyph is not None


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_glyph_name():
    font = Font.new()
    g = font.create_glyph("TestGlyph", 0x0041)
    assert g.name == "TestGlyph"
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_glyph_unicode():
    font = Font.new()
    g = font.create_glyph("UniGlyph", 0x0042)
    assert g.unicode == 0x0042
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_glyph_width_set_get():
    font = Font.new()
    g = font.create_glyph("WideGlyph", -1)
    g.set_width(600)
    assert g.width == 600
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_glyph_width_property():
    font = Font.new()
    g = font.create_glyph("PropGlyph", -1)
    g.width = 500
    assert g.width == 500
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_glyph_repr():
    font = Font.new()
    g = font.create_glyph("ReprGlyph", -1)
    r = repr(g)
    assert "ReprGlyph" in r
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_glyph_ff_property():
    font = Font.new()
    g = font.create_glyph("FFGlyph", -1)
    assert g._ff is not None
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_glyph_clear():
    font = Font.new()
    g = font.create_glyph("ClearGlyph", -1)
    g.clear()  # Should not raise
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_glyph_bounding_box():
    font = Font.new()
    g = font.create_glyph("BBGlyph", -1)
    bb = g.bounding_box
    assert len(bb) == 4
    font.close()
