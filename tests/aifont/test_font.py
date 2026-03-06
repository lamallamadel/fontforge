"""
Unit tests for aifont.core.font.

Tests run with or without the fontforge C extension.  When fontforge is
not available, all tests that actually need it are skipped gracefully.
"""

from __future__ import annotations

import pytest

# Try to import fontforge to decide whether to skip live tests.
try:
    import fontforge as _ff
    _FF = hasattr(_ff, "font")
except ImportError:
    _FF = False

from aifont.core.font import Font


# ---------------------------------------------------------------------------
# Import-time tests (no fontforge required)
# ---------------------------------------------------------------------------


def test_font_module_importable():
    """Font class can be imported without fontforge installed."""
    assert Font is not None


# ---------------------------------------------------------------------------
# Tests that require fontforge
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_font_new_creates_instance():
    font = Font.new()
    assert isinstance(font, Font)
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_font_metadata_defaults():
    font = Font.new()
    meta = font.metadata
    assert "fontname" in meta
    assert "familyname" in meta
    assert "em" in meta
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_font_set_metadata():
    font = Font.new()
    font.set_metadata(fontname="TestFont", familyname="Test Family")
    assert font.metadata["fontname"] == "TestFont"
    assert font.metadata["familyname"] == "Test Family"
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_font_set_metadata_invalid_key():
    font = Font.new()
    with pytest.raises(ValueError, match="Unknown metadata field"):
        font.set_metadata(nonexistent_key="value")
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_font_glyphs_empty_font():
    font = Font.new()
    glyphs = font.glyphs
    assert isinstance(glyphs, list)
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_font_create_glyph():
    font = Font.new()
    g = font.create_glyph("testglyph", 0x0041)
    assert g.name == "testglyph"
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_font_repr():
    font = Font.new()
    r = repr(font)
    assert "Font" in r
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_font_iter():
    font = Font.new()
    font.create_glyph("a_glyph", 0x0041)
    names = [g.name for g in font]
    assert "a_glyph" in names
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_font_ff_property():
    font = Font.new()
    assert font._ff is not None
    font.close()
