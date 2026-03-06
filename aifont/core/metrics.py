"""Kerning and spacing utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from aifont.core.font import Font


def get_kern_pairs(font: "Font") -> Dict[Tuple[str, str], int]:
    """Return all kerning pairs in *font* as ``{(left, right): value}``."""
    pairs: Dict[Tuple[str, str], int] = {}
    ff = font._ff
    if not hasattr(ff, "subtables"):
        return pairs
    try:
        for name in ff:  # type: ignore[union-attr]
            glyph = ff[name]  # type: ignore[index]
            if hasattr(glyph, "getPosSub"):
                for sub in glyph.getPosSub("*"):
                    # sub[0] = subtable name, sub[1] = type, rest varies
                    if len(sub) >= 4 and sub[1] == "Pair":
                        pairs[(name, sub[2])] = sub[3]
    except (TypeError, AttributeError):
        pass
    return pairs


def set_kern(
    font: "Font",
    left: str,
    right: str,
    value: int,
    subtable: str = "aifont-kern",
) -> None:
    """Set a kern pair value between *left* and *right* glyphs.

    Creates a kern lookup and subtable named *subtable* if it does not
    already exist.
    """
    ff = font._ff
    # Ensure the lookup/subtable exists
    lookups = getattr(ff, "gpos_lookups", None)
    existing = list(lookups) if lookups is not None else []
    if subtable not in existing:
        try:
            ff.addLookup(  # type: ignore[union-attr]
                subtable,
                "gpos_pair",
                (),
                [["kern", [["DFLT", ["dflt"]], ["latn", ["dflt"]]]]],
            )
            ff.addLookupSubtable(subtable, subtable + "-1")  # type: ignore[union-attr]
        except (AttributeError, Exception):
            pass
    # Set the kern value on the left glyph
    try:
        glyph = ff[left]  # type: ignore[index]
        glyph.addPosSub(subtable + "-1", right, value, 0, 0, 0, 0, 0)  # type: ignore[union-attr]
    except (KeyError, AttributeError, Exception):
        pass


def auto_space(font: "Font", target_ratio: float = 0.15) -> None:
    """Adjust sidebearings so that the side-bearing/width ratio is roughly
    *target_ratio* for each glyph.

    This is a simple heuristic; for production use prefer
    ``fontforge.font.autoWidth()``.
    """
    ff = font._ff
    if hasattr(ff, "autoWidth"):
        try:
            ff.autoWidth(0, 0)  # type: ignore[union-attr]
            return
        except (AttributeError, Exception):
            pass
    # Fallback: iterate and set bearings manually
    try:
        for name in ff:  # type: ignore[union-attr]
            glyph = ff[name]  # type: ignore[index]
            w = getattr(glyph, "width", 0)
            if w > 0:
                bearing = int(w * target_ratio)
                glyph.left_side_bearing = bearing
                glyph.right_side_bearing = bearing
    except (TypeError, AttributeError):
        pass
