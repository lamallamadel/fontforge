"""Tests for aifont.core.export — OTF, TTF, WOFF, WOFF2, UFO, SVG export.

These tests use the existing test fonts already present in tests/fonts/.
Run with:
    python tests/test_aifont_export.py tests/fonts/Caliban.sfd
or via the project's standard test runner.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Allow running directly from repo root without installing the package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import fontforge
    _FONTFORGE_AVAILABLE = hasattr(fontforge, "open")
except ImportError:
    fontforge = None  # type: ignore[assignment]
    _FONTFORGE_AVAILABLE = False

from aifont.core.export import (
    ExportOptions,
    export_all,
    export_otf,
    export_ttf,
    export_ufo,
    export_woff,
    export_woff2,
)

# The default test font shipped with the repository.
_FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "Caliban.sfd")


def _font_path() -> str:
    """Return the path to the test font, or skip if unavailable."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    return _FONT_PATH


class TestExportOptions(unittest.TestCase):
    """Unit tests for ExportOptions — no font I/O required."""

    def test_default_flags(self) -> None:
        opts = ExportOptions()
        flags = opts._build_flags()
        self.assertIn("opentype", flags)
        self.assertNotIn("old-kern", flags)

    def test_old_kern_flag(self) -> None:
        opts = ExportOptions(old_style_kern=True)
        self.assertIn("old-kern", opts._build_flags())

    def test_no_opentype_flag(self) -> None:
        opts = ExportOptions(opentype=False)
        self.assertNotIn("opentype", opts._build_flags())

    def test_extra_flags(self) -> None:
        opts = ExportOptions(extra_flags=["apple"])
        self.assertIn("apple", opts._build_flags())


@unittest.skipUnless(_FONTFORGE_AVAILABLE, "fontforge Python bindings not available")
class TestExportFunctions(unittest.TestCase):
    """Integration tests that open a real font and generate outputs."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.font_path = _font_path()
        if not os.path.exists(cls.font_path):
            raise unittest.SkipTest(
                f"Test font not found: {cls.font_path}"
            )
        cls.tmp = tempfile.mkdtemp(prefix="aifont_test_")

    @classmethod
    def tearDownClass(cls) -> None:
        import shutil
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _out(self, name: str) -> str:
        return os.path.join(self.tmp, name)

    # ------------------------------------------------------------------
    # Individual format exports
    # ------------------------------------------------------------------

    def test_export_otf(self) -> None:
        out = export_otf(self.font_path, self._out("test.otf"))
        self.assertTrue(out.exists(), "OTF file was not created")
        self.assertGreater(out.stat().st_size, 0, "OTF file is empty")
        # Verify FontForge can re-open the file.
        ff = fontforge.open(str(out))
        ff.close()

    def test_export_ttf(self) -> None:
        out = export_ttf(self.font_path, self._out("test.ttf"))
        self.assertTrue(out.exists(), "TTF file was not created")
        self.assertGreater(out.stat().st_size, 0, "TTF file is empty")
        ff = fontforge.open(str(out))
        ff.close()

    def test_export_woff(self) -> None:
        out = export_woff(self.font_path, self._out("test.woff"))
        self.assertTrue(out.exists(), "WOFF file was not created")
        self.assertGreater(out.stat().st_size, 0, "WOFF file is empty")

    def test_export_woff2(self) -> None:
        out = export_woff2(self.font_path, self._out("test.woff2"))
        self.assertTrue(out.exists(), "WOFF2 file was not created")
        self.assertGreater(out.stat().st_size, 0, "WOFF2 file is empty")

    def test_export_svg(self) -> None:
        from aifont.core.export import export_svg
        out = export_svg(self.font_path, self._out("test.svg"))
        self.assertTrue(out.exists(), "SVG file was not created")
        self.assertGreater(out.stat().st_size, 0, "SVG file is empty")

    # ------------------------------------------------------------------
    # Extension auto-correction
    # ------------------------------------------------------------------

    def test_otf_extension_added(self) -> None:
        out = export_otf(self.font_path, self._out("no_ext"))
        self.assertEqual(out.suffix, ".otf")

    def test_ttf_extension_added(self) -> None:
        out = export_ttf(self.font_path, self._out("no_ext2"))
        self.assertEqual(out.suffix, ".ttf")

    # ------------------------------------------------------------------
    # Hinting option
    # ------------------------------------------------------------------

    def test_export_otf_with_hints(self) -> None:
        opts = ExportOptions(hints=True)
        out = export_otf(self.font_path, self._out("hinted.otf"), options=opts)
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 0)

    # ------------------------------------------------------------------
    # Batch export
    # ------------------------------------------------------------------

    def test_export_all_default(self) -> None:
        results = export_all(
            self.font_path,
            self._out("batch"),
            formats=["otf", "ttf", "woff"],
        )
        self.assertIn("otf", results)
        self.assertIn("ttf", results)
        self.assertIn("woff", results)
        for fmt, path in results.items():
            self.assertTrue(path.exists(), f"{fmt} output not found: {path}")
            self.assertGreater(path.stat().st_size, 0, f"{fmt} output is empty")

    def test_export_all_unknown_format(self) -> None:
        with self.assertRaises(ValueError):
            export_all(self.font_path, self._out("batch2"), formats=["xyz"])

    def test_export_all_custom_basename(self) -> None:
        results = export_all(
            self.font_path,
            self._out("batch3"),
            basename="MyFont",
            formats=["otf"],
        )
        self.assertIn("MyFont", str(results["otf"]))

    # ------------------------------------------------------------------
    # Font object (not path) input
    # ------------------------------------------------------------------

    def test_export_from_fontforge_object(self) -> None:
        ff = fontforge.open(self.font_path)
        try:
            out = export_ttf(ff, self._out("from_obj.ttf"))
            self.assertTrue(out.exists())
        finally:
            ff.close()


if __name__ == "__main__":
    # When invoked directly the first positional argument may be a font path.
    # Strip it before passing remaining args to unittest.
    _font_extensions = (".sfd", ".ttf", ".otf", ".woff", ".woff2")
    argv = [sys.argv[0]] + [
        a for a in sys.argv[1:] if not a.endswith(_font_extensions)
    ]
    unittest.main(argv=argv, verbosity=2)
