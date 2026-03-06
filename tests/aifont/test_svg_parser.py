"""
Unit tests for aifont.core.svg_parser.

Tests for the SVG path tokenizer / parser do NOT require FontForge and
run in any Python environment.  Tests for the full svg_to_glyph()
integration require FontForge.
"""

from __future__ import annotations

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
