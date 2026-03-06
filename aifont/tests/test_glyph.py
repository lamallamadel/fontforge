"""Unit tests for aifont.core.glyph — Glyph class.

Tests are designed to run both with real FontForge Python bindings (integration)
and with mock objects (unit tests, no FontForge required).

The integration tests are skipped when fontforge is not available.
"""

from __future__ import annotations

import math
import sys
import unittest
from unittest.mock import MagicMock, PropertyMock, patch

# ---------------------------------------------------------------------------
# Detect FontForge availability
# ---------------------------------------------------------------------------

try:
    import fontforge  # type: ignore
    import psMat  # type: ignore
    _FONTFORGE_AVAILABLE = hasattr(fontforge, "font")
except ImportError:
    _FONTFORGE_AVAILABLE = False

from aifont.core.glyph import Glyph


# ===========================================================================
# Unit tests — using mock fontforge glyph objects (no compiled FontForge)
# ===========================================================================

class _MockFfGlyph:
    """Minimal in-memory stand-in for a ``fontforge.glyph`` object."""

    def __init__(self, name: str = "A", unicode_val: int = 65):
        self.glyphname = name
        self.unicode = unicode_val
        self.width = 500
        self.left_side_bearing = 50
        self.right_side_bearing = 50
        self._transform_calls: list = []
        self._stroke_calls: list = []
        self._cleared = False
        self._simplified = False
        self._overlap_removed = False
        self._direction_corrected = False
        self._auto_hinted = False
        self._rounded = False
        # Simple foreground layer mock
        self.foreground = _MockLayer()

    def clear(self):
        self._cleared = True
        self.foreground = _MockLayer()

    def transform(self, matrix):
        self._transform_calls.append(matrix)

    def stroke(self, *args, **kwargs):
        self._stroke_calls.append((args, kwargs))

    def simplify(self, error_bound, flags):
        self._simplified = True
        self._simplify_args = (error_bound, flags)

    def removeOverlap(self):
        self._overlap_removed = True

    def correctDirection(self):
        self._direction_corrected = True

    def autoHint(self):
        self._auto_hinted = True

    def round(self):
        self._rounded = True

    def glyphPen(self):
        return MagicMock()

    def draw(self, pen):
        pass

    def export(self, path, *args):
        """Write a minimal SVG or PNG to *path* so export methods work."""
        if path.endswith(".svg"):
            svg = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<svg xmlns="http://www.w3.org/2000/svg">'
                '<path d="M 0 0 L 100 0 L 100 100 Z"/>'
                "</svg>"
            )
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(svg)
        elif path.endswith(".png"):
            # Write a minimal 1×1 valid PNG
            import struct
            import zlib
            def _chunk(name, data):
                c = struct.pack(">I", len(data)) + name + data
                crc = struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)
                return c + crc
            sig = b"\x89PNG\r\n\x1a\n"
            ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            raw = b"\x00\xff\xff\xff"
            idat = _chunk(b"IDAT", zlib.compress(raw))
            iend = _chunk(b"IEND", b"")
            with open(path, "wb") as fh:
                fh.write(sig + ihdr + idat + iend)


class _MockLayer:
    """Minimal mock for a fontforge layer (iterable contour container)."""

    def __init__(self):
        self._contours: list = []

    def __iter__(self):
        return iter(self._contours)

    def __iadd__(self, contour):
        self._contours.append(contour)
        return self


class _MockContour:
    """Minimal mock for a fontforge contour."""

    def __init__(self, closed: bool = True):
        self.closed = closed


# ---------------------------------------------------------------------------
# Test: Identity properties
# ---------------------------------------------------------------------------

class TestGlyphIdentity(unittest.TestCase):
    """Test name, unicode properties."""

    def setUp(self):
        self._ff = _MockFfGlyph("A", 65)
        self.glyph = Glyph(self._ff)

    def test_name(self):
        self.assertEqual(self.glyph.name, "A")

    def test_unicode(self):
        self.assertEqual(self.glyph.unicode, 65)

    def test_unicode_setter(self):
        self.glyph.unicode = 66
        self.assertEqual(self._ff.unicode, 66)

    def test_repr_with_unicode(self):
        r = repr(self.glyph)
        self.assertIn("A", r)
        self.assertIn("0041", r)

    def test_repr_no_unicode(self):
        self._ff.unicode = -1
        r = repr(self.glyph)
        self.assertIn("A", r)
        self.assertNotIn("U+", r)


# ---------------------------------------------------------------------------
# Test: Metrics (width, bearings)
# ---------------------------------------------------------------------------

class TestGlyphMetrics(unittest.TestCase):
    """Test width and side-bearing properties."""

    def setUp(self):
        self._ff = _MockFfGlyph()
        self.glyph = Glyph(self._ff)

    def test_width_getter(self):
        self.assertEqual(self.glyph.width, 500)

    def test_width_setter(self):
        self.glyph.width = 600
        self.assertEqual(self._ff.width, 600)

    def test_width_setter_coerces_to_int(self):
        self.glyph.width = 600.9
        self.assertEqual(self._ff.width, 600)

    def test_width_setter_raises_on_negative(self):
        with self.assertRaises(ValueError):
            self.glyph.width = -1

    def test_set_width_returns_self(self):
        result = self.glyph.set_width(700)
        self.assertIs(result, self.glyph)
        self.assertEqual(self._ff.width, 700)

    def test_left_side_bearing_getter(self):
        self.assertEqual(self.glyph.left_side_bearing, 50)

    def test_left_side_bearing_setter(self):
        self.glyph.left_side_bearing = 30
        self.assertEqual(self._ff.left_side_bearing, 30)

    def test_right_side_bearing_getter(self):
        self.assertEqual(self.glyph.right_side_bearing, 50)

    def test_right_side_bearing_setter(self):
        self.glyph.right_side_bearing = 40
        self.assertEqual(self._ff.right_side_bearing, 40)


# ---------------------------------------------------------------------------
# Test: Contours
# ---------------------------------------------------------------------------

class TestGlyphContours(unittest.TestCase):
    """Test contour access and manipulation."""

    def setUp(self):
        self._ff = _MockFfGlyph()
        self.glyph = Glyph(self._ff)

    def test_contours_returns_foreground(self):
        self.assertIs(self.glyph.contours, self._ff.foreground)

    def test_has_open_contours_empty(self):
        self.assertFalse(self.glyph.has_open_contours)

    def test_has_open_contours_closed(self):
        self._ff.foreground._contours.append(_MockContour(closed=True))
        self.assertFalse(self.glyph.has_open_contours)

    def test_has_open_contours_open(self):
        self._ff.foreground._contours.append(_MockContour(closed=False))
        self.assertTrue(self.glyph.has_open_contours)

    def test_remove_all_contours_calls_clear(self):
        result = self.glyph.remove_all_contours()
        self.assertTrue(self._ff._cleared)
        self.assertIs(result, self.glyph)


# ---------------------------------------------------------------------------
# Test: add_contour (requires real fontforge.contour and fontforge.point)
# ---------------------------------------------------------------------------

@unittest.skipUnless(_FONTFORGE_AVAILABLE, "fontforge Python bindings not available")
class TestGlyphAddContour(unittest.TestCase):
    """Integration tests for add_contour using real fontforge objects."""

    def setUp(self):
        self._font = fontforge.font()
        self._ff_glyph = self._font.createChar(65, "A")
        self.glyph = Glyph(self._ff_glyph)

    def tearDown(self):
        self._font.close()

    def test_add_contour_single_triangle(self):
        points = [(0, 0), (200, 0), (100, 200)]
        self.glyph.add_contour(points)
        # Foreground layer should now contain one contour
        layer = self._ff_glyph.foreground
        contours = list(layer)
        self.assertEqual(len(contours), 1)

    def test_add_contour_returns_self(self):
        result = self.glyph.add_contour([(0, 0), (100, 0), (50, 100)])
        self.assertIs(result, self.glyph)

    def test_add_contour_closed_by_default(self):
        self.glyph.add_contour([(0, 0), (100, 0), (50, 100)])
        layer = self._ff_glyph.foreground
        for c in layer:
            self.assertTrue(c.closed)

    def test_add_contour_open(self):
        self.glyph.add_contour([(0, 0), (100, 0)], closed=False)
        layer = self._ff_glyph.foreground
        for c in layer:
            self.assertFalse(c.closed)


# ---------------------------------------------------------------------------
# Test: Typographic operations
# ---------------------------------------------------------------------------

class TestTypographicOps(unittest.TestCase):
    """Test simplify, remove_overlap, correct_direction, auto_hint, round."""

    def setUp(self):
        self._ff = _MockFfGlyph()
        self.glyph = Glyph(self._ff)

    def test_simplify_called(self):
        result = self.glyph.simplify()
        self.assertTrue(self._ff._simplified)
        self.assertIs(result, self.glyph)

    def test_simplify_custom_error_bound(self):
        self.glyph.simplify(error_bound=2.5)
        self.assertEqual(self._ff._simplify_args[0], 2.5)

    def test_remove_overlap_called(self):
        result = self.glyph.remove_overlap()
        self.assertTrue(self._ff._overlap_removed)
        self.assertIs(result, self.glyph)

    def test_correct_direction_called(self):
        result = self.glyph.correct_direction()
        self.assertTrue(self._ff._direction_corrected)
        self.assertIs(result, self.glyph)

    def test_auto_hint_called(self):
        result = self.glyph.auto_hint()
        self.assertTrue(self._ff._auto_hinted)
        self.assertIs(result, self.glyph)

    def test_round_to_int_called(self):
        result = self.glyph.round_to_int()
        self.assertTrue(self._ff._rounded)
        self.assertIs(result, self.glyph)

    def test_stroke_called(self):
        result = self.glyph.stroke(width=50)
        self.assertEqual(len(self._ff._stroke_calls), 1)
        self.assertIs(result, self.glyph)

    def test_stroke_passes_width(self):
        self.glyph.stroke(width=80)
        args, _ = self._ff._stroke_calls[0]
        # width is the second positional arg (after stroke_type)
        self.assertEqual(args[1], 80)


# ---------------------------------------------------------------------------
# Test: Geometric transformations
# ---------------------------------------------------------------------------

class TestGeometricTransforms(unittest.TestCase):
    """Test scale, rotate, move, skew, transform — via mock psMat."""

    def setUp(self):
        self._ff = _MockFfGlyph()
        self.glyph = Glyph(self._ff)

    def _patch_psmat(self):
        """Return a context manager that patches psMat in glyph module."""
        mock_mat = MagicMock()
        mock_mat.scale.return_value = (2, 0, 0, 2, 0, 0)
        mock_mat.rotate.return_value = (0, 1, -1, 0, 0, 0)
        mock_mat.translate.return_value = (1, 0, 0, 1, 10, 20)
        mock_mat.skew.return_value = (1, 0.5, 0, 1, 0, 0)
        return patch("aifont.core.glyph.psMat", mock_mat), mock_mat

    def test_scale_uniform(self):
        ctx, mock_mat = self._patch_psmat()
        with ctx:
            result = self.glyph.scale(2.0)
        mock_mat.scale.assert_called_once_with(2.0, 2.0)
        self.assertIs(result, self.glyph)
        self.assertEqual(len(self._ff._transform_calls), 1)

    def test_scale_non_uniform(self):
        ctx, mock_mat = self._patch_psmat()
        with ctx:
            self.glyph.scale(2.0, factor_y=3.0)
        mock_mat.scale.assert_called_once_with(2.0, 3.0)

    def test_rotate_converts_degrees(self):
        ctx, mock_mat = self._patch_psmat()
        with ctx:
            result = self.glyph.rotate(90)
        call_args = mock_mat.rotate.call_args[0][0]
        self.assertAlmostEqual(call_args, math.radians(90), places=10)
        self.assertIs(result, self.glyph)

    def test_move(self):
        ctx, mock_mat = self._patch_psmat()
        with ctx:
            result = self.glyph.move(dx=10, dy=20)
        mock_mat.translate.assert_called_once_with(10, 20)
        self.assertIs(result, self.glyph)

    def test_skew_converts_degrees(self):
        ctx, mock_mat = self._patch_psmat()
        with ctx:
            result = self.glyph.skew(30)
        call_args = mock_mat.skew.call_args[0][0]
        self.assertAlmostEqual(call_args, math.radians(30), places=10)
        self.assertIs(result, self.glyph)

    def test_transform_direct(self):
        matrix = (1, 0, 0, 1, 50, 0)
        result = self.glyph.transform(matrix)
        self.assertEqual(self._ff._transform_calls[-1], matrix)
        self.assertIs(result, self.glyph)

    def test_method_chaining(self):
        """Multiple transform methods can be chained."""
        ctx, mock_mat = self._patch_psmat()
        with ctx:
            result = self.glyph.scale(1.2).move(dx=5).rotate(10)
        self.assertIs(result, self.glyph)
        self.assertEqual(len(self._ff._transform_calls), 3)


# ---------------------------------------------------------------------------
# Test: Export — SVG / PNG
# ---------------------------------------------------------------------------

class TestGlyphExport(unittest.TestCase):
    """Test to_svg() and to_png() via the mock glyph's export method."""

    def setUp(self):
        self._ff = _MockFfGlyph("A", 65)
        self.glyph = Glyph(self._ff)

    def test_to_svg_returns_string(self):
        svg = self.glyph.to_svg()
        self.assertIsInstance(svg, str)
        self.assertIn("<svg", svg)

    def test_to_svg_contains_path(self):
        svg = self.glyph.to_svg()
        self.assertIn("<path", svg)

    def test_to_png_returns_bytes(self):
        png = self.glyph.to_png()
        self.assertIsInstance(png, bytes)

    def test_to_png_starts_with_png_signature(self):
        png = self.glyph.to_png()
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_to_png_accepts_size_param(self):
        """to_png(size=...) should pass size to the underlying export call."""
        called_with: list = []
        original_export = self._ff.export

        def _mock_export(path, *args):
            called_with.extend(args)
            original_export(path, *args)

        self._ff.export = _mock_export
        self.glyph.to_png(size=128)
        self.assertIn(128, called_with)


# ---------------------------------------------------------------------------
# Test: copy_from
# ---------------------------------------------------------------------------

class TestGlyphCopyFrom(unittest.TestCase):
    """Test copy_from() delegates to clear + draw."""

    def test_copy_from_clears_and_draws(self):
        src_ff = _MockFfGlyph("B", 66)
        dst_ff = _MockFfGlyph("A", 65)

        src = Glyph(src_ff)
        dst = Glyph(dst_ff)

        mock_pen = MagicMock()
        dst_ff.glyphPen = MagicMock(return_value=mock_pen)

        result = dst.copy_from(src)
        self.assertTrue(dst_ff._cleared)
        dst_ff.glyphPen.assert_called_once()
        self.assertIs(result, dst)


# ---------------------------------------------------------------------------
# Integration tests — require compiled FontForge
# ---------------------------------------------------------------------------

@unittest.skipUnless(_FONTFORGE_AVAILABLE, "fontforge Python bindings not available")
class TestGlyphIntegration(unittest.TestCase):
    """End-to-end integration tests using real FontForge objects."""

    def setUp(self):
        self._font = fontforge.font()
        ff_glyph = self._font.createChar(65, "A")
        self.glyph = Glyph(ff_glyph)

    def tearDown(self):
        self._font.close()

    def _add_square(self):
        """Add a 100×100 square to the glyph for transform tests."""
        self.glyph.add_contour([(0, 0), (100, 0), (100, 100), (0, 100)])

    def test_width_roundtrip(self):
        self.glyph.width = 600
        self.assertEqual(self.glyph.width, 600)

    def test_scale_changes_bounding_box(self):
        self._add_square()
        bb_before = self.glyph._ff.boundingBox()
        self.glyph.scale(2.0)
        bb_after = self.glyph._ff.boundingBox()
        w_before = bb_before[2] - bb_before[0]
        w_after = bb_after[2] - bb_after[0]
        self.assertAlmostEqual(w_after, w_before * 2, delta=1)

    def test_move_shifts_bounding_box(self):
        self._add_square()
        bb_before = self.glyph._ff.boundingBox()
        self.glyph.move(dx=50, dy=0)
        bb_after = self.glyph._ff.boundingBox()
        self.assertAlmostEqual(bb_after[0], bb_before[0] + 50, delta=1)

    def test_remove_overlap_no_error(self):
        self._add_square()
        self.glyph.remove_overlap()

    def test_correct_direction_no_error(self):
        self._add_square()
        self.glyph.correct_direction()

    def test_round_to_int_no_error(self):
        self._add_square()
        self.glyph.round_to_int()

    def test_to_svg_integration(self):
        self._add_square()
        svg = self.glyph.to_svg()
        self.assertIsInstance(svg, str)
        self.assertIn("<svg", svg)


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
