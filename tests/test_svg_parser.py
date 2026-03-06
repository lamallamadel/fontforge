"""Tests for aifont.utils.svg_parser.

These tests cover SVG path parsing and coordinate transformation without
requiring FontForge, plus full glyph-import tests when FontForge is available.
"""

import os
import sys
import math

# Make the repo root importable regardless of working directory.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from aifont.utils.svg_parser import (
    SVGParser,
    _tokenise_path,
    _parse_transform,
    _apply_matrix,
    _unicode_from_filename,
    _parse_viewbox,
    _rect_to_path,
    _collect_paths,
)
import xml.etree.ElementTree as ET

try:
    import fontforge as _ff

    _fontforge_available = hasattr(_ff, "font")
except ImportError:
    _fontforge_available = False

_FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


# ---------------------------------------------------------------------------
# _tokenise_path
# ---------------------------------------------------------------------------

def test_tokenise_moveto_lineto():
    cmds = _tokenise_path("M 10 20 L 30 40")
    assert cmds[0] == ("M", [10.0, 20.0])
    assert cmds[1] == ("L", [30.0, 40.0])


def test_tokenise_implicit_lineto_after_moveto():
    # M followed by extra coords becomes implicit L
    cmds = _tokenise_path("M 0 0 10 20 30 40")
    assert cmds[0] == ("M", [0.0, 0.0])
    assert cmds[1] == ("L", [10.0, 20.0])
    assert cmds[2] == ("L", [30.0, 40.0])


def test_tokenise_closepath():
    cmds = _tokenise_path("M 0 0 L 10 10 Z")
    assert any(c[0] == "Z" for c in cmds)


def test_tokenise_cubic_bezier():
    cmds = _tokenise_path("M 0 0 C 10 20 30 40 50 60")
    c_cmds = [c for c in cmds if c[0] == "C"]
    assert len(c_cmds) == 1
    assert c_cmds[0][1] == [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]


def test_tokenise_implicit_cubic_repeat():
    # Two cubic bezier repetitions in one C command
    cmds = _tokenise_path("M 0 0 C 1 2 3 4 5 6 7 8 9 10 11 12")
    c_cmds = [c for c in cmds if c[0] == "C"]
    assert len(c_cmds) == 2


def test_tokenise_quadratic_bezier():
    cmds = _tokenise_path("M 0 0 Q 50 10 100 0")
    q_cmds = [c for c in cmds if c[0] == "Q"]
    assert len(q_cmds) == 1
    assert q_cmds[0][1] == [50.0, 10.0, 100.0, 0.0]


def test_tokenise_horizontal_vertical():
    cmds = _tokenise_path("M 0 0 H 50 V 50 Z")
    assert any(c[0] == "H" and c[1] == [50.0] for c in cmds)
    assert any(c[0] == "V" and c[1] == [50.0] for c in cmds)


def test_tokenise_relative_lineto():
    cmds = _tokenise_path("m 5 5 l 10 0 l 0 10 z")
    assert cmds[0] == ("m", [5.0, 5.0])
    assert cmds[1] == ("l", [10.0, 0.0])


def test_tokenise_smooth_cubic():
    cmds = _tokenise_path("M 0 0 C 10 20 30 40 50 0 S 70 -40 100 0")
    s_cmds = [c for c in cmds if c[0] == "S"]
    assert len(s_cmds) == 1


def test_tokenise_arc_command():
    # Arc commands should be parsed without error
    cmds = _tokenise_path("M 50 0 A 50 50 0 1 0 50 100")
    a_cmds = [c for c in cmds if c[0].upper() == "A"]
    assert len(a_cmds) == 1


def test_tokenise_negative_numbers():
    cmds = _tokenise_path("M -10 -20 L -30 -40")
    assert cmds[0][1] == [-10.0, -20.0]


def test_tokenise_scientific_notation():
    cmds = _tokenise_path("M 1e2 2.5e1")
    assert cmds[0][1] == [100.0, 25.0]


def test_tokenise_empty_path():
    cmds = _tokenise_path("")
    assert cmds == []


# ---------------------------------------------------------------------------
# _parse_transform / _apply_matrix
# ---------------------------------------------------------------------------

def test_identity_transform():
    m = _parse_transform("")
    assert m == (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def test_translate_transform():
    m = _parse_transform("translate(10, 20)")
    x, y = _apply_matrix(m, 0.0, 0.0)
    assert abs(x - 10.0) < 1e-6
    assert abs(y - 20.0) < 1e-6


def test_translate_single_value():
    m = _parse_transform("translate(15)")
    x, y = _apply_matrix(m, 0.0, 0.0)
    assert abs(x - 15.0) < 1e-6
    assert abs(y - 0.0) < 1e-6


def test_scale_transform():
    m = _parse_transform("scale(2, 3)")
    x, y = _apply_matrix(m, 5.0, 7.0)
    assert abs(x - 10.0) < 1e-6
    assert abs(y - 21.0) < 1e-6


def test_scale_uniform():
    m = _parse_transform("scale(4)")
    x, y = _apply_matrix(m, 2.0, 3.0)
    assert abs(x - 8.0) < 1e-6
    assert abs(y - 12.0) < 1e-6


def test_matrix_transform():
    # matrix(a,b,c,d,e,f): x'=ax+cy+e, y'=bx+dy+f
    m = _parse_transform("matrix(1 0 0 1 50 100)")
    x, y = _apply_matrix(m, 0.0, 0.0)
    assert abs(x - 50.0) < 1e-6
    assert abs(y - 100.0) < 1e-6


def test_chained_transforms():
    m = _parse_transform("translate(10, 0) scale(2)")
    x, y = _apply_matrix(m, 5.0, 0.0)
    # scale first, then translate: x = 5*2 + 10 = 20
    # (chained left-to-right per SVG spec: scale then translate)
    assert abs(x - 20.0) < 1e-6


# ---------------------------------------------------------------------------
# _unicode_from_filename
# ---------------------------------------------------------------------------

def test_unicode_single_char():
    assert _unicode_from_filename("A") == "A"
    assert _unicode_from_filename("z") == "z"


def test_unicode_uni_notation():
    assert _unicode_from_filename("uni0041") == "A"
    assert _unicode_from_filename("uni0042") == "B"


def test_unicode_uplus_notation():
    assert _unicode_from_filename("U+0041") == "A"
    assert _unicode_from_filename("u+0042") == "B"


def test_unicode_decimal_codepoint():
    assert _unicode_from_filename("65") == "A"
    assert _unicode_from_filename("66") == "B"


def test_unicode_unrecognised():
    assert _unicode_from_filename("MyGlyph") is None
    assert _unicode_from_filename("hello") is None


def test_unicode_empty():
    assert _unicode_from_filename("") is None


# ---------------------------------------------------------------------------
# _parse_viewbox
# ---------------------------------------------------------------------------

def test_parse_viewbox_standard():
    vb = _parse_viewbox("0 0 100 200", None, None)
    assert vb == (0.0, 0.0, 100.0, 200.0)


def test_parse_viewbox_with_commas():
    vb = _parse_viewbox("0,0,100,200", None, None)
    assert vb == (0.0, 0.0, 100.0, 200.0)


def test_parse_viewbox_fallback_to_wh():
    vb = _parse_viewbox(None, "100", "200")
    assert vb == (0.0, 0.0, 100.0, 200.0)


def test_parse_viewbox_with_units():
    vb = _parse_viewbox(None, "100px", "200px")
    assert vb == (0.0, 0.0, 100.0, 200.0)


def test_parse_viewbox_none_when_missing():
    vb = _parse_viewbox(None, None, None)
    assert vb is None


# ---------------------------------------------------------------------------
# _rect_to_path
# ---------------------------------------------------------------------------

def test_rect_to_path_simple():
    el = ET.fromstring('<rect x="10" y="20" width="80" height="60"/>')
    d = _rect_to_path(el)
    assert d is not None
    cmds = _tokenise_path(d)
    assert any(c[0] == "Z" for c in cmds)


def test_rect_to_path_zero_size():
    el = ET.fromstring('<rect x="0" y="0" width="0" height="0"/>')
    assert _rect_to_path(el) is None


def test_rect_to_path_rounded():
    el = ET.fromstring('<rect x="0" y="0" width="100" height="100" rx="10" ry="10"/>')
    d = _rect_to_path(el)
    assert d is not None
    # Rounded rects use cubic beziers
    cmds = _tokenise_path(d)
    assert any(c[0] == "C" for c in cmds)


# ---------------------------------------------------------------------------
# _collect_paths (from SVG XML)
# ---------------------------------------------------------------------------

def test_collect_paths_single():
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><path d="M 0 0 L 10 10"/></svg>'
    root = ET.fromstring(svg)
    paths = _collect_paths(root)
    assert len(paths) == 1
    assert "M 0 0" in paths[0][0]


def test_collect_paths_grouped():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<g><path d="M 0 0 L 10 0"/><path d="M 0 0 L 0 10"/></g>'
        "</svg>"
    )
    root = ET.fromstring(svg)
    paths = _collect_paths(root)
    assert len(paths) == 2


def test_collect_paths_group_transform():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<g transform="translate(5,5)">'
        '<path d="M 0 0 L 10 0"/>'
        "</g>"
        "</svg>"
    )
    root = ET.fromstring(svg)
    paths = _collect_paths(root)
    assert len(paths) == 1
    _, tf = paths[0]
    assert tf is not None
    # translate(5,5) → e=5, f=5
    assert abs(tf[4] - 5.0) < 1e-6
    assert abs(tf[5] - 5.0) < 1e-6


def test_collect_paths_rect():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<rect x="0" y="0" width="50" height="50"/>'
        "</svg>"
    )
    root = ET.fromstring(svg)
    paths = _collect_paths(root)
    assert len(paths) == 1


# ---------------------------------------------------------------------------
# SVGParser.parse_svg_paths (no FontForge required)
# ---------------------------------------------------------------------------

def test_parse_svg_paths_triangle():
    parser = SVGParser()
    vb, paths = parser.parse_svg_paths(
        os.path.join(_FONTS_DIR, "triangle.svg")
    )
    assert vb == (0.0, 0.0, 100.0, 100.0)
    assert len(paths) == 1
    assert "M" in paths[0][0]


def test_parse_svg_paths_multi_path():
    parser = SVGParser()
    _, paths = parser.parse_svg_paths(os.path.join(_FONTS_DIR, "A.svg"))
    # A.svg has two paths (outer shape + cross-bar)
    assert len(paths) == 2


def test_parse_svg_paths_rect_element():
    parser = SVGParser()
    _, paths = parser.parse_svg_paths(os.path.join(_FONTS_DIR, "rect.svg"))
    assert len(paths) == 1


def test_parse_svg_paths_transformed():
    parser = SVGParser()
    _, paths = parser.parse_svg_paths(os.path.join(_FONTS_DIR, "transformed.svg"))
    assert len(paths) == 1
    _, tf = paths[0]
    assert tf is not None


# ---------------------------------------------------------------------------
# SVGParser — FontForge-dependent tests
# ---------------------------------------------------------------------------

if _fontforge_available:

    def test_build_contours_triangle():
        parser = SVGParser(em_size=1000)
        contours = parser.build_contours(os.path.join(_FONTS_DIR, "triangle.svg"))
        assert len(contours) == 1
        assert contours[0].closed

    def test_build_contours_coordinate_range():
        """Contour points should be within [0, em_size] after scaling."""
        parser = SVGParser(em_size=1000)
        contours = parser.build_contours(os.path.join(_FONTS_DIR, "triangle.svg"))
        for contour in contours:
            for point in contour:
                assert -1 <= point.x <= 1001, f"x out of range: {point.x}"
                assert -1 <= point.y <= 1001, f"y out of range: {point.y}"

    def test_build_contours_y_axis_flip():
        """FontForge y should increase upward (topmost SVG point → largest y)."""
        parser = SVGParser(em_size=1000)
        # triangle.svg: M 50 10 L 90 90 L 10 90 Z
        # SVG y=10 is the top vertex → should map to highest FontForge y
        contours = parser.build_contours(os.path.join(_FONTS_DIR, "triangle.svg"))
        assert len(contours) == 1
        ys = [p.y for p in contours[0]]
        max_y = max(ys)
        # The apex (SVG y=10) should yield the highest y in FontForge coords
        # For a 100×100 viewBox scaled to 1000: y_ff = (100-y_svg)*10
        # Apex: (100-10)*10 = 900, base: (100-90)*10 = 100
        assert abs(max_y - 900.0) < 1.0

    def test_svg_to_glyph_creates_glyph():
        import fontforge

        font = fontforge.font()
        parser = SVGParser()
        glyph = parser.svg_to_glyph(
            os.path.join(_FONTS_DIR, "triangle.svg"),
            font=font,
            unicode_char="T",
        )
        assert glyph is not None
        assert glyph.unicode == ord("T")
        assert len(glyph.foreground) > 0

    def test_svg_to_glyph_default_width():
        import fontforge

        font = fontforge.font()
        parser = SVGParser(em_size=1000)
        glyph = parser.svg_to_glyph(
            os.path.join(_FONTS_DIR, "square.svg"),
            font=font,
            unicode_char="S",
        )
        assert glyph.width == 1000

    def test_svg_to_glyph_custom_width():
        import fontforge

        font = fontforge.font()
        parser = SVGParser()
        glyph = parser.svg_to_glyph(
            os.path.join(_FONTS_DIR, "square.svg"),
            font=font,
            unicode_char="W",
            width=600,
        )
        assert glyph.width == 600

    def test_svg_to_glyph_no_font_creates_font():
        parser = SVGParser()
        glyph = parser.svg_to_glyph(
            os.path.join(_FONTS_DIR, "triangle.svg"),
            unicode_char="X",
        )
        assert glyph is not None

    def test_svg_to_glyph_no_unicode():
        import fontforge

        font = fontforge.font()
        parser = SVGParser()
        glyph = parser.svg_to_glyph(
            os.path.join(_FONTS_DIR, "triangle.svg"),
            font=font,
        )
        assert glyph.glyphname == "triangle"

    def test_svg_to_glyph_cubic_bezier():
        import fontforge

        font = fontforge.font()
        parser = SVGParser()
        glyph = parser.svg_to_glyph(
            os.path.join(_FONTS_DIR, "circle.svg"),
            font=font,
            unicode_char="O",
        )
        assert len(glyph.foreground) > 0

    def test_svg_to_glyph_quadratic_bezier():
        import fontforge

        font = fontforge.font()
        parser = SVGParser()
        glyph = parser.svg_to_glyph(
            os.path.join(_FONTS_DIR, "quadratic.svg"),
            font=font,
            unicode_char="Q",
        )
        assert len(glyph.foreground) > 0

    def test_svg_to_glyph_invalid_unicode_char():
        import fontforge
        import traceback

        font = fontforge.font()
        parser = SVGParser()
        try:
            parser.svg_to_glyph(
                os.path.join(_FONTS_DIR, "triangle.svg"),
                font=font,
                unicode_char="AB",
            )
            assert False, "Expected ValueError"
        except ValueError:
            pass

    def test_import_directory_with_mapping():
        import fontforge

        font = fontforge.font()
        parser = SVGParser()
        results = parser.import_directory(
            _FONTS_DIR,
            font,
            mapping={"A.svg": "A", "B.svg": "B"},
        )
        assert "A.svg" in results
        assert "B.svg" in results
        assert results["A.svg"].unicode == ord("A")
        assert results["B.svg"].unicode == ord("B")

    def test_import_directory_missing_file():
        import fontforge

        font = fontforge.font()
        parser = SVGParser()
        try:
            parser.import_directory(
                _FONTS_DIR,
                font,
                mapping={"nonexistent.svg": "X"},
            )
            assert False, "Expected FileNotFoundError"
        except FileNotFoundError:
            pass

    def test_auto_import():
        import fontforge
        import tempfile
        import shutil

        font = fontforge.font()
        parser = SVGParser()

        # Copy A.svg and B.svg to a temp dir
        tmpdir = tempfile.mkdtemp()
        try:
            shutil.copy(os.path.join(_FONTS_DIR, "A.svg"), os.path.join(tmpdir, "A.svg"))
            shutil.copy(os.path.join(_FONTS_DIR, "B.svg"), os.path.join(tmpdir, "B.svg"))
            results = parser.auto_import(tmpdir, font)
            assert "A.svg" in results
            assert "B.svg" in results
        finally:
            shutil.rmtree(tmpdir)

    def test_auto_import_uni_notation():
        import fontforge
        import tempfile
        import shutil

        font = fontforge.font()
        parser = SVGParser()

        tmpdir = tempfile.mkdtemp()
        try:
            shutil.copy(
                os.path.join(_FONTS_DIR, "A.svg"),
                os.path.join(tmpdir, "uni0041.svg"),
            )
            results = parser.auto_import(tmpdir, font)
            assert "uni0041.svg" in results
            assert results["uni0041.svg"].unicode == ord("A")
        finally:
            shutil.rmtree(tmpdir)

    def test_auto_import_skips_unrecognised():
        import fontforge
        import tempfile
        import shutil

        font = fontforge.font()
        parser = SVGParser()

        tmpdir = tempfile.mkdtemp()
        try:
            shutil.copy(
                os.path.join(_FONTS_DIR, "A.svg"),
                os.path.join(tmpdir, "MyGlyph.svg"),
            )
            results = parser.auto_import(tmpdir, font)
            assert len(results) == 0
        finally:
            shutil.rmtree(tmpdir)

    def test_svg_with_transform():
        import fontforge

        font = fontforge.font()
        parser = SVGParser()
        glyph = parser.svg_to_glyph(
            os.path.join(_FONTS_DIR, "transformed.svg"),
            font=font,
            unicode_char="V",
        )
        assert len(glyph.foreground) > 0

    def test_multi_path_glyph():
        import fontforge

        font = fontforge.font()
        parser = SVGParser()
        glyph = parser.svg_to_glyph(
            os.path.join(_FONTS_DIR, "A.svg"),
            font=font,
            unicode_char="A",
        )
        # A.svg has 2 paths → 2 contours in the layer
        assert len(glyph.foreground) == 2


# ---------------------------------------------------------------------------
# Entry point for running as a plain script (consistent with other tests)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Collect and run all test_* functions defined in this module.
    # FontForge-dependent tests are already guarded by the
    # ``if _fontforge_available:`` block above, so they simply won't be
    # defined when FontForge is unavailable.
    import traceback

    this = sys.modules[__name__]
    failures = []

    for name in sorted(dir(this)):
        if not name.startswith("test_"):
            continue
        fn = getattr(this, name)
        if not callable(fn):
            continue

        try:
            fn()
            print(f"  PASS  {name}")
        except Exception:
            failures.append(name)
            print(f"  FAIL  {name}")
            traceback.print_exc()

    if not _fontforge_available:
        print(
            "\nNote: FontForge Python extension not available; "
            "fontforge-dependent tests were skipped."
        )

    if failures:
        print(f"\n{len(failures)} test(s) FAILED: {', '.join(failures)}")
        sys.exit(1)
    else:
        print("\nAll tests passed.")
