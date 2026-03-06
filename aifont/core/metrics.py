"""Kerning and spacing utilities for AIFont fonts."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aifont.core.font import Font

KernPair = tuple[str, str, int]


def get_kern_pairs(font: Font) -> list[KernPair]:
    """Return all kern pairs defined in *font* as ``(left, right, value)`` triples.

    Iterates over all GPOS kern lookups via fontforge's lookup API.
    """
    pairs: list[KernPair] = []
    ff = font._raw
    for lookup in ff.gpos_lookups:
        linfo = ff.getLookupInfo(lookup)
        if linfo[0] != "kern":
            continue
        for subtable in ff.getLookupSubtables(lookup):
            for glyph_name in ff:
                glyph = ff[glyph_name]
                kerns: dict = {}
                try:
                    kerns = dict(glyph.getPosSub(subtable) or {})
                except Exception:  # noqa: BLE001
                    continue
                for right, value in kerns.items():
                    pairs.append((glyph_name, right, value))
    return pairs


def set_kern(font: Font, left: str, right: str, value: int) -> None:
    """Set a kern pair *value* for (*left*, *right*) in *font*.

    Creates a dedicated kern lookup/subtable if none exists.
    """
    ff = font._raw
    lookup_name = "aifont-kern"
    subtable_name = "aifont-kern-1"

    if lookup_name not in (ff.gsub_lookups + ff.gpos_lookups):
        ff.addLookup(lookup_name, "gpos_pair", 0, [["kern", [["latn", ["dflt"]]]]])
        ff.addLookupSubtable(lookup_name, subtable_name)

    ff[left].addPosSub(subtable_name, right, 0, 0, value, 0, 0, 0, 0, 0)


def auto_space(font: Font, target_ratio: float = 0.15) -> None:
    """Apply automatic sidebearing spacing to all glyphs in *font*.

    Uses fontforge's built-in :meth:`~fontforge.glyph.autoWidth` to set
    sidebearings so that the whitespace-to-em ratio approximates
    *target_ratio*.

    Args:
        font: The :class:`~aifont.core.font.Font` to space.
        target_ratio: Target ratio of sidebearing to em size (0–1).
    """
    ff = font._raw
    em = ff.em
    separation = int(em * target_ratio)
    ff.autoWidth(separation)
