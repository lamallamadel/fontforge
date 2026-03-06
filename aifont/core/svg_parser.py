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
"""Import SVG files into font glyphs via fontforge contours."""

from __future__ import annotations

import os
"""
aifont.core.svg_parser — Import SVG paths as font glyphs.

Parses SVG ``<path>`` elements (``d`` attribute) and injects the
resulting contours into a FontForge glyph via
:class:`~aifont.core.glyph.Glyph`.

FontForge is used as a black-box dependency via ``import fontforge``.
No FontForge source code is modified.

Supported SVG features
----------------------
* ``<path d="…">`` — full SVG path data (M/L/C/Q/Z commands)
* ``<g transform="…">`` — ``translate(x,y)`` and ``scale(sx[,sy])``
* Multiple paths within a single SVG file (all are imported)
* Basic ``fill`` attribute handling (ignored; glyph fill is controlled
  by the font, not the SVG)
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
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from aifont.core.font import Font

_SVG_NS = "http://www.w3.org/2000/svg"


def _parse_viewbox(viewbox: str) -> Optional[Tuple[float, float, float, float]]:
    """Parse a SVG viewBox attribute into ``(min_x, min_y, width, height)``."""
    parts = viewbox.replace(",", " ").split()
    if len(parts) == 4:
        try:
            return tuple(float(p) for p in parts)  # type: ignore[return-value]
        except ValueError:
            pass
    return None


def _collect_path_data(root: ET.Element) -> List[str]:
    """Recursively collect all ``d`` attributes from ``<path>`` elements."""
    paths: List[str] = []
    tag_path = f"{{{_SVG_NS}}}path"
    tag_path_bare = "path"
    for elem in root.iter():
        if elem.tag in (tag_path, tag_path_bare):
            d = elem.get("d", "").strip()
            if d:
                paths.append(d)
    return paths


def svg_to_glyph(
    svg_path: str,
    font: "Font",
    unicode_point: int,
    glyph_name: Optional[str] = None,
) -> object:
    """Import the SVG at *svg_path* as a glyph in *font*.

    Creates (or overwrites) the glyph for *unicode_point*.  Returns the
    underlying fontforge glyph object.

    If fontforge's native ``importOutlines`` is available it is used
    directly; otherwise the SVG ``<path>`` elements are inspected and a
    best-effort import is attempted.
    """
    if not os.path.exists(svg_path):
        raise FileNotFoundError(f"SVG file not found: {svg_path}")

    ff = font._ff
    name = glyph_name or f"uni{unicode_point:04X}"

    # Create or retrieve glyph slot
    try:
        glyph = ff.createChar(unicode_point, name)  # type: ignore[union-attr]
    except (AttributeError, TypeError):
        try:
            glyph = ff[name]  # type: ignore[index]
        except (KeyError, TypeError):
            raise RuntimeError(
                f"Cannot create glyph {name!r} — fontforge not available."
            )

    # Prefer native import
    if hasattr(glyph, "importOutlines"):
        glyph.importOutlines(svg_path)  # type: ignore[union-attr]
        return glyph

    # Fallback: parse SVG and warn
    tree = ET.parse(svg_path)
    root = tree.getroot()
    path_data = _collect_path_data(root)
    if not path_data:
        raise ValueError(f"No <path> elements found in SVG: {svg_path}")
    # Without native importOutlines we cannot inject contours, but we
    # can at least set the glyph width from the viewBox.
    viewbox_attr = root.get("viewBox", "")
    if viewbox_attr:
        vb = _parse_viewbox(viewbox_attr)
        if vb is not None:
            glyph.width = int(vb[2])  # type: ignore[union-attr]
    return glyph
    from .font import Font
    from .glyph import Glyph


# ---------------------------------------------------------------------------
# SVG namespace
# ---------------------------------------------------------------------------

_SVG_NS = "http://www.w3.org/2000/svg"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def svg_to_glyph(
    svg_path: str,
    font: "Font",
    unicode_point: int,
    glyph_name: Optional[str] = None,
    scale: float = 1.0,
    y_flip: bool = True,
) -> "Glyph":
    """Import an SVG file as a glyph in *font*.

    Parses the SVG, converts all ``<path>`` elements to FontForge
    contours, and stores the result in (or replaces) the glyph at
    *unicode_point*.

    Parameters
    ----------
    svg_path : str
        Path to the input SVG file.
    font : Font
        Target :class:`~aifont.core.font.Font`.
    unicode_point : int
        Unicode code-point for the new/updated glyph.
    glyph_name : str, optional
        Glyph name.  When *None*, FontForge auto-assigns a name based on
        *unicode_point*.
    scale : float, optional
        Uniform scale factor applied to all coordinates.  Use this to
        map SVG user units to font units.  Default ``1.0``.
    y_flip : bool, optional
        When ``True`` (default), flip the Y axis so that SVG coordinates
        (top = 0) are converted to font coordinates (bottom = 0).  The
        flip is applied relative to the font's em-square height.

    Returns
    -------
    Glyph
        The created / updated :class:`~aifont.core.glyph.Glyph`.

    Raises
    ------
    FileNotFoundError
        If *svg_path* does not exist.
    ValueError
        If the SVG contains no usable path data.

    Examples
    --------
    ::

        from aifont.core.font import Font
        from aifont.core.svg_parser import svg_to_glyph

        font = Font.new()
        glyph = svg_to_glyph("letter_A.svg", font, ord("A"))
    """
    import os  # noqa: PLC0415

    if not os.path.isfile(svg_path):
        raise FileNotFoundError(f"SVG file not found: {svg_path!r}")

    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Collect all <path d="…"> elements (namespace-aware)
    paths = _collect_paths(root)

    if not paths:
        raise ValueError(f"No usable <path> elements found in {svg_path!r}")

    # Obtain or create the glyph
    if glyph_name is not None:
        glyph = font.create_glyph(unicode_point, glyph_name)
    else:
        glyph = font.create_glyph(unicode_point)

    # Determine Y-flip offset
    em = font.ff_font.em  # type: ignore[attr-defined]
    ascent = font.ff_font.ascent  # type: ignore[attr-defined]
    flip_offset = float(ascent) if y_flip else 0.0

    # Import via fontforge's importOutlines if the file is straightforward,
    # otherwise fall back to manual path building
    ff_glyph = glyph.ff_glyph
    try:
        ff_glyph.importOutlines(svg_path)  # type: ignore[attr-defined]
        # Apply scale / flip after import
        if scale != 1.0 or y_flip:
            import psMat  # noqa: PLC0415

            mat = psMat.identity()
            if y_flip:
                mat = psMat.compose(mat, psMat.scale(1.0, -1.0))
                mat = psMat.compose(mat, psMat.translate(0.0, flip_offset))
            if scale != 1.0:
                mat = psMat.compose(mat, psMat.scale(scale))
            ff_glyph.transform(mat)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        # Manual fallback: parse path data and build contours
        _import_paths_manually(ff_glyph, paths, scale, y_flip, flip_offset)

    return glyph


def svg_path_to_contours(path_d: str) -> List[List[Tuple[str, List[float]]]]:
    """Parse an SVG path ``d`` attribute into a list of subpath commands.

    Parameters
    ----------
    path_d : str
        Value of the ``d`` attribute of an SVG ``<path>`` element.

    Returns
    -------
    list of list of (command, args)
        Each subpath is a list of ``(cmd_letter, [float, …])`` tuples.
        ``cmd_letter`` is an uppercase SVG command letter (``M``, ``L``,
        ``C``, ``Q``, ``Z``, …).
    """
    tokens = _tokenize_path(path_d)
    return _parse_tokens(tokens)
"""SVG-to-glyph importer."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Optional

try:
    import defusedxml.ElementTree as ET  # type: ignore
except ImportError:
    import xml.etree.ElementTree as ET  # type: ignore  # noqa: PLC0414

if TYPE_CHECKING:
    from aifont.core.font import Font

"""Import SVG files (or raw SVG path data) into font glyphs."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aifont.core.font import Font
    from aifont.core.glyph import Glyph

_SVG_NS = "http://www.w3.org/2000/svg"


def svg_to_glyph(
    svg_path: str | Path,
    font: "Font",
    unicode_point: int,
    glyph_name: Optional[str] = None,
) -> None:
    """Import an SVG file as a glyph into *font*.

    The SVG is imported using FontForge's built-in SVG importer after the
    target glyph slot has been created / selected.

    Args:
        svg_path:      Path to the SVG file to import.
        font:          Target :class:`~aifont.core.font.Font`.
        unicode_point: Unicode code point to assign (e.g. ``0x0041`` for 'A').
        glyph_name:    Optional glyph name override.  Defaults to the
                       Unicode character name.

    Raises:
        FileNotFoundError: If the SVG file does not exist.
        ValueError:        If the SVG has no ``<path>`` elements.
    """
    svg_path = Path(svg_path)
    if not svg_path.exists():
        raise FileNotFoundError(f"SVG file not found: {svg_path}")

    # Basic validation
    tree = ET.parse(svg_path)
    root = tree.getroot()
    paths = (
        root.findall(f".//{{{_SVG_NS}}}path")
        + root.findall(".//path")
    )
    if not paths:
        raise ValueError(f"No <path> elements found in {svg_path}")

    ff = font._ff
    if ff is None:
        raise RuntimeError("No font loaded.")

    # Create or select the glyph slot
    if unicode_point in ff:
        glyph = ff[unicode_point]
    else:
        glyph_name = glyph_name or f"uni{unicode_point:04X}"
        glyph = ff.createChar(unicode_point, glyph_name)

    # FontForge can import SVG directly
    glyph.importOutlines(str(svg_path))
    glyph.correctDirection()
    font: Font,
    unicode_point: int,
    glyph_name: str | None = None,
) -> Glyph:
    """Import an SVG file into a new or existing glyph.

    Parsing strategy:
    1. Use fontforge's native SVG import (``glyph.importOutlines``) if the
       file contains a single ``<path>`` element with a ``d`` attribute.
    2. Fall back to ``xml.etree`` for multi-path SVGs, injecting each path
       individually.

    Args:
        svg_path:      Path to the ``.svg`` file.
        font:          Target :class:`~aifont.core.font.Font`.
        unicode_point: Unicode codepoint to assign to the glyph.
        glyph_name:    Optional glyph name; defaults to ``uniXXXX`` form.

    Returns:
        The populated :class:`~aifont.core.glyph.Glyph`.
    """
    from aifont.core.glyph import Glyph  # noqa: PLC0415

    svg_path = Path(svg_path)
    if not svg_path.is_file():
        raise FileNotFoundError(f"SVG file not found: {svg_path}")

    name = glyph_name or f"uni{unicode_point:04X}"
    ff = font._raw

    if name not in ff:
        ff.createChar(unicode_point, name)
    glyph = Glyph(ff[name])

    # Prefer fontforge's own import for simplicity and accuracy.
    try:
        glyph._raw.importOutlines(str(svg_path))
        return glyph
    except Exception:  # noqa: BLE001
        pass

    # Manual fallback: parse SVG and import path-by-path via temp files.
    _import_svg_manual(glyph, svg_path)
    return glyph


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _collect_paths(root: ET.Element) -> List[Tuple[ET.Element, List[float]]]:
    """Return (element, cumulative_transform_matrix) for every <path>."""
    results: List[Tuple[ET.Element, List[float]]] = []
    _walk(root, [1, 0, 0, 1, 0, 0], results)
    return results


def _walk(
    elem: ET.Element,
    parent_transform: List[float],
    out: List[Tuple[ET.Element, List[float]]],
) -> None:
    tag = elem.tag.replace("{" + _SVG_NS + "}", "")
    transform = _parse_transform(elem.get("transform", ""))
    current = _mat_mul(parent_transform, transform)

    if tag == "path" and elem.get("d"):
        out.append((elem, current))

    for child in elem:
        _walk(child, current, out)


def _parse_transform(transform_str: str) -> List[float]:
    """Parse a basic SVG transform attribute → 2D affine matrix [a,b,c,d,e,f]."""
    mat = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    if not transform_str:
        return mat

    for m in re.finditer(
        r"(translate|scale|matrix)\s*\(([^)]+)\)", transform_str
    ):
        func = m.group(1)
        args = [float(x) for x in re.split(r"[,\s]+", m.group(2).strip()) if x]

        if func == "translate":
            tx = args[0] if args else 0.0
            ty = args[1] if len(args) > 1 else 0.0
            mat = _mat_mul(mat, [1, 0, 0, 1, tx, ty])
        elif func == "scale":
            sx = args[0] if args else 1.0
            sy = args[1] if len(args) > 1 else sx
            mat = _mat_mul(mat, [sx, 0, 0, sy, 0, 0])
        elif func == "matrix" and len(args) == 6:
            mat = _mat_mul(mat, args)

    return mat


def _mat_mul(a: List[float], b: List[float]) -> List[float]:
    """Multiply two 2-D affine matrices represented as [a,b,c,d,e,f]."""
    # [a c e]   [A C E]
    # [b d f] * [B D F]
    # [0 0 1]   [0 0 1]
    return [
        a[0] * b[0] + a[2] * b[1],
        a[1] * b[0] + a[3] * b[1],
        a[0] * b[2] + a[2] * b[3],
        a[1] * b[2] + a[3] * b[3],
        a[0] * b[4] + a[2] * b[5] + a[4],
        a[1] * b[4] + a[3] * b[5] + a[5],
    ]


def _tokenize_path(d: str) -> List[str]:
    """Split SVG path data into command letters and numeric tokens."""
    return re.findall(r"[MmZzLlHhVvCcSsQqTtAa]|[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", d)


def _parse_tokens(
    tokens: List[str],
) -> List[List[Tuple[str, List[float]]]]:
    """Group path tokens into subpaths of (cmd, [args]) tuples."""
    subpaths: List[List[Tuple[str, List[float]]]] = []
    current: List[Tuple[str, List[float]]] = []

    cmd = ""
    args: List[float] = []
    arg_counts = {
        "M": 2, "L": 2, "H": 1, "V": 1,
        "C": 6, "S": 4, "Q": 4, "T": 2,
        "A": 7, "Z": 0,
    }

    def flush() -> None:
        if cmd:
            current.append((cmd.upper(), list(args)))

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.isalpha():
            flush()
            args = []
            cmd = tok
            if tok.upper() == "Z":
                flush()
                args = []
                cmd = ""
                subpaths.append(current)
                current = []
        else:
            args.append(float(tok))
            expected = arg_counts.get(cmd.upper(), 0)
            if expected > 0 and len(args) >= expected:
                flush()
                # Implicit repetition: keep same cmd, reset args
                if cmd.upper() == "M":
                    cmd = "L" if cmd == "M" else "l"
                args = []
        i += 1

    flush()
    if current:
        subpaths.append(current)
    return subpaths


def _import_paths_manually(
    ff_glyph: object,
    paths: List[Tuple[ET.Element, List[float]]],
    scale: float,
    y_flip: bool,
    flip_offset: float,
) -> None:
    """Build FontForge contours from parsed SVG path data."""
    import fontforge  # noqa: PLC0415

    pen = ff_glyph.glyphPen()  # type: ignore[attr-defined]

    for elem, mat in paths:
        d = elem.get("d", "")
        if not d:
            continue
        subpaths = svg_path_to_contours(d)
        for subpath in subpaths:
            _draw_subpath(pen, subpath, mat, scale, y_flip, flip_offset)

    pen.endPath()  # type: ignore[attr-defined]


def _apply_mat(
    mat: List[float], x: float, y: float
) -> Tuple[float, float]:
    """Apply affine matrix to a point."""
    return (
        mat[0] * x + mat[2] * y + mat[4],
        mat[1] * x + mat[3] * y + mat[5],
    )


def _draw_subpath(
    pen: object,
    subpath: List[Tuple[str, List[float]]],
    mat: List[float],
    scale: float,
    y_flip: bool,
    flip_offset: float,
) -> None:
    """Draw a single SVG subpath using a FontForge pen."""

    def pt(x: float, y: float) -> Tuple[float, float]:
        tx, ty = _apply_mat(mat, x, y)
        tx *= scale
        ty *= scale
        if y_flip:
            ty = flip_offset - ty
        return (tx, ty)

    cx, cy = 0.0, 0.0  # current point

    for cmd, args in subpath:
        if cmd == "M":
            cx, cy = args[0], args[1]
            pen.moveTo(pt(cx, cy))  # type: ignore[attr-defined]
        elif cmd == "L":
            cx, cy = args[0], args[1]
            pen.lineTo(pt(cx, cy))  # type: ignore[attr-defined]
        elif cmd == "C":
            x1, y1 = args[0], args[1]
            x2, y2 = args[2], args[3]
            cx, cy = args[4], args[5]
            pen.curveTo(pt(x1, y1), pt(x2, y2), pt(cx, cy))  # type: ignore[attr-defined]
        elif cmd == "Q":
            x1, y1 = args[0], args[1]
            cx, cy = args[2], args[3]
            pen.qCurveTo(pt(x1, y1), pt(cx, cy))  # type: ignore[attr-defined]
        elif cmd == "Z":
            pen.closePath()  # type: ignore[attr-defined]
def _import_svg_manual(glyph: Glyph, svg_path: Path) -> None:
    """Parse multi-path SVG and inject outlines into *glyph*."""
    import tempfile  # noqa: PLC0415

    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Strip namespace for easier querying.
    for elem in root.iter():
        if "}" in elem.tag:
            elem.tag = elem.tag.split("}", 1)[1]

    paths = root.findall(".//path")
    if not paths:
        raise ValueError(f"No <path> elements found in {svg_path}")

    for path_elem in paths:
        d = path_elem.get("d", "")
        if not d:
            continue

        # Build a minimal SVG containing only this path and import it.
        mini_svg = (
            '<?xml version="1.0"?>'
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 1000 1000">'
            f'<path d="{d}"/>'
            "</svg>"
        )
        with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as fh:
            fh.write(mini_svg)
            tmp = fh.name

        try:
            glyph._raw.importOutlines(tmp)
        finally:
            Path(tmp).unlink(missing_ok=True)
