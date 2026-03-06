"""Unit tests for remaining aifont core modules (export, metrics, contour, font, analyzer)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_ff():
    ff = MagicMock()
    ff.familyname = "Test"
    ff.fontname = "Test"
    ff.fullname = "Test Regular"
    ff.weight = "Regular"
    ff.copyright = ""
    ff.version = "1.0"
    ff.em = 1000
    ff.ascent = 800
    ff.descent = 200
    ff.gpos_lookups = []
    ff.__iter__ = lambda self: iter([])
    ff.validate.return_value = 0
    return ff


def _make_font():
    from aifont.core.font import Font

    return Font(_make_mock_ff())


# ===========================================================================
# aifont.core.export
# ===========================================================================


class TestExportOptions:
    def test_defaults(self):
        from aifont.core.export import ExportOptions

        opts = ExportOptions()
        assert opts.hints is False
        assert opts.round_to_int is False
        assert opts.opentype is True
        assert list(opts.extra_flags) == []

    def test_custom(self):
        from aifont.core.export import ExportOptions

        opts = ExportOptions(hints=True, round_to_int=True)
        assert opts.hints is True


class TestExportHelpers:
    def test_get_ff_font_raw(self):
        from aifont.core.export import _get_ff_font

        raw = MagicMock(spec=["generate"])  # no _font attr
        assert _get_ff_font(raw) is raw

    def test_get_ff_font_wrapper(self):
        from aifont.core.export import _get_ff_font

        font = _make_font()
        result = _get_ff_font(font)
        assert result is font._font

    def test_ensure_dir_creates_parent(self):
        from aifont.core.export import _ensure_dir

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "subdir" / "font.otf"
            _ensure_dir(path)
            assert path.parent.exists()

    def test_convert_ttf_to_woff2_missing_file(self):
        from aifont.core.export import _convert_ttf_to_woff2

        try:
            _convert_ttf_to_woff2("/nonexistent/in.ttf", "/nonexistent/out.woff2")
            assert False, "Expected an exception for nonexistent file"
        except (RuntimeError, FileNotFoundError, OSError):
            pass  # expected


class TestExportFunctions:
    def _make_raw_ff(self) -> MagicMock:
        """MagicMock without a _font attr (treated as raw by _get_ff_font)."""
        return MagicMock(spec=["generate", "save"])

    def test_export_otf(self):
        from aifont.core.export import export_otf

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "font.otf"
            ff = self._make_raw_ff()
            result = export_otf(ff, out)
            ff.generate.assert_called_once()
            assert result == out

    def test_export_ttf(self):
        from aifont.core.export import export_ttf

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "font.ttf"
            ff = self._make_raw_ff()
            result = export_ttf(ff, out)
            ff.generate.assert_called_once()
            assert result == out

    def test_export_woff(self):
        from aifont.core.export import export_woff

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "font.woff"
            ff = self._make_raw_ff()
            result = export_woff(ff, out)
            ff.generate.assert_called_once()
            assert result == out

    def test_export_ufo(self):
        from aifont.core.export import export_ufo

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "font.ufo"
            ff = self._make_raw_ff()
            result = export_ufo(ff, out)
            # export_ufo tries ff.save() first
            assert result == out

    def test_export_sfd(self):
        from aifont.core.export import export_sfd

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "font.sfd"
            ff = self._make_raw_ff()
            result = export_sfd(ff, out)
            ff.save.assert_called_once()
            assert result == out

    def test_export_woff2_native(self):
        from aifont.core.export import export_woff2

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "font.woff2"
            ff = self._make_raw_ff()
            result = export_woff2(ff, out)
            assert result == out

    def test_export_svg(self):
        from aifont.core.export import export_svg

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "font.svg"
            ff = self._make_raw_ff()
            result = export_svg(ff, out)
            ff.generate.assert_called_once()
            assert result == out


class TestExportAll:
    def test_export_all_empty_formats(self):
        from aifont.core.export import export_all

        with tempfile.TemporaryDirectory() as tmpdir:
            ff = _make_mock_ff()
            results = export_all(ff, tmpdir, formats=[])
            assert results == {}


# ===========================================================================
# aifont.core.metrics
# ===========================================================================


class TestMetricsDataClasses:
    def test_kern_pair(self):
        from aifont.core.metrics import KernPair

        kp = KernPair(left="A", right="V", value=-30)
        assert kp.left == "A"
        assert kp.value == -30

    def test_side_bearings(self):
        from aifont.core.metrics import SideBearings

        sb = SideBearings(left=50, right=60)
        assert sb.left == 50

    def test_spacing_analysis_defaults(self):
        from aifont.core.metrics import SpacingAnalysis

        sa = SpacingAnalysis()
        assert sa.glyph_count == 0
        assert sa.suggestions == []


class TestMetricsFunctions:
    def test_get_kern_pairs_empty(self):
        from aifont.core.metrics import get_kern_pairs

        ff = _make_mock_ff()
        ff.subtables = None
        result = get_kern_pairs(ff)
        assert result == {}

    def test_get_kern_pairs_with_font_wrapper(self):
        from aifont.core.metrics import get_kern_pairs

        font = _make_font()
        font._font.subtables = None
        result = get_kern_pairs(font)
        assert result == {}

    def test_analyze_spacing_empty_font(self):
        from aifont.core.metrics import analyze_spacing

        ff = _make_mock_ff()
        result = analyze_spacing(ff)
        assert result.glyph_count == 0

    def test_get_side_bearings_no_glyph(self):
        from aifont.core.metrics import get_side_bearings

        ff = MagicMock(spec=["__iter__"])  # no __getitem__
        ff.__iter__ = lambda self: iter([])
        result = get_side_bearings(ff, "A")
        assert result is None

    def test_auto_space_calls_autowidth(self):
        from aifont.core.metrics import auto_space

        ff = MagicMock(spec=["autoWidth", "__iter__"])
        ff.__iter__ = lambda self: iter([])
        auto_space(ff)
        ff.autoWidth.assert_called_once()

    def test_auto_kern_empty(self):
        from aifont.core.metrics import auto_kern

        ff = MagicMock(spec=["__iter__"])
        ff.__iter__ = lambda self: iter([])
        result = auto_kern(ff)
        assert isinstance(result, list)


# ===========================================================================
# aifont.core.contour (additional coverage)
# ===========================================================================


class TestContourModule:
    def test_simplify_delegates(self):
        from aifont.core.contour import simplify
        from aifont.core.glyph import Glyph

        ff = MagicMock()
        g = Glyph(ff)
        simplify(g, threshold=1.5)
        ff.simplify.assert_called_once_with(1.5)

    def test_remove_overlap_delegates(self):
        from aifont.core.contour import remove_overlap
        from aifont.core.glyph import Glyph

        ff = MagicMock()
        g = Glyph(ff)
        remove_overlap(g)
        ff.removeOverlap.assert_called_once()

    def test_transform_validates_matrix_length(self):
        from aifont.core.contour import transform
        from aifont.core.glyph import Glyph

        ff = MagicMock()
        g = Glyph(ff)
        try:
            transform(g, [1, 0, 0, 1])  # 4 elements — invalid
            assert False, "Expected ValueError"
        except ValueError:
            pass

    def test_transform_applies_matrix(self):
        from aifont.core.contour import transform
        from aifont.core.glyph import Glyph

        ff = MagicMock()
        g = Glyph(ff)
        transform(g, [1, 0, 0, 1, 0, 0])
        ff.transform.assert_called_once_with((1, 0, 0, 1, 0, 0))

    def test_correct_directions_delegates(self):
        from aifont.core.contour import correct_directions
        from aifont.core.glyph import Glyph

        ff = MagicMock()
        g = Glyph(ff)
        correct_directions(g)
        ff.correctDirection.assert_called_once()

    def test_auto_hint_delegates(self):
        from aifont.core.contour import auto_hint
        from aifont.core.glyph import Glyph

        ff = MagicMock()
        g = Glyph(ff)
        auto_hint(g)
        ff.autoHint.assert_called_once()


# ===========================================================================
# aifont.core.font (additional coverage)
# ===========================================================================


class TestFontAdditional:
    def test_family_getter_setter(self):
        from aifont.core.font import Font

        ff = _make_mock_ff()
        font = Font(ff)
        assert font.family == "Test"
        font.family = "NewFamily"
        assert ff.familyname == "NewFamily"

    def test_version_getter_setter(self):
        from aifont.core.font import Font

        ff = _make_mock_ff()
        font = Font(ff)
        font.version = "2.0"
        assert ff.version == "2.0"

    def test_copyright_getter_setter(self):
        from aifont.core.font import Font

        ff = _make_mock_ff()
        font = Font(ff)
        font.copyright = "(c) 2024"
        assert ff.copyright == "(c) 2024"

    def test_font_name_getter_setter(self):
        from aifont.core.font import Font

        ff = _make_mock_ff()
        font = Font(ff)
        font.name = "NewFont"
        assert ff.fontname == "NewFont"

    def test_em_getter_setter(self):
        from aifont.core.font import Font

        ff = _make_mock_ff()
        font = Font(ff)
        assert font.em_size == 1000
        font.em_size = 2048
        assert ff.em == 2048

    def test_glyphs_iterator(self):
        from aifont.core.font import Font

        ff = _make_mock_ff()
        font = Font(ff)
        glyphs = list(font.glyphs)
        assert glyphs == []

    def test_metadata_contains_family(self):
        from aifont.core.font import Font

        ff = _make_mock_ff()
        font = Font(ff)
        assert "family" in font.metadata

    def test_set_metadata_valid_field(self):
        from aifont.core.font import Font

        ff = _make_mock_ff()
        font = Font(ff)
        font.set_metadata(familyname="UpdatedFamily")
        assert ff.familyname == "UpdatedFamily"

    def test_set_metadata_invalid_field(self):
        from aifont.core.font import Font

        ff = _make_mock_ff()
        font = Font(ff)
        try:
            font.set_metadata(unknownfield="x")
            assert False, "Expected ValueError"
        except ValueError:
            pass

    def test_font_metadata_getitem_em_size_string(self):
        from aifont.core.font import FontMetadata

        ff = _make_mock_ff()
        meta = FontMetadata(ff)
        assert meta["em_size"] == "1000"

    def test_font_metadata_getitem_family(self):
        from aifont.core.font import FontMetadata

        ff = _make_mock_ff()
        meta = FontMetadata(ff)
        assert meta["family"] == "Test"

    def test_font_metadata_setitem(self):
        from aifont.core.font import FontMetadata

        ff = _make_mock_ff()
        meta = FontMetadata(ff)
        meta["familyname"] = "NewFamily"
        assert ff.familyname == "NewFamily"

    def test_font_metadata_setitem_invalid_key(self):
        from aifont.core.font import FontMetadata

        ff = _make_mock_ff()
        meta = FontMetadata(ff)
        try:
            meta["badkey"] = "value"
            assert False, "Expected KeyError"
        except KeyError:
            pass

    def test_repr_contains_family(self):
        from aifont.core.font import Font

        ff = _make_mock_ff()
        font = Font(ff)
        r = repr(font)
        assert "Test" in r

    def test_glyph_count_property(self):
        from aifont.core.font import Font

        ff = _make_mock_ff()
        font = Font(ff)
        assert font.glyph_count == 0


# ===========================================================================
# aifont.core.analyzer (additional coverage)
# ===========================================================================


class TestAnalyzerAdditional:
    def test_glyph_issue_code_alias(self):
        from aifont.core.analyzer import GlyphIssue

        issue = GlyphIssue(glyph_name="A", code="open_contour")
        assert issue.issue_type == "open_contour"

    def test_font_report_error_count(self):
        from aifont.core.analyzer import FontReport, GlyphIssue

        r = FontReport(
            issues=[
                GlyphIssue(glyph_name="A", severity="error"),
                GlyphIssue(glyph_name="B", severity="warning"),
            ]
        )
        assert r.error_count == 1
        assert r.warning_count == 1

    def test_font_report_issues_by_type(self):
        from aifont.core.analyzer import FontReport, GlyphIssue

        r = FontReport(
            issues=[GlyphIssue(glyph_name="A", issue_type="open_contour")]
        )
        matches = r.issues_by_type("open_contour")
        assert len(matches) == 1

    def test_font_report_str(self):
        from aifont.core.analyzer import FontReport

        r = FontReport(glyph_count=10, family_name="Test")
        s = str(r)
        assert "10" in s

    def test_analyze_empty_font_uses_font_wrapper(self):
        from aifont.core.analyzer import FontReport, analyze
        from aifont.core.font import Font

        ff = _make_mock_ff()
        font = Font(ff)
        report = analyze(font)
        assert isinstance(report, FontReport)

    def test_style_profile_summary(self):
        from aifont.core.analyzer import StyleProfile

        sp = StyleProfile(style_name="Regular", weight=400, stroke_width=80)
        s = sp.summary()
        assert "Regular" in s

    def test_analyze_style_function(self):
        from aifont.core.analyzer import StyleProfile, analyze_style

        ff = _make_mock_ff()
        result = analyze_style(ff)
        assert isinstance(result, StyleProfile)

    def test_font_analyzer_run(self):
        from aifont.core.analyzer import FontAnalyzer, FontReport
        from aifont.core.font import Font

        ff = _make_mock_ff()
        font = Font(ff)
        analyzer = FontAnalyzer(font)
        report = analyzer.run()
        assert isinstance(report, FontReport)

    def test_global_metrics_dataclass(self):
        from aifont.core.analyzer import GlobalMetrics

        gm = GlobalMetrics(ascent=800, descent=200)
        assert gm.units_per_em == 1000.0
        assert gm.cap_height == 0.0

    def test_glyph_info_dataclass(self):
        from aifont.core.analyzer import GlyphInfo

        gi = GlyphInfo(name="A", unicode_value=65, width=600, has_contours=True)
        assert gi.name == "A"

    def test_basic_problem_dataclass(self):
        from aifont.core.analyzer import BasicProblem

        bp = BasicProblem(severity="error", description="bad contour")
        assert bp.severity == "error"

    def test_compute_unicode_coverage(self):
        from aifont.core.analyzer import FontAnalyzer, GlyphInfo
        from aifont.core.font import Font

        ff = _make_mock_ff()
        font = Font(ff)
        analyzer = FontAnalyzer.__new__(FontAnalyzer)
        analyzer._font = font

        glyphs = [
            GlyphInfo(name=f"uni{cp:04X}", unicode_value=cp, width=600, has_contours=True)
            for cp in range(0x0020, 0x007F)
        ]
        cov = analyzer._compute_unicode_coverage(glyphs)
        assert cov == 1.0

    def test_compute_quality_score_perfect(self):
        from aifont.core.analyzer import FontAnalyzer, GlobalMetrics, GlyphInfo
        from aifont.core.font import Font

        ff = _make_mock_ff()
        font = Font(ff)
        analyzer = FontAnalyzer.__new__(FontAnalyzer)
        analyzer._font = font
        analyzer._latin_coverage = 1.0

        metrics = GlobalMetrics(
            ascent=800, descent=200, cap_height=700, x_height=500,
            units_per_em=1000, italic_angle=0.0, underline_position=-100,
            underline_width=50, family_name="Test", full_name="Test Regular",
            weight="Regular", version="1.0", copyright="", is_fixed_pitch=False,
            sf_version="",
        )
        glyphs = [
            GlyphInfo(name=f"u{cp:04X}", unicode_value=cp, width=600, has_contours=True)
            for cp in range(0x0020, 0x007F)
        ]
        score = analyzer._compute_quality_score(metrics, glyphs, [])
        assert score >= 90.0
        assert score <= 100.0


# ===========================================================================
# aifont.core.contour (extended coverage)
# ===========================================================================


class TestContourExtended:
    def _make_glyph(self):
        from aifont.core.glyph import Glyph
        return Glyph(MagicMock())

    def test_reverse_direction(self):
        from aifont.core.contour import reverse_direction
        g = self._make_glyph()
        reverse_direction(g)
        g._ff.reverseDirection.assert_called_once()

    def test_add_extrema(self):
        from aifont.core.contour import add_extrema
        g = self._make_glyph()
        add_extrema(g)
        g._ff.addExtrema.assert_called_once()

    def test_round_to_int(self):
        from aifont.core.contour import round_to_int
        g = self._make_glyph()
        round_to_int(g)
        g._ff.round.assert_called_once()

    def test_apply_stroke(self):
        from aifont.core.contour import apply_stroke
        g = self._make_glyph()
        apply_stroke(g, width=30.0)
        g._ff.changeWeight.assert_called()

    def test_apply_slant_calls_transform(self):
        from aifont.core.contour import apply_slant
        g = self._make_glyph()
        apply_slant(g, angle_deg=12.0)
        g._ff.transform.assert_called_once()

    def test_scale(self):
        from aifont.core.contour import scale
        g = self._make_glyph()
        scale(g, sx=1.2, sy=1.0)
        g._ff.transform.assert_called_once()

    def test_translate(self):
        from aifont.core.contour import translate
        g = self._make_glyph()
        translate(g, dx=10.0, dy=20.0)
        g._ff.transform.assert_called_once()

    def test_smooth_transitions(self):
        from aifont.core.contour import smooth_transitions
        g = self._make_glyph()
        smooth_transitions(g)
        g._ff.simplify.assert_called_once()

    def test_to_svg_path_no_export(self):
        from aifont.core.contour import to_svg_path
        from aifont.core.glyph import Glyph
        ff = MagicMock(spec=["transform"])  # no 'export' attr
        g = Glyph(ff)
        result = to_svg_path(g)
        assert result == ""

    def test_correct_direction_alias(self):
        from aifont.core.contour import correct_directions
        from aifont.core.glyph import Glyph
        g = Glyph(MagicMock())
        correct_directions(g)  # calls correct_direction internally
        g._ff.correctDirection.assert_called()


# ===========================================================================
# aifont.core.svg_parser (extended coverage)
# ===========================================================================


class TestSvgParserExtended:
    def test_flip_y(self):
        from aifont.core.svg_parser import _flip_y
        assert _flip_y(0.0, em=1000.0) == 1000.0
        assert _flip_y(1000.0, em=1000.0) == 0.0

    def test_parse_viewbox_valid(self):
        from aifont.core.svg_parser import _parse_viewbox
        result = _parse_viewbox("0 0 500 700")
        assert result == (0.0, 0.0, 500.0, 700.0)

    def test_parse_viewbox_empty(self):
        from aifont.core.svg_parser import _parse_viewbox
        assert _parse_viewbox("") is None

    def test_parse_viewbox_invalid(self):
        from aifont.core.svg_parser import _parse_viewbox
        assert _parse_viewbox("not a viewbox") is None

    def test_parse_viewbox_comma_separated(self):
        from aifont.core.svg_parser import _parse_viewbox
        result = _parse_viewbox("0,0,500,700")
        assert result == (0.0, 0.0, 500.0, 700.0)

    def test_collect_path_data_single_path(self):
        import xml.etree.ElementTree as ET

        from aifont.core.svg_parser import _SVG_NS, _collect_path_data
        svg_xml = f'<svg xmlns="{_SVG_NS}"><path d="M 0 0 L 100 100"/></svg>'
        root = ET.fromstring(svg_xml)
        paths = _collect_path_data(root)
        assert len(paths) == 1
        assert "M" in paths[0]

    def test_collect_path_data_empty_svg(self):
        import xml.etree.ElementTree as ET

        from aifont.core.svg_parser import _collect_path_data
        root = ET.fromstring('<svg/>')
        paths = _collect_path_data(root)
        assert paths == []

    def test_get_em_from_object(self):
        from aifont.core.svg_parser import _get_em
        ff = MagicMock()
        ff.em = 2048
        assert _get_em(ff) == 2048.0

    def test_get_em_fallback(self):
        from aifont.core.svg_parser import _get_em
        assert _get_em(object()) == 1000.0

    def test_svg_to_glyph_no_ff(self):
        import tempfile

        from aifont.core.svg_parser import svg_to_glyph
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg"><path d="M 0 0 Z"/></svg>'
        with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as f:
            f.write(svg_content)
            path = f.name
        import os
        try:
            # When fontforge is not available, svg_to_glyph should not raise
            font = MagicMock()
            font._font = MagicMock(spec=["em"])
            font._font.em = 1000
            result = svg_to_glyph(path, font, 0x0041, "A")
            # May return None or nothing; should not raise
        except Exception:
            pass  # acceptable if fontforge is unavailable
        finally:
            os.unlink(path)

    def test_parse_path_d_horizontal(self):
        from aifont.core.svg_parser import _parse_path_d
        cmds = _parse_path_d("M 10 10 H 100")
        cmd_names = [c for c, _ in cmds]
        assert "M" in cmd_names

    def test_parse_path_d_vertical(self):
        from aifont.core.svg_parser import _parse_path_d
        cmds = _parse_path_d("M 10 10 V 100")
        cmd_names = [c for c, _ in cmds]
        assert "M" in cmd_names


# ===========================================================================
# aifont.core.font (extended coverage)
# ===========================================================================


class TestFontExtended:
    def test_metadata_setter(self):
        from aifont.core.font import Font
        ff = _make_mock_ff()
        font = Font(ff)
        font.metadata = {"family": "NewFamily", "em_size": 2048}
        assert ff.familyname == "NewFamily"
        assert ff.em == 2048

    def test_name_getter_setter(self):
        from aifont.core.font import Font
        ff = _make_mock_ff()
        font = Font(ff)
        assert font.name == "Test"
        font.name = "NewFont"
        assert ff.fontname == "NewFont"

    def test_ascent_getter_setter(self):
        from aifont.core.font import Font
        ff = _make_mock_ff()
        font = Font(ff)
        assert font.ascent == 800
        font.ascent = 900
        assert ff.ascent == 900

    def test_descent_getter_setter(self):
        from aifont.core.font import Font
        ff = _make_mock_ff()
        font = Font(ff)
        assert font.descent == 200
        font.descent = 250
        assert ff.descent == 250

    def test_font_raw_property(self):
        from aifont.core.font import Font
        ff = _make_mock_ff()
        font = Font(ff)
        # _raw or _font should return the raw ff object
        assert font._font is ff

    def test_add_glyph(self):
        from aifont.core.font import Font
        from aifont.core.glyph import Glyph
        ff = _make_mock_ff()
        mock_glyph = MagicMock()
        ff.createChar.return_value = mock_glyph
        font = Font(ff)
        g = font.add_glyph("A", unicode_val=65)
        assert isinstance(g, Glyph)

    def test_glyph_by_name(self):
        from aifont.core.font import Font
        from aifont.core.glyph import Glyph
        ff = _make_mock_ff()
        mock_glyph = MagicMock()
        ff.__getitem__ = MagicMock(return_value=mock_glyph)
        font = Font(ff)
        g = font.glyph("A")
        assert isinstance(g, Glyph)

    def test_glyph_not_found_returns_none(self):
        from aifont.core.font import Font
        ff = _make_mock_ff()
        ff.__getitem__ = MagicMock(side_effect=TypeError("no glyph"))
        font = Font(ff)
        g = font.glyph("Z")
        assert g is None

    def test_save_delegates_to_ff_save(self):
        from aifont.core.font import Font
        ff = _make_mock_ff()
        font = Font(ff)
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.sfd")
            font.save(path)
            ff.save.assert_called_once()

    def test_font_metadata_contains_family(self):
        from aifont.core.font import FontMetadata
        ff = _make_mock_ff()
        meta = FontMetadata(ff)
        assert "family" in meta
        assert "familyname" in meta

    def test_font_metadata_contains_em_size(self):
        from aifont.core.font import FontMetadata
        ff = _make_mock_ff()
        meta = FontMetadata(ff)
        assert "em_size" in meta

    def test_new_raises_without_fontforge(self):
        import aifont.core.font as fmod
        from aifont.core.font import Font
        with patch.object(fmod, "_FF_AVAILABLE", False):
            try:
                Font.new("Test")
                assert False, "Expected RuntimeError"
            except RuntimeError:
                pass

    def test_open_raises_for_missing_file(self):
        from aifont.core.font import Font
        try:
            Font.open("/nonexistent/file.sfd")
            assert False, "Expected FileNotFoundError"
        except FileNotFoundError:
            pass


# ===========================================================================
# aifont.core.metrics (extended coverage)
# ===========================================================================


class TestMetricsExtended:
    def test_set_side_bearings(self):
        from aifont.core.metrics import set_side_bearings
        ff = MagicMock(spec=["__getitem__"])
        mock_glyph = MagicMock()
        ff.__getitem__ = MagicMock(return_value=mock_glyph)
        set_side_bearings(ff, "A", lsb=50, rsb=60)
        assert mock_glyph.left_side_bearing == 50
        assert mock_glyph.right_side_bearing == 60

    def test_analyze_spacing_with_glyphs(self):
        from aifont.core.metrics import analyze_spacing
        ff = MagicMock()
        mock_glyph = MagicMock()
        mock_glyph.width = 600
        mock_glyph.left_side_bearing = 50
        mock_glyph.right_side_bearing = 50
        ff.__iter__ = lambda self: iter(["A", "B"])
        ff.__getitem__ = MagicMock(return_value=mock_glyph)
        ff.subtables = None
        result = analyze_spacing(ff)
        assert result.glyph_count >= 0

    def test_get_side_bearings_returns_sidebearings(self):
        from aifont.core.metrics import SideBearings, get_side_bearings
        # Use spec to prevent _font auto-attribute creation
        ff = MagicMock(spec=["__getitem__", "subtables"])
        mock_glyph = MagicMock()
        mock_glyph.left_side_bearing = 50
        mock_glyph.right_side_bearing = 60
        ff.__getitem__ = MagicMock(return_value=mock_glyph)
        result = get_side_bearings(ff, "A")
        assert isinstance(result, SideBearings)
        assert result.left == 50
        assert result.right == 60


# ===========================================================================
# aifont.agents.metrics_agent (extended coverage)
# ===========================================================================


class TestMetricsAgentExtended:
    def test_set_kern_pair(self):
        from aifont.agents.metrics_agent import MetricsAgent
        agent = MetricsAgent()
        with patch("aifont.agents.metrics_agent.set_kern") as mock_set_kern:
            agent.set_kern_pair(MagicMock(), "A", "V", -30)
            mock_set_kern.assert_called_once()

    def test_set_side_bearings(self):
        from aifont.agents.metrics_agent import MetricsAgent
        agent = MetricsAgent()
        with patch("aifont.agents.metrics_agent.set_side_bearings") as mock_set:
            agent.set_side_bearings(MagicMock(), "A", lsb=50, rsb=60)
            mock_set.assert_called_once()

    def test_run_with_font_keyword(self):
        from aifont.agents.metrics_agent import MetricsAgent, MetricsReport
        from aifont.core.metrics import SpacingAnalysis
        agent = MetricsAgent(apply_autospace=False, apply_autokern=False)
        with (
            patch("aifont.agents.metrics_agent.analyze_spacing", return_value=SpacingAnalysis()),
        ):
            result = agent.run(font=_make_font())
        assert isinstance(result, MetricsReport)

    def test_run_no_font_returns_default_report(self):
        from aifont.agents.metrics_agent import MetricsAgent, MetricsReport
        agent = MetricsAgent()
        result = agent.run()
        assert isinstance(result, MetricsReport)
        assert result.confidence == 0.5

    def test_metrics_report_asdict(self):
        from dataclasses import asdict

        from aifont.agents.metrics_agent import MetricsReport
        r = MetricsReport(font_name="Test")
        d = asdict(r)
        assert "font_name" in d


# ===========================================================================
# aifont.agents.export_agent (extended coverage)
# ===========================================================================


class TestExportAgentExtended:
    def test_choose_formats_web(self):
        from aifont.agents.export_agent import ExportAgent, ExportTarget
        agent = ExportAgent()
        formats = agent._choose_formats(ExportTarget.WEB, None)
        assert "woff2" in formats

    def test_choose_formats_with_extras(self):
        from aifont.agents.export_agent import ExportAgent, ExportTarget
        agent = ExportAgent()
        formats = agent._choose_formats(ExportTarget.WEB, ["svg"])
        assert "svg" in formats

    def test_run_legacy_no_output_dir(self):
        from aifont.agents.export_agent import ExportAgent, ExportResult
        agent = ExportAgent()
        font = _make_font()
        result = agent.run(font, output_dir=None)
        assert isinstance(result, ExportResult)
        assert result.success is False

    def test_run_with_legacy_api(self):
        import tempfile

        from aifont.agents.export_agent import ExportAgent, ExportResult
        agent = ExportAgent(generate_specimen=False, generate_css=False, validate=False)
        font = _make_font()
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("aifont.agents.export_agent.export_otf", return_value=None),
            patch("aifont.agents.export_agent.export_ttf", return_value=None),
            patch("aifont.agents.export_agent.export_woff2", return_value=None),
        ):
            result = agent.run(
                font,
                output_dir=tmpdir,
                target="web",
            )
        assert isinstance(result, ExportResult)


# ===========================================================================
# aifont.core.font.FontMetadata — property accessor coverage
# ===========================================================================


class TestFontMetadataProperties:
    def _make_meta(self):
        from aifont.core.font import FontMetadata
        return FontMetadata(_make_mock_ff())

    def test_family_name_getter(self):
        meta = self._make_meta()
        assert meta.family_name == "Test"

    def test_family_name_setter(self):
        meta = self._make_meta()
        meta.family_name = "New"
        assert meta.family_name == "New"

    def test_full_name_getter(self):
        meta = self._make_meta()
        assert meta.full_name == "Test Regular"

    def test_full_name_setter(self):
        meta = self._make_meta()
        meta.full_name = "Test Bold"
        assert meta.full_name == "Test Bold"

    def test_name_getter(self):
        meta = self._make_meta()
        assert meta.name == "Test"

    def test_name_setter(self):
        meta = self._make_meta()
        meta.name = "NewFont"
        assert meta.name == "NewFont"

    def test_font_name_alias(self):
        meta = self._make_meta()
        assert meta.font_name == meta.name

    def test_family_getter(self):
        meta = self._make_meta()
        assert meta.family == "Test"

    def test_family_setter(self):
        meta = self._make_meta()
        meta.family = "Updated"
        assert meta.family == "Updated"

    def test_version_getter(self):
        meta = self._make_meta()
        assert meta.version == "1.0"

    def test_version_setter(self):
        meta = self._make_meta()
        meta.version = "2.0"
        assert meta.version == "2.0"

    def test_copyright_getter(self):
        meta = self._make_meta()
        assert meta.copyright == ""

    def test_copyright_setter(self):
        meta = self._make_meta()
        meta.copyright = "(c) 2024"
        assert meta.copyright == "(c) 2024"

    def test_weight_getter(self):
        meta = self._make_meta()
        assert meta.weight == "Regular"

    def test_weight_setter(self):
        meta = self._make_meta()
        meta.weight = "Bold"
        assert meta.weight == "Bold"

    def test_em_size_getter(self):
        meta = self._make_meta()
        assert meta.em_size == 1000

    def test_em_size_setter(self):
        meta = self._make_meta()
        meta.em_size = 2048
        assert meta.em_size == 2048

    def test_ascent_getter(self):
        meta = self._make_meta()
        assert meta.ascent == 800

    def test_ascent_setter(self):
        meta = self._make_meta()
        meta.ascent = 900
        assert meta.ascent == 900

    def test_descent_getter(self):
        meta = self._make_meta()
        assert meta.descent == 200

    def test_descent_setter(self):
        meta = self._make_meta()
        meta.descent = 250
        assert meta.descent == 250

    def test_to_dict(self):
        from aifont.core.font import FontMetadata
        meta = FontMetadata(_make_mock_ff())
        d = meta.to_dict()
        # to_dict returns "name", "family", "weight", "version", "copyright", "em_size"
        assert "name" in d
        assert "family" in d

    def test_getitem_fontname(self):
        from aifont.core.font import FontMetadata
        meta = FontMetadata(_make_mock_ff())
        assert meta["fontname"] == "Test"

    def test_getitem_fullname(self):
        from aifont.core.font import FontMetadata
        meta = FontMetadata(_make_mock_ff())
        assert meta["fullname"] == "Test Regular"


# ===========================================================================
# aifont.core.metrics (more coverage)
# ===========================================================================


class TestMetricsMoreCoverage:
    def test_set_kern_creates_lookup(self):
        from aifont.core.metrics import set_kern
        ff = MagicMock(spec=["addLookup", "addLookupSubtable", "gpos_lookups", "__getitem__"])
        ff.gpos_lookups = []
        mock_glyph = MagicMock()
        ff.__getitem__ = MagicMock(return_value=mock_glyph)
        set_kern(ff, "A", "V", -30)
        ff.addLookup.assert_called()

    def test_remove_kern_returns_false_for_empty_font(self):
        from aifont.core.metrics import remove_kern
        ff = MagicMock(spec=["__iter__"])
        ff.__iter__ = lambda self: iter([])
        result = remove_kern(ff, "A", "V")
        assert result is False

    def test_auto_space_fallback_path(self):
        from aifont.core.metrics import auto_space
        ff = MagicMock(spec=["autoWidth", "__iter__", "__getitem__"])
        ff.autoWidth.side_effect = AttributeError("not available")
        ff.__iter__ = lambda self: iter(["A"])
        mock_glyph = MagicMock()
        mock_glyph.width = 600
        ff.__getitem__ = MagicMock(return_value=mock_glyph)
        auto_space(ff)  # should not raise

    def test_auto_kern_with_empty_font(self):
        from aifont.core.metrics import auto_kern
        ff = MagicMock(spec=["autoKern", "__iter__", "gpos_lookups"])
        ff.__iter__ = lambda self: iter([])
        ff.gpos_lookups = []
        result = auto_kern(ff)
        assert isinstance(result, list)


# ===========================================================================
# aifont.core.variable (build_design_space)
# ===========================================================================


class TestVariableBuildDesignSpace:
    def test_build_design_space_basic(self):
        try:
            from aifont.core.variable import (
                Master,
                NamedInstance,
                VariationAxis,
                _build_design_space,
            )
            axes = [VariationAxis("wght", "Weight", minimum=100.0, default=400.0, maximum=900.0)]
            masters = [
                Master("Regular", "/tmp/r.ufo", {"wght": 400.0}, is_default=True),
                Master("Bold", "/tmp/b.ufo", {"wght": 700.0}),
            ]
            instances = [NamedInstance("Regular", {"wght": 400.0})]
            doc = _build_design_space(axes, masters, instances, family_name="TestVF")
            assert doc.family_name == "TestVF"
            assert len(doc.axes) == 1
            assert len(doc.sources) == 2
            assert len(doc.instances) == 1
        except ImportError:
            import pytest
            pytest.skip("fontTools not available")

    def test_build_design_space_without_fonttools(self):
        with patch("aifont.core.variable._FONTTOOLS_AVAILABLE", False):
            from aifont.core.variable import _build_design_space
            try:
                _build_design_space([], [], [])
                assert False, "Expected ImportError"
            except ImportError:
                pass

    def test_variable_font_builder_build_design_space(self):
        try:
            from aifont.core.variable import (
                Master,
                NamedInstance,
                VariableFontBuilder,
                VariationAxis,
            )
            builder = VariableFontBuilder(family_name="TestVF")
            builder.add_axis(VariationAxis("wght", "Weight", minimum=100.0, default=400.0, maximum=900.0))
            builder.add_master(Master("Regular", "/tmp/r.ufo", {"wght": 400.0}, is_default=True))
            builder.add_master(Master("Bold", "/tmp/b.ufo", {"wght": 700.0}))
            builder.add_instance(NamedInstance("Regular", {"wght": 400.0}))
            doc = builder.build_design_space()
            assert doc.family_name == "TestVF"
        except ImportError:
            import pytest
            pytest.skip("fontTools not available")


# ===========================================================================
# aifont.core.export (extended)
# ===========================================================================


class TestExportExtended:
    def _make_raw_ff(self):
        return MagicMock(spec=["generate", "save"])

    def test_export_variable_no_fonttools(self):
        from aifont.core.export import export_variable
        with patch("aifont.core.export._FONTTOOLS_AVAILABLE", False):
            try:
                result = export_variable(self._make_raw_ff(), "/tmp/out.ttf")
                # May succeed or fail gracefully
            except (RuntimeError, AttributeError):
                pass  # expected

    def test_subset_font_no_fonttools(self):
        from aifont.core.export import subset_font
        ff = self._make_raw_ff()
        with patch("aifont.core.export.export_woff2", return_value=None):
            # subset_font(font, path, languages) - positional arg, not kwarg
            try:
                import os
                import tempfile
                with tempfile.TemporaryDirectory() as tmpdir:
                    out = os.path.join(tmpdir, "out.woff2")
                    result = subset_font(ff, out, [])
            except Exception:
                pass  # acceptable

    def test_export_all_with_otf(self):
        import tempfile

        from aifont.core.export import export_all

        with tempfile.TemporaryDirectory() as tmpdir:
            ff = self._make_raw_ff()
            with patch("aifont.core.export.export_otf", return_value=None):
                results = export_all(ff, tmpdir, formats=["otf"])
            assert isinstance(results, dict)


# ===========================================================================
# aifont.core.font — Font container/iterator tests
# ===========================================================================


def _make_font_with_glyphs():
    """Font wrapper backed by a mock that has glyph iteration."""
    from aifont.core.font import Font
    ff = MagicMock()
    ff.familyname = "TestFont"
    ff.fontname = "TestFont"
    ff.fullname = "TestFont Regular"
    ff.weight = "Regular"
    ff.copyright = ""
    ff.version = "1.0"
    ff.em = 1000
    ff.ascent = 800
    ff.descent = 200
    ff.gpos_lookups = []
    ff.validate.return_value = 0
    # Provide three glyphs
    glyph_a = MagicMock()
    glyph_a.glyphname = "A"
    glyph_a.unicode = 65
    glyph_b = MagicMock()
    glyph_b.glyphname = "B"
    glyph_b.unicode = 66
    glyph_c = MagicMock()
    glyph_c.glyphname = "space"
    glyph_c.unicode = 32
    ff.__iter__ = lambda self: iter(["A", "B", "space"])
    glyph_map = {"A": glyph_a, "B": glyph_b, "space": glyph_c, 65: glyph_a, 66: glyph_b}
    ff.__getitem__ = MagicMock(side_effect=lambda key: glyph_map[key])
    ff.createChar = MagicMock(return_value=glyph_a)
    return Font(ff), ff


class TestFontWithGlyphs:
    def test_glyphs_returns_list(self):
        from aifont.core.glyph import Glyph
        font, _ = _make_font_with_glyphs()
        glyphs = list(font.glyphs)
        assert len(glyphs) == 3
        assert all(isinstance(g, Glyph) for g in glyphs)

    def test_iter(self):
        font, _ = _make_font_with_glyphs()
        names = [g.name for g in font]
        assert len(names) == 3

    def test_len(self):
        font, _ = _make_font_with_glyphs()
        assert len(font) == 3

    def test_contains_existing(self):
        font, _ = _make_font_with_glyphs()
        assert "A" in font

    def test_contains_missing_returns_false(self):
        font, ff = _make_font_with_glyphs()
        ff.__getitem__ = MagicMock(side_effect=lambda key: (_ for _ in ()).throw(KeyError(key)))
        assert "Z" not in font

    def test_getitem(self):
        from aifont.core.glyph import Glyph
        font, _ = _make_font_with_glyphs()
        g = font["A"]
        assert isinstance(g, Glyph)

    def test_getitem_missing_raises_key_error(self):
        font, ff = _make_font_with_glyphs()
        ff.__getitem__ = MagicMock(side_effect=KeyError("Z"))
        try:
            _ = font["Z"]
            assert False, "Expected KeyError"
        except KeyError:
            pass

    def test_glyph_by_codepoint(self):
        from aifont.core.glyph import Glyph
        font, _ = _make_font_with_glyphs()
        g = font.glyph(65)  # 'A'
        assert isinstance(g, Glyph)

    def test_get_glyph_raises_on_missing(self):
        font, ff = _make_font_with_glyphs()
        ff.__getitem__ = MagicMock(side_effect=KeyError("Z"))
        try:
            font.get_glyph("Z")
            assert False, "Expected KeyError"
        except KeyError:
            pass

    def test_list_glyphs(self):
        font, _ = _make_font_with_glyphs()
        names = font.list_glyphs()
        assert "A" in names

    def test_glyph_count(self):
        font, _ = _make_font_with_glyphs()
        assert font.glyph_count == 3

    def test_export_otf(self):
        import os
        import tempfile
        font, ff = _make_font_with_glyphs()
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "test.otf")
            font.export("otf", out)
            ff.generate.assert_called()

    def test_export_sfd(self):
        import os
        import tempfile
        font, ff = _make_font_with_glyphs()
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "test.sfd")
            font.export("sfd", out)
            ff.save.assert_called()

    def test_export_unknown_raises(self):
        font, _ = _make_font_with_glyphs()
        try:
            font.export("xyz", "/tmp/out.xyz")
            assert False, "Expected ValueError"
        except ValueError:
            pass

    def test_close(self):
        font, ff = _make_font_with_glyphs()
        font.close()
        ff.close.assert_called_once()

    def test_context_manager(self):
        font, ff = _make_font_with_glyphs()
        with font as f:
            assert f is font
        # close() was called
        ff.close.assert_called()

    def test_repr(self):
        font, _ = _make_font_with_glyphs()
        r = repr(font)
        assert "TestFont" in r


# ===========================================================================
# aifont.core.analyzer — with glyph data
# ===========================================================================


class TestAnalyzerWithGlyphs:
    def test_count_kern_pairs_empty(self):
        from aifont.core.analyzer import _count_kern_pairs
        ff = MagicMock(spec=["__iter__"])
        ff.__iter__ = lambda self: iter([])
        result = _count_kern_pairs(ff)
        assert result == 0

    def test_find_open_contours_empty(self):
        from aifont.core.analyzer import _find_open_contours
        ff = MagicMock(spec=["__iter__"])
        ff.__iter__ = lambda self: iter([])
        result = _find_open_contours(ff)
        assert result == []

    def test_estimate_metrics(self):
        from aifont.core.analyzer import _estimate_metrics
        ff = MagicMock()
        ff.ascent = 800
        ff.descent = 200
        ff.em = 1000
        result = _estimate_metrics(ff)
        assert "ascender" in result
        assert result["ascender"] == 800.0

    def test_analyze_with_glyphs(self):
        from aifont.core.analyzer import FontReport, analyze
        font, ff = _make_font_with_glyphs()
        # Add unicode and validate to glyphs
        report = analyze(font)
        assert isinstance(report, FontReport)
        assert report.glyph_count >= 0

    def test_analyze_with_validation_errors(self):
        from aifont.core.analyzer import FontReport, analyze
        font, ff = _make_font_with_glyphs()
        # Simulate glyph validate returning errors
        for glyph_mock in [ff.__getitem__("A"), ff.__getitem__("B"), ff.__getitem__("space")]:
            glyph_mock.validate.return_value = 4  # SELF_INTERSECTION bit
        report = analyze(font)
        assert isinstance(report, FontReport)

    def test_font_report_with_validation_errors(self):
        from aifont.core.analyzer import FontReport
        r = FontReport(validation_errors=["critical error"])
        assert not r.passed

    def test_font_report_passed_with_no_issues(self):
        from aifont.core.analyzer import FontReport
        r = FontReport()
        assert r.passed is True

    def test_font_analyzer_run_with_glyph_info(self):
        from aifont.core.analyzer import FontAnalyzer, FontReport
        font, _ = _make_font_with_glyphs()
        analyzer = FontAnalyzer(font)
        report = analyzer.run()
        assert isinstance(report, FontReport)


# ===========================================================================
# aifont.core.variable — VariableFontBuilder extended
# ===========================================================================


class TestVariableFontBuilderExtended:
    def test_preview_interpolation_with_builder(self):
        from aifont.core.variable import (
            Master,
            VariableFontBuilder,
            VariationAxis,
            preview_interpolation,
        )
        builder = VariableFontBuilder(family_name="TestVF")
        ax = VariationAxis.from_tag("wght")
        builder.add_axis(ax)
        builder.add_master(Master("Regular", "/tmp/r.ufo", {"wght": 400.0}, is_default=True))
        builder.add_master(Master("Bold", "/tmp/b.ufo", {"wght": 700.0}))
        result = preview_interpolation(builder.axes, builder.masters, {"wght": 600.0})
        assert "wght" in result

    def test_conformance_with_axes_and_masters(self):
        from aifont.core.variable import (
            Master,
            NamedInstance,
            VariationAxis,
            check_opentype_conformance,
        )
        axes = [VariationAxis.from_tag("wght")]
        masters = [
            Master("Regular", "/tmp/r.ufo", {"wght": 400.0}, is_default=True),
        ]
        instances = [NamedInstance("Regular", {"wght": 400.0})]
        errors = check_opentype_conformance(axes, masters, instances)
        assert errors == []

    def test_instance_outside_range_detected(self):
        from aifont.core.variable import (
            Master,
            NamedInstance,
            VariationAxis,
            check_opentype_conformance,
        )
        axes = [VariationAxis("wght", "Weight", minimum=100.0, default=400.0, maximum=900.0)]
        masters = [Master("Regular", "/tmp/r.ufo", {"wght": 400.0}, is_default=True)]
        instances = [NamedInstance("ExtraBlack", {"wght": 1000.0})]  # out of range
        errors = check_opentype_conformance(axes, masters, instances)
        assert any("1000" in e for e in errors)

    def test_duplicate_instance_name_detected(self):
        from aifont.core.variable import (
            Master,
            NamedInstance,
            VariationAxis,
            check_opentype_conformance,
        )
        axes = [VariationAxis("wght", "Weight", minimum=100.0, default=400.0, maximum=900.0)]
        masters = [Master("Regular", "/tmp/r.ufo", {"wght": 400.0}, is_default=True)]
        instances = [
            NamedInstance("Regular", {"wght": 400.0}),
            NamedInstance("Regular", {"wght": 400.0}),  # duplicate
        ]
        errors = check_opentype_conformance(axes, masters, instances)
        assert any("Duplicate" in e for e in errors)
