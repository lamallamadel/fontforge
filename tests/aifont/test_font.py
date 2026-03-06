"""
Unit tests for aifont.core.font.

Tests run with FontForge available (via ``import fontforge``).
Each test is isolated and operates on in-memory font objects.
"""

import pytest

_fontforge = pytest.importorskip("fontforge")
if not hasattr(_fontforge, "font"):
    pytest.skip("fontforge C extension not available", allow_module_level=True)

from aifont.core.font import Font, FontMetadata  # noqa: E402


# ---------------------------------------------------------------------------
# Font.new()
# ---------------------------------------------------------------------------


class TestFontNew:
    def test_creates_font_instance(self):
        font = Font.new()
        assert isinstance(font, Font)

    def test_initial_glyph_count_is_zero(self):
        font = Font.new()
        assert len(font) == 0

    def test_glyphs_returns_empty_list(self):
        font = Font.new()
        assert font.glyphs == []

    def test_ff_font_attribute(self):
        font = Font.new()
        # ff_font should be a real fontforge.font object
        assert font.ff_font is not None

    def test_metadata_returns_font_metadata(self):
        font = Font.new()
        assert isinstance(font.metadata, FontMetadata)


# ---------------------------------------------------------------------------
# FontMetadata read/write
# ---------------------------------------------------------------------------


class TestFontMetadata:
    def test_set_family_name(self):
        font = Font.new()
        font.metadata.family_name = "TestFamily"
        assert font.metadata.family_name == "TestFamily"

    def test_set_full_name(self):
        font = Font.new()
        font.metadata.full_name = "TestFamily Regular"
        assert font.metadata.full_name == "TestFamily Regular"

    def test_set_weight(self):
        font = Font.new()
        font.metadata.weight = "Bold"
        assert font.metadata.weight == "Bold"

    def test_em_size_default_positive(self):
        font = Font.new()
        assert font.metadata.em_size > 0

    def test_set_em_size(self):
        font = Font.new()
        font.metadata.em_size = 2048
        assert font.metadata.em_size == 2048

    def test_ascent_default_positive(self):
        font = Font.new()
        assert font.metadata.ascent > 0

    def test_set_copyright(self):
        font = Font.new()
        font.metadata.copyright = "(c) 2024 Test"
        assert font.metadata.copyright == "(c) 2024 Test"

    def test_set_version(self):
        font = Font.new()
        font.metadata.version = "1.001"
        assert font.metadata.version == "1.001"


# ---------------------------------------------------------------------------
# Font.open() error handling
# ---------------------------------------------------------------------------


class TestFontOpen:
    def test_raises_os_error_for_missing_file(self):
        with pytest.raises(OSError):
            Font.open("/nonexistent/path/to/font.otf")


# ---------------------------------------------------------------------------
# Glyph creation and access
# ---------------------------------------------------------------------------


class TestFontGlyphAccess:
    def test_create_glyph_increases_count(self):
        font = Font.new()
        font.create_glyph(65, "A")
        assert len(font) == 1

    def test_create_glyph_returns_glyph(self):
        from aifont.core.glyph import Glyph

        font = Font.new()
        g = font.create_glyph(65, "A")
        assert isinstance(g, Glyph)

    def test_create_glyph_name_correct(self):
        font = Font.new()
        g = font.create_glyph(65, "A")
        assert g.name == "A"

    def test_create_glyph_unicode_correct(self):
        font = Font.new()
        g = font.create_glyph(65, "A")
        assert g.unicode_value == 65

    def test_contains_by_name(self):
        font = Font.new()
        font.create_glyph(65, "A")
        assert "A" in font

    def test_contains_by_codepoint(self):
        font = Font.new()
        font.create_glyph(65, "A")
        assert 65 in font

    def test_getitem_by_name(self):
        from aifont.core.glyph import Glyph

        font = Font.new()
        font.create_glyph(65, "A")
        assert isinstance(font["A"], Glyph)

    def test_getitem_missing_raises_key_error(self):
        font = Font.new()
        with pytest.raises(KeyError):
            _ = font["nonexistent_glyph"]

    def test_get_glyph_returns_none_when_missing(self):
        font = Font.new()
        assert font.get_glyph("missing") is None

    def test_get_glyph_returns_glyph_when_present(self):
        from aifont.core.glyph import Glyph

        font = Font.new()
        font.create_glyph(65, "A")
        g = font.get_glyph("A")
        assert isinstance(g, Glyph)

    def test_iter_yields_glyphs(self):
        from aifont.core.glyph import Glyph

        font = Font.new()
        font.create_glyph(65, "A")
        font.create_glyph(66, "B")
        glyphs = list(font)
        assert len(glyphs) == 2
        assert all(isinstance(g, Glyph) for g in glyphs)

    def test_glyphs_property_list(self):
        font = Font.new()
        font.create_glyph(65, "A")
        font.create_glyph(66, "B")
        assert len(font.glyphs) == 2


# ---------------------------------------------------------------------------
# Font.save() error handling
# ---------------------------------------------------------------------------


class TestFontSave:
    def test_save_raises_value_error_for_unknown_format(self, tmp_path):
        font = Font.new()
        with pytest.raises(ValueError):
            font.save(str(tmp_path / "out"))  # no extension, no fmt

    def test_save_sfd(self, tmp_path):
        font = Font.new()
        font.metadata.family_name = "TestSave"
        out = str(tmp_path / "test.sfd")
        font.save(out)
        import os

        assert os.path.isfile(out)
