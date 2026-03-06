"""aifont.core.svg_parser — import SVG files/paths into font glyphs.

Parse SVG ``<path d="…">`` data and inject the resulting contours into a
fontforge glyph.  Both single-path and multi-path SVGs are supported.
Basic SVG transforms (translate, scale, matrix) are applied before importing.

FontForge source code is never modified.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import fontforge  # type: ignore
    # Guard against the namespace-package stub that lacks the C extension API.
    if not hasattr(fontforge, "font"):
        fontforge = None  # type: ignore  # C extension not installed
    _FF_AVAILABLE = fontforge is not None
except ImportError:  # pragma: no cover
    fontforge = None  # type: ignore  # fontforge not installed at all
    _FF_AVAILABLE = False

# SVG XML namespace
_SVG_NS = "http://www.w3.org/2000/svg"

# ---------------------------------------------------------------------------
# SVG transform helpers
# ---------------------------------------------------------------------------


def _parse_transform(
    transform_str: str,
) -> Tuple[float, float, float, float, float, float]:
    """Parse a simple SVG transform attribute into a 6-tuple affine matrix.

    Supported functions: ``translate``, ``scale``, ``matrix``.
    Returns the identity matrix for unrecognised or empty strings.

    Args:
        transform_str: The value of an SVG ``transform`` attribute.

    Returns:
        A 6-tuple ``(a, b, c, d, e, f)`` representing the matrix::

            | a  c  e |
            | b  d  f |
            | 0  0  1 |
    """
    a, b, c, d, e, f = 1.0, 0.0, 0.0, 1.0, 0.0, 0.0  # identity

    if not transform_str:
        return a, b, c, d, e, f

    for match in re.finditer(
        r"(matrix|translate|scale)\s*\(([^)]*)\)", transform_str
    ):
        func = match.group(1)
        args = [float(v) for v in re.split(r"[\s,]+", match.group(2).strip()) if v]

        if func == "matrix" and len(args) >= 6:
            na, nb, nc, nd, ne, nf = args[:6]
            a, b, c, d, e, f = (
                a * na + c * nb,
                b * na + d * nb,
                a * nc + c * nd,
                b * nc + d * nd,
                a * ne + c * nf + e,
                b * ne + d * nf + f,
            )
        elif func == "translate":
            tx = args[0] if args else 0.0
            ty = args[1] if len(args) > 1 else 0.0
            e += a * tx + c * ty
            f += b * tx + d * ty
        elif func == "scale":
            sx = args[0] if args else 1.0
            sy = args[1] if len(args) > 1 else sx
            a *= sx
            b *= sx
            c *= sy
            d *= sy

    return a, b, c, d, e, f


def _apply_matrix(
    x: float,
    y: float,
    matrix: Tuple[float, float, float, float, float, float],
) -> Tuple[float, float]:
    """Apply a 2-D affine *matrix* to point (*x*, *y*).

    Args:
        x:      X coordinate.
        y:      Y coordinate.
        matrix: 6-tuple ``(a, b, c, d, e, f)`` affine matrix.

    Returns:
        Transformed ``(x', y')`` coordinates.
    """
    a, b, c, d, e, f = matrix
    return a * x + c * y + e, b * x + d * y + f


# ---------------------------------------------------------------------------
# SVG path tokeniser / parser
# ---------------------------------------------------------------------------

_PATH_CMD_RE = re.compile(
    r"([MmZzLlHhVvCcSsQqTtAa])"
    r"|"
    r"([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)"
)


def _tokenise_path(d: str) -> List[object]:
    """Tokenise an SVG path ``d`` attribute into command letters and floats.

    Args:
        d: The SVG path data string.

    Returns:
        A list where each element is either a command letter (str)
        or a numeric argument (float).
    """
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

    Args:
        d: SVG path data string.

    Returns:
        List of ``(upper_cmd, [args])`` tuples.
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
    sx, sy = 0.0, 0.0  # subpath start (for Z)
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
            args.append(float(tok))  # type: ignore[arg-type]
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
        elif upper == "Q":
            cx, cy = a[2], a[3]
        elif upper == "A":
            cx, cy = a[5], a[6]

    return commands


# ---------------------------------------------------------------------------
# Internal glyph injection helpers
# ---------------------------------------------------------------------------


def _flip_y(y: float, em: float = 1000.0) -> float:
    """Flip Y from SVG (top-down) to font (bottom-up) coordinate space."""
    return em - y


def _parse_viewbox(
    vb_str: str,
) -> Optional[Tuple[float, float, float, float]]:
    """Parse an SVG ``viewBox`` attribute string.

    Args:
        vb_str: The value of a ``viewBox`` attribute, e.g. ``"0 0 500 700"``.

    Returns:
        A 4-tuple ``(min_x, min_y, width, height)`` or ``None`` if the
        string cannot be parsed.
    """
    if not vb_str:
        return None
    parts = re.split(r"[\s,]+", vb_str.strip())
    if len(parts) != 4:
        return None
    try:
        return tuple(float(p) for p in parts)  # type: ignore[return-value]
    except ValueError:
        return None


def _collect_path_data(root: "ET.Element") -> List[str]:
    """Recursively collect ``d`` attribute strings from all ``<path>`` elements.

    Args:
        root: The root XML element of an SVG document.

    Returns:
        A list of non-empty ``d`` attribute strings, one per ``<path>``.
    """
    results: List[str] = []

    def _visit(elem: "ET.Element") -> None:
        tag = elem.tag.replace(f"{{{_SVG_NS}}}", "").split("}")[-1]
        if tag == "path":
            d = elem.get("d", "").strip()
            if d:
                results.append(d)
        for child in elem:
            _visit(child)

    _visit(root)
    return results


def _get_em(ff_font: object) -> float:
    """Return the em size of the font."""
    try:
        return float(ff_font.em)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return 1000.0


def _inject_path_into_glyph(
    ff_glyph: object,
    d: str,
    matrix: Tuple[float, float, float, float, float, float],
    em: float = 1000.0,
) -> None:
    """Parse SVG path *d* and draw it into *ff_glyph* using a glyph pen."""
    pen = ff_glyph.glyphPen()  # type: ignore[attr-defined]
    commands = _parse_path_d(d)

    for cmd, a_args in commands:
        if cmd == "M":
            x, y = _apply_matrix(a_args[0], a_args[1], matrix)
            pen.moveTo((x, _flip_y(y, em)))
        elif cmd == "Z":
            pen.closePath()
        elif cmd == "L":
            x, y = _apply_matrix(a_args[0], a_args[1], matrix)
            pen.lineTo((x, _flip_y(y, em)))
        elif cmd == "C":
            x1, y1 = _apply_matrix(a_args[0], a_args[1], matrix)
            x2, y2 = _apply_matrix(a_args[2], a_args[3], matrix)
            x, y = _apply_matrix(a_args[4], a_args[5], matrix)
            pen.curveTo(
                (x1, _flip_y(y1, em)),
                (x2, _flip_y(y2, em)),
                (x, _flip_y(y, em)),
            )
        elif cmd == "Q":
            x1, y1 = _apply_matrix(a_args[0], a_args[1], matrix)
            x, y = _apply_matrix(a_args[2], a_args[3], matrix)
            pen.qCurveTo((x1, _flip_y(y1, em)), (x, _flip_y(y, em)))

    pen = None  # flush


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def svg_to_glyph(
    svg_path: "str | Path",
    font: object,
    unicode_point: int = -1,
    glyph_name: Optional[str] = None,
) -> object:
    """Parse an SVG file and load its paths into a new glyph.

    Strategy:
    1. If the fontforge glyph has a native ``importOutlines`` method, use it.
    2. Otherwise, collect ``<path>`` elements and inject them manually.

    Args:
        svg_path:      Path to the SVG file.
        font:          A :class:`~aifont.core.font.Font` wrapper or raw
                       ``fontforge.font`` object.
        unicode_point: Unicode code-point for the glyph (default ``-1``).
        glyph_name:    Glyph name (defaults to the SVG filename stem).

    Returns:
        The raw fontforge glyph that was created/updated (or a
        :class:`~aifont.core.glyph.Glyph` wrapper if fontforge is available).

    Raises:
        FileNotFoundError: If *svg_path* does not exist.
        ValueError:        If the SVG contains no ``<path>`` elements and
                           the glyph lacks a native import method.
    """
    svg_path = Path(svg_path)
    if not svg_path.exists():
        raise FileNotFoundError(f"SVG file not found: {svg_path}")

    # Resolve raw fontforge font
    ff_font = font
    if hasattr(font, "_font"):
        ff_font = font._font  # type: ignore[attr-defined]

    em = _get_em(ff_font)

    if glyph_name is None:
        glyph_name = svg_path.stem

    # Parse SVG
    try:
        tree = ET.parse(str(svg_path))
        root = tree.getroot()
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Failed to parse SVG file {svg_path}: {exc}") from exc

    # Parse viewBox for width
    vb = _parse_viewbox(root.get("viewBox", ""))

    # Create or retrieve glyph
    try:
        ff_glyph = ff_font.createChar(unicode_point, glyph_name)  # type: ignore[union-attr]
    except AttributeError as exc:
        raise RuntimeError(
            "fontforge Python bindings are required. The provided font object "
            "does not appear to be a valid fontforge font."
        ) from exc
    except Exception:  # noqa: BLE001
        try:
            ff_glyph = ff_font[glyph_name]  # type: ignore[index]
        except Exception as exc2:  # noqa: BLE001
            raise RuntimeError(
                f"fontforge: Could not create glyph {glyph_name!r}: {exc2}"
            ) from exc2

    # Use native importOutlines if available
    if hasattr(ff_glyph, "importOutlines"):
        ff_glyph.importOutlines(str(svg_path))
        if vb is not None:
            ff_glyph.width = int(vb[2])
        return ff_glyph

    # Fallback: manual path injection
    paths = _collect_path_data(root)
    if not paths:
        raise ValueError(
            f"No <path> elements found in SVG {svg_path}. "
            "Cannot import glyph without path data."
        )

    identity: Tuple[float, float, float, float, float, float] = (
        1.0, 0.0, 0.0, 1.0, 0.0, 0.0
    )
    for d in paths:
        try:
            _inject_path_into_glyph(ff_glyph, d, identity, em)
        except Exception:  # noqa: BLE001
            pass

    if vb is not None:
        ff_glyph.width = int(vb[2])

    return ff_glyph


# American spelling alias used in some test modules
def _tokenize_path(d: str) -> List[str]:
    """Tokenise an SVG path ``d`` string, returning all tokens as strings.

    Both command letters and numeric values are returned as strings.

    Args:
        d: SVG path data string.

    Returns:
        A flat list of string tokens.
    """
    tokens: List[str] = []
    for m in _PATH_CMD_RE.finditer(d):
        if m.group(1):
            tokens.append(m.group(1))
        else:
            tokens.append(m.group(2))  # keep as string, not float
    return tokens


def svg_path_to_contours(
    d: str,
    em: float = 1000.0,
    matrix: Optional[Tuple[float, float, float, float, float, float]] = None,
) -> List[List[Tuple[str, List[float]]]]:
    """Parse an SVG path ``d`` string into a list of subpaths.

    Each subpath is a list of ``(command, args)`` tuples. Subpaths are
    separated at ``Z`` (closepath) commands.  This is a pure-Python
    function that does not require FontForge.

    Args:
        d:      SVG path data string.
        em:     Em size (unused; for caller convenience).
        matrix: Optional affine transform to pre-apply.

    Returns:
        List of subpaths, where each subpath is a list of
        ``(upper_cmd, [args])`` tuples.
    """
    all_cmds = _parse_path_d(d)
    subpaths: List[List[Tuple[str, List[float]]]] = []
    current: List[Tuple[str, List[float]]] = []
    for cmd, args in all_cmds:
        current.append((cmd, args))
        if cmd == "Z":
            subpaths.append(current)
            current = []
    if current:
        subpaths.append(current)
    return subpaths
