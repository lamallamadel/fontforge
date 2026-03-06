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
