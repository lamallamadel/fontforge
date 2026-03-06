"""
Unit tests for aifont.core.svg_parser.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

try:
    import fontforge as _ff
    _FF = hasattr(_ff, "font")
except ImportError:
    _FF = False

from aifont.core.svg_parser import (
    _parse_transform,
    _apply_matrix,
    _parse_path_d,
    _tokenise_path,
    svg_to_glyph,
)
from aifont.core.font import Font


# ---------------------------------------------------------------------------
# Pure-Python (no fontforge) tests
# ---------------------------------------------------------------------------


def test_svg_parser_importable():
    assert svg_to_glyph is not None


def test_parse_transform_identity():
    m = _parse_transform("")
    assert m == (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def test_parse_transform_translate():
    m = _parse_transform("translate(10, 20)")
    assert m[4] == pytest.approx(10.0)
    assert m[5] == pytest.approx(20.0)


def test_parse_transform_scale():
    m = _parse_transform("scale(2)")
    assert m[0] == pytest.approx(2.0)
    assert m[3] == pytest.approx(2.0)


def test_apply_matrix_identity():
    x, y = _apply_matrix(5.0, 10.0, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    assert x == pytest.approx(5.0)
    assert y == pytest.approx(10.0)


def test_apply_matrix_translate():
    x, y = _apply_matrix(0.0, 0.0, (1.0, 0.0, 0.0, 1.0, 10.0, 20.0))
    assert x == pytest.approx(10.0)
    assert y == pytest.approx(20.0)


def test_tokenise_path_basic():
    tokens = _tokenise_path("M 10 20 L 30 40 Z")
    assert "M" in tokens
    assert "L" in tokens
    assert "Z" in tokens
    assert 10.0 in tokens


def test_parse_path_d_moveto():
    cmds = _parse_path_d("M 10 20 Z")
    assert cmds[0] == ("M", [10.0, 20.0])
    assert cmds[-1][0] == "Z"


def test_parse_path_d_relative_moveto():
    """Relative 'm' should be converted to absolute 'M'."""
    cmds = _parse_path_d("m 10 20 z")
    # Starting from (0,0), relative (10,20) → absolute (10,20)
    assert cmds[0][0] == "M"
    assert cmds[0][1][0] == pytest.approx(10.0)
    assert cmds[0][1][1] == pytest.approx(20.0)


def test_parse_path_d_cubic():
    d = "M 0 0 C 10 20 30 40 50 60 Z"
    cmds = _parse_path_d(d)
    assert any(cmd == "C" for cmd, _ in cmds)


def test_svg_to_glyph_missing_file():
    """svg_to_glyph should raise FileNotFoundError for non-existent files."""
    if not _FF:
        pytest.skip("fontforge not installed")
    font = Font.new()
    with pytest.raises(FileNotFoundError):
        svg_to_glyph("/nonexistent/path/glyph.svg", font, 0x0041)
    font.close()


def test_svg_to_glyph_no_fontforge(monkeypatch, tmp_path):
    """svg_to_glyph should raise RuntimeError when fontforge is absent."""
    import aifont.core.svg_parser as sp_mod
    monkeypatch.setattr(sp_mod, "fontforge", None)

    svg_file = tmp_path / "test.svg"
    svg_file.write_text(
        textwrap.dedent("""\
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
          <path d="M 10 10 L 90 10 L 90 90 L 10 90 Z"/>
        </svg>
        """)
    )
    with pytest.raises(RuntimeError, match="fontforge"):
        svg_to_glyph(svg_file, object(), 0x0041)


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_svg_to_glyph_simple(tmp_path):
    """svg_to_glyph should create a glyph from a simple square SVG."""
    svg_file = tmp_path / "square.svg"
    svg_file.write_text(
        textwrap.dedent("""\
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
          <path d="M 10 10 L 90 10 L 90 90 L 10 90 Z"/>
        </svg>
        """)
    )
    font = Font.new()
    ff_glyph = svg_to_glyph(svg_file, font, 0x0041, glyph_name="A")
    assert ff_glyph is not None
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_svg_to_glyph_default_name(tmp_path):
    """glyph_name should default to the SVG filename stem."""
    svg_file = tmp_path / "my_glyph.svg"
    svg_file.write_text(
        textwrap.dedent("""\
        <svg xmlns="http://www.w3.org/2000/svg">
          <path d="M 0 0 Z"/>
        </svg>
        """)
    )
    font = Font.new()
    ff_glyph = svg_to_glyph(svg_file, font)
    assert ff_glyph.glyphname == "my_glyph"
    font.close()
