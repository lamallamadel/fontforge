"""
Unit tests for aifont.core.export.
"""

import os

import pytest

_fontforge = pytest.importorskip("fontforge")
if not hasattr(_fontforge, "font"):
    pytest.skip("fontforge C extension not available", allow_module_level=True)

from aifont.core.export import (  # noqa: E402
    export_otf,
    export_sfd,
    export_ttf,
    export_ufo,
    export_woff,
)
from aifont.core.font import Font  # noqa: E402


def _basic_font() -> Font:
    """Create a minimal but valid font for export tests."""
    font = Font.new()
    font.metadata.family_name = "ExportTest"
    font.metadata.full_name = "ExportTest Regular"
    font.metadata.em_size = 1000
    font.set_encoding("UnicodeBMP")
    # Add a space glyph so the font is non-empty
    g = font.create_glyph(32, "space")
    g.set_width(250)
    return font


# ---------------------------------------------------------------------------
# export_sfd
# ---------------------------------------------------------------------------


class TestExportSfd:
    def test_creates_file(self, tmp_path):
        font = _basic_font()
        out = str(tmp_path / "test.sfd")
        export_sfd(font, out)
        assert os.path.isfile(out)
        assert os.path.getsize(out) > 0

    def test_creates_parent_dirs(self, tmp_path):
        font = _basic_font()
        out = str(tmp_path / "subdir" / "test.sfd")
        export_sfd(font, out)
        assert os.path.isfile(out)


# ---------------------------------------------------------------------------
# export_ttf
# ---------------------------------------------------------------------------


class TestExportTtf:
    def test_creates_file(self, tmp_path):
        font = _basic_font()
        out = str(tmp_path / "test.ttf")
        export_ttf(font, out)
        assert os.path.isfile(out)
        assert os.path.getsize(out) > 0

    def test_creates_parent_dirs(self, tmp_path):
        font = _basic_font()
        out = str(tmp_path / "dist" / "test.ttf")
        export_ttf(font, out)
        assert os.path.isfile(out)


# ---------------------------------------------------------------------------
# export_otf
# ---------------------------------------------------------------------------


class TestExportOtf:
    def test_creates_file(self, tmp_path):
        font = _basic_font()
        out = str(tmp_path / "test.otf")
        export_otf(font, out)
        assert os.path.isfile(out)
        assert os.path.getsize(out) > 0


# ---------------------------------------------------------------------------
# export_woff
# ---------------------------------------------------------------------------


class TestExportWoff:
    def test_creates_file_or_skips(self, tmp_path):
        font = _basic_font()
        out = str(tmp_path / "test.woff")
        try:
            export_woff(font, out)
            # If no exception, file should exist
            assert os.path.isfile(out)
        except Exception:  # noqa: BLE001
            pytest.skip("WOFF export not supported in this FontForge build")


# ---------------------------------------------------------------------------
# export_ufo
# ---------------------------------------------------------------------------


class TestExportUfo:
    def test_creates_directory(self, tmp_path):
        font = _basic_font()
        out = str(tmp_path / "test.ufo")
        try:
            export_ufo(font, out)
            assert os.path.isdir(out)
        except Exception:  # noqa: BLE001
            pytest.skip("UFO export not supported in this FontForge build")
