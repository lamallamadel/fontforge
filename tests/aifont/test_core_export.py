"""Unit tests for aifont.core.export."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch, call

import pytest

from aifont.core.export import export_otf, export_ttf, export_woff2


class TestExportOtf:
    def test_calls_ff_generate(self, font, mock_ff_font, tmp_path):
        out = str(tmp_path / "out.otf")
        export_otf(font, out)
        mock_ff_font.generate.assert_called_once_with(out, flags=("opentype",))

    def test_creates_output_directory(self, font, mock_ff_font, tmp_path):
        out = str(tmp_path / "subdir" / "font.otf")
        export_otf(font, out)
        assert os.path.exists(str(tmp_path / "subdir"))


class TestExportTtf:
    def test_calls_ff_generate(self, font, mock_ff_font, tmp_path):
        out = str(tmp_path / "out.ttf")
        export_ttf(font, out)
        mock_ff_font.generate.assert_called_once_with(out)


class TestExportWoff2:
    def test_calls_native_woff2(self, font, mock_ff_font, tmp_path):
        out = str(tmp_path / "out.woff2")
        export_woff2(font, out)
        mock_ff_font.generate.assert_called_once_with(out, flags=("woff2",))

    def test_fallback_to_ttf_then_fonttools(self, font, mock_ff_font, tmp_path):
        out = str(tmp_path / "out.woff2")
        # First call (native woff2) raises, second (ttf fallback) succeeds
        generate_calls = []

        def side_effect(*args, **kwargs):
            generate_calls.append((args, kwargs))
            if "woff2" in kwargs.get("flags", ()):
                raise Exception("no woff2")
            # Create a dummy TTF file
            if args:
                open(args[0], "wb").close()

        mock_ff_font.generate.side_effect = side_effect

        with patch("aifont.core.export._convert_ttf_to_woff2") as mock_convert:
            export_woff2(font, out)
        mock_convert.assert_called_once()

    def test_convert_raises_without_fonttools(self, font, mock_ff_font, tmp_path):
        from aifont.core.export import _convert_ttf_to_woff2

        ttf = tmp_path / "src.ttf"
        ttf.write_bytes(b"dummy")
        woff2 = tmp_path / "out.woff2"

        with patch.dict("sys.modules", {"fontTools": None, "fontTools.ttLib": None}):
            with pytest.raises((RuntimeError, ImportError)):
                _convert_ttf_to_woff2(str(ttf), str(woff2))
