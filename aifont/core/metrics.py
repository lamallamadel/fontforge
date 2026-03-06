"""Kerning and spacing utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

if TYPE_CHECKING:
    from aifont.core.font import Font


def get_kern_pairs(font: "Font") -> List[Tuple[str, str, int]]:
    """Return all kern pairs defined in the font.

    Args:
        font: The :class:`~aifont.core.font.Font` to inspect.

    Returns:
        A list of ``(left_glyph, right_glyph, kern_value)`` tuples.
    """
    pairs: List[Tuple[str, str, int]] = []
    if font._ff is None:
        return pairs
    for glyph in font._ff.glyphs():
        for subtable, kern in glyph.getPosSub("*"):
            # Only process kern lookups
            if "kern" in subtable.lower():
                pairs.append((glyph.glyphname, subtable, kern))
    return pairs


def set_kern(font: "Font", left: str, right: str, value: int) -> None:
    """Set a kern pair value.

    Args:
        font:  The font to modify.
        left:  Name of the left glyph.
        right: Name of the right glyph.
        value: Kern value in font units (negative = tighter).
    """
    if font._ff is None:
        return
    # Ensure a kern lookup/subtable exists
    lookup = "kern-pairs"
    subtable = "kern-pairs-1"
    lookup_exists = False
    if hasattr(font._ff, "getLookupInfo"):
        try:
            font._ff.getLookupInfo(lookup)
            lookup_exists = True
        except Exception:
            lookup_exists = False
    if not lookup_exists:
        font._ff.addLookup(lookup, "gpos_pair", (), [["kern", [["latn", ["dflt"]]]]])
        font._ff.addLookupSubtable(lookup, subtable)
    font._ff[left].addPosSub(subtable, right, 0, 0, value, 0, 0, 0, 0, 0)


def auto_space(font: "Font", target_ratio: float = 0.15) -> None:
    """Apply automatic sidebearing spacing to all glyphs.

    Args:
        font:         The font to space.
        target_ratio: Target ratio of sidebearing to em-size (default 0.15).
    """
    if font._ff is None:
        return
    em = font._ff.em
    target = int(em * target_ratio)
    for glyph in font._ff.glyphs():
        if glyph.width > 0:
            glyph.left_side_bearing = target
            glyph.right_side_bearing = target
