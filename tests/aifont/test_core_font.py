"""Unit tests for aifont.core.font (Font and FontMetadata)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aifont.core.font import Font, FontMetadata


# ---------------------------------------------------------------------------
# FontMetadata
# ---------------------------------------------------------------------------


class TestFontMetadata:
    def test_name_property(self, mock_ff_font):
        meta = FontMetadata(mock_ff_font)
        assert meta.name == "TestFont"

    def test_name_setter(self, mock_ff_font):
        meta = FontMetadata(mock_ff_font)
        meta.name = "NewFont"
        assert mock_ff_font.fontname == "NewFont"

    def test_family_property(self, mock_ff_font):
        meta = FontMetadata(mock_ff_font)
        assert meta.family == "TestFont"

    def test_family_setter(self, mock_ff_font):
        meta = FontMetadata(mock_ff_font)
        meta.family = "NewFamily"
        assert mock_ff_font.familyname == "NewFamily"

    def test_weight_property(self, mock_ff_font):
        meta = FontMetadata(mock_ff_font)
        assert meta.weight == "Regular"

    def test_weight_setter(self, mock_ff_font):
        meta = FontMetadata(mock_ff_font)
        meta.weight = "Bold"
        assert mock_ff_font.weight == "Bold"

    def test_version_property(self, mock_ff_font):
        meta = FontMetadata(mock_ff_font)
        assert meta.version == "1.0"

    def test_to_dict(self, mock_ff_font):
        meta = FontMetadata(mock_ff_font)
        d = meta.to_dict()
        assert isinstance(d, dict)
        assert d["name"] == "TestFont"
        assert "family" in d
        assert "weight" in d
        assert "version" in d


# ---------------------------------------------------------------------------
# Font
# ---------------------------------------------------------------------------


class TestFont:
    def test_metadata_returns_font_metadata(self, font):
        assert isinstance(font.metadata, FontMetadata)

    def test_metadata_name(self, font):
        assert font.metadata.name == "TestFont"

    def test_glyph_count(self, font):
        assert font.glyph_count == 3

    def test_len(self, font):
        assert len(font) == 3

    def test_repr(self, font):
        r = repr(font)
        assert "Font(" in r
        assert "TestFont" in r

    def test_glyphs_returns_list(self, font):
        from aifont.core.glyph import Glyph

        glyphs = font.glyphs
        assert isinstance(glyphs, list)
        assert all(isinstance(g, Glyph) for g in glyphs)

    def test_glyphs_count_matches(self, font):
        assert len(font.glyphs) == 3

    def test_get_glyph_found(self, font):
        from aifont.core.glyph import Glyph

        g = font.get_glyph("A")
        assert isinstance(g, Glyph)
        assert g.name == "A"

    def test_get_glyph_not_found(self, font, mock_ff_font):
        mock_ff_font.__getitem__.side_effect = KeyError("Z")
        with pytest.raises(KeyError):
            font.get_glyph("Z")

    def test_iterate_font(self, font):
        names = [g.name for g in font]
        assert "A" in names
        assert "B" in names

    def test_save_calls_ff_save(self, font, mock_ff_font):
        font.save("/tmp/out.sfd")
        mock_ff_font.save.assert_called_once_with("/tmp/out.sfd")

    def test_save_with_format(self, font, mock_ff_font):
        font.save("/tmp/out.otf", fmt="otf")
        mock_ff_font.save.assert_called_once_with("/tmp/out.otf", "otf")

    def test_generate_calls_ff_generate(self, font, mock_ff_font):
        font.generate("/tmp/out.otf")
        mock_ff_font.generate.assert_called_once_with("/tmp/out.otf")

    def test_close_calls_ff_close(self, font, mock_ff_font):
        font.close()
        mock_ff_font.close.assert_called_once()

    def test_context_manager(self, mock_ff_font):
        with Font(mock_ff_font) as f:
            assert f.metadata.name == "TestFont"
        mock_ff_font.close.assert_called_once()

    # ------------------------------------------------------------------
    # Font.open / Font.new require fontforge — mock the module
    # ------------------------------------------------------------------

    def test_open_raises_when_ff_unavailable(self, tmp_path):
        dummy = tmp_path / "test.otf"
        dummy.write_bytes(b"dummy")
        import aifont.core.font as font_mod

        orig_ff = font_mod._ff
        orig_avail = font_mod._FF_AVAILABLE
        try:
            font_mod._ff = None
            font_mod._FF_AVAILABLE = False
            with pytest.raises(RuntimeError, match="fontforge"):
                Font.open(str(dummy))
        finally:
            font_mod._ff = orig_ff
            font_mod._FF_AVAILABLE = orig_avail

    def test_open_raises_when_file_missing(self):
        import aifont.core.font as font_mod

        orig_avail = font_mod._FF_AVAILABLE
        try:
            font_mod._FF_AVAILABLE = True
            with pytest.raises(FileNotFoundError):
                Font.open("/nonexistent/path/font.otf")
        finally:
            font_mod._FF_AVAILABLE = orig_avail

    def test_new_raises_when_ff_unavailable(self):
        import aifont.core.font as font_mod

        orig_ff = font_mod._ff
        orig_avail = font_mod._FF_AVAILABLE
        try:
            font_mod._ff = None
            font_mod._FF_AVAILABLE = False
            with pytest.raises(RuntimeError, match="fontforge"):
                Font.new("Test")
        finally:
            font_mod._ff = orig_ff
            font_mod._FF_AVAILABLE = orig_avail

    def test_new_with_mocked_ff(self, mock_ff_font):
        import aifont.core.font as font_mod

        mock_module = MagicMock()
        mock_module.font = MagicMock(return_value=mock_ff_font)

        orig_ff = font_mod._ff
        orig_avail = font_mod._FF_AVAILABLE
        try:
            font_mod._ff = mock_module
            font_mod._FF_AVAILABLE = True
            f = Font.new("MyFont")
            assert isinstance(f, Font)
        finally:
            font_mod._ff = orig_ff
            font_mod._FF_AVAILABLE = orig_avail

    def test_open_with_mocked_ff(self, mock_ff_font, tmp_path):
        import aifont.core.font as font_mod

        dummy = tmp_path / "font.otf"
        dummy.write_bytes(b"dummy")

        mock_module = MagicMock()
        mock_module.open = MagicMock(return_value=mock_ff_font)

        orig_ff = font_mod._ff
        orig_avail = font_mod._FF_AVAILABLE
        try:
            font_mod._ff = mock_module
            font_mod._FF_AVAILABLE = True
            f = Font.open(str(dummy))
            assert isinstance(f, Font)
        finally:
            font_mod._ff = orig_ff
            font_mod._FF_AVAILABLE = orig_avail
