"""
aifont.utils.svg_parser — SVG import utilities (re-exported from core).

For the primary SVG parser implementation, see
:mod:`aifont.core.svg_parser`.  This module re-exports the public API
so that users can import from ``aifont.utils`` as documented in the
issue structure.
"""

from aifont.core.svg_parser import svg_to_glyph  # noqa: F401

__all__ = ["svg_to_glyph"]
aifont.utils.svg_parser — Re-export of :mod:`aifont.core.svg_parser`.

This module exists for convenience so that users can also import SVG
utilities from ``aifont.utils``.
"""

from aifont.core.svg_parser import svg_to_glyph, svg_path_to_contours  # noqa: F401

__all__ = ["svg_to_glyph", "svg_path_to_contours"]
"""SVG Parser — import SVG files as font glyphs.

Parse SVG path data and convert to FontForge contours, enabling import of
vector drawings (from tools like Figma, Illustrator, or AI-generated SVGs)
directly as font glyphs.

Example usage::

    from aifont.utils.svg_parser import SVGParser

    parser = SVGParser()

    # Import a single glyph into an existing FontForge font
    glyph = parser.svg_to_glyph("A.svg", font, unicode_char="A")

    # Batch import with explicit mapping
    parser.import_directory("svgs/", font, mapping={"A.svg": "A", "B.svg": "B"})

    # Auto-detect Unicode from filename (A.svg → 'A', B.svg → 'B')
    parser.auto_import("svgs/", font)
"""

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

try:
    import fontforge as _fontforge

    _HAS_FONTFORGE = True
except ImportError:
    _fontforge = None  # type: ignore[assignment]
    _HAS_FONTFORGE = False

# SVG XML namespace
_SVG_NS = "http://www.w3.org/2000/svg"


def _ns(tag: str) -> str:
    """Return *tag* wrapped with the SVG namespace prefix."""
    return f"{{{_SVG_NS}}}{tag}"


# ---------------------------------------------------------------------------
# SVG transform parsing
# ---------------------------------------------------------------------------

def _parse_transform(transform_str: str) -> Tuple[float, float, float, float, float, float]:
    """Parse an SVG *transform* attribute into a 2-D affine matrix (a,b,c,d,e,f).

    The returned tuple represents the matrix::

        | a  c  e |
        | b  d  f |
        | 0  0  1 |

    Only ``translate``, ``scale``, and ``matrix`` are supported; unsupported
    functions are silently ignored (identity matrix is returned).
    """
    a, b, c, d, e, f = 1.0, 0.0, 0.0, 1.0, 0.0, 0.0  # identity

    for match in re.finditer(
        r"(matrix|translate|scale)\s*\(([^)]*)\)", transform_str
    ):
        func = match.group(1)
        args = [float(v) for v in re.split(r"[\s,]+", match.group(2).strip()) if v]

        if func == "matrix" and len(args) >= 6:
            na, nb, nc, nd, ne, nf = args[:6]
            # Multiply current matrix by new matrix
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
    matrix: Tuple[float, float, float, float, float, float],
    x: float,
    y: float,
) -> Tuple[float, float]:
    """Apply a 2-D affine *matrix* to point (*x*, *y*)."""
    a, b, c, d, e, f = matrix
    return a * x + c * y + e, b * x + d * y + f


# ---------------------------------------------------------------------------
# SVG path tokeniser and parser
# ---------------------------------------------------------------------------

_PATH_TOKEN_RE = re.compile(
    r"([MmLlHhVvCcSsQqTtAaZz])"
    r"|"
    r"([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)"
)


def _tokenise_path(d: str) -> List[Tuple[str, List[float]]]:
    """Tokenise SVG path *d* attribute into ``(command, [args])`` pairs.

    Handles implicit command repetition as per the SVG specification.
    """
    raw: List[Tuple[str, List[float]]] = []
    current_cmd: Optional[str] = None
    current_args: List[float] = []

    for cmd_char, num_str in _PATH_TOKEN_RE.findall(d):
        if cmd_char:
            if current_cmd is not None:
                raw.append((current_cmd, current_args))
            current_cmd = cmd_char
            current_args = []
        elif num_str:
            current_args.append(float(num_str))

    if current_cmd is not None:
        raw.append((current_cmd, current_args))

    return _expand_implicit(raw)


def _expand_implicit(
    raw: List[Tuple[str, List[float]]]
) -> List[Tuple[str, List[float]]]:
    """Expand commands with multiple coordinate sets into individual commands.

    For example ``L 10 20 30 40`` becomes two ``L`` commands.
    """
    result: List[Tuple[str, List[float]]] = []

    for cmd, args in raw:
        upper = cmd.upper()

        if upper == "Z":
            result.append((cmd, []))

        elif upper == "M":
            # First pair is M/m; subsequent pairs are implicit L/l
            if len(args) >= 2:
                result.append((cmd, args[:2]))
                follow = "l" if cmd == "m" else "L"
                for i in range(2, len(args) - 1, 2):
                    result.append((follow, args[i : i + 2]))

        elif upper in ("L", "T"):
            for i in range(0, len(args) - 1, 2):
                result.append((cmd, args[i : i + 2]))

        elif upper in ("H", "V"):
            for val in args:
                result.append((cmd, [val]))

        elif upper == "C":
            for i in range(0, len(args) - 5, 6):
                result.append((cmd, args[i : i + 6]))

        elif upper in ("S", "Q"):
            for i in range(0, len(args) - 3, 4):
                result.append((cmd, args[i : i + 4]))

        elif upper == "A":
            for i in range(0, len(args) - 6, 7):
                result.append((cmd, args[i : i + 7]))

        else:
            result.append((cmd, args))

    return result


# ---------------------------------------------------------------------------
# SVG path → FontForge contour converter
# ---------------------------------------------------------------------------

class _ContourBuilder:
    """Convert a list of SVG path commands into FontForge contour objects.

    Coordinate transformation applied:

    * SVG element transform matrix
    * Scaling to the target em-square size
    * Y-axis flip (SVG y increases downward; FontForge y increases upward)
    * Optional X/Y offset to shift the glyph origin

    Parameters
    ----------
    em_size:
        The font's units-per-em value (default 1000).
    viewbox:
        ``(min_x, min_y, width, height)`` extracted from the SVG viewBox.
        When ``None``, no scaling is applied.
    offset_x, offset_y:
        Additional translation applied *after* the viewBox transform, in
        FontForge coordinate units.
    svg_transform:
        Pre-parsed element-level SVG transform matrix (a,b,c,d,e,f).
    """

    def __init__(
        self,
        em_size: float = 1000.0,
        viewbox: Optional[Tuple[float, float, float, float]] = None,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
        svg_transform: Optional[Tuple[float, float, float, float, float, float]] = None,
    ) -> None:
        self._em = em_size
        self._vb = viewbox  # (min_x, min_y, width, height)
        self._off_x = offset_x
        self._off_y = offset_y
        self._svg_tf = svg_transform  # optional element-level matrix

        # Derived scale factors (set lazily once viewbox is known)
        self._sx: Optional[float] = None
        self._sy: Optional[float] = None
        self._vb_min_x: float = 0.0
        self._vb_min_y: float = 0.0
        self._vb_h: float = em_size

        if viewbox is not None:
            self._vb_min_x, self._vb_min_y, vb_w, vb_h = viewbox
            if vb_w > 0 and vb_h > 0:
                self._sx = em_size / vb_w
                self._sy = em_size / vb_h
                self._vb_h = vb_h

    def _to_ff(self, x: float, y: float) -> Tuple[float, float]:
        """Transform SVG coordinates (*x*, *y*) to FontForge coordinates."""
        # 1. Apply element-level SVG transform if present
        if self._svg_tf is not None:
            x, y = _apply_matrix(self._svg_tf, x, y)

        # 2. Translate by viewBox origin
        x -= self._vb_min_x
        y -= self._vb_min_y

        # 3. Scale to em-square
        if self._sx is not None and self._sy is not None:
            x *= self._sx
            y *= self._sy

        # 4. Flip Y axis (SVG → FontForge)
        y = self._vb_h * (self._sy or 1.0) - y

        # 5. Apply caller-supplied offset
        x += self._off_x
        y += self._off_y

        return x, y

    def build(
        self, commands: List[Tuple[str, List[float]]]
    ) -> List:  # List[fontforge.contour]
        """Convert *commands* into a list of ``fontforge.contour`` objects."""
        if not _HAS_FONTFORGE:
            raise ImportError(
                "The 'fontforge' Python extension is required to build contours. "
                "Make sure FontForge is installed and its Python bindings are available."
            )

        contours: List = []
        current: Optional[object] = None  # fontforge.contour

        cx = cy = 0.0          # current pen position
        sx = sy = 0.0          # subpath start (for Z)
        last_cmd: str = ""
        last_ctrl: Optional[Tuple[float, float]] = None  # for S/s and T/t

        for cmd, args in commands:
            upper = cmd.upper()

            # ---- Move-to ----
            if upper == "M":
                if current is not None:
                    contours.append(current)
                current = _fontforge.contour()
                if cmd == "M":
                    cx, cy = args[0], args[1]
                else:
                    cx += args[0]
                    cy += args[1]
                sx, sy = cx, cy
                px, py = self._to_ff(cx, cy)
                current += _fontforge.point(px, py, True)
                last_ctrl = None

            # ---- Close-path ----
            elif upper == "Z":
                if current is not None:
                    current.closed = True
                    contours.append(current)
                    current = None
                cx, cy = sx, sy
                last_ctrl = None

            # ---- Line-to ----
            elif upper == "L":
                if current is None:
                    current = _fontforge.contour()
                if cmd == "L":
                    cx, cy = args[0], args[1]
                else:
                    cx += args[0]
                    cy += args[1]
                px, py = self._to_ff(cx, cy)
                current += _fontforge.point(px, py, True)
                last_ctrl = None

            # ---- Horizontal line ----
            elif upper == "H":
                if current is None:
                    current = _fontforge.contour()
                cx = args[0] if cmd == "H" else cx + args[0]
                px, py = self._to_ff(cx, cy)
                current += _fontforge.point(px, py, True)
                last_ctrl = None

            # ---- Vertical line ----
            elif upper == "V":
                if current is None:
                    current = _fontforge.contour()
                cy = args[0] if cmd == "V" else cy + args[0]
                px, py = self._to_ff(cx, cy)
                current += _fontforge.point(px, py, True)
                last_ctrl = None

            # ---- Cubic Bézier ----
            elif upper == "C":
                if current is None:
                    current = _fontforge.contour()
                if cmd == "C":
                    x1, y1, x2, y2, x, y = args[:6]
                else:
                    x1 = cx + args[0]
                    y1 = cy + args[1]
                    x2 = cx + args[2]
                    y2 = cy + args[3]
                    x = cx + args[4]
                    y = cy + args[5]
                px1, py1 = self._to_ff(x1, y1)
                px2, py2 = self._to_ff(x2, y2)
                px, py = self._to_ff(x, y)
                current += _fontforge.point(px1, py1, False)
                current += _fontforge.point(px2, py2, False)
                current += _fontforge.point(px, py, True)
                last_ctrl = (x2, y2)
                cx, cy = x, y

            # ---- Smooth cubic Bézier ----
            elif upper == "S":
                if current is None:
                    current = _fontforge.contour()
                if last_cmd.upper() in ("C", "S") and last_ctrl is not None:
                    x1 = 2.0 * cx - last_ctrl[0]
                    y1 = 2.0 * cy - last_ctrl[1]
                else:
                    x1, y1 = cx, cy
                if cmd == "S":
                    x2, y2, x, y = args[:4]
                else:
                    x2 = cx + args[0]
                    y2 = cy + args[1]
                    x = cx + args[2]
                    y = cy + args[3]
                px1, py1 = self._to_ff(x1, y1)
                px2, py2 = self._to_ff(x2, y2)
                px, py = self._to_ff(x, y)
                current += _fontforge.point(px1, py1, False)
                current += _fontforge.point(px2, py2, False)
                current += _fontforge.point(px, py, True)
                last_ctrl = (x2, y2)
                cx, cy = x, y

            # ---- Quadratic Bézier (converted to cubic) ----
            elif upper == "Q":
                if current is None:
                    current = _fontforge.contour()
                if cmd == "Q":
                    x1, y1, x, y = args[:4]
                else:
                    x1 = cx + args[0]
                    y1 = cy + args[1]
                    x = cx + args[2]
                    y = cy + args[3]
                # Convert Q → C:  cp1 = P0 + 2/3*(P1-P0), cp2 = P2 + 2/3*(P1-P2)
                cx1 = cx + (2.0 / 3.0) * (x1 - cx)
                cy1 = cy + (2.0 / 3.0) * (y1 - cy)
                cx2 = x + (2.0 / 3.0) * (x1 - x)
                cy2 = y + (2.0 / 3.0) * (y1 - y)
                px1, py1 = self._to_ff(cx1, cy1)
                px2, py2 = self._to_ff(cx2, cy2)
                px, py = self._to_ff(x, y)
                current += _fontforge.point(px1, py1, False)
                current += _fontforge.point(px2, py2, False)
                current += _fontforge.point(px, py, True)
                last_ctrl = (x1, y1)
                cx, cy = x, y

            # ---- Smooth quadratic Bézier (converted to cubic) ----
            elif upper == "T":
                if current is None:
                    current = _fontforge.contour()
                if last_cmd.upper() in ("Q", "T") and last_ctrl is not None:
                    x1 = 2.0 * cx - last_ctrl[0]
                    y1 = 2.0 * cy - last_ctrl[1]
                else:
                    x1, y1 = cx, cy
                if cmd == "T":
                    x, y = args[:2]
                else:
                    x = cx + args[0]
                    y = cy + args[1]
                cx1 = cx + (2.0 / 3.0) * (x1 - cx)
                cy1 = cy + (2.0 / 3.0) * (y1 - cy)
                cx2 = x + (2.0 / 3.0) * (x1 - x)
                cy2 = y + (2.0 / 3.0) * (y1 - y)
                px1, py1 = self._to_ff(cx1, cy1)
                px2, py2 = self._to_ff(cx2, cy2)
                px, py = self._to_ff(x, y)
                current += _fontforge.point(px1, py1, False)
                current += _fontforge.point(px2, py2, False)
                current += _fontforge.point(px, py, True)
                last_ctrl = (x1, y1)
                cx, cy = x, y

            # ---- Arc (A) — approximated as line-to endpoint ----
            elif upper == "A":
                # Full arc-to-bezier conversion is complex; approximate with
                # a straight line to the endpoint so the contour closes
                # correctly.  Callers that need precise arcs should
                # pre-process the SVG with a dedicated tool.
                if current is None:
                    current = _fontforge.contour()
                if cmd == "A":
                    x, y = args[5], args[6]
                else:
                    x = cx + args[5]
                    y = cy + args[6]
                px, py = self._to_ff(x, y)
                current += _fontforge.point(px, py, True)
                cx, cy = x, y
                last_ctrl = None

            last_cmd = cmd

        if current is not None and len(current) > 0:
            contours.append(current)

        return contours


# ---------------------------------------------------------------------------
# SVG document reader
# ---------------------------------------------------------------------------

def _parse_viewbox(
    vb_str: Optional[str],
    width_str: Optional[str],
    height_str: Optional[str],
) -> Optional[Tuple[float, float, float, float]]:
    """Return ``(min_x, min_y, width, height)`` from SVG attributes."""
    if vb_str:
        parts = re.split(r"[\s,]+", vb_str.strip())
        if len(parts) == 4:
            try:
                return tuple(float(p) for p in parts)  # type: ignore[return-value]
            except ValueError:
                pass

    # Fall back to width/height attributes
    try:
        w = float(re.sub(r"[a-z%]+$", "", width_str or "", flags=re.I) or 0)
        h = float(re.sub(r"[a-z%]+$", "", height_str or "", flags=re.I) or 0)
        if w > 0 and h > 0:
            return 0.0, 0.0, w, h
    except ValueError:
        pass

    return None


def _collect_paths(
    element: ET.Element,
    inherited_transform: Optional[Tuple[float, float, float, float, float, float]] = None,
) -> List[Tuple[str, Optional[Tuple[float, float, float, float, float, float]]]]:
    """Recursively collect ``(d_attr, transform_matrix)`` from *element*."""
    results: List[
        Tuple[str, Optional[Tuple[float, float, float, float, float, float]]]
    ] = []

    tag = element.tag.replace(_ns(""), "").replace("{%s}" % _SVG_NS, "")

    # Combine inherited transform with this element's transform
    own_tf_str = element.get("transform", "")
    if own_tf_str:
        own_tf = _parse_transform(own_tf_str)
        if inherited_transform is not None:
            # Compose: inherited ∘ own
            ia, ib, ic, id_, ie, if_ = inherited_transform
            oa, ob, oc, od, oe, of_ = own_tf
            combined: Optional[Tuple[float, float, float, float, float, float]] = (
                ia * oa + ic * ob,
                ib * oa + id_ * ob,
                ia * oc + ic * od,
                ib * oc + id_ * od,
                ia * oe + ic * of_ + ie,
                ib * oe + id_ * of_ + if_,
            )
        else:
            combined = own_tf
    else:
        combined = inherited_transform

    if tag == "path":
        d = element.get("d", "")
        if d.strip():
            results.append((d, combined))

    elif tag in ("rect",):
        d = _rect_to_path(element)
        if d:
            results.append((d, combined))

    # Recurse into child elements (handles <g>, <svg>, etc.)
    for child in element:
        results.extend(_collect_paths(child, combined))

    return results


def _rect_to_path(element: ET.Element) -> Optional[str]:
    """Convert an SVG ``<rect>`` element to an equivalent path ``d`` string."""
    try:
        x = float(element.get("x", "0"))
        y = float(element.get("y", "0"))
        w = float(element.get("width", "0"))
        h = float(element.get("height", "0"))
        rx = float(element.get("rx", "0"))
        ry = float(element.get("ry", rx or "0"))
    except ValueError:
        return None

    if w <= 0 or h <= 0:
        return None

    if rx == 0 and ry == 0:
        return f"M {x} {y} H {x+w} V {y+h} H {x} Z"

    # Rounded rect — approximate with cubic beziers
    k = 0.5523  # magic constant for quarter-circle approximation
    krx, kry = k * rx, k * ry
    return (
        f"M {x+rx} {y} "
        f"H {x+w-rx} "
        f"C {x+w-rx+krx} {y} {x+w} {y+ry-kry} {x+w} {y+ry} "
        f"V {y+h-ry} "
        f"C {x+w} {y+h-ry+kry} {x+w-rx+krx} {y+h} {x+w-rx} {y+h} "
        f"H {x+rx} "
        f"C {x+rx-krx} {y+h} {x} {y+h-ry+kry} {x} {y+h-ry} "
        f"V {y+ry} "
        f"C {x} {y+ry-kry} {x+rx-krx} {y} {x+rx} {y} Z"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class SVGParser:
    """Import SVG files as FontForge glyphs.

    Parameters
    ----------
    em_size:
        Units-per-em to scale SVG artwork to.  Defaults to 1000, which is
        standard for OTF/CFF fonts.  Pass ``None`` to use the font's own UPM
        when calling :meth:`svg_to_glyph` with a font argument.
    """

    def __init__(self, em_size: Optional[float] = 1000.0) -> None:
        self.em_size = em_size

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    def parse_svg_paths(
        self, svg_path: Union[str, "os.PathLike[str]"]
    ) -> Tuple[
        Optional[Tuple[float, float, float, float]],
        List[Tuple[str, Optional[Tuple[float, float, float, float, float, float]]]],
    ]:
        """Parse an SVG file and return its viewBox and path data.

        This method does *not* require FontForge.

        Parameters
        ----------
        svg_path:
            Path to the SVG file.

        Returns
        -------
        viewbox:
            ``(min_x, min_y, width, height)`` or ``None`` if not found.
        paths:
            List of ``(d_attribute, transform_matrix)`` tuples, where
            *transform_matrix* is a 6-element affine matrix or ``None``.
        """
        tree = ET.parse(str(svg_path))
        root = tree.getroot()

        viewbox = _parse_viewbox(
            root.get("viewBox"),
            root.get("width"),
            root.get("height"),
        )

        paths = _collect_paths(root)
        return viewbox, paths

    def build_contours(
        self,
        svg_path: Union[str, "os.PathLike[str]"],
        em_size: Optional[float] = None,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
    ) -> List:
        """Parse *svg_path* and return a list of ``fontforge.contour`` objects.

        Requires the FontForge Python extension.

        Parameters
        ----------
        svg_path:
            Path to the SVG file.
        em_size:
            Override the instance-level em size for this call.
        offset_x, offset_y:
            Translate all points by this amount *after* scaling.
        """
        effective_em = em_size if em_size is not None else self.em_size or 1000.0
        viewbox, paths = self.parse_svg_paths(svg_path)

        all_contours: List = []
        for d, tf in paths:
            commands = _tokenise_path(d)
            builder = _ContourBuilder(
                em_size=effective_em,
                viewbox=viewbox,
                offset_x=offset_x,
                offset_y=offset_y,
                svg_transform=tf,
            )
            all_contours.extend(builder.build(commands))

        return all_contours

    # ------------------------------------------------------------------
    # High-level glyph import methods
    # ------------------------------------------------------------------

    def svg_to_glyph(
        self,
        svg_path: Union[str, "os.PathLike[str]"],
        font=None,
        unicode_char: Optional[str] = None,
        glyph_name: Optional[str] = None,
        width: Optional[int] = None,
    ):
        """Import an SVG file as a glyph.

        Parameters
        ----------
        svg_path:
            Path to the SVG file.
        font:
            A ``fontforge.font`` object to add the glyph to.  When ``None``
            a new font is created automatically.
        unicode_char:
            Single Unicode character to assign to the glyph (e.g. ``"A"``).
        glyph_name:
            Explicit glyph name.  Defaults to the Unicode character name or
            the stem of the SVG filename.
        width:
            Advance width in font units.  Defaults to the em size.

        Returns
        -------
        The created ``fontforge.glyph`` object.
        """
        if not _HAS_FONTFORGE:
            raise ImportError(
                "The 'fontforge' Python extension is required to create glyphs."
            )

        svg_path = Path(svg_path)

        # Resolve or create the font
        if font is None:
            font = _fontforge.font()

        em = self.em_size if self.em_size is not None else font.em

        # Determine Unicode code point
        codepoint: Optional[int] = None
        if unicode_char is not None:
            if len(unicode_char) != 1:
                raise ValueError(
                    f"unicode_char must be a single character, got {unicode_char!r}"
                )
            codepoint = ord(unicode_char)

        # Determine glyph name
        if glyph_name is None:
            if unicode_char is not None:
                glyph_name = _fontforge.nameFromUnicode(codepoint)
            else:
                glyph_name = svg_path.stem

        # Create the glyph
        if codepoint is not None:
            glyph = font.createChar(codepoint, glyph_name)
        else:
            glyph = font.createChar(-1, glyph_name)

        # Build and attach contours
        contours = self.build_contours(svg_path, em_size=em)
        layer = _fontforge.layer()
        for contour in contours:
            layer += contour
        glyph.foreground = layer

        # Set advance width
        glyph.width = int(width if width is not None else em)

        return glyph

    def import_directory(
        self,
        directory: Union[str, "os.PathLike[str]"],
        font,
        mapping: Dict[str, str],
        width: Optional[int] = None,
    ) -> Dict[str, object]:
        """Batch import SVG files with an explicit filename→character mapping.

        Parameters
        ----------
        directory:
            Directory containing the SVG files.
        font:
            A ``fontforge.font`` object to add glyphs to.
        mapping:
            Dict of ``{filename: unicode_char}``, e.g.
            ``{"A.svg": "A", "B.svg": "B"}``.
        width:
            Advance width for all imported glyphs (optional).

        Returns
        -------
        A dict of ``{filename: glyph}`` for successfully imported glyphs.
        """
        directory = Path(directory)
        results: Dict[str, object] = {}

        for filename, unicode_char in mapping.items():
            svg_path = directory / filename
            if not svg_path.exists():
                raise FileNotFoundError(
                    f"SVG file not found: {svg_path}"
                )
            glyph = self.svg_to_glyph(
                svg_path, font=font, unicode_char=unicode_char, width=width
            )
            results[filename] = glyph

        return results

    def auto_import(
        self,
        directory: Union[str, "os.PathLike[str]"],
        font,
        width: Optional[int] = None,
    ) -> Dict[str, object]:
        """Batch import all SVG files in *directory*, auto-detecting Unicode chars.

        The Unicode character is inferred from the filename stem:

        * ``A.svg`` → ``"A"`` (code point U+0041)
        * ``uni0041.svg`` → ``"A"`` (hex code point)
        * ``U+0041.svg`` → ``"A"`` (U+ notation)

        Files whose names cannot be mapped to a single Unicode character are
        silently skipped.

        Parameters
        ----------
        directory:
            Directory containing the SVG files.
        font:
            A ``fontforge.font`` object to add glyphs to.
        width:
            Advance width for all imported glyphs (optional).

        Returns
        -------
        A dict of ``{filename: glyph}`` for successfully imported glyphs.
        """
        directory = Path(directory)
        results: Dict[str, object] = {}

        for svg_file in sorted(directory.glob("*.svg")):
            unicode_char = _unicode_from_filename(svg_file.stem)
            if unicode_char is None:
                continue
            glyph = self.svg_to_glyph(
                svg_file, font=font, unicode_char=unicode_char, width=width
            )
            results[svg_file.name] = glyph

        return results


# ---------------------------------------------------------------------------
# Filename → Unicode character detection
# ---------------------------------------------------------------------------

def _unicode_from_filename(stem: str) -> Optional[str]:
    """Infer a single Unicode character from an SVG filename stem.

    Supported patterns
    ------------------
    * Single ASCII character:  ``A`` → ``"A"``
    * ``uni`` + 4-hex-digit:   ``uni0041`` → ``"A"``
    * ``U+`` hex notation:     ``U+0041`` → ``"A"``
    * Decimal code point:      ``65`` → ``"A"`` (only 1- to 5-digit numbers)

    Returns ``None`` when the stem cannot be resolved to a single character.
    """
    # Single character
    if len(stem) == 1:
        return stem

    # U+XXXX or U+XXXXX notation
    m = re.fullmatch(r"[Uu]\+([0-9A-Fa-f]{4,6})", stem)
    if m:
        cp = int(m.group(1), 16)
        try:
            return chr(cp)
        except (ValueError, OverflowError):
            return None

    # uniXXXX notation (exactly 4 hex digits)
    m = re.fullmatch(r"uni([0-9A-Fa-f]{4})", stem)
    if m:
        cp = int(m.group(1), 16)
        try:
            return chr(cp)
        except (ValueError, OverflowError):
            return None

    # Pure decimal number (single character code point)
    m = re.fullmatch(r"(\d{1,7})", stem)
    if m:
        cp = int(m.group(1))
        if 0 <= cp <= 0x10FFFF:
            try:
                return chr(cp)
            except (ValueError, OverflowError):
                return None

    return None
