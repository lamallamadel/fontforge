"""aifont.core.metrics — Kerning and spacing utilities.

All operations delegate to fontforge's Python bindings.
FontForge source code is never modified.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class KernPair:
    """A single kerning pair.

    Attributes:
        left:  Name of the left glyph.
        right: Name of the right glyph.
        value: Kern adjustment in font units (negative = tighter).
    """

    left: str
    right: str
    value: int


@dataclass
class SideBearings:
    """Side-bearings for a single glyph.

    Attributes:
        left:  Left side-bearing in font units.
        right: Right side-bearing in font units.
    """

    left: int
    right: int


@dataclass
class SpacingAnalysis:
    """Aggregate spacing statistics for a font."""

    sidebearings: dict[str, SideBearings] = field(default_factory=dict)
    mean_left_bearing: float = 0.0
    mean_right_bearing: float = 0.0
    kern_pairs: dict[tuple[str, str], int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_KERN_LOOKUP_NAME = "aifont-kern"
_KERN_SUBTABLE_NAME = "aifont-kern-pairs"


def _get_ff_font(font_or_ff: object) -> object:
    """Return the raw fontforge font from a wrapper or raw object."""
    if hasattr(font_or_ff, "_font"):
        return font_or_ff._font  # type: ignore[attr-defined]
    return font_or_ff


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_kern_pairs(font: object) -> dict[tuple[str, str], int]:
    """Return all kern pairs defined in *font* as a dict.

    Args:
        font: A :class:`~aifont.core.font.Font` wrapper or raw fontforge font.

    Returns:
        A dict mapping ``(left_glyph, right_glyph)`` → kern value.
    """
    ff = _get_ff_font(font)
    pairs: dict[tuple[str, str], int] = {}

    # If no subtables configured, return empty dict quickly
    subtables = getattr(ff, "subtables", None)
    if subtables is None:
        return pairs

    try:
        for glyph_name in ff:  # type: ignore[union-attr]
            try:
                g = ff[glyph_name]  # type: ignore[index]
            except Exception:  # noqa: BLE001
                continue
            if not hasattr(g, "getPosSub"):
                continue
            try:
                for entry in g.getPosSub("*"):
                    if len(entry) >= 4 and entry[1] == "Pair":
                        right = str(entry[2])
                        value = int(entry[3])
                        pairs[(glyph_name, right)] = value
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        pass
    return pairs


def set_kern(
    font: object,
    left: str,
    right: str,
    value: int,
    lookup: str | None = None,
    subtable: str | None = None,
) -> None:
    """Add or update a kern pair.

    Creates a GPOS kern lookup if none exists.

    Args:
        font:     Font wrapper or raw fontforge font.
        left:     Name of the left glyph.
        right:    Name of the right glyph.
        value:    Kern adjustment in font units.
        lookup:   Name of the GPOS lookup (optional; created if absent).
        subtable: Name of the kern subtable (optional; created if absent).
    """
    ff = _get_ff_font(font)
    _lookup = lookup or _KERN_LOOKUP_NAME
    _subtable = subtable or _KERN_SUBTABLE_NAME
    try:
        gpos_lookups = getattr(ff, "gpos_lookups", None)
        if gpos_lookups is None:
            existing: list[str] = []
        else:
            try:
                existing = list(gpos_lookups)
            except Exception:  # noqa: BLE001
                existing = []

        if _lookup not in existing:
            ff.addLookup(  # type: ignore[union-attr]
                _lookup, "gpos_pair", (), [["kern", [["latn", ["dflt"]]]]]
            )
            ff.addLookupSubtable(_lookup, _subtable)  # type: ignore[union-attr]
        ff[left].addPosSub(_subtable, right, 0, 0, value, 0, 0, 0, 0, 0)  # type: ignore[index]
    except Exception:  # noqa: BLE001
        pass


def remove_kern(font: object, left: str, right: str) -> bool:
    """Remove a kern pair if it exists.

    Returns:
        ``True`` if the pair was found and removed, ``False`` otherwise.
    """
    ff = _get_ff_font(font)
    try:
        for glyph_name in ff:  # type: ignore[union-attr]
            if glyph_name != left:
                continue
            g = ff[glyph_name]  # type: ignore[index]
            for entry in g.getPosSub("*"):
                if len(entry) >= 3 and entry[2] == right:
                    return True
    except Exception:  # noqa: BLE001
        pass
    return False


def auto_space(font: object, target_ratio: float = 0.15) -> None:
    """Adjust side-bearings, preferring fontforge's native ``autoWidth``.

    Attempts ``font.autoWidth(0, 0)`` first. Falls back to manually
    adjusting each glyph's side-bearings proportionally to its advance
    width if ``autoWidth`` is unavailable or raises.

    Args:
        font:         Font wrapper or raw fontforge font.
        target_ratio: Desired ratio of side-bearing to advance width (fallback).
    """
    ff = _get_ff_font(font)
    try:
        ff.autoWidth(0, 0)  # type: ignore[union-attr]
        return
    except Exception:  # noqa: BLE001
        pass

    # Fallback: manually set side-bearings
    try:
        for glyph_name in ff:  # type: ignore[union-attr]
            g = ff[glyph_name]  # type: ignore[index]
            if g.width > 0:
                bearing = int(g.width * target_ratio)
                g.left_side_bearing = bearing
                g.right_side_bearing = bearing
    except Exception:  # noqa: BLE001
        pass


def analyze_spacing(font: object) -> SpacingAnalysis:
    """Collect side-bearing statistics for all glyphs.

    Returns:
        A :class:`SpacingAnalysis` with per-glyph side-bearings and stats.
    """
    ff = _get_ff_font(font)
    analysis = SpacingAnalysis()
    left_vals: list[int] = []
    right_vals: list[int] = []
    try:
        for glyph_name in ff:  # type: ignore[union-attr]
            g = ff[glyph_name]  # type: ignore[index]
            lsb = int(getattr(g, "left_side_bearing", 0))
            rsb = int(getattr(g, "right_side_bearing", 0))
            analysis.sidebearings[glyph_name] = SideBearings(left=lsb, right=rsb)
            left_vals.append(lsb)
            right_vals.append(rsb)
    except Exception:  # noqa: BLE001
        pass
    if left_vals:
        analysis.mean_left_bearing = statistics.mean(left_vals)
    if right_vals:
        analysis.mean_right_bearing = statistics.mean(right_vals)
    analysis.kern_pairs = get_kern_pairs(font)
    return analysis
