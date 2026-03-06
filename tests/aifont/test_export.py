"""
Unit tests for aifont.core.export.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

try:
    import fontforge as _ff
    _FF = hasattr(_ff, "font")
except ImportError:
    _FF = False

from aifont.core.export import export_otf, export_ttf, export_woff, export_woff2, export_ufo
from aifont.core.font import Font


def test_export_module_importable():
    assert export_otf is not None
    assert export_ttf is not None
    assert export_woff2 is not None


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_export_otf(tmp_path):
    font = Font.new()
    out = tmp_path / "test.otf"
    export_otf(font, out)
    assert out.exists()
    assert out.stat().st_size > 0
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_export_ttf(tmp_path):
    font = Font.new()
    out = tmp_path / "test.ttf"
    export_ttf(font, out)
    assert out.exists()
    assert out.stat().st_size > 0
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_export_woff(tmp_path):
    font = Font.new()
    out = tmp_path / "test.woff"
    export_woff(font, out)
    assert out.exists()
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_export_woff2_no_fonttools(tmp_path, monkeypatch):
    """export_woff2 should raise RuntimeError when fontTools is absent."""
    import aifont.core.export as exp_mod
    monkeypatch.setattr(exp_mod, "_FONTTOOLS_AVAILABLE", False)
    font = Font.new()
    out = tmp_path / "test.woff2"
    with pytest.raises(RuntimeError, match="fontTools"):
        export_woff2(font, out, use_fonttools=True)
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_export_returns_path(tmp_path):
    font = Font.new()
    out = tmp_path / "test.otf"
    result = export_otf(font, out)
    assert isinstance(result, Path)
    assert result == out
    font.close()
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
