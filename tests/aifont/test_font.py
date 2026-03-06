"""
Unit tests for aifont.core.font.

Tests run with or without the fontforge C extension.  When fontforge is
not available, all tests that actually need it are skipped gracefully.
Unit tests for aifont.core.font (AIFont) and aifont.core.glyph (Glyph).

FontForge is not available in every CI environment, so these tests use
``unittest.mock`` to stub out the ``fontforge`` C bindings.  The tests
therefore focus on the *Python-level* behaviour of the wrappers rather
than the correctness of the underlying FontForge operations.
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
import sys
import types
from pathlib import Path
from typing import Iterator
from unittest.mock import MagicMock, patch, PropertyMock
import pytest

# ---------------------------------------------------------------------------
# Build a minimal stub for the ``fontforge`` C extension so that the tests
# can run without FontForge installed.
# ---------------------------------------------------------------------------


def _make_fontforge_stub() -> types.ModuleType:
    """Return a minimal ``fontforge`` stub module."""
    ff_mod = types.ModuleType("fontforge")

    class _FakeGlyph:
        def __init__(self, name: str, unicode_value: int = -1) -> None:
            self.glyphname = name
            self.unicode = unicode_value
            self.width = 500
            self.left_side_bearing = 50
            self.right_side_bearing = 50
            self.foreground = []
            self.font = None  # filled in by _FakeFont

        def unlinkThisGlyph(self) -> None:
            pass

    class _FakeFont:
        def __init__(self) -> None:
            self.fontname = ""
            self.familyname = ""
            self.fullname = ""
            self.version = ""
            self.copyright = ""
            self._glyphs: dict[str, _FakeGlyph] = {}

        # ------------------------------------------------------------------
        # FontForge font iteration protocol
        # ------------------------------------------------------------------

        def __iter__(self) -> Iterator[str]:
            return iter(list(self._glyphs))

        def __contains__(self, name: str) -> bool:
            return name in self._glyphs

        def __getitem__(self, name: str) -> _FakeGlyph:
            return self._glyphs[name]

        def createChar(self, unicode_value: int, name: str) -> _FakeGlyph:
            if name not in self._glyphs:
                g = _FakeGlyph(name, unicode_value)
                g.font = self
                self._glyphs[name] = g
            return self._glyphs[name]

        def removeGlyph(self, name: str) -> None:
            self._glyphs.pop(name, None)

        def save(self, path: str) -> None:
            pass

        def generate(self, path: str) -> None:
            # Create an empty file so Path.exists() can be checked if needed.
            Path(path).touch()

        def close(self) -> None:
            pass

    def _font_constructor() -> _FakeFont:
        return _FakeFont()

    def _open(path: str) -> _FakeFont:
        return _FakeFont()

    ff_mod.font = _font_constructor  # type: ignore[attr-defined]
    ff_mod.open = _open  # type: ignore[attr-defined]
    return ff_mod


# Install the stub before importing aifont so that the ``try: import fontforge``
# block inside font.py picks up our stub instead of failing.
_ff_stub = _make_fontforge_stub()
sys.modules.setdefault("fontforge", _ff_stub)

# ---------------------------------------------------------------------------
# Now import the modules under test
# ---------------------------------------------------------------------------

from aifont.core.font import AIFont  # noqa: E402
from aifont.core.glyph import Glyph  # noqa: E402


# ===========================================================================
# AIFont — constructor tests
# ===========================================================================


class TestAIFontCreate:
    """Tests for AIFont.create()."""

    def test_create_sets_fontname(self) -> None:
        font = AIFont.create("TestFont")
        assert font.name == "TestFont"

    def test_create_sets_familyname_when_provided(self) -> None:
        font = AIFont.create("TestFont", family="TestFamily")
        assert font.family == "TestFamily"

    def test_create_defaults_family_to_name(self) -> None:
        font = AIFont.create("TestFont")
        assert font.family == "TestFont"

    def test_create_returns_aifont_instance(self) -> None:
        font = AIFont.create("TestFont")
        assert isinstance(font, AIFont)


class TestAIFontOpen:
    """Tests for AIFont.open()."""

    def test_open_returns_aifont(self, tmp_path: Path) -> None:
        # Create a dummy file so the existence check passes.
        dummy = tmp_path / "test.sfd"
        dummy.write_text("")
        font = AIFont.open(str(dummy))
        assert isinstance(font, AIFont)

    def test_open_raises_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            AIFont.open("/nonexistent/path/font.sfd")

    def test_open_accepts_path_object(self, tmp_path: Path) -> None:
        dummy = tmp_path / "test.sfd"
        dummy.write_text("")
        font = AIFont.open(dummy)
        assert isinstance(font, AIFont)


# ===========================================================================
# AIFont — metadata tests
# ===========================================================================


class TestAIFontMetadata:
    """Tests for name, family, version and copyright properties."""

    def setup_method(self) -> None:
        self.font = AIFont.create("InitialName", family="InitialFamily")

    def test_name_getter(self) -> None:
        assert self.font.name == "InitialName"

    def test_name_setter(self) -> None:
        self.font.name = "NewName"
        assert self.font.name == "NewName"

    def test_family_getter(self) -> None:
        assert self.font.family == "InitialFamily"

    def test_family_setter(self) -> None:
        self.font.family = "NewFamily"
        assert self.font.family == "NewFamily"

    def test_version_default_empty(self) -> None:
        assert self.font.version == ""

    def test_version_setter(self) -> None:
        self.font.version = "1.0"
        assert self.font.version == "1.0"

    def test_copyright_default_empty(self) -> None:
        assert self.font.copyright == ""

    def test_copyright_setter(self) -> None:
        self.font.copyright = "© 2025 AIFont"
        assert self.font.copyright == "© 2025 AIFont"


# ===========================================================================
# AIFont — glyph management tests
# ===========================================================================


class TestAIFontGlyphManagement:
    """Tests for list_glyphs, add_glyph, remove_glyph and get_glyph."""

    def setup_method(self) -> None:
        self.font = AIFont.create("GlyphFont")

    def test_list_glyphs_empty_on_new_font(self) -> None:
        assert self.font.list_glyphs() == []

    def test_add_glyph_returns_glyph(self) -> None:
        g = self.font.add_glyph("A")
        assert isinstance(g, Glyph)

    def test_add_glyph_appears_in_list(self) -> None:
        self.font.add_glyph("A")
        assert "A" in self.font.list_glyphs()

    def test_add_multiple_glyphs(self) -> None:
        for name in ("A", "B", "C"):
            self.font.add_glyph(name)
        names = self.font.list_glyphs()
        assert set(names) == {"A", "B", "C"}

    def test_remove_glyph(self) -> None:
        self.font.add_glyph("Z")
        self.font.remove_glyph("Z")
        assert "Z" not in self.font.list_glyphs()

    def test_remove_nonexistent_glyph_raises_key_error(self) -> None:
        with pytest.raises(KeyError):
            self.font.remove_glyph("Z")

    def test_get_glyph_returns_glyph(self) -> None:
        self.font.add_glyph("A")
        g = self.font.get_glyph("A")
        assert isinstance(g, Glyph)
        assert g.name == "A"

    def test_get_nonexistent_glyph_raises_key_error(self) -> None:
        with pytest.raises(KeyError):
            self.font.get_glyph("Z")


# ===========================================================================
# AIFont — persistence tests
# ===========================================================================


class TestAIFontSave:
    """Tests for AIFont.save()."""

    def test_save_calls_underlying_font_save(self, tmp_path: Path) -> None:
        font = AIFont.create("SaveFont")
        save_path = tmp_path / "output.sfd"
        # Patch the underlying _font.save to spy on the call.
        font._font.save = MagicMock()
        font.save(str(save_path))
        font._font.save.assert_called_once_with(str(save_path))

    def test_save_accepts_path_object(self, tmp_path: Path) -> None:
        font = AIFont.create("SaveFont")
        save_path = tmp_path / "output.sfd"
        font._font.save = MagicMock()
        font.save(save_path)
        font._font.save.assert_called_once_with(str(save_path))


class TestAIFontExport:
    """Tests for AIFont.export()."""

    def test_export_otf_returns_path(self, tmp_path: Path) -> None:
        font = AIFont.create("ExportFont")
        font._font.generate = MagicMock()
        result = font.export("otf", tmp_path / "out.otf")
        assert isinstance(result, Path)
        assert result.suffix == ".otf"

    def test_export_uses_font_name_when_no_path(self, tmp_path: Path) -> None:
        font = AIFont.create("ExportFont")
        font._font.generate = MagicMock()
        # Change working directory so the generated file lands in tmp_path.
        import os
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = font.export("ttf")
            assert result.name == "ExportFont.ttf"
        finally:
            os.chdir(original_dir)

    def test_export_invalid_format_raises_value_error(self) -> None:
        font = AIFont.create("ExportFont")
        with pytest.raises(ValueError, match="Unknown export format"):
            font.export("xyz")

    def test_export_case_insensitive(self, tmp_path: Path) -> None:
        font = AIFont.create("ExportFont")
        font._font.generate = MagicMock()
        result = font.export("OTF", tmp_path / "out.otf")
        assert result.suffix == ".otf"


# ===========================================================================
# AIFont — context manager
# ===========================================================================


class TestAIFontContextManager:
    """Tests for using AIFont as a context manager."""

    def test_context_manager_calls_close(self) -> None:
        font = AIFont.create("CtxFont")
        font._font.close = MagicMock()
        with font:
            pass
        font._font.close.assert_called_once()


# ===========================================================================
# AIFont — repr
# ===========================================================================


class TestAIFontRepr:
    def test_repr_contains_name(self) -> None:
        font = AIFont.create("MyFont")
        assert "MyFont" in repr(font)


# ===========================================================================
# Glyph — property tests
# ===========================================================================


class TestGlyph:
    """Tests for the Glyph wrapper."""

    def setup_method(self) -> None:
        self.font = AIFont.create("GlyphTestFont")
        self.glyph = self.font.add_glyph("A")

    def test_name_property(self) -> None:
        assert self.glyph.name == "A"

    def test_unicode_property(self) -> None:
        # Our stub sets unicode to -1 for createChar(-1, name).
        assert isinstance(self.glyph.unicode, int)

    def test_width_getter(self) -> None:
        assert self.glyph.width == 500

    def test_width_setter(self) -> None:
        self.glyph.width = 600
        assert self.glyph.width == 600

    def test_set_width(self) -> None:
        self.glyph.set_width(700)
        assert self.glyph.width == 700

    def test_left_side_bearing(self) -> None:
        assert self.glyph.left_side_bearing == 50

    def test_right_side_bearing(self) -> None:
        assert self.glyph.right_side_bearing == 50

    def test_contours_returns_list(self) -> None:
        assert isinstance(self.glyph.contours, list)

    def test_repr_contains_name(self) -> None:
        assert "A" in repr(self.glyph)
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
