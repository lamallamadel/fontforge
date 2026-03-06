"""Unit tests for aifont.core.svg_parser."""

from __future__ import annotations

import os
import textwrap
from unittest.mock import MagicMock

import pytest

from aifont.core.svg_parser import _collect_path_data, _parse_viewbox, svg_to_glyph


SIMPLE_SVG = textwrap.dedent("""\
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 700">
      <path d="M 0 0 L 500 0 L 500 700 Z"/>
    </svg>
""")

MULTI_PATH_SVG = textwrap.dedent("""\
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 700">
      <path d="M 0 0 L 250 700 Z"/>
      <path d="M 250 700 L 500 0 Z"/>
    </svg>
""")

NO_PATH_SVG = textwrap.dedent("""\
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 700">
      <rect x="0" y="0" width="500" height="700"/>
    </svg>
""")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestParseViewbox:
    def test_valid_viewbox(self):
        result = _parse_viewbox("0 0 500 700")
        assert result == (0.0, 0.0, 500.0, 700.0)

    def test_comma_separated(self):
        result = _parse_viewbox("0,0,500,700")
        assert result == (0.0, 0.0, 500.0, 700.0)

    def test_invalid_returns_none(self):
        assert _parse_viewbox("not a viewbox") is None

    def test_wrong_length_returns_none(self):
        assert _parse_viewbox("0 0 500") is None


class TestCollectPathData:
    def test_single_path(self, tmp_path):
        import xml.etree.ElementTree as ET

        root = ET.fromstring(SIMPLE_SVG)
        paths = _collect_path_data(root)
        assert len(paths) == 1
        assert paths[0].startswith("M")

    def test_multi_path(self, tmp_path):
        import xml.etree.ElementTree as ET

        root = ET.fromstring(MULTI_PATH_SVG)
        paths = _collect_path_data(root)
        assert len(paths) == 2

    def test_no_path(self, tmp_path):
        import xml.etree.ElementTree as ET

        root = ET.fromstring(NO_PATH_SVG)
        paths = _collect_path_data(root)
        assert paths == []


# ---------------------------------------------------------------------------
# svg_to_glyph
# ---------------------------------------------------------------------------


class TestSvgToGlyph:
    def test_file_not_found_raises(self, font):
        with pytest.raises(FileNotFoundError):
            svg_to_glyph("/nonexistent/file.svg", font, 0x0041)

    def test_no_path_elements_raises(self, tmp_path, font, mock_ff_font):
        svg_file = tmp_path / "empty.svg"
        svg_file.write_text(NO_PATH_SVG)
        # Return a glyph with no importOutlines to force fallback
        no_import_glyph = MagicMock(spec=["width"])
        no_import_glyph.width = 0
        mock_ff_font.createChar.side_effect = None
        mock_ff_font.createChar.return_value = no_import_glyph

        with pytest.raises(ValueError, match="No <path>"):
            svg_to_glyph(str(svg_file), font, 0x0041)

    def test_imports_via_native_method(self, tmp_path, font, mock_ff_font):
        svg_file = tmp_path / "test.svg"
        svg_file.write_text(SIMPLE_SVG)

        # Return a glyph WITH importOutlines
        native_glyph = MagicMock()
        native_glyph.importOutlines = MagicMock()
        mock_ff_font.createChar.side_effect = None
        mock_ff_font.createChar.return_value = native_glyph

        result = svg_to_glyph(str(svg_file), font, 0x0041)
        native_glyph.importOutlines.assert_called_once_with(str(svg_file))
        assert result is native_glyph

    def test_sets_width_from_viewbox_in_fallback(self, tmp_path, font, mock_ff_font):
        svg_file = tmp_path / "test.svg"
        svg_file.write_text(SIMPLE_SVG)

        # Return a glyph WITHOUT importOutlines (fallback path)
        fallback_glyph = MagicMock(spec=["width"])
        fallback_glyph.width = 0
        mock_ff_font.createChar.side_effect = None
        mock_ff_font.createChar.return_value = fallback_glyph

        svg_to_glyph(str(svg_file), font, 0x0041)
        assert fallback_glyph.width == 500
