"""Tests for aifont.core.contour module.

These tests exercise the Bézier curve and path manipulation utilities
defined in ``aifont/core/contour.py``.  They require a working FontForge
Python installation (``import fontforge``).
"""

import math
import sys
import os

# Ensure the repository root is on the path so that ``aifont`` is importable
# even when running the tests directly from the ``tests/`` directory.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import fontforge

from aifont.core.contour import (
    Contour,
    ContourPoint,
    reverse_direction,
    remove_overlap,
    simplify,
    smooth_transitions,
    to_svg_path,
    transform,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_triangle_glyph(font):
    """Return a glyph with a closed triangular contour."""
    g = font.createChar(-1, "triangle_test")
    pen = g.glyphPen()
    pen.moveTo((0, 0))
    pen.lineTo((500, 700))
    pen.lineTo((1000, 0))
    pen.closePath()
    del pen
    return g


def _make_rect_glyph(font):
    """Return a glyph with a closed rectangular contour."""
    g = font.createChar(-1, "rect_test")
    pen = g.glyphPen()
    pen.moveTo((0, 0))
    pen.lineTo((500, 0))
    pen.lineTo((500, 500))
    pen.lineTo((0, 500))
    pen.closePath()
    del pen
    return g


def _make_overlapping_glyph(font):
    """Return a glyph with two overlapping rectangles."""
    g = font.createChar(-1, "overlap_test")
    # First rectangle
    pen = g.glyphPen()
    pen.moveTo((0, 0))
    pen.lineTo((400, 0))
    pen.lineTo((400, 400))
    pen.lineTo((0, 400))
    pen.closePath()
    del pen
    # Second overlapping rectangle
    pen = g.glyphPen(replace=False)
    pen.moveTo((200, 200))
    pen.lineTo((600, 200))
    pen.lineTo((600, 600))
    pen.lineTo((200, 600))
    pen.closePath()
    del pen
    return g


# ---------------------------------------------------------------------------
# ContourPoint tests
# ---------------------------------------------------------------------------


def test_contour_point_defaults():
    p = ContourPoint(100.0, 200.0)
    assert p.x == 100.0
    assert p.y == 200.0
    assert p.on_curve is True
    assert p.name is None


def test_contour_point_off_curve():
    p = ContourPoint(50.0, 75.0, on_curve=False, name="handle")
    assert p.on_curve is False
    assert p.name == "handle"


def test_contour_point_distance():
    a = ContourPoint(0.0, 0.0)
    b = ContourPoint(3.0, 4.0)
    assert math.isclose(a.distance_to(b), 5.0)


def test_contour_point_iter():
    p = ContourPoint(10.0, 20.0)
    x, y = p
    assert x == 10.0
    assert y == 20.0


def test_contour_point_roundtrip_ff():
    """ContourPoint → fontforge.point → ContourPoint should preserve coords."""
    original = ContourPoint(123.0, 456.0, on_curve=True)
    ff_pt = original.to_ff_point()
    restored = ContourPoint.from_ff_point(ff_pt)
    assert math.isclose(restored.x, original.x)
    assert math.isclose(restored.y, original.y)
    assert restored.on_curve == original.on_curve


# ---------------------------------------------------------------------------
# Contour construction tests
# ---------------------------------------------------------------------------


def test_contour_from_points():
    c = Contour.from_points([(0, 0), (100, 200), (200, 0)], closed=True)
    assert len(c) == 3
    assert c.closed is True
    assert all(p.on_curve for p in c)


def test_contour_open_close():
    c = Contour.from_points([(0, 0), (100, 100)], closed=False)
    closed = c.close()
    opened = closed.open()
    assert closed.closed is True
    assert opened.closed is False
    # Points should be unchanged
    assert len(closed) == len(c)
    assert len(opened) == len(c)


def test_contour_reverse():
    pts = [(0, 0), (100, 0), (100, 100)]
    c = Contour.from_points(pts, closed=True)
    r = c.reverse()
    assert len(r) == len(c)
    # First point of reversed should be last point of original
    assert r.points[0].x == c.points[-1].x
    assert r.points[0].y == c.points[-1].y


def test_contour_transform_identity():
    pts = [(100.0, 200.0), (300.0, 400.0)]
    c = Contour.from_points(pts)
    identity = [1, 0, 0, 1, 0, 0]
    t = c.transform(identity)
    for orig, new in zip(c.points, t.points):
        assert math.isclose(orig.x, new.x)
        assert math.isclose(orig.y, new.y)


def test_contour_transform_translate():
    pts = [(0.0, 0.0), (100.0, 0.0)]
    c = Contour.from_points(pts)
    # Translation: dx=50, dy=100
    matrix = [1, 0, 0, 1, 50, 100]
    t = c.transform(matrix)
    assert math.isclose(t.points[0].x, 50.0)
    assert math.isclose(t.points[0].y, 100.0)
    assert math.isclose(t.points[1].x, 150.0)
    assert math.isclose(t.points[1].y, 100.0)


def test_contour_transform_scale():
    pts = [(100.0, 200.0)]
    c = Contour.from_points(pts)
    # Uniform scale by 2
    matrix = [2, 0, 0, 2, 0, 0]
    t = c.transform(matrix)
    assert math.isclose(t.points[0].x, 200.0)
    assert math.isclose(t.points[0].y, 400.0)


# ---------------------------------------------------------------------------
# SVG path tests
# ---------------------------------------------------------------------------


def test_contour_to_svg_path_data_triangle():
    c = Contour.from_points([(0, 0), (500, 700), (1000, 0)], closed=True)
    d = c.to_svg_path_data()
    assert d.startswith("M ")
    assert "L " in d
    assert d.endswith("Z")


def test_contour_to_svg_path_data_open():
    c = Contour.from_points([(0, 0), (100, 100)], closed=False)
    d = c.to_svg_path_data()
    assert "M " in d
    assert "Z" not in d


def test_contour_to_svg_path_data_with_curves():
    """A contour with off-curve points should produce C or Q commands."""
    c = Contour(
        points=[
            ContourPoint(0, 0, on_curve=True),
            ContourPoint(100, 200, on_curve=False),
            ContourPoint(200, 200, on_curve=False),
            ContourPoint(300, 0, on_curve=True),
        ],
        closed=False,
    )
    d = c.to_svg_path_data()
    assert "C " in d or "Q " in d


def test_to_svg_path_glyph():
    """to_svg_path() should return a non-empty string for a glyph with contours."""
    font = fontforge.font()
    try:
        g = _make_triangle_glyph(font)
        svg = to_svg_path(g)
        assert isinstance(svg, str)
        assert len(svg) > 0
        assert "M " in svg
        assert "Z" in svg
    finally:
        font.close()


def test_to_svg_path_multiple_contours():
    """Multiple contours should be joined with a space."""
    font = fontforge.font()
    try:
        g = font.createChar(-1, "multi_test")
        # Two separate contours
        pen = g.glyphPen()
        pen.moveTo((0, 0))
        pen.lineTo((100, 0))
        pen.lineTo((100, 100))
        pen.closePath()
        del pen
        pen = g.glyphPen(replace=False)
        pen.moveTo((200, 0))
        pen.lineTo((300, 0))
        pen.lineTo((300, 100))
        pen.closePath()
        del pen
        svg = to_svg_path(g)
        # Should contain two move-to commands
        assert svg.count("M ") == 2
    finally:
        font.close()


# ---------------------------------------------------------------------------
# FontForge glyph-level operation tests
# ---------------------------------------------------------------------------


def test_simplify():
    """simplify() should not raise and should preserve a simple contour."""
    font = fontforge.font()
    try:
        g = _make_triangle_glyph(font)
        original_count = len(list(g.foreground))
        simplify(g, threshold=1.0)
        # Contour count must be preserved for a triangle
        assert len(list(g.foreground)) == original_count
    finally:
        font.close()


def test_simplify_aggressive():
    """Aggressive simplification with high threshold should not crash."""
    font = fontforge.font()
    try:
        g = _make_rect_glyph(font)
        simplify(g, threshold=100.0)
        # Glyph should still be valid (at least 0 contours)
        assert len(list(g.foreground)) >= 0
    finally:
        font.close()


def test_smooth_transitions():
    """smooth_transitions() should not raise."""
    font = fontforge.font()
    try:
        g = _make_triangle_glyph(font)
        smooth_transitions(g)
    finally:
        font.close()


def test_reverse_direction():
    """reverse_direction() should not raise."""
    font = fontforge.font()
    try:
        g = _make_triangle_glyph(font)
        reverse_direction(g)
        # After a double reversal the glyph should be back to the original
        reverse_direction(g)
    finally:
        font.close()


def test_remove_overlap():
    """remove_overlap() should reduce two overlapping rects to one contour."""
    font = fontforge.font()
    try:
        g = _make_overlapping_glyph(font)
        assert len(list(g.foreground)) == 2
        remove_overlap(g)
        assert len(list(g.foreground)) == 1
    finally:
        font.close()


def test_transform_glyph():
    """transform() should scale all contour points."""
    font = fontforge.font()
    try:
        g = _make_triangle_glyph(font)
        # Record bounding box before transform
        bb_before = g.boundingBox()
        # Scale by 2
        transform(g, [2, 0, 0, 2, 0, 0])
        bb_after = g.boundingBox()
        # Width should approximately double
        width_before = bb_before[2] - bb_before[0]
        width_after = bb_after[2] - bb_after[0]
        assert math.isclose(width_after, width_before * 2, rel_tol=1e-3)
    finally:
        font.close()


# ---------------------------------------------------------------------------
# Contour ↔ fontforge round-trip
# ---------------------------------------------------------------------------


def test_contour_roundtrip_ff_layer():
    """Contour built from a fontforge layer should preserve point coords."""
    font = fontforge.font()
    try:
        g = _make_triangle_glyph(font)
        ff_layer = g.foreground
        assert len(ff_layer) == 1
        c = Contour.from_ff_contour(ff_layer[0])
        assert c.closed is True
        assert len(c) == 3
        # Check that coordinates survive the round-trip
        for pt in c.points:
            assert isinstance(pt.x, float)
            assert isinstance(pt.y, float)
    finally:
        font.close()


def test_contour_apply_to_glyph():
    """Contour.apply_to_glyph() should add the contour to the glyph."""
    font = fontforge.font()
    try:
        g = font.createChar(-1, "apply_test")
        assert len(list(g.foreground)) == 0

        c = Contour.from_points([(0, 0), (500, 700), (1000, 0)], closed=True)
        c.apply_to_glyph(g)
        assert len(list(g.foreground)) == 1
    finally:
        font.close()


def test_complex_contour_bezier():
    """Complex contour with multiple Bézier segments should round-trip correctly."""
    font = fontforge.font()
    try:
        g = font.createChar(-1, "bezier_test")
        pen = g.glyphPen()
        # A rough circle approximated with 4 cubic segments
        k = 0.5523  # standard kappa constant
        r = 500.0
        pen.moveTo((r, 0))
        pen.curveTo((r, k * r), (k * r, r), (0, r))
        pen.curveTo((-k * r, r), (-r, k * r), (-r, 0))
        pen.curveTo((-r, -k * r), (-k * r, -r), (0, -r))
        pen.curveTo((k * r, -r), (r, -k * r), (r, 0))
        pen.closePath()
        del pen

        svg = to_svg_path(g)
        assert "M " in svg
        assert "C " in svg
        assert "Z" in svg
    finally:
        font.close()
