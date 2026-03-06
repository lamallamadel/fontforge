"""
Unit tests for aifont.core.metrics.
"""

from __future__ import annotations

import pytest

try:
    import fontforge as _ff
    _FF = hasattr(_ff, "font")
except ImportError:
    _FF = False

from aifont.core.metrics import (
    KernPair,
    SideBearings,
    SpacingAnalysis,
    get_kern_pairs,
    set_kern,
    auto_space,
    analyze_spacing,
)
from aifont.core.font import Font


def test_metrics_module_importable():
    assert KernPair is not None
    assert SideBearings is not None
    assert SpacingAnalysis is not None


def test_kern_pair_dataclass():
    kp = KernPair(left="A", right="V", value=-50)
    assert kp.left == "A"
    assert kp.right == "V"
    assert kp.value == -50


def test_side_bearings_dataclass():
    sb = SideBearings(left=40, right=30)
    assert sb.left == 40
    assert sb.right == 30


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_get_kern_pairs_empty_font():
    font = Font.new()
    pairs = get_kern_pairs(font)
    assert isinstance(pairs, list)
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_auto_space_runs():
    font = Font.new()
    g = font.create_glyph("SpacedGlyph", -1)
    g.set_width(600)
    auto_space(font, target_ratio=0.1)
    font.close()


@pytest.mark.skipif(not _FF, reason="fontforge not installed")
def test_analyze_spacing_empty():
    font = Font.new()
    result = analyze_spacing(font)
    assert isinstance(result, SpacingAnalysis)
    font.close()
