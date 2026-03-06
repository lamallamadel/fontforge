"""
aifont.core.svg_parser — import SVG files/paths into font glyphs.

Parse SVG ``<path d="…">`` data and inject the resulting contours into a
fontforge glyph.  Both single-path and multi-path SVGs are supported.
Basic SVG transforms (translate, scale) are applied before importing.

FontForge source code is never modified.

Public API
----------
svg_to_glyph(svg_path, font, unicode_point, glyph_name)
    Parse an SVG file and load its paths into a new glyph.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import fontforge  # type: ignore
    if not hasattr(fontforge, "font"):
        fontforge = None  # type: ignore  # namespace package stub, not the real extension
    _FF_AVAILABLE = fontforge is not None
except ImportError:  # pragma: no cover
    fontforge = None  # type: ignore
    _FF_AVAILABLE = False

# SVG namespace
_SVG_NS = "http://www.w3.org/2000/svg"

# ---------------------------------------------------------------------------
# SVG transform helpers
# ---------------------------------------------------------------------------


def _parse_transform(transform_str: str) -> Tuple[float, float, float, float, float, float]:
    """Parse a simple SVG transform attribute into a 6-tuple matrix.

    Supported: ``translate(dx, dy)``, ``scale(sx[, sy])``.
    Returns the identity matrix if the transform is not recognised.
    """
    # Default: identity
    matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

    if not transform_str:
        return matrix

    t = transform_str.strip()

    m = re.match(r"translate\(\s*([+-]?[\d.]+)\s*,?\s*([+-]?[\d.]+)?\s*\)", t)
    if m:
        dx = float(m.group(1))
        dy = float(m.group(2)) if m.group(2) else 0.0
        return (1.0, 0.0, 0.0, 1.0, dx, dy)

    m = re.match(r"scale\(\s*([+-]?[\d.]+)\s*,?\s*([+-]?[\d.]+)?\s*\)", t)
    if m:
        sx = float(m.group(1))
        sy = float(m.group(2)) if m.group(2) else sx
        return (sx, 0.0, 0.0, sy, 0.0, 0.0)

    return matrix


def _apply_matrix(
    x: float, y: float,
    matrix: Tuple[float, float, float, float, float, float],
) -> Tuple[float, float]:
    """Apply a 2-D affine matrix to a point (x, y)."""
    a, b, c, d, e, f = matrix
    return (a * x + c * y + e, b * x + d * y + f)


# ---------------------------------------------------------------------------
# SVG path tokeniser / parser
# ---------------------------------------------------------------------------

_PATH_CMD_RE = re.compile(
    r"([MmZzLlHhVvCcSsQqTtAa])|([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"
)


def _tokenise_path(d: str) -> List[object]:
    """Return a list of command letters and float values from a path ``d`` attribute."""
    tokens: List[object] = []
    for m in _PATH_CMD_RE.finditer(d):
        if m.group(1):
            tokens.append(m.group(1))
        else:
            tokens.append(float(m.group(2)))
    return tokens


def _parse_path_d(d: str) -> List[Tuple[str, List[float]]]:
    """Parse SVG path data into a list of ``(command, [args])`` tuples.

    Only absolute commands are returned.  Relative commands are converted
    to absolute using the current cursor position.
    """
    tokens = _tokenise_path(d)
    commands: List[Tuple[str, List[float]]] = []

    # Number of coordinate arguments expected per command.
    _arg_count = {
        "M": 2, "L": 2, "H": 1, "V": 1,
        "C": 6, "S": 4, "Q": 4, "T": 2,
        "A": 7, "Z": 0,
    }

    cx, cy = 0.0, 0.0  # current point
    sx, sy = 0.0, 0.0  # path start (for Z)
    cmd = ""
    args: List[float] = []

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if isinstance(tok, str):
            cmd = tok
            i += 1
            args = []
        else:
            args.append(tok)  # type: ignore[arg-type]
            i += 1

        upper = cmd.upper()
        n = _arg_count.get(upper, 0)

        if upper == "Z":
            commands.append(("Z", []))
            cx, cy = sx, sy
            args = []
            continue

        if n == 0 or len(args) < n:
            continue

        # Convert relative → absolute
        rel = cmd.islower()
        a = list(args[:n])
        args = args[n:]

        if rel:
            if upper == "H":
                a[0] += cx
            elif upper == "V":
                a[0] += cy
            elif upper in ("M", "L", "T"):
                a[0] += cx
                a[1] += cy
            elif upper == "C":
                a[0] += cx
                a[1] += cy
                a[2] += cx
                a[3] += cy
                a[4] += cx
                a[5] += cy
            elif upper == "S":
                a[0] += cx
                a[1] += cy
                a[2] += cx
                a[3] += cy
            elif upper == "Q":
                a[0] += cx
                a[1] += cy
                a[2] += cx
                a[3] += cy
            elif upper == "A":
                a[5] += cx
                a[6] += cy

        commands.append((upper, a))

        # Update current point.
        if upper in ("M", "L", "T"):
            cx, cy = a[0], a[1]
            if upper == "M":
                sx, sy = cx, cy
        elif upper == "H":
            cx = a[0]
        elif upper == "V":
            cy = a[0]
        elif upper in ("C", "S"):
            cx, cy = a[-2], a[-1]
        elif upper in ("Q",):
            cx, cy = a[2], a[3]
        elif upper == "A":
            cx, cy = a[5], a[6]

    return commands


# ---------------------------------------------------------------------------
# Glyph injection
# ---------------------------------------------------------------------------


def _flip_y(y: float, em: float = 1000.0) -> float:
    """Flip Y coordinate from SVG (top-down) to font (bottom-up) space."""
    return em - y


def _inject_path_into_glyph(
    ff_glyph: object,
    d: str,
    matrix: Tuple[float, float, float, float, float, float],
    em: float = 1000.0,
) -> None:
    """Parse SVG path *d* and draw it into *ff_glyph* using a glyph pen."""
    pen = ff_glyph.glyphPen()
    commands = _parse_path_d(d)

    last_ctrl: Optional[Tuple[float, float]] = None

    for cmd, args in commands:
        if cmd == "M":
            x, y = _apply_matrix(args[0], args[1], matrix)
            pen.moveTo((x, _flip_y(y, em)))
            last_ctrl = None
        elif cmd == "Z":
            pen.closePath()
            last_ctrl = None
        elif cmd == "L":
            x, y = _apply_matrix(args[0], args[1], matrix)
            pen.lineTo((x, _flip_y(y, em)))
            last_ctrl = None
        elif cmd == "H":
            x, _ = _apply_matrix(args[0], 0, matrix)
            pen.lineTo((x, _flip_y(0, em)))  # y unchanged — caller should track
            last_ctrl = None
        elif cmd == "V":
            _, y = _apply_matrix(0, args[0], matrix)
            pen.lineTo((_apply_matrix(0, 0, matrix)[0], _flip_y(y, em)))
            last_ctrl = None
        elif cmd == "C":
            x1, y1 = _apply_matrix(args[0], args[1], matrix)
            x2, y2 = _apply_matrix(args[2], args[3], matrix)
            x, y   = _apply_matrix(args[4], args[5], matrix)
            pen.curveTo(
                (x1, _flip_y(y1, em)),
                (x2, _flip_y(y2, em)),
                (x, _flip_y(y, em)),
            )
            last_ctrl = (x2, _flip_y(y2, em))
        elif cmd == "Q":
            x1, y1 = _apply_matrix(args[0], args[1], matrix)
            x, y   = _apply_matrix(args[2], args[3], matrix)
            pen.qCurveTo((x1, _flip_y(y1, em)), (x, _flip_y(y, em)))
            last_ctrl = (x1, _flip_y(y1, em))

    pen = None  # flush


def _get_em(ff_font: object) -> float:
    """Return the em size of the font."""
    try:
        return float(ff_font.em)
    except Exception:
        return 1000.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def svg_to_glyph(
    svg_path: str | Path,
    font: object,
    unicode_point: int = -1,
    glyph_name: Optional[str] = None,
) -> object:
    """Parse an SVG file and load its paths into a glyph.

    The function creates (or overwrites) a glyph in *font* whose Unicode
    code point is *unicode_point*.  All ``<path>`` elements in the SVG
    are imported.  Basic ``transform`` attributes (``translate``,
    ``scale``) on each ``<path>`` are applied.

    Args:
        svg_path:      Path to the ``.svg`` file.
        font:          :class:`~aifont.core.font.Font` wrapper or raw
                       ``fontforge.font``.
        unicode_point: Unicode code point for the new glyph (default: -1
                       for no mapping).
        glyph_name:    Explicit glyph name.  When omitted, the function
                       uses the SVG filename stem (e.g. ``"glyph_A"``).

    Returns:
        The raw ``fontforge.glyph`` object that was created/modified.

    Raises:
        RuntimeError: If the fontforge Python bindings are unavailable.
        FileNotFoundError: If *svg_path* does not exist.
    """
    if fontforge is None:
        raise RuntimeError(
            "fontforge Python bindings are not available. "
            "Install FontForge with Python support."
        )

    svg_path = Path(svg_path)
    if not svg_path.exists():
        raise FileNotFoundError(f"SVG file not found: {svg_path}")

    # Resolve the font object.
    ff_font = font._font if hasattr(font, "_font") else font  # type: ignore[attr-defined]
    em = _get_em(ff_font)

    # Derive glyph name from filename if not provided.
    if glyph_name is None:
        glyph_name = svg_path.stem

    # Create (or retrieve) the glyph slot.
    if unicode_point >= 0:
        ff_glyph = ff_font.createChar(unicode_point, glyph_name)
    else:
        ff_glyph = ff_font.createChar(-1, glyph_name)

    ff_glyph.clear()

    # Parse SVG.
    tree = ET.parse(str(svg_path))
    root = tree.getroot()

    # Collect viewBox for optional scaling.
    viewbox_scale: Tuple[float, float, float, float, float, float] = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    vb = root.get("viewBox")
    if vb:
        parts = vb.replace(",", " ").split()
        if len(parts) == 4:
            vb_x, vb_y, vb_w, vb_h = map(float, parts)
            if vb_w > 0 and vb_h > 0:
                sx = em / vb_w
                sy = em / vb_h
                viewbox_scale = (sx, 0.0, 0.0, sy, -vb_x * sx, -vb_y * sy)

    # Iterate over all <path> elements regardless of nesting.
    for elem in root.iter():
        tag = elem.tag.replace(f"{{{_SVG_NS}}}", "")
        if tag != "path":
            continue
        d = elem.get("d", "").strip()
        if not d:
            continue
        transform_attr = elem.get("transform", "")
        local_matrix = _parse_transform(transform_attr)

        # Compose local transform with viewBox scale.
        # Simple composition: apply viewbox_scale then local_matrix.
        a1, b1, c1, d1, e1, f1 = viewbox_scale
        a2, b2, c2, d2, e2, f2 = local_matrix
        composed = (
            a1 * a2 + b1 * c2,
            a1 * b2 + b1 * d2,
            c1 * a2 + d1 * c2,
            c1 * b2 + d1 * d2,
            e1 * a2 + f1 * c2 + e2,
            e1 * b2 + f1 * d2 + f2,
        )

        _inject_path_into_glyph(ff_glyph, d, composed, em)

    return ff_glyph
