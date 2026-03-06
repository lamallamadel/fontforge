"""Unit tests for aifont.agents.* — mock-based, no FontForge or LLM required."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_font(family: str = "Test") -> MagicMock:
    ff = MagicMock()
    ff.familyname = family
    ff.fullname = f"{family} Regular"
    ff.fontname = family
    ff.weight = "Regular"
    ff.copyright = ""
    ff.version = "1.0"
    ff.em = 1000
    ff.ascent = 800
    ff.descent = 200
    ff.__iter__ = lambda self: iter([])
    ff.gsub_lookups = []
    ff.gpos_lookups = []
    ff.validate.return_value = 0
    return ff


def _make_font_wrapper(family: str = "Test"):
    from aifont.core.font import Font

    return Font(_make_mock_font(family))


# ===========================================================================
# DesignAgent
# ===========================================================================


class TestDesignAgent:
    def test_instantiation_no_args(self):
        from aifont.agents.design_agent import DesignAgent

        agent = DesignAgent()
        assert agent._llm is None

    def test_instantiation_with_llm(self):
        from aifont.agents.design_agent import DesignAgent

        llm = MagicMock()
        agent = DesignAgent(llm_client=llm)
        assert agent._llm is llm

    def test_extract_glyph_name_uppercase(self):
        from aifont.agents.design_agent import DesignAgent

        agent = DesignAgent()
        assert agent._extract_glyph_name("Draw a letter A") == "A"

    def test_extract_glyph_name_lowercase_uppercases(self):
        from aifont.agents.design_agent import DesignAgent

        agent = DesignAgent()
        result = agent._extract_glyph_name("draw letter b please")
        assert result == "B"

    def test_extract_glyph_name_no_match_returns_A(self):
        from aifont.agents.design_agent import DesignAgent

        agent = DesignAgent()
        assert agent._extract_glyph_name("no match here 123") == "A"

    def test_generate_svg_no_llm_returns_placeholder(self):
        from aifont.agents.design_agent import DesignAgent

        agent = DesignAgent()
        svg = agent._generate_svg("draw something")
        assert svg is not None
        assert "<svg" in svg

    def test_generate_svg_with_llm(self):
        from aifont.agents.design_agent import DesignAgent

        llm = MagicMock()
        llm.generate_svg.return_value = "<svg><path/></svg>"
        agent = DesignAgent(llm_client=llm)
        svg = agent._generate_svg("draw A")
        assert svg == "<svg><path/></svg>"

    def test_generate_svg_llm_exception_falls_back(self):
        from aifont.agents.design_agent import DesignAgent

        llm = MagicMock()
        llm.generate_svg.side_effect = RuntimeError("LLM error")
        agent = DesignAgent(llm_client=llm)
        svg = agent._generate_svg("draw A")
        assert svg is not None
        assert "<svg" in svg

    def test_run_no_font(self):
        from aifont.agents.design_agent import DesignAgent, DesignResult

        agent = DesignAgent()
        result = agent.run("Draw a letter A")
        assert isinstance(result, DesignResult)
        assert result.glyph_name == "A"
        assert result.font is None

    def test_run_with_font_injects_svg(self):
        from aifont.agents.design_agent import DesignAgent, DesignResult

        font = _make_font_wrapper()
        agent = DesignAgent()
        with patch("aifont.core.svg_parser.svg_to_glyph"):
            result = agent.run("Draw letter A", font=font)
        assert isinstance(result, DesignResult)
        assert result.font is font

    def test_design_result_defaults(self):
        from aifont.agents.design_agent import DesignResult

        r = DesignResult(font=None, glyph_name="A")
        assert r.confidence == 1.0
        assert r.svg_data is None


# ===========================================================================
# MetricsAgent
# ===========================================================================


class TestMetricsAgent:
    def test_instantiation(self):
        from aifont.agents.metrics_agent import MetricsAgent

        agent = MetricsAgent()
        assert agent.apply_autospace is True
        assert agent.apply_autokern is True

    def test_instantiation_with_style(self):
        from aifont.agents.metrics_agent import MetricsAgent

        agent = MetricsAgent(style_intent="tight")
        assert agent.style_intent == "tight"

    def test_analyze_spacing_delegates(self):
        from aifont.agents.metrics_agent import MetricsAgent
        from aifont.core.metrics import SpacingAnalysis

        agent = MetricsAgent()
        with patch("aifont.agents.metrics_agent.analyze_spacing", return_value=SpacingAnalysis()):
            result = agent.analyze_spacing(MagicMock())
        assert isinstance(result, SpacingAnalysis)

    def test_auto_kern_delegates(self):
        from aifont.agents.metrics_agent import MetricsAgent

        agent = MetricsAgent()
        with patch("aifont.agents.metrics_agent.auto_kern", return_value=[]):
            result = agent.auto_kern(MagicMock())
        assert result == []

    def test_run_returns_report(self):
        from aifont.agents.metrics_agent import MetricsAgent, MetricsReport
        from aifont.core.metrics import SpacingAnalysis

        agent = MetricsAgent(apply_autospace=False, apply_autokern=False)
        with (
            patch("aifont.agents.metrics_agent.analyze_spacing", return_value=SpacingAnalysis()),
            patch("aifont.agents.metrics_agent.auto_space", return_value=[]),
            patch("aifont.agents.metrics_agent.auto_kern", return_value=[]),
        ):
            result = agent.run(_make_font_wrapper())
        assert isinstance(result, MetricsReport)

    def test_metrics_report_dataclass(self):
        from aifont.agents.metrics_agent import MetricsReport

        r = MetricsReport(font_name="TestFont", summary="OK")
        assert r.font_name == "TestFont"
        assert r.summary == "OK"
        assert r.kern_pairs_added == []

    def test_glyph_metrics_snapshot(self):
        from aifont.agents.metrics_agent import GlyphMetricsSnapshot

        s = GlyphMetricsSnapshot(glyph_name="A", lsb=50, rsb=50, width=600)
        assert s.lsb == 50


# ===========================================================================
# StyleAgent
# ===========================================================================


class TestStyleAgent:
    def test_instantiation(self):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        assert agent.default_stroke_delta == 30.0
        assert agent.default_slant_angle == 12.0

    def test_detect_intent_bold(self):
        from aifont.agents.style_agent import _detect_intent

        assert _detect_intent("make it bold") == "bold"

    def test_detect_intent_light(self):
        from aifont.agents.style_agent import _detect_intent

        assert _detect_intent("make it lighter") == "light"

    def test_detect_intent_italic(self):
        from aifont.agents.style_agent import _detect_intent

        assert _detect_intent("apply italic style") == "italic"

    def test_detect_intent_vintage(self):
        from aifont.agents.style_agent import _detect_intent

        assert _detect_intent("give it a vintage look") == "vintage"

    def test_detect_intent_transfer(self):
        from aifont.agents.style_agent import _detect_intent

        assert _detect_intent("inspire from this font") == "transfer"

    def test_detect_intent_unknown(self):
        from aifont.agents.style_agent import _detect_intent

        assert _detect_intent("nothing specific") == "unknown"

    def test_run_bold_intent(self):
        from aifont.agents.style_agent import StyleAgent, StyleTransferResult

        font = _make_font_wrapper()
        agent = StyleAgent()
        with patch.object(agent, "apply_stroke", return_value=StyleTransferResult(font=font)):
            result = agent.run("make this bold", font=font)
        assert isinstance(result, StyleTransferResult)

    def test_run_italic_intent(self):
        from aifont.agents.style_agent import StyleAgent, StyleTransferResult

        font = _make_font_wrapper()
        agent = StyleAgent()
        with patch.object(agent, "apply_slant", return_value=StyleTransferResult(font=font)):
            result = agent.run("make it italic", font=font)
        assert isinstance(result, StyleTransferResult)

    def test_run_no_font_unknown_intent(self):
        from aifont.agents.style_agent import StyleAgent, StyleTransferResult

        agent = StyleAgent()
        result = agent.run("do nothing", font=None)
        assert isinstance(result, StyleTransferResult)

    def test_style_transfer_result_sync(self):
        from aifont.agents.style_agent import StyleTransferResult

        font = _make_font_wrapper()
        r = StyleTransferResult(font=font)
        assert r.target_font is font

    def test_style_transfer_result_summary(self):
        from aifont.agents.style_agent import StyleTransferResult

        r = StyleTransferResult(changes_applied=["stroked glyphs"])
        summary = r.summary()
        assert isinstance(summary, str)

    def test_style_result_alias(self):
        from aifont.agents.style_agent import StyleResult, StyleTransferResult

        assert StyleResult is StyleTransferResult


# ===========================================================================
# QAAgent
# ===========================================================================


class TestQAAgent:
    def test_instantiation_no_font(self):
        from aifont.agents.qa_agent import QAAgent

        agent = QAAgent()
        assert agent._font is None

    def test_instantiation_with_font(self):
        from aifont.agents.qa_agent import QAAgent

        font = _make_font_wrapper()
        agent = QAAgent(font=font)
        assert agent._font is font

    def test_validate_font_with_mock_analyze(self):
        from aifont.agents.qa_agent import QAAgent
        from aifont.core.analyzer import FontReport

        agent = QAAgent(font=_make_font_wrapper())
        with patch("aifont.agents.qa_agent.analyze", return_value=FontReport()):
            report = agent.validate_font()
        assert isinstance(report, FontReport)

    def test_generate_qa_report_from_fresh_analysis(self):
        from aifont.agents.qa_agent import QAAgent, QAReport
        from aifont.core.analyzer import FontReport

        font = _make_font_wrapper()
        agent = QAAgent(font=font)
        with patch("aifont.agents.qa_agent.analyze", return_value=FontReport()):
            qa_report = agent.generate_qa_report()
        assert isinstance(qa_report, QAReport)

    def test_fix_overlaps_with_explicit_empty_list(self):
        from aifont.agents.qa_agent import QAAgent

        font = _make_font_wrapper()
        agent = QAAgent(font=font)
        result = agent.fix_overlaps([])
        assert result == []

    def test_simplify_contours_with_explicit_empty_list(self):
        from aifont.agents.qa_agent import QAAgent

        font = _make_font_wrapper()
        agent = QAAgent(font=font)
        result = agent.simplify_contours([])
        assert result == []

    def test_run_returns_qa_report(self):
        from aifont.agents.qa_agent import QAAgent, QAReport
        from aifont.core.analyzer import FontReport

        font = _make_font_wrapper()
        agent = QAAgent(font=font)
        with patch("aifont.agents.qa_agent.analyze", return_value=FontReport()):
            result = agent.run("check quality", font=font)
        assert isinstance(result, QAReport)

    def test_run_no_font_returns_minimal_report(self):
        from aifont.agents.qa_agent import QAAgent, QAReport

        agent = QAAgent()
        result = agent.run("check quality")
        assert isinstance(result, QAReport)
        assert result.confidence == 0.0

    def test_check_result_passed(self):
        from aifont.agents.qa_agent import CheckResult

        cr = CheckResult(name="Open Contours", passed=True)
        assert cr.passed is True

    def test_qa_report_score(self):
        from aifont.agents.qa_agent import QAReport

        r = QAReport(score=90.0)
        assert r.score == 90.0
        assert isinstance(r.checks, dict)


# ===========================================================================
# ExportAgent
# ===========================================================================


class TestExportAgent:
    def test_instantiation(self):
        from aifont.agents.export_agent import ExportAgent, ExportTarget

        agent = ExportAgent()
        assert agent.target == ExportTarget.WEB

    def test_instantiation_custom_target(self):
        from aifont.agents.export_agent import ExportAgent, ExportTarget

        agent = ExportAgent(target=ExportTarget.PRINT)
        assert agent.target == ExportTarget.PRINT

    def test_run_no_font_no_output_path(self):
        from aifont.agents.export_agent import ExportAgent, ExportResult

        agent = ExportAgent()
        result = agent.run("export to web")
        assert isinstance(result, ExportResult)
        assert result.success is False
        assert result.error is not None

    def test_run_with_output_path_no_font(self):
        from aifont.agents.export_agent import ExportAgent, ExportResult

        agent = ExportAgent()
        result = agent.run("export to otf", output_path="/tmp/out.otf")
        assert isinstance(result, ExportResult)
        assert result.success is False

    def test_choose_format_web(self):
        from aifont.agents.export_agent import ExportAgent

        agent = ExportAgent()
        assert agent._choose_format("export for web") == "woff2"

    def test_choose_format_desktop(self):
        from aifont.agents.export_agent import ExportAgent

        agent = ExportAgent()
        assert agent._choose_format("export for desktop windows") == "ttf"

    def test_choose_format_default_otf(self):
        from aifont.agents.export_agent import ExportAgent

        agent = ExportAgent()
        assert agent._choose_format("export something") == "otf"

    def test_export_target_enum(self):
        from aifont.agents.export_agent import ExportTarget

        assert ExportTarget.WEB in ExportTarget
        assert ExportTarget.PRINT in ExportTarget
        assert ExportTarget.APP in ExportTarget
        assert ExportTarget.VARIABLE in ExportTarget
        assert ExportTarget.FULL in ExportTarget

    def test_export_result_all_passed_empty(self):
        from aifont.agents.export_agent import ExportResult

        r = ExportResult(success=True)
        assert r.all_passed is True

    def test_format_validation_valid(self):
        from pathlib import Path

        from aifont.agents.export_agent import FormatValidation

        fv = FormatValidation(format="woff2", path=Path("/tmp/f.woff2"), file_size_bytes=100, passed=True)
        assert fv.passed is True
        assert fv.format == "woff2"


# ===========================================================================
# StyleAgent - extended
# ===========================================================================


class TestStyleAgentExtended:
    def test_analyze_style(self):
        from aifont.agents.style_agent import StyleAgent
        from aifont.core.analyzer import StyleProfile

        font = _make_font_wrapper()
        agent = StyleAgent()
        with patch("aifont.agents.style_agent.analyze_style", return_value=StyleProfile()):
            result = agent.analyze_style(font)
        assert isinstance(result, StyleProfile)

    def test_apply_stroke_no_glyphs(self):
        from aifont.agents.style_agent import StyleAgent, StyleTransferResult
        from aifont.core.analyzer import StyleProfile

        font = _make_font_wrapper()
        agent = StyleAgent()
        with patch("aifont.agents.style_agent.analyze_style", return_value=StyleProfile()):
            result = agent.apply_stroke(font, stroke_width=30.0)
        assert isinstance(result, StyleTransferResult)
        assert "ApplyStroke" in result.changes_applied[0]

    def test_apply_slant_no_glyphs(self):
        from aifont.agents.style_agent import StyleAgent, StyleTransferResult
        from aifont.core.analyzer import StyleProfile

        font = _make_font_wrapper()
        agent = StyleAgent()
        with patch("aifont.agents.style_agent.analyze_style", return_value=StyleProfile()):
            result = agent.apply_slant(font, angle=12.0)
        assert isinstance(result, StyleTransferResult)
        assert "ApplySlant" in result.changes_applied[0]

    def test_transform_glyph_no_glyphs(self):
        from aifont.agents.style_agent import StyleAgent, StyleTransferResult
        from aifont.core.analyzer import StyleProfile

        font = _make_font_wrapper()
        agent = StyleAgent()
        with patch("aifont.agents.style_agent.analyze_style", return_value=StyleProfile()):
            result = agent.transform_glyph(font, (1, 0, 0, 1, 0, 0))
        assert isinstance(result, StyleTransferResult)

    def test_interpolate_style_no_delta(self):
        from aifont.agents.style_agent import StyleAgent, StyleTransferResult
        from aifont.core.analyzer import StyleProfile

        target = _make_font_wrapper("Target")
        reference = _make_font_wrapper("Reference")
        agent = StyleAgent()
        profile = StyleProfile(stroke_width=80.0, italic_angle=0.0)
        with patch("aifont.agents.style_agent.analyze_style", return_value=profile):
            result = agent.interpolate_style(target, reference, factor=0.5)
        assert isinstance(result, StyleTransferResult)

    def test_run_light_intent(self):
        from aifont.agents.style_agent import StyleAgent, StyleTransferResult
        from aifont.core.analyzer import StyleProfile

        font = _make_font_wrapper()
        agent = StyleAgent()
        with (
            patch.object(agent, "apply_stroke", return_value=StyleTransferResult(font=font)),
            patch("aifont.agents.style_agent.analyze_style", return_value=StyleProfile()),
        ):
            result = agent.run("make it thinner", font=font)
        assert isinstance(result, StyleTransferResult)

    def test_run_vintage_intent(self):
        from aifont.agents.style_agent import StyleAgent, StyleTransferResult
        from aifont.core.analyzer import StyleProfile

        font = _make_font_wrapper()
        agent = StyleAgent()
        with patch("aifont.agents.style_agent.analyze_style", return_value=StyleProfile()):
            result = agent.run("give it a vintage feel", font=font)
        assert isinstance(result, StyleTransferResult)

    def test_run_with_reference_font(self):
        from aifont.agents.style_agent import StyleAgent, StyleTransferResult
        from aifont.core.analyzer import StyleProfile

        font = _make_font_wrapper("Target")
        ref = _make_font_wrapper("Reference")
        agent = StyleAgent()
        profile = StyleProfile()
        with patch("aifont.agents.style_agent.analyze_style", return_value=profile):
            result = agent.run("something else", font=font, reference_font=ref)
        assert isinstance(result, StyleTransferResult)

    def test_compute_scale(self):
        from aifont.agents.style_agent import StyleAgent

        font1 = _make_font_wrapper()
        font2 = _make_font_wrapper()
        agent = StyleAgent()
        scale = agent._compute_scale(font1, font2)
        assert scale == 1.0


# ===========================================================================
# QAAgent - extended
# ===========================================================================


class TestQAAgentExtended:
    def test_fix_overlaps_with_glyphs(self):
        from aifont.agents.qa_agent import QAAgent
        from aifont.core.contour import remove_overlap

        font = _make_font_wrapper()
        agent = QAAgent(font=font)
        with patch("aifont.agents.qa_agent.remove_overlap"):
            result = agent.fix_overlaps(["A", "B"])
        # Should process glyphs (may skip on exception)
        assert isinstance(result, list)

    def test_simplify_contours_with_glyphs(self):
        from aifont.agents.qa_agent import QAAgent

        font = _make_font_wrapper()
        agent = QAAgent(font=font)
        with patch("aifont.agents.qa_agent.simplify"):
            result = agent.simplify_contours(["A", "B"])
        assert isinstance(result, list)

    def test_correct_directions_with_glyphs(self):
        from aifont.agents.qa_agent import QAAgent

        font = _make_font_wrapper()
        agent = QAAgent(font=font)
        with patch("aifont.agents.qa_agent.correct_directions"):
            result = agent.correct_directions(["A", "B"])
        assert isinstance(result, list)

    def test_generate_qa_report_from_provided_report(self):
        from aifont.agents.qa_agent import QAAgent, QAReport
        from aifont.core.analyzer import FontReport, GlyphIssue

        font = _make_font_wrapper()
        agent = QAAgent(font=font)
        fr = FontReport(
            issues=[GlyphIssue(glyph_name="A", code="open_contour", issue_type="open_contour")]
        )
        report = agent.generate_qa_report(fr)
        assert isinstance(report, QAReport)

    def test_qa_report_to_dict(self):
        from aifont.agents.qa_agent import QAReport

        r = QAReport(score=85.0)
        d = r.to_dict()
        assert "score" in d

    def test_qa_report_str(self):
        from aifont.agents.qa_agent import QAReport

        r = QAReport(score=85.0)
        s = str(r)
        assert "85" in s


# ===========================================================================
# ExportAgent - extended (beyond just no-font cases)
# ===========================================================================


class TestExportAgentMoreCoverage:
    def test_export_unsupported_format_raises(self):
        from aifont.agents.export_agent import ExportAgent

        agent = ExportAgent()
        font = _make_font_wrapper()
        try:
            agent._export(font, "/tmp/out.xyz", "xyz")
            assert False, "Expected ValueError"
        except ValueError:
            pass

    def test_export_validate_file_missing(self):
        from aifont.agents.export_agent import ExportAgent
        from pathlib import Path

        agent = ExportAgent()
        result = agent._validate_file("woff2", Path("/tmp/nonexistent.woff2"))
        assert result.passed is False

    def test_choose_formats_print(self):
        from aifont.agents.export_agent import ExportAgent, ExportTarget

        agent = ExportAgent()
        formats = agent._choose_formats(ExportTarget.PRINT, None)
        assert "otf" in formats

    def test_build_css_snippet(self):
        from pathlib import Path

        from aifont.agents.export_agent import ExportAgent

        agent = ExportAgent()
        css = agent._build_css("TestFont", {"woff2": Path("/out/font.woff2")})
        assert "TestFont" in css
        assert "@font-face" in css or "woff2" in css


# ===========================================================================
# ExportAgent — more coverage paths
# ===========================================================================


class TestExportAgentMorePaths:
    def test_run_with_output_path(self):
        import tempfile, os
        from aifont.agents.export_agent import ExportAgent, ExportResult

        agent = ExportAgent()
        font = _make_font_wrapper()
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "font.otf")
            with patch.object(agent, "_export"):
                result = agent.run("export as otf", font=font, output_path=out)
        assert isinstance(result, ExportResult)
        assert result.success is True

    def test_run_with_output_path_no_font(self):
        from aifont.agents.export_agent import ExportAgent, ExportResult

        agent = ExportAgent()
        result = agent.run("export", font=None, output_path="/tmp/font.otf")
        assert result.success is False

    def test_write_specimen(self):
        import tempfile
        from pathlib import Path
        from aifont.agents.export_agent import ExportAgent

        agent = ExportAgent()
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            files = {"woff2": out / "font.woff2", "ttf": out / "font.ttf"}
            for f in files.values():
                f.write_bytes(b"fake data")
            result = agent._write_specimen(out, "TestFont", files)
            assert result.exists()
            content = result.read_text()
            assert "TestFont" in content

    def test_build_css_relative(self):
        from pathlib import Path
        from aifont.agents.export_agent import ExportAgent

        agent = ExportAgent()
        css = agent._build_css("TestFont", {"woff2": Path("/out/font.woff2")}, relative=True)
        assert "@font-face" in css or "font-family" in css

    def test_validate_file_existing_small(self):
        import tempfile
        from pathlib import Path
        from aifont.agents.export_agent import ExportAgent

        agent = ExportAgent()
        with tempfile.NamedTemporaryFile(suffix=".woff2") as f:
            p = Path(f.name)
            p.write_bytes(b"")  # Empty file
            result = agent._validate_file("woff2", p)
            assert result.passed is False
            assert any("empty" in issue.lower() for issue in result.issues)

    def test_choose_format_default_otf(self):
        from aifont.agents.export_agent import ExportAgent

        agent = ExportAgent()
        fmt = agent._choose_format("export the font")
        assert fmt == "otf"

    def test_export_format_path_woff2(self):
        import tempfile
        from pathlib import Path
        from aifont.agents.export_agent import ExportAgent

        agent = ExportAgent()
        font = _make_font_wrapper()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("aifont.agents.export_agent.export_woff2", return_value=Path(tmpdir) / "x.woff2"):
                result = agent._export_format(font, "woff2", Path(tmpdir), "TestFont", [])
            assert result is not None

    def test_run_full_pipeline_with_mock_exports(self):
        import tempfile
        from pathlib import Path
        from aifont.agents.export_agent import ExportAgent, ExportResult

        agent = ExportAgent(generate_specimen=True, generate_css=True, validate=False)
        font = _make_font_wrapper()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "font.woff2"
            out_path.write_bytes(b"wOF2fake")
            with patch.object(
                agent,
                "_export_format",
                return_value=out_path,
            ):
                result = agent.run(
                    font,
                    output_dir=tmpdir,
                    target="web",
                    family_name="TestFont",
                )
        assert isinstance(result, ExportResult)


# ===========================================================================
# QAAgent — more coverage
# ===========================================================================


class TestQAAgentMorePaths:
    def test_run_full_qa_pipeline(self):
        from aifont.agents.qa_agent import QAAgent, QAReport
        from aifont.core.analyzer import FontReport

        font = _make_font_wrapper()
        agent = QAAgent(font=font)
        with patch("aifont.agents.qa_agent.analyze", return_value=FontReport()):
            result = agent.run(font=font)
        assert isinstance(result, QAReport)

    def test_run_without_font(self):
        from aifont.agents.qa_agent import QAAgent, QAReport
        agent = QAAgent()
        result = agent.run()
        assert isinstance(result, QAReport)

    def test_qa_agent_run_applies_fixes(self):
        from aifont.agents.qa_agent import QAAgent, QAReport
        from aifont.core.analyzer import FontReport, GlyphIssue

        font = _make_font_wrapper()
        report = FontReport(
            issues=[
                GlyphIssue(glyph_name="A", issue_type="open_contour", severity="warning")
            ]
        )
        agent = QAAgent(font=font, auto_fix=True)
        with patch("aifont.agents.qa_agent.analyze", return_value=report):
            result = agent.run(font=font)
        assert isinstance(result, QAReport)

    def test_check_result_init(self):
        from aifont.agents.qa_agent import CheckResult
        from aifont.core.analyzer import GlyphIssue
        cr = CheckResult(name="test", passed=True)
        assert cr.passed is True
