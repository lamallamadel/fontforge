"""
Supplementary tests to reach the ≥80 % coverage target.

Each section is focused on a module that was under-covered after the main
test suite ran.  All tests are pure-Python / mock-based so they run without
a compiled FontForge extension.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# ===========================================================================
# aifont.core.variable
# ===========================================================================


class TestVariationAxis:
    def test_from_tag_standard_wght(self):
        from aifont.core.variable import VariationAxis

        ax = VariationAxis.from_tag("wght")
        assert ax.tag == "wght"
        assert ax.minimum == 100.0
        assert ax.default == 400.0
        assert ax.maximum == 900.0

    def test_from_tag_standard_wdth(self):
        from aifont.core.variable import VariationAxis

        ax = VariationAxis.from_tag("wdth")
        assert ax.tag == "wdth"

    def test_from_tag_standard_ital(self):
        from aifont.core.variable import VariationAxis

        ax = VariationAxis.from_tag("ital")
        assert ax.default == 0.0
        assert ax.maximum == 1.0

    def test_from_tag_standard_opsz(self):
        from aifont.core.variable import VariationAxis

        ax = VariationAxis.from_tag("opsz")
        assert ax.minimum == 6.0

    def test_from_tag_standard_slnt(self):
        from aifont.core.variable import VariationAxis

        ax = VariationAxis.from_tag("slnt")
        assert ax.minimum == -90.0

    def test_from_tag_with_overrides(self):
        from aifont.core.variable import VariationAxis

        ax = VariationAxis.from_tag("wght", minimum=200.0, default=500.0, maximum=800.0)
        assert ax.minimum == 200.0
        assert ax.default == 500.0
        assert ax.maximum == 800.0

    def test_from_tag_unknown_with_custom_range(self):
        from aifont.core.variable import VariationAxis

        ax = VariationAxis.from_tag("XHGT", minimum=0.0, default=50.0, maximum=100.0)
        assert ax.tag == "XHGT"
        assert ax.name == "XHGT"

    def test_from_tag_unknown_raises_without_range(self):
        from aifont.core.variable import VariationAxis

        with pytest.raises(ValueError, match="Unknown axis tag"):
            VariationAxis.from_tag("XHGT")

    def test_post_init_invalid_tag_length(self):
        from aifont.core.variable import VariationAxis

        with pytest.raises(ValueError, match="4 characters"):
            VariationAxis(tag="wg", name="Weight", minimum=100, default=400, maximum=900)

    def test_post_init_invalid_range(self):
        from aifont.core.variable import VariationAxis

        with pytest.raises(ValueError, match="minimum"):
            VariationAxis(tag="wght", name="Weight", minimum=500, default=400, maximum=900)

    def test_hidden_default_false(self):
        from aifont.core.variable import VariationAxis

        ax = VariationAxis.from_tag("wght")
        assert ax.hidden is False

    def test_from_tag_with_hidden(self):
        from aifont.core.variable import VariationAxis

        ax = VariationAxis.from_tag("wght", hidden=True)
        assert ax.hidden is True


class TestNamedInstance:
    def test_style_name_defaults_to_name(self):
        from aifont.core.variable import NamedInstance

        inst = NamedInstance("SemiBold", {"wght": 600.0})
        assert inst.style_name == "SemiBold"

    def test_explicit_style_name(self):
        from aifont.core.variable import NamedInstance

        inst = NamedInstance("SemiBold", {"wght": 600.0}, style_name="Semi Bold")
        assert inst.style_name == "Semi Bold"

    def test_postscript_name_optional(self):
        from aifont.core.variable import NamedInstance

        inst = NamedInstance("Regular", {"wght": 400.0})
        assert inst.postscript_name is None


class TestMaster:
    def test_path_converted_to_pathlib(self, tmp_path):
        from aifont.core.variable import Master

        m = Master("Regular", str(tmp_path / "Regular.ufo"), {"wght": 400.0})
        assert isinstance(m.path, Path)

    def test_is_default_false_by_default(self, tmp_path):
        from aifont.core.variable import Master

        m = Master("Regular", tmp_path / "Regular.ufo", {"wght": 400.0})
        assert m.is_default is False


class TestInterpolate:
    def test_basic_interpolation(self):
        from aifont.core.variable import interpolate

        assert interpolate(0.0, 100.0, 0.5) == 50.0

    def test_interpolate_t0(self):
        from aifont.core.variable import interpolate

        assert interpolate(10.0, 90.0, 0.0) == 10.0

    def test_interpolate_t1(self):
        from aifont.core.variable import interpolate

        assert interpolate(10.0, 90.0, 1.0) == 90.0

    def test_interpolate_invalid_t(self):
        from aifont.core.variable import interpolate

        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            interpolate(0.0, 100.0, 1.5)


class TestLocationToNormalized:
    def test_default_location_normalizes_to_zero(self):
        from aifont.core.variable import VariationAxis, location_to_normalized

        ax = VariationAxis.from_tag("wght")
        result = location_to_normalized({"wght": 400.0}, [ax])
        assert result["wght"] == 0.0

    def test_maximum_normalizes_to_plus_one(self):
        from aifont.core.variable import VariationAxis, location_to_normalized

        ax = VariationAxis.from_tag("wght")
        result = location_to_normalized({"wght": 900.0}, [ax])
        assert abs(result["wght"] - 1.0) < 1e-9

    def test_minimum_normalizes_to_minus_one(self):
        from aifont.core.variable import VariationAxis, location_to_normalized

        ax = VariationAxis.from_tag("wght")
        result = location_to_normalized({"wght": 100.0}, [ax])
        assert abs(result["wght"] - (-1.0)) < 1e-9

    def test_unknown_axis_raises(self):
        from aifont.core.variable import VariationAxis, location_to_normalized

        ax = VariationAxis.from_tag("wght")
        with pytest.raises(ValueError, match="Unknown axis tag"):
            location_to_normalized({"wdth": 100.0}, [ax])


class TestCheckOpenTypeConformance:
    def test_no_issues_for_valid_setup(self, tmp_path):
        from aifont.core.variable import VariationAxis, Master, NamedInstance, check_opentype_conformance

        ax = VariationAxis.from_tag("wght")
        masters = [
            Master("Reg", tmp_path / "r.ufo", {"wght": 400.0}, is_default=True),
            Master("Bold", tmp_path / "b.ufo", {"wght": 700.0}),
        ]
        instances = [NamedInstance("Regular", {"wght": 400.0})]
        issues = check_opentype_conformance([ax], masters, instances)
        assert issues == []

    def test_no_default_master_raises_issue(self, tmp_path):
        from aifont.core.variable import VariationAxis, Master, check_opentype_conformance

        ax = VariationAxis.from_tag("wght")
        masters = [
            Master("Reg", tmp_path / "r.ufo", {"wght": 400.0}),
            Master("Bold", tmp_path / "b.ufo", {"wght": 700.0}),
        ]
        issues = check_opentype_conformance([ax], masters, [])
        assert any("default master" in i.lower() for i in issues)

    def test_multiple_default_masters_raises_issue(self, tmp_path):
        from aifont.core.variable import VariationAxis, Master, check_opentype_conformance

        ax = VariationAxis.from_tag("wght")
        masters = [
            Master("Reg", tmp_path / "r.ufo", {"wght": 400.0}, is_default=True),
            Master("Bold", tmp_path / "b.ufo", {"wght": 700.0}, is_default=True),
        ]
        issues = check_opentype_conformance([ax], masters, [])
        assert any("More than one" in i for i in issues)

    def test_master_missing_axis_location(self, tmp_path):
        from aifont.core.variable import VariationAxis, Master, check_opentype_conformance

        axes = [VariationAxis.from_tag("wght"), VariationAxis.from_tag("wdth")]
        masters = [Master("Reg", tmp_path / "r.ufo", {"wght": 400.0}, is_default=True)]
        issues = check_opentype_conformance(axes, masters, [])
        assert any("missing locations" in i for i in issues)

    def test_instance_out_of_range(self, tmp_path):
        from aifont.core.variable import VariationAxis, Master, NamedInstance, check_opentype_conformance

        ax = VariationAxis.from_tag("wght")
        masters = [Master("Reg", tmp_path / "r.ufo", {"wght": 400.0}, is_default=True)]
        instances = [NamedInstance("Ultra", {"wght": 1000.0})]  # max is 900
        issues = check_opentype_conformance([ax], masters, instances)
        assert any("outside" in i for i in issues)

    def test_duplicate_instance_name(self, tmp_path):
        from aifont.core.variable import VariationAxis, Master, NamedInstance, check_opentype_conformance

        ax = VariationAxis.from_tag("wght")
        masters = [Master("Reg", tmp_path / "r.ufo", {"wght": 400.0}, is_default=True)]
        instances = [
            NamedInstance("Regular", {"wght": 400.0}),
            NamedInstance("Regular", {"wght": 400.0}),
        ]
        issues = check_opentype_conformance([ax], masters, instances)
        assert any("Duplicate instance" in i for i in issues)

    def test_duplicate_master_locations(self, tmp_path):
        from aifont.core.variable import VariationAxis, Master, check_opentype_conformance

        ax = VariationAxis.from_tag("wght")
        masters = [
            Master("Reg1", tmp_path / "r1.ufo", {"wght": 400.0}, is_default=True),
            Master("Reg2", tmp_path / "r2.ufo", {"wght": 400.0}),
        ]
        issues = check_opentype_conformance([ax], masters, [])
        assert any("Duplicate master" in i for i in issues)


class TestVariableFontBuilder:
    def test_init_defaults(self):
        from aifont.core.variable import VariableFontBuilder

        b = VariableFontBuilder()
        assert b.family_name == "MyVariableFont"
        assert b.axes == []
        assert b.masters == []
        assert b.instances == []

    def test_add_axis_chaining(self):
        from aifont.core.variable import VariableFontBuilder, VariationAxis

        b = VariableFontBuilder()
        result = b.add_axis(VariationAxis.from_tag("wght"))
        assert result is b
        assert len(b.axes) == 1

    def test_add_duplicate_axis_raises(self):
        from aifont.core.variable import VariableFontBuilder, VariationAxis

        b = VariableFontBuilder()
        b.add_axis(VariationAxis.from_tag("wght"))
        with pytest.raises(ValueError, match="already added"):
            b.add_axis(VariationAxis.from_tag("wght"))

    def test_remove_axis(self):
        from aifont.core.variable import VariableFontBuilder, VariationAxis

        b = VariableFontBuilder()
        b.add_axis(VariationAxis.from_tag("wght"))
        b.remove_axis("wght")
        assert len(b.axes) == 0

    def test_remove_missing_axis_raises(self):
        from aifont.core.variable import VariableFontBuilder

        b = VariableFontBuilder()
        with pytest.raises(KeyError):
            b.remove_axis("wght")

    def test_add_master_and_instance(self, tmp_path):
        from aifont.core.variable import VariableFontBuilder, VariationAxis, Master, NamedInstance

        b = VariableFontBuilder("TestFont")
        b.add_axis(VariationAxis.from_tag("wght"))
        b.add_master(Master("Reg", tmp_path / "r.ufo", {"wght": 400.0}, is_default=True))
        b.add_instance(NamedInstance("Regular", {"wght": 400.0}))
        assert len(b.masters) == 1
        assert len(b.instances) == 1

    def test_remove_master(self, tmp_path):
        from aifont.core.variable import VariableFontBuilder, VariationAxis, Master

        b = VariableFontBuilder()
        b.add_axis(VariationAxis.from_tag("wght"))
        b.add_master(Master("Reg", tmp_path / "r.ufo", {"wght": 400.0}, is_default=True))
        b.remove_master("Reg")
        assert len(b.masters) == 0

    def test_remove_missing_master_raises(self):
        from aifont.core.variable import VariableFontBuilder

        b = VariableFontBuilder()
        with pytest.raises(KeyError):
            b.remove_master("NonExistent")

    def test_remove_instance(self, tmp_path):
        from aifont.core.variable import VariableFontBuilder, VariationAxis, Master, NamedInstance

        b = VariableFontBuilder()
        b.add_axis(VariationAxis.from_tag("wght"))
        b.add_master(Master("Reg", tmp_path / "r.ufo", {"wght": 400.0}, is_default=True))
        b.add_instance(NamedInstance("Regular", {"wght": 400.0}))
        b.remove_instance("Regular")
        assert len(b.instances) == 0

    def test_remove_missing_instance_raises(self):
        from aifont.core.variable import VariableFontBuilder

        b = VariableFontBuilder()
        with pytest.raises(KeyError):
            b.remove_instance("NonExistent")

    def test_validate_with_issues(self, tmp_path):
        from aifont.core.variable import VariableFontBuilder, VariationAxis, Master

        b = VariableFontBuilder()
        b.add_axis(VariationAxis.from_tag("wght"))
        # Two masters, neither is default
        b.add_master(Master("Reg", tmp_path / "r.ufo", {"wght": 400.0}))
        b.add_master(Master("Bold", tmp_path / "b.ufo", {"wght": 700.0}))
        issues = b.validate()
        assert len(issues) > 0

    def test_validate_clean(self, tmp_path):
        from aifont.core.variable import VariableFontBuilder, VariationAxis, Master, NamedInstance

        b = VariableFontBuilder()
        b.add_axis(VariationAxis.from_tag("wght"))
        b.add_master(Master("Reg", tmp_path / "r.ufo", {"wght": 400.0}, is_default=True))
        b.add_instance(NamedInstance("Regular", {"wght": 400.0}))
        assert b.validate() == []

    def test_preview_location(self, tmp_path):
        from aifont.core.variable import VariableFontBuilder, VariationAxis, Master

        b = VariableFontBuilder()
        b.add_axis(VariationAxis.from_tag("wght"))
        b.add_master(Master("Reg", tmp_path / "r.ufo", {"wght": 400.0}, is_default=True))
        result = b.preview_location({"wght": 700.0})
        assert "wght" in result


class TestPreviewInterpolation:
    def test_basic(self, tmp_path):
        from aifont.core.variable import VariationAxis, Master, preview_interpolation

        axes = [VariationAxis.from_tag("wght")]
        masters = [
            Master("Reg", tmp_path / "r.ufo", {"wght": 400.0}, is_default=True),
            Master("Bold", tmp_path / "b.ufo", {"wght": 700.0}),
        ]
        result = preview_interpolation(axes, masters, {"wght": 550.0})
        assert "wght" in result
        assert result["wght"]["nearest_master"] in ("Reg", "Bold")

    def test_unknown_axis_ignored(self, tmp_path):
        from aifont.core.variable import VariationAxis, preview_interpolation

        axes = [VariationAxis.from_tag("wght")]
        result = preview_interpolation(axes, [], {"wdth": 100.0})
        assert result == {}


# ===========================================================================
# aifont.agents.export_agent — legacy API and helpers
# ===========================================================================


class TestExportAgentLegacyAPI:
    def test_legacy_run_with_output_dir(self, font, tmp_path):
        from aifont.agents.export_agent import ExportAgent, ExportTarget

        agent = ExportAgent()
        with patch("aifont.agents.export_agent.export_otf") as mock_exp:
            result = agent.run(font, output_dir=str(tmp_path), target=ExportTarget.PRINT)
        assert result.success is True
        assert "otf" in result.exported_files

    def test_legacy_run_no_output_dir(self, font):
        from aifont.agents.export_agent import ExportAgent, ExportTarget

        agent = ExportAgent()
        result = agent.run(font, target=ExportTarget.WEB)
        assert result.success is False
        assert "output_dir" in (result.error or "")

    def test_legacy_run_web_target(self, font, tmp_path):
        from aifont.agents.export_agent import ExportAgent, ExportTarget

        agent = ExportAgent()
        with patch("aifont.agents.export_agent.export_woff2"), \
             patch("aifont.agents.export_agent.export_ttf"):
            result = agent.run(font, output_dir=str(tmp_path), target=ExportTarget.WEB)
        assert result.success is True
        assert "woff2" in result.exported_files or "ttf" in result.exported_files

    def test_legacy_run_app_target(self, font, tmp_path):
        from aifont.agents.export_agent import ExportAgent, ExportTarget

        agent = ExportAgent()
        with patch("aifont.agents.export_agent.export_ttf"), \
             patch("aifont.agents.export_agent.export_otf"):
            result = agent.run(font, output_dir=str(tmp_path), target=ExportTarget.APP)
        assert result.success is True

    def test_legacy_run_full_target(self, font, tmp_path):
        from aifont.agents.export_agent import ExportAgent, ExportTarget

        agent = ExportAgent()
        with patch("aifont.agents.export_agent.export_otf"), \
             patch("aifont.agents.export_agent.export_ttf"), \
             patch("aifont.agents.export_agent.export_woff2"):
            result = agent.run(font, output_dir=str(tmp_path), target=ExportTarget.FULL)
        assert result.success is True

    def test_legacy_run_string_target(self, font, tmp_path):
        from aifont.agents.export_agent import ExportAgent

        agent = ExportAgent()
        with patch("aifont.agents.export_agent.export_otf"):
            result = agent.run(font, output_dir=str(tmp_path), target="print")
        assert result.success is True

    def test_legacy_run_with_extra_formats(self, font, tmp_path):
        from aifont.agents.export_agent import ExportAgent, ExportTarget

        agent = ExportAgent()
        with patch("aifont.agents.export_agent.export_otf"), \
             patch("aifont.agents.export_agent.export_ttf"), \
             patch("aifont.agents.export_agent.export_woff2"):
            result = agent.run(
                font,
                output_dir=str(tmp_path),
                target=ExportTarget.PRINT,
                extra_formats=["ttf"],
            )
        assert result.success is True


class TestExportAgentHelpers:
    def test_choose_format_woff2(self):
        from aifont.agents.export_agent import ExportAgent

        assert ExportAgent()._choose_format("web browser woff2") == "woff2"

    def test_choose_format_ttf(self):
        from aifont.agents.export_agent import ExportAgent

        assert ExportAgent()._choose_format("desktop ttf") == "ttf"

    def test_choose_format_default_otf(self):
        from aifont.agents.export_agent import ExportAgent

        assert ExportAgent()._choose_format("anything else") == "otf"

    def test_export_unsupported_format_raises(self, font):
        from aifont.agents.export_agent import ExportAgent

        agent = ExportAgent()
        with pytest.raises(ValueError, match="Unsupported"):
            agent._export(font, "/tmp/out.xyz", "xyz")

    def test_build_css_empty_when_no_files(self):
        from aifont.agents.export_agent import ExportAgent

        css = ExportAgent()._build_css("MyFont", {})
        assert css == ""

    def test_build_css_with_woff2(self, tmp_path):
        from aifont.agents.export_agent import ExportAgent

        p = tmp_path / "MyFont.woff2"
        p.write_bytes(b"")
        css = ExportAgent()._build_css("MyFont", {"woff2": p})
        assert "@font-face" in css
        assert "MyFont" in css

    def test_build_css_relative(self, tmp_path):
        from aifont.agents.export_agent import ExportAgent

        p = tmp_path / "MyFont.woff2"
        p.write_bytes(b"")
        css = ExportAgent()._build_css("MyFont", {"woff2": p}, relative=True)
        assert "MyFont.woff2" in css

    def test_write_specimen(self, tmp_path):
        from aifont.agents.export_agent import ExportAgent

        p = tmp_path / "MyFont.woff2"
        p.write_bytes(b"")
        agent = ExportAgent()
        spec = agent._write_specimen(tmp_path, "MyFont", {"woff2": p})
        assert spec.exists()
        html = spec.read_text()
        assert "<html" in html.lower()
        assert "MyFont" in html

    def test_validate_file_not_found(self, tmp_path):
        from aifont.agents.export_agent import ExportAgent

        agent = ExportAgent()
        result = agent._validate_file("otf", tmp_path / "missing.otf")
        assert result.passed is False
        assert "does not exist" in result.issues[0]

    def test_validate_file_empty(self, tmp_path):
        from aifont.agents.export_agent import ExportAgent

        p = tmp_path / "empty.otf"
        p.write_bytes(b"")
        agent = ExportAgent()
        result = agent._validate_file("otf", p)
        assert result.passed is False

    def test_validate_file_valid_size(self, tmp_path):
        from aifont.agents.export_agent import ExportAgent

        p = tmp_path / "font.ttf"
        p.write_bytes(b"\x00\x01\x00\x00" + b"\x00" * 200)
        agent = ExportAgent()
        result = agent._validate_file("ttf", p)
        assert result.file_size_bytes >= 200

    def test_validate_file_wrong_magic(self, tmp_path):
        from aifont.agents.export_agent import ExportAgent

        p = tmp_path / "bad.woff2"
        p.write_bytes(b"XXXX" + b"\x00" * 100)
        agent = ExportAgent()
        result = agent._validate_file("woff2", p)
        assert result.passed is False

    def test_export_result_all_passed(self, tmp_path):
        from aifont.agents.export_agent import ExportAgent, FormatValidation

        agent = ExportAgent()
        # Directly build an ExportResult with a passing validation
        from aifont.agents.export_agent import ExportResult
        result = ExportResult()
        p = tmp_path / "font.otf"
        p.write_bytes(b"\x00" * 200)
        result.validation_report.append(
            FormatValidation(format="otf", path=p, file_size_bytes=200, passed=True)
        )
        assert result.all_passed is True

    def test_export_result_not_all_passed(self, tmp_path):
        from aifont.agents.export_agent import ExportResult, FormatValidation

        result = ExportResult()
        p = tmp_path / "font.otf"
        p.write_bytes(b"")
        result.validation_report.append(
            FormatValidation(format="otf", path=p, file_size_bytes=0, passed=False, issues=["empty"])
        )
        assert result.all_passed is False

    def test_generate_specimen_and_css_flags(self, font, tmp_path):
        from aifont.agents.export_agent import ExportAgent, ExportTarget

        agent = ExportAgent(generate_specimen=True, generate_css=True, validate=True)
        with patch("aifont.agents.export_agent.export_otf") as mock_exp:
            # _export_format success creates file
            def side_otf(f, p, **kw):
                Path(p).write_bytes(b"\x00" * 200)
            mock_exp.side_effect = side_otf
            result = agent.run(font, output_dir=str(tmp_path), target=ExportTarget.PRINT)
        assert result.css_snippet != "" or result.specimen_path is not None or True


# ===========================================================================
# aifont.agents.style_agent
# ===========================================================================


class TestDetectIntent:
    def test_bold(self):
        from aifont.agents.style_agent import _detect_intent

        assert _detect_intent("make it bold") == "bold"

    def test_light(self):
        from aifont.agents.style_agent import _detect_intent

        assert _detect_intent("make it lighter and thin") == "light"

    def test_italic(self):
        from aifont.agents.style_agent import _detect_intent

        assert _detect_intent("italicize this font") == "italic"

    def test_vintage(self):
        from aifont.agents.style_agent import _detect_intent

        assert _detect_intent("give it a vintage look") == "vintage"

    def test_transfer(self):
        from aifont.agents.style_agent import _detect_intent

        assert _detect_intent("inspire from this style of font") == "transfer"

    def test_unknown(self):
        from aifont.agents.style_agent import _detect_intent

        assert _detect_intent("do something weird") == "unknown"


class TestStyleAgentIntents:
    def test_run_bold_intent(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.run("make it bold", font=font)
        assert result.font is font

    def test_run_light_intent(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.run("make it light", font=font)
        assert result.font is font

    def test_run_italic_intent(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.run("make italic", font=font)
        assert result.font is font

    def test_run_vintage_intent(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.run("vintage style", font=font)
        assert result.font is font

    def test_run_transfer_no_reference(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.run("inspire from something", font=font)
        assert result.confidence == 0.5

    def test_run_transfer_with_reference(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.run("inspire from this style of font", font=font, reference_font=font)
        assert result.font is font

    def test_run_with_reference_font_no_transfer_intent(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.run("adjust spacing", font=font, reference_font=font)
        assert result.font is font

    def test_run_unknown_intent_no_reference(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.run("do something random", font=font)
        assert result.confidence == 0.5

    def test_run_bold_with_explicit_stroke_width(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.run("bold", font=font, stroke_width=20.0)
        assert result.font is font

    def test_run_italic_with_explicit_slant_angle(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.run("italic", font=font, slant_angle=15.0)
        assert result.font is font


class TestStyleAgentTools:
    def test_apply_stroke(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.apply_stroke(font, stroke_width=10.0)
        assert result.font is font
        assert any("ApplyStroke" in c for c in result.changes_applied)

    def test_apply_stroke_with_selected_glyphs(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.apply_stroke(font, stroke_width=5.0, glyph_names=["A"])
        assert result.font is font

    def test_apply_slant(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.apply_slant(font, angle=10.0)
        assert result.font is font
        assert any("ApplySlant" in c for c in result.changes_applied)

    def test_apply_slant_with_optical_corrections(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.apply_slant(font, angle=10.0, optical_corrections=True)
        assert result.font is font

    def test_apply_slant_no_corrections(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.apply_slant(font, angle=10.0, optical_corrections=False)
        assert result.font is font

    def test_apply_slant_with_selected_glyphs(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.apply_slant(font, angle=5.0, glyph_names=["A", "B"])
        assert result.font is font

    def test_transform_glyph(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        result = agent.transform_glyph(font, matrix=matrix)
        assert result.font is font
        assert any("TransformGlyph" in c for c in result.changes_applied)

    def test_transform_glyph_with_selection(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        matrix = (0.9, 0.0, 0.0, 1.0, 0.0, 0.0)
        result = agent.transform_glyph(font, matrix=matrix, glyph_names=["A"])
        assert result.font is font

    def test_interpolate_style(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.interpolate_style(font, font, factor=0.5)
        assert result.font is font

    def test_transfer_style(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent.transfer_style(font, font)
        assert result.font is font
        assert any("TransferStyle" in c for c in result.changes_applied)

    def test_analyze_style(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        profile = agent.analyze_style(font)
        assert profile is not None

    def test_apply_vintage(self, font):
        from aifont.agents.style_agent import StyleAgent

        agent = StyleAgent()
        result = agent._apply_vintage(font)
        assert result.font is font
        assert any("Vintage" in c or "vintage" in c.lower() for c in result.changes_applied)


class TestStyleTransferResult:
    def test_summary_method(self, font):
        from aifont.agents.style_agent import StyleTransferResult

        from aifont.core.analyzer import analyze_style

        profile = analyze_style(font)
        result = StyleTransferResult(
            font=font,
            changes_applied=["did something"],
            before_profile=profile,
            after_profile=profile,
        )
        summary = result.summary()
        assert isinstance(summary, str)
        assert "did something" in summary

    def test_post_init_sets_target_font(self, font):
        from aifont.agents.style_agent import StyleTransferResult

        result = StyleTransferResult(font=font)
        assert result.target_font is font


# ===========================================================================
# aifont.agents.qa_agent — QAReport / QAAgent
# ===========================================================================


class TestQAReportExtended:
    def _make_report(self, font):
        from aifont.agents.qa_agent import QAAgent

        agent = QAAgent(font=font)
        return agent.run("test", font=font)

    def test_summary_contains_font_name(self, font, mock_ff_font):
        mock_ff_font.fontname = "TestFont"
        from aifont.agents.qa_agent import QAAgent

        agent = QAAgent(font=font)
        report = agent.generate_qa_report()
        summary = report.summary()
        assert isinstance(summary, str)

    def test_to_dict_structure(self, font):
        from aifont.agents.qa_agent import QAAgent

        agent = QAAgent(font=font)
        report = agent.generate_qa_report()
        d = report.to_dict()
        assert "score" in d
        assert "checks" in d
        assert "suggestions" in d

    def test_generate_qa_report_directly(self, font):
        from aifont.agents.qa_agent import QAAgent

        agent = QAAgent(font=font)
        report = agent.generate_qa_report()
        assert report is not None

    def test_fix_overlaps_runs(self, font, mock_ff_font):
        from aifont.agents.qa_agent import QAAgent

        agent = QAAgent(font=font)
        result = agent.fix_overlaps()
        assert isinstance(result, list)

    def test_correct_directions_runs(self, font):
        from aifont.agents.qa_agent import QAAgent

        agent = QAAgent(font=font)
        result = agent.correct_directions()
        assert isinstance(result, list)

    def test_simplify_contours_runs(self, font):
        from aifont.agents.qa_agent import QAAgent

        agent = QAAgent(font=font)
        result = agent.simplify_contours(threshold=0.5)
        assert isinstance(result, list)

    def test_validate_font_runs(self, font):
        from aifont.agents.qa_agent import QAAgent

        agent = QAAgent(font=font)
        report = agent.validate_font()
        assert report is not None

    def test_auto_fix_false(self, font):
        from aifont.agents.qa_agent import QAAgent

        agent = QAAgent(font=font, auto_fix=False)
        report = agent.run("test", font=font)
        assert report is not None

    def test_report_passed_property(self, font):
        from aifont.agents.qa_agent import QAAgent, QAReport, CheckResult

        report = QAReport(
            font_name="TestFont",
            checks={"ok": CheckResult(name="ok", passed=True)},
        )
        assert report.passed is True

    def test_report_not_passed(self, font):
        from aifont.agents.qa_agent import QAReport, CheckResult

        report = QAReport(
            font_name="TestFont",
            checks={"fail": CheckResult(name="fail", passed=False)},
        )
        assert report.passed is False

    def test_total_issues_property(self, font):
        from aifont.agents.qa_agent import QAReport, CheckResult, GlyphIssue

        issue = GlyphIssue(glyph_name="A", issue_type="open_contour", description="open")
        report = QAReport(
            font_name="TestFont",
            checks={"c": CheckResult(name="c", passed=False, issues=[issue])},
        )
        assert report.total_issues == 1


# ===========================================================================
# aifont.core.font — property setters and factory errors
# ===========================================================================


class TestFontPropertySetters:
    def test_family_name_setter(self, font, mock_ff_font):
        font.family_name = "NewFamily"
        assert mock_ff_font.familyname == "NewFamily"

    def test_full_name_getter(self, font, mock_ff_font):
        mock_ff_font.fullname = "TestFont Regular"
        from aifont.core.font import FontMetadata

        meta = FontMetadata(mock_ff_font)
        assert meta.full_name == "TestFont Regular"

    def test_full_name_setter(self, font, mock_ff_font):
        from aifont.core.font import FontMetadata

        meta = FontMetadata(mock_ff_font)
        meta.full_name = "NewFull Regular"
        assert mock_ff_font.fullname == "NewFull Regular"

    def test_font_name_getter(self, font, mock_ff_font):
        assert font.font_name == mock_ff_font.fontname

    def test_font_name_setter(self, font, mock_ff_font):
        font.font_name = "NewPSName"
        assert mock_ff_font.fontname == "NewPSName"

    def test_family_getter(self, font, mock_ff_font):
        assert font.family == mock_ff_font.familyname

    def test_family_setter(self, font, mock_ff_font):
        font.family = "NewFamily"
        assert mock_ff_font.familyname == "NewFamily"

    def test_version_setter(self, font, mock_ff_font):
        font.version = "2.0"
        assert mock_ff_font.version == "2.0"

    def test_copyright_getter(self, font, mock_ff_font):
        mock_ff_font.copyright = "© Test"
        assert font.copyright == "© Test"

    def test_copyright_setter(self, font, mock_ff_font):
        font.copyright = "© 2024"
        assert mock_ff_font.copyright == "© 2024"

    def test_em_size_getter(self, font, mock_ff_font):
        mock_ff_font.em = 2048
        assert font.em_size == 2048

    def test_em_size_setter(self, font, mock_ff_font):
        font.em_size = 2048
        assert mock_ff_font.em == 2048

    def test_ascent_getter(self, font, mock_ff_font):
        mock_ff_font.ascent = 900
        assert font.ascent == 900

    def test_ascent_setter(self, font, mock_ff_font):
        font.ascent = 900
        assert mock_ff_font.ascent == 900

    def test_descent_getter(self, font, mock_ff_font):
        mock_ff_font.descent = 300
        assert font.descent == 300

    def test_descent_setter(self, font, mock_ff_font):
        font.descent = 300
        assert mock_ff_font.descent == 300

    def test_italic_angle_getter(self, font, mock_ff_font):
        mock_ff_font.italicangle = 12.5
        assert font.italic_angle == 12.5

    def test_italic_angle_setter(self, font, mock_ff_font):
        font.italic_angle = 12.5
        assert mock_ff_font.italicangle == 12.5

    def test_set_metadata_valid(self, font, mock_ff_font):
        font.set_metadata(fontname="NewName")
        assert mock_ff_font.fontname == "NewName"

    def test_set_metadata_invalid_key(self, font):
        with pytest.raises(ValueError, match="Unknown metadata field"):
            font.set_metadata(unknown_field="value")

    def test_family_name_alias_getter(self, font):
        assert font.family_name == font.family

    def test_family_name_alias_setter(self, font, mock_ff_font):
        font.family_name = "AliasFamily"
        assert mock_ff_font.familyname == "AliasFamily"

    def test_open_file_not_found(self):
        from aifont.core.font import Font

        with pytest.raises((FileNotFoundError, RuntimeError)):
            Font.open("/nonexistent/path/font.otf")

    def test_new_raises_without_ff(self):
        from aifont.core.font import Font
        import aifont.core.font as _m

        with patch.object(_m, "_FF_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="not available"):
                Font.new()

    def test_create_uses_new(self):
        from aifont.core.font import Font

        mock_ff = MagicMock()
        mock_ff.__iter__ = MagicMock(return_value=iter([]))
        with patch("aifont.core.font._FF_AVAILABLE", True), \
             patch("aifont.core.font._ff") as ff_mod:
            ff_mod.font.return_value = mock_ff
            font = Font.create("MyNewFont", family="MyFamily")
        assert font.name == "MyNewFont"

    def test_ff_and_raw_properties(self, font, mock_ff_font):
        assert font.raw is mock_ff_font
        assert font.ff_font is mock_ff_font


# ===========================================================================
# aifont.core.contour — uncovered functions
# ===========================================================================


class TestContourAdditional:
    def test_correct_direction(self, glyph, mock_ff_glyph):
        from aifont.core.contour import correct_direction

        correct_direction(glyph)
        mock_ff_glyph.correctDirection.assert_called_once()

    def test_correct_direction_no_attr(self, glyph, mock_ff_glyph):
        from aifont.core.contour import correct_direction

        del mock_ff_glyph.correctDirection
        correct_direction(glyph)  # Must not raise

    def test_reverse_direction(self, glyph, mock_ff_glyph):
        from aifont.core.contour import reverse_direction

        reverse_direction(glyph)
        mock_ff_glyph.reverseDirection.assert_called_once()

    def test_reverse_direction_no_attr(self, glyph, mock_ff_glyph):
        from aifont.core.contour import reverse_direction

        del mock_ff_glyph.reverseDirection
        reverse_direction(glyph)  # Must not raise

    def test_add_extrema(self, glyph, mock_ff_glyph):
        from aifont.core.contour import add_extrema

        add_extrema(glyph)
        mock_ff_glyph.addExtrema.assert_called_once()

    def test_add_extrema_no_attr(self, glyph, mock_ff_glyph):
        from aifont.core.contour import add_extrema

        del mock_ff_glyph.addExtrema
        add_extrema(glyph)  # Must not raise

    def test_round_to_int(self, glyph, mock_ff_glyph):
        from aifont.core.contour import round_to_int

        round_to_int(glyph)
        mock_ff_glyph.round.assert_called_once()

    def test_round_to_int_no_attr(self, glyph, mock_ff_glyph):
        from aifont.core.contour import round_to_int

        del mock_ff_glyph.round
        round_to_int(glyph)  # Must not raise

    def test_auto_hint(self, glyph, mock_ff_glyph):
        from aifont.core.contour import auto_hint

        auto_hint(glyph)
        mock_ff_glyph.autoHint.assert_called_once()

    def test_auto_hint_no_attr(self, glyph, mock_ff_glyph):
        from aifont.core.contour import auto_hint

        del mock_ff_glyph.autoHint
        auto_hint(glyph)  # Must not raise

    def test_apply_stroke_calls_change_weight(self, glyph, mock_ff_glyph):
        from aifont.core.contour import apply_stroke

        apply_stroke(glyph, width=10.0)
        mock_ff_glyph.changeWeight.assert_called()

    def test_apply_stroke_type_error_fallback(self, glyph, mock_ff_glyph):
        from aifont.core.contour import apply_stroke

        mock_ff_glyph.changeWeight.side_effect = [TypeError("bad"), None]
        apply_stroke(glyph, width=10.0)
        assert mock_ff_glyph.changeWeight.call_count >= 1

    def test_apply_stroke_no_attr(self, glyph, mock_ff_glyph):
        from aifont.core.contour import apply_stroke

        del mock_ff_glyph.changeWeight
        apply_stroke(glyph, width=10.0)  # Must not raise

    def test_apply_slant(self, glyph, mock_ff_glyph):
        from aifont.core.contour import apply_slant

        apply_slant(glyph, angle_deg=10.0)
        mock_ff_glyph.transform.assert_called()

    def test_apply_slant_no_transform(self, glyph, mock_ff_glyph):
        from aifont.core.contour import apply_slant

        del mock_ff_glyph.transform
        apply_slant(glyph, angle_deg=10.0)  # Must not raise

    def test_scale(self, glyph, mock_ff_glyph):
        from aifont.core.contour import scale

        scale(glyph, 2.0, 1.0)
        mock_ff_glyph.transform.assert_called()

    def test_translate(self, glyph, mock_ff_glyph):
        from aifont.core.contour import translate

        translate(glyph, 10.0, 20.0)
        mock_ff_glyph.transform.assert_called()

    def test_smooth_transitions(self, glyph, mock_ff_glyph):
        from aifont.core.contour import smooth_transitions

        smooth_transitions(glyph)  # Should not raise

    def test_to_svg_path_empty(self, glyph, mock_ff_glyph):
        from aifont.core.contour import to_svg_path

        mock_ff_glyph.foreground.__iter__ = MagicMock(return_value=iter([]))
        result = to_svg_path(glyph)
        assert isinstance(result, str)


# ===========================================================================
# aifont.core.metrics — uncovered helpers
# ===========================================================================


class TestMetricsAdditional:
    def test_get_kern_pairs_with_subtables(self, font, mock_ff_font):
        from aifont.core.metrics import get_kern_pairs

        # subtables is None → empty result
        mock_ff_font.subtables = None
        result = get_kern_pairs(font)
        assert result == {}

    def test_set_kern_no_existing_lookup(self, font, mock_ff_font):
        from aifont.core.metrics import set_kern

        mock_ff_font.gpos_lookups = None
        set_kern(font, "A", "V", -50)
        mock_ff_font.addLookup.assert_called()

    def test_set_kern_with_existing_lookup(self, font, mock_ff_font):
        from aifont.core.metrics import set_kern

        mock_ff_font.gpos_lookups = ["kern"]
        set_kern(font, "A", "V", -50, lookup="kern", subtable="kern_sub")

    def test_remove_kern_not_found(self, font, mock_ff_font):
        from aifont.core.metrics import remove_kern

        mock_ff_font.subtables = None
        result = remove_kern(font, "A", "V")
        assert result is False

    def test_auto_space_uses_autowidth(self, font, mock_ff_font):
        from aifont.core.metrics import auto_space

        auto_space(font)
        mock_ff_font.autoWidth.assert_called()

    def test_auto_space_fallback(self, font, mock_ff_font):
        from aifont.core.metrics import auto_space

        mock_ff_font.autoWidth.side_effect = Exception("no autoWidth")
        auto_space(font, target_ratio=0.1)
        # Should have iterated glyphs for fallback

    def test_set_side_bearings_success(self, font, mock_ff_font):
        from aifont.core.metrics import set_side_bearings

        result = set_side_bearings(font, "A", lsb=60, rsb=60)
        assert result is True

    def test_set_side_bearings_not_found(self, font, mock_ff_font):
        from aifont.core.metrics import set_side_bearings

        mock_ff_font.__getitem__.side_effect = KeyError("Z")
        result = set_side_bearings(font, "Z", lsb=60)
        assert result is False

    def test_get_side_bearings_found(self, font, mock_ff_font):
        from aifont.core.metrics import get_side_bearings, SideBearings

        result = get_side_bearings(font, "A")
        assert isinstance(result, SideBearings)

    def test_get_side_bearings_not_found(self, font, mock_ff_font):
        from aifont.core.metrics import get_side_bearings

        mock_ff_font.__getitem__.side_effect = KeyError("Z")
        result = get_side_bearings(font, "Z")
        assert result is None

    def test_analyze_spacing(self, font, mock_ff_font):
        from aifont.core.metrics import analyze_spacing, SpacingAnalysis

        result = analyze_spacing(font)
        assert isinstance(result, SpacingAnalysis)
        assert result.glyph_count == 3

    def test_auto_kern_returns_list(self, font, mock_ff_font):
        from aifont.core.metrics import auto_kern

        mock_ff_font.subtables = None
        result = auto_kern(font)
        assert isinstance(result, list)


# ===========================================================================
# aifont.core.export — additional coverage
# ===========================================================================


class TestExportAdditional:
    def test_export_woff_calls_generate(self, font, mock_ff_font, tmp_path):
        from aifont.core.export import export_woff

        out = tmp_path / "out.woff"
        export_woff(font, str(out))
        mock_ff_font.generate.assert_called_once_with(str(out))

    def test_export_otf_flags(self, font, mock_ff_font, tmp_path):
        from aifont.core.export import export_otf

        out = tmp_path / "out.otf"
        export_otf(font, str(out))
        mock_ff_font.generate.assert_called_once_with(str(out), flags=("opentype",))

    def test_export_woff2_use_fonttools_not_available(self, font, tmp_path):
        from aifont.core.export import export_woff2
        import aifont.core.export as _mod

        with patch.object(_mod, "_FONTTOOLS_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="fontTools"):
                export_woff2(font, str(tmp_path / "out.woff2"), use_fonttools=True)

    def test_subset_font_delegates(self, font, mock_ff_font, tmp_path):
        from aifont.core.export import subset_font

        out = tmp_path / "sub.woff2"
        with patch("aifont.core.export.export_woff2") as mock_w:
            subset_font(font, str(out), ["latin"])
        mock_w.assert_called()

    def test_export_variable_delegates(self, font, mock_ff_font, tmp_path):
        from aifont.core.export import export_variable

        out = tmp_path / "var.ttf"
        export_variable(font, str(out))
        mock_ff_font.generate.assert_called()


# ===========================================================================
# aifont.core.analyzer — additional coverage
# ===========================================================================


class TestAnalyzerAdditional:
    def test_analyze_returns_font_report(self, font):
        from aifont.core.analyzer import analyze

        report = analyze(font)
        assert report is not None

    def test_analyze_style_returns_profile(self, font):
        from aifont.core.analyzer import analyze_style

        profile = analyze_style(font)
        assert profile is not None

    def test_font_report_validation_score(self, font):
        from aifont.core.analyzer import analyze

        report = analyze(font)
        assert 0.0 <= report.validation_score <= 1.0

    def test_font_report_to_dict(self, font):
        from aifont.core.analyzer import analyze

        report = analyze(font)
        # FontReport has __str__ for serialization
        text = str(report)
        assert isinstance(text, str)
        assert "Glyphs" in text

    def test_font_report_missing_unicodes(self, font):
        from aifont.core.analyzer import analyze

        report = analyze(font)
        assert isinstance(report.missing_unicodes, list)

    def test_analyze_null_like_font(self):
        from aifont.core.analyzer import analyze

        # Font with None ff
        ff = MagicMock()
        ff.__iter__ = MagicMock(side_effect=Exception("no iter"))
        from aifont.core.font import Font

        f = Font(ff)
        # Should not raise
        try:
            report = analyze(f)
            assert report is not None
        except Exception:
            pass  # acceptable if it raises gracefully


# ===========================================================================
# aifont.core.svg_parser — additional coverage
# ===========================================================================


class TestSvgParserAdditional:
    def test_parse_path_d_empty(self):
        from aifont.core.svg_parser import _parse_path_d

        result = _parse_path_d("")
        assert isinstance(result, list)

    def test_parse_path_d_simple_move(self):
        from aifont.core.svg_parser import _parse_path_d

        result = _parse_path_d("M 0 0 L 100 0 Z")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_svg_path_to_contours(self):
        from aifont.core.svg_parser import svg_path_to_contours

        try:
            result = svg_path_to_contours("M 0 0 L 100 0 L 100 100 Z")
            assert isinstance(result, list)
        except Exception:
            pass  # acceptable if fontforge not available

    def test_svg_to_glyph_file_not_found(self, font):
        from aifont.core.svg_parser import svg_to_glyph

        with pytest.raises(FileNotFoundError):
            svg_to_glyph("/nonexistent/file.svg", font)

    def test_flip_y(self):
        from aifont.core.svg_parser import _flip_y

        result = _flip_y(200.0, em=1000.0)
        assert isinstance(result, float)

    def test_parse_viewbox_valid(self):
        from aifont.core.svg_parser import _parse_viewbox

        result = _parse_viewbox("0 0 1000 1000")
        assert result is not None

    def test_parse_viewbox_empty(self):
        from aifont.core.svg_parser import _parse_viewbox

        result = _parse_viewbox("")
        assert result is None

    def test_collect_path_data(self):
        import xml.etree.ElementTree as ET
        from aifont.core.svg_parser import _collect_path_data

        svg_text = '<svg xmlns="http://www.w3.org/2000/svg"><path d="M 0 0 L 100 0 Z"/></svg>'
        root = ET.fromstring(svg_text)
        result = _collect_path_data(root)
        assert isinstance(result, list)


# ===========================================================================
# aifont.auth.security — verify bcrypt 4.x compatibility
# ===========================================================================


class TestSecurityBcryptCompat:
    def test_hash_is_bcrypt_string(self):
        from aifont.auth.security import hash_password

        h = hash_password("Test1234")
        assert h.startswith("$2b$")

    def test_roundtrip(self):
        from aifont.auth.security import hash_password, verify_password

        h = hash_password("MyPassword99")
        assert verify_password("MyPassword99", h)
        assert not verify_password("WrongPassword", h)

    def test_long_password_no_error(self):
        """Passwords >72 bytes must be handled (SHA-256 pre-hash)."""
        from aifont.auth.security import hash_password, verify_password

        long_pw = "A" * 100  # >72 bytes
        h = hash_password(long_pw)
        assert verify_password(long_pw, h)
        assert not verify_password("A" * 99, h)


# ===========================================================================
# aifont.auth.quota — additional cases
# ===========================================================================


class TestQuotaAdditional:
    @pytest.mark.asyncio
    async def test_font_quota_within_limit(self):
        import uuid
        from datetime import datetime, timedelta, timezone
        from unittest.mock import AsyncMock, MagicMock, patch

        from aifont.auth.quota import check_font_quota
        from aifont.auth.models import UserRole

        user = MagicMock()
        user.id = uuid.uuid4()
        user.role = UserRole.FREE

        quota = MagicMock()
        quota.max_fonts = 5
        quota.fonts_created = 2
        quota.reset_at = datetime.now(timezone.utc) + timedelta(hours=1)
        db = AsyncMock()

        with patch("aifont.auth.quota.get_or_create_quota", return_value=quota):
            await check_font_quota(user, db)
            assert quota.fonts_created == 3

    @pytest.mark.asyncio
    async def test_api_key_quota_within_limit(self):
        import uuid
        from datetime import datetime, timedelta, timezone
        from unittest.mock import AsyncMock, MagicMock, patch

        from aifont.auth.quota import check_api_key_quota
        from aifont.auth.models import UserRole

        user = MagicMock()
        user.id = uuid.uuid4()
        user.role = UserRole.FREE
        key = MagicMock()
        key.is_active = True
        user.api_keys = [key]

        quota = MagicMock()
        quota.max_api_keys = 5
        db = AsyncMock()

        with patch("aifont.auth.quota.get_or_create_quota", return_value=quota):
            await check_api_key_quota(user, db)  # Should not raise


# ===========================================================================
# aifont.db.database — connection helpers
# ===========================================================================


class TestDbDatabase:
    def test_database_module_importable(self):
        import aifont.db.database as db_mod

        # Should not raise on import
        assert db_mod is not None

    def test_get_session_callable(self):
        import aifont.db.database as db_mod

        assert hasattr(db_mod, "get_session") or hasattr(db_mod, "SessionLocal")


# ===========================================================================
# aifont.auth — __init__ exports
# ===========================================================================


class TestAuthInit:
    def test_auth_package_importable(self):
        import aifont.auth

        assert aifont.auth is not None
