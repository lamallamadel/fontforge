"""
Unit tests for aifont.core.contour.
"""

from __future__ import annotations

import pytest

try:
    import fontforge as _ff
    _FF = hasattr(_ff, "font")
except ImportError:
    _FF = False

from aifont.core.contour import (
    simplify,
    remove_overlap,
    correct_directions,
    transform,
    round_to_int,
    add_extrema,
)
from aifont.core.font import Font


def test_contour_module_importable():
    assert simplify is not None
    assert remove_overlap is not None
    assert transform is not None


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_simplify_runs():
    font = Font.new()
    g = font.create_glyph("SimplifyGlyph", -1)
    simplify(g)
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_remove_overlap_runs():
    font = Font.new()
    g = font.create_glyph("OverlapGlyph", -1)
    remove_overlap(g)
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_correct_directions_runs():
    font = Font.new()
    g = font.create_glyph("DirGlyph", -1)
    correct_directions(g)
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_transform_identity():
    font = Font.new()
    g = font.create_glyph("TransformGlyph", -1)
    transform(g, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))  # identity — should be no-op
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_round_to_int_runs():
    font = Font.new()
    g = font.create_glyph("RoundGlyph", -1)
    round_to_int(g)
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_add_extrema_runs():
    font = Font.new()
    g = font.create_glyph("ExtremaGlyph", -1)
    add_extrema(g)
    font.close()
