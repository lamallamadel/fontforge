"""Shared pytest fixtures and mock helpers for AIFont tests."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, PropertyMock
from typing import Any, Dict, Iterator, List, Optional

import pytest


# ---------------------------------------------------------------------------
# Mock fontforge module
# ---------------------------------------------------------------------------

def _make_mock_ff_glyph(
    name: str = "A",
    unicode_val: int = 0x0041,
    width: int = 600,
) -> MagicMock:
    """Return a MagicMock that mimics a fontforge.glyph object."""
    glyph = MagicMock()
    glyph.glyphname = name
    glyph.unicode = unicode_val
    glyph.width = width
    glyph.left_side_bearing = 60
    glyph.right_side_bearing = 60
    glyph.foreground = MagicMock()
    # Make foreground iterable (no contours by default)
    glyph.foreground.__iter__ = MagicMock(return_value=iter([]))
    glyph.importOutlines = MagicMock()
    glyph.clear = MagicMock()
    glyph.autoHint = MagicMock()
    glyph.simplify = MagicMock()
    glyph.removeOverlap = MagicMock()
    glyph.transform = MagicMock()
    glyph.getPosSub = MagicMock(return_value=[])
    glyph.addPosSub = MagicMock()
    return glyph


def _make_mock_ff_font(
    name: str = "TestFont",
    glyphs: Optional[List[MagicMock]] = None,
) -> MagicMock:
    """Return a MagicMock that mimics a fontforge.font object."""
    if glyphs is None:
        glyphs = [
            _make_mock_ff_glyph("A", 0x0041),
            _make_mock_ff_glyph("B", 0x0042),
            _make_mock_ff_glyph("space", 0x0020, width=250),
        ]

    ff_font = MagicMock()
    ff_font.fontname = name
    ff_font.familyname = name
    ff_font.weight = "Regular"
    ff_font.version = "1.0"
    ff_font.em = 1000

    glyph_map: Dict[str, MagicMock] = {g.glyphname: g for g in glyphs}
    ff_font.__iter__ = MagicMock(side_effect=lambda: iter(glyph_map.keys()))
    ff_font.__getitem__ = MagicMock(side_effect=lambda k: glyph_map[k])
    ff_font.createChar = MagicMock(
        side_effect=lambda u, n: glyph_map.setdefault(
            n, _make_mock_ff_glyph(n, u)
        )
    )
    ff_font.save = MagicMock()
    ff_font.generate = MagicMock()
    ff_font.close = MagicMock()
    ff_font.autoWidth = MagicMock()
    ff_font.addLookup = MagicMock()
    ff_font.addLookupSubtable = MagicMock()
    ff_font.gpos_lookups = None
    ff_font.subtables = None
    return ff_font


@pytest.fixture()
def mock_ff_glyph() -> MagicMock:
    """Fixture: a single mock fontforge.glyph object."""
    return _make_mock_ff_glyph()


@pytest.fixture()
def mock_ff_font() -> MagicMock:
    """Fixture: a mock fontforge.font object with three glyphs."""
    return _make_mock_ff_font()


# ---------------------------------------------------------------------------
# Wrapped SDK fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def font(mock_ff_font: MagicMock):
    """Fixture: an aifont.core.font.Font wrapping a mock fontforge.font."""
    from aifont.core.font import Font

    return Font(mock_ff_font)


@pytest.fixture()
def glyph(mock_ff_glyph: MagicMock):
    """Fixture: an aifont.core.glyph.Glyph wrapping a mock fontforge.glyph."""
    from aifont.core.glyph import Glyph

    return Glyph(mock_ff_glyph)


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------

@pytest.fixture()
def api_client():
    """Fixture: synchronous test client for the FastAPI app."""
    from starlette.testclient import TestClient
    from aifont.api.main import create_app

    application = create_app()
    with TestClient(application) as client:
        yield client


@pytest.fixture()
async def async_api_client():
    """Fixture: async HTTPX test client for the FastAPI app."""
    import httpx
    from aifont.api.main import create_app

    application = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        yield client
