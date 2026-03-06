"""
Unit tests for aifont.core.svg_parser.

Tests for the SVG path tokenizer / parser do NOT require FontForge and
run in any Python environment.  Tests for the full svg_to_glyph()
integration require FontForge.
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
import importlib
import importlib.util
import os
import textwrap

import pytest

from aifont.core.svg_parser import svg_path_to_contours, _tokenize_path


# ---------------------------------------------------------------------------
# _tokenize_path
# ---------------------------------------------------------------------------


class TestTokenizePath:
    def test_simple_move_line(self):
        tokens = _tokenize_path("M 10 20 L 30 40")
        assert "M" in tokens
        assert "L" in tokens
        assert "10" in tokens

    def test_cubic_bezier(self):
        tokens = _tokenize_path("M0,0 C10,20 30,40 50,60")
        assert "M" in tokens
        assert "C" in tokens

    def test_close_path(self):
        tokens = _tokenize_path("M0 0 L10 10 Z")
        assert "Z" in tokens

    def test_negative_values(self):
        tokens = _tokenize_path("M -10 -20")
        assert "-10" in tokens
        assert "-20" in tokens

    def test_decimal_values(self):
        tokens = _tokenize_path("M 1.5 2.75")
        assert "1.5" in tokens
        assert "2.75" in tokens


# ---------------------------------------------------------------------------
# svg_path_to_contours
# ---------------------------------------------------------------------------


class TestSvgPathToContours:
    def test_returns_list(self):
        result = svg_path_to_contours("M 0 0 L 100 100 Z")
        assert isinstance(result, list)

    def test_simple_closed_path_one_subpath(self):
        result = svg_path_to_contours("M 0 0 L 100 0 L 100 100 Z")
        assert len(result) >= 1

    def test_subpath_contains_tuples(self):
        result = svg_path_to_contours("M 0 0 L 100 0 Z")
        for subpath in result:
            for cmd, args in subpath:
                assert isinstance(cmd, str)
                assert isinstance(args, list)

    def test_move_to_uppercase(self):
        result = svg_path_to_contours("M 10 20 Z")
        # After parsing, all commands should be uppercase
        for subpath in result:
            for cmd, _ in subpath:
                assert cmd == cmd.upper()

    def test_empty_path_returns_empty(self):
        result = svg_path_to_contours("")
        assert result == [] or all(len(sp) == 0 for sp in result)

    def test_cubic_bezier_parsed(self):
        result = svg_path_to_contours("M 0 0 C 10 20 30 40 50 0 Z")
        cmds = [cmd for sp in result for cmd, _ in sp]
        assert "C" in cmds

    def test_multiple_subpaths(self):
        d = "M 0 0 L 10 0 Z M 20 0 L 30 0 Z"
        result = svg_path_to_contours(d)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# svg_to_glyph — requires FontForge
# ---------------------------------------------------------------------------

import importlib as _importlib

_ff_module = _importlib.util.find_spec("fontforge")
_ff_available = _ff_module is not None and hasattr(
    _importlib.import_module("fontforge"), "font"
)
_skip_ff = pytest.mark.skipif(
    not _ff_available,
    reason="fontforge C extension not available",
)


def _write_svg(tmp_path, content: str) -> str:
    p = tmp_path / "test.svg"
    p.write_text(content)
    return str(p)


_SIMPLE_SVG = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg"
         width="100" height="100" viewBox="0 0 100 100">
      <path d="M 10 10 L 90 10 L 90 90 L 10 90 Z"/>
    </svg>
""")


@_skip_ff
class TestSvgToGlyph:
    def test_file_not_found_raises(self, tmp_path):
        from aifont.core.font import Font
        from aifont.core.svg_parser import svg_to_glyph

        font = Font.new()
        with pytest.raises(FileNotFoundError):
            svg_to_glyph("/nonexistent/file.svg", font, 65)

    def test_creates_glyph(self, tmp_path):
        from aifont.core.font import Font
        from aifont.core.glyph import Glyph
        from aifont.core.svg_parser import svg_to_glyph

        svg_file = _write_svg(tmp_path, _SIMPLE_SVG)
        font = Font.new()
        glyph = svg_to_glyph(svg_file, font, 65, "A")
        assert isinstance(glyph, Glyph)

    def test_glyph_has_correct_unicode(self, tmp_path):
        from aifont.core.font import Font
        from aifont.core.svg_parser import svg_to_glyph

        svg_file = _write_svg(tmp_path, _SIMPLE_SVG)
        font = Font.new()
        glyph = svg_to_glyph(svg_file, font, 65, "A")
        assert glyph.unicode_value == 65

    def test_glyph_added_to_font(self, tmp_path):
        from aifont.core.font import Font
        from aifont.core.svg_parser import svg_to_glyph

        svg_file = _write_svg(tmp_path, _SIMPLE_SVG)
        font = Font.new()
        svg_to_glyph(svg_file, font, 65, "A")
        assert "A" in font

    def test_empty_svg_raises_value_error(self, tmp_path):
        from aifont.core.font import Font
        from aifont.core.svg_parser import svg_to_glyph

        empty_svg = textwrap.dedent("""\
            <?xml version="1.0"?>
            <svg xmlns="http://www.w3.org/2000/svg"/>
        """)
        svg_file = _write_svg(tmp_path, empty_svg)
        font = Font.new()
        with pytest.raises(ValueError):
            svg_to_glyph(svg_file, font, 65)
