"""Tests for aifont.agents.export_agent and aifont.core.export.

These tests use unittest.mock to avoid requiring a live fontforge installation
and actual font files.  They validate the agent's logic: format selection,
CSS generation, specimen generation, and validation.
"""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_font(name: str = "TestFont") -> MagicMock:
    """Return a MagicMock that mimics a fontforge.font object."""
    font = MagicMock()
    font.fontname = name
    font.familyname = name
    # Make font.generate() write a plausible binary stub so validation passes.
    def _generate(path, flags=()):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        suffix = p.suffix.lower()
        if suffix == ".otf":
            p.write_bytes(b"OTTO" + b"\x00" * 500)
        elif suffix in (".ttf",):
            p.write_bytes(b"\x00\x01\x00\x00" + b"\x00" * 500)
        else:
            p.write_bytes(b"\x00" * 500)

    font.generate.side_effect = _generate
    font.autoHint.return_value = None
    return font


def _make_woff2_bytes() -> bytes:
    """Return minimal plausible WOFF2 bytes (magic + padding)."""
    return b"wOF2" + b"\x00" * 100


# ---------------------------------------------------------------------------
# aifont.core.export tests
# ---------------------------------------------------------------------------

class TestCoreExport:
    def test_export_otf_creates_file(self, tmp_path):
        from aifont.core.export import export_otf

        font = _make_mock_font()
        dest = export_otf(font, tmp_path / "out.otf")
        assert dest.exists()
        assert dest.suffix == ".otf"
        font.generate.assert_called_once()

    def test_export_ttf_calls_autohint_by_default(self, tmp_path):
        from aifont.core.export import export_ttf

        font = _make_mock_font()
        export_ttf(font, tmp_path / "out.ttf", autohint=True)
        font.autoHint.assert_called_once()

    def test_export_ttf_skips_autohint_when_disabled(self, tmp_path):
        from aifont.core.export import export_ttf

        font = _make_mock_font()
        export_ttf(font, tmp_path / "out.ttf", autohint=False)
        font.autoHint.assert_not_called()

    def test_export_otf_creates_parent_dirs(self, tmp_path):
        from aifont.core.export import export_otf

        font = _make_mock_font()
        deep = tmp_path / "a" / "b" / "c" / "font.otf"
        export_otf(font, deep)
        assert deep.parent.exists()

    def test_export_variable_delegates_generate(self, tmp_path):
        from aifont.core.export import export_variable

        font = _make_mock_font()
        dest = export_variable(font, tmp_path / "var.ttf")
        font.generate.assert_called_once()

    def test_subset_font_requires_criteria(self, tmp_path):
        from aifont.core.export import subset_font
        pytest.importorskip("fontTools")

        with pytest.raises(ValueError, match="At least one of"):
            subset_font(tmp_path / "in.ttf", tmp_path / "out.ttf")

    def test_language_tag_to_unicodes_latin(self):
        from aifont.core.export import _language_tag_to_unicodes

        codes = _language_tag_to_unicodes("en")
        # ASCII range must be included
        assert ord("A") in codes
        assert ord("z") in codes

    def test_language_tag_to_unicodes_subtag_fallback(self):
        from aifont.core.export import _language_tag_to_unicodes

        # "fr-CA" should fall back to "fr"
        codes_subtag = _language_tag_to_unicodes("fr-CA")
        codes_base   = _language_tag_to_unicodes("fr")
        assert codes_subtag == codes_base

    def test_language_tag_to_unicodes_unknown_returns_empty(self):
        from aifont.core.export import _language_tag_to_unicodes

        assert _language_tag_to_unicodes("zz-ZZ") == []

    def test_export_woff2_raises_without_fonttools(self, tmp_path):
        from aifont.core import export as export_mod

        font = _make_mock_font()
        original = export_mod._FONTTOOLS_AVAILABLE
        try:
            export_mod._FONTTOOLS_AVAILABLE = False
            with pytest.raises(ImportError, match="fontTools"):
                export_mod.export_woff2(font, tmp_path / "out.woff2")
        finally:
            export_mod._FONTTOOLS_AVAILABLE = original

    def test_subset_font_raises_without_fonttools(self, tmp_path):
        from aifont.core import export as export_mod

        original = export_mod._FONTTOOLS_AVAILABLE
        try:
            export_mod._FONTTOOLS_AVAILABLE = False
            with pytest.raises(ImportError, match="fontTools"):
                export_mod.subset_font(
                    tmp_path / "in.ttf",
                    tmp_path / "out.ttf",
                    unicodes=[65],
                )
        finally:
            export_mod._FONTTOOLS_AVAILABLE = original


# ---------------------------------------------------------------------------
# ExportAgent tests
# ---------------------------------------------------------------------------

class TestExportAgentFormatSelection:
    def setup_method(self):
        from aifont.agents.export_agent import ExportAgent
        self.agent = ExportAgent(generate_specimen=False, generate_css=False, validate=False)

    def test_web_formats(self):
        from aifont.agents.export_agent import ExportTarget
        fmts = self.agent._choose_formats(ExportTarget.WEB, None)
        assert "woff2" in fmts
        assert "ttf" in fmts

    def test_print_formats(self):
        from aifont.agents.export_agent import ExportTarget
        fmts = self.agent._choose_formats(ExportTarget.PRINT, None)
        assert "otf" in fmts

    def test_app_formats(self):
        from aifont.agents.export_agent import ExportTarget
        fmts = self.agent._choose_formats(ExportTarget.APP, None)
        assert "ttf" in fmts

    def test_variable_formats(self):
        from aifont.agents.export_agent import ExportTarget
        fmts = self.agent._choose_formats(ExportTarget.VARIABLE, None)
        assert "variable" in fmts

    def test_full_formats(self):
        from aifont.agents.export_agent import ExportTarget
        fmts = self.agent._choose_formats(ExportTarget.FULL, None)
        assert set(fmts) >= {"otf", "ttf", "woff2"}

    def test_extra_formats_appended(self):
        from aifont.agents.export_agent import ExportTarget
        fmts = self.agent._choose_formats(ExportTarget.PRINT, ["ttf"])
        assert "otf" in fmts
        assert "ttf" in fmts

    def test_extra_formats_no_duplicates(self):
        from aifont.agents.export_agent import ExportTarget
        fmts = self.agent._choose_formats(ExportTarget.WEB, ["woff2"])
        assert fmts.count("woff2") == 1


class TestExportAgentCSS:
    def setup_method(self):
        from aifont.agents.export_agent import ExportAgent
        self.agent = ExportAgent(generate_specimen=False, generate_css=True, validate=False)

    def test_css_contains_font_family(self, tmp_path):
        exported = {"otf": tmp_path / "MyFont.otf"}
        css = self.agent._build_css("MyFont", exported)
        assert "MyFont" in css
        assert "@font-face" in css

    def test_css_woff2_format_label(self, tmp_path):
        exported = {"woff2": tmp_path / "MyFont.woff2"}
        css = self.agent._build_css("MyFont", exported)
        assert "woff2" in css

    def test_css_otf_format_label(self, tmp_path):
        exported = {"otf": tmp_path / "MyFont.otf"}
        css = self.agent._build_css("MyFont", exported)
        assert "opentype" in css

    def test_css_empty_when_no_files(self):
        css = self.agent._build_css("MyFont", {})
        assert css == ""

    def test_css_src_order_woff2_before_ttf(self, tmp_path):
        exported = {
            "ttf":   tmp_path / "MyFont.ttf",
            "woff2": tmp_path / "MyFont.woff2",
        }
        css = self.agent._build_css("MyFont", exported)
        assert css.index("woff2") < css.index("truetype")

    def test_css_font_display_swap(self, tmp_path):
        exported = {"otf": tmp_path / "MyFont.otf"}
        css = self.agent._build_css("MyFont", exported)
        assert "font-display: swap" in css


class TestExportAgentSpecimen:
    def setup_method(self):
        from aifont.agents.export_agent import ExportAgent
        self.agent = ExportAgent(generate_specimen=True, generate_css=True, validate=False)

    def test_specimen_is_html(self, tmp_path):
        exported = {"otf": tmp_path / "MyFont.otf"}
        path = self.agent._write_specimen(tmp_path, "MyFont", exported)
        content = path.read_text(encoding="utf-8")
        assert content.strip().startswith("<!DOCTYPE html>")
        assert "<html" in content

    def test_specimen_contains_family_name(self, tmp_path):
        exported = {"otf": tmp_path / "MyFont.otf"}
        path = self.agent._write_specimen(tmp_path, "MyFont", exported)
        assert "MyFont" in path.read_text(encoding="utf-8")

    def test_specimen_saved_as_html_file(self, tmp_path):
        exported = {"otf": tmp_path / "MyFont.otf"}
        path = self.agent._write_specimen(tmp_path, "MyFont", exported)
        assert path.suffix == ".html"
        assert path.exists()

    def test_specimen_contains_pangram(self, tmp_path):
        exported = {"otf": tmp_path / "MyFont.otf"}
        path = self.agent._write_specimen(tmp_path, "MyFont", exported)
        assert "The quick brown fox jumps over the lazy dog." in path.read_text(encoding="utf-8")


class TestExportAgentValidation:
    def setup_method(self):
        from aifont.agents.export_agent import ExportAgent
        self.agent = ExportAgent(validate=True)

    def test_validate_missing_file(self, tmp_path):
        v = self.agent._validate_file("otf", tmp_path / "missing.otf")
        assert not v.passed
        assert any("does not exist" in i for i in v.issues)

    def test_validate_empty_file(self, tmp_path):
        p = tmp_path / "empty.otf"
        p.write_bytes(b"")
        v = self.agent._validate_file("otf", p)
        assert not v.passed
        assert any("empty" in i.lower() for i in v.issues)

    def test_validate_otf_bad_magic(self, tmp_path):
        p = tmp_path / "bad.otf"
        p.write_bytes(b"\xFF\xFF\xFF\xFF" + b"\x00" * 500)
        v = self.agent._validate_file("otf", p)
        assert not v.passed
        assert any("magic" in i.lower() for i in v.issues)

    def test_validate_otf_good(self, tmp_path):
        p = tmp_path / "good.otf"
        p.write_bytes(b"OTTO" + b"\x00" * 500)
        v = self.agent._validate_file("otf", p)
        assert v.passed
        assert v.file_size_bytes > 0

    def test_validate_woff2_good(self, tmp_path):
        p = tmp_path / "good.woff2"
        p.write_bytes(b"wOF2" + b"\x00" * 100)
        v = self.agent._validate_file("woff2", p)
        assert v.passed

    def test_validate_ttf_good(self, tmp_path):
        p = tmp_path / "good.ttf"
        p.write_bytes(b"\x00\x01\x00\x00" + b"\x00" * 500)
        v = self.agent._validate_file("ttf", p)
        assert v.passed


class TestExportAgentRun:
    """Integration-style tests for ExportAgent.run() using mocked core functions."""

    def test_run_web_target_exports_woff2_and_ttf(self, tmp_path):
        from aifont.agents.export_agent import ExportAgent, ExportTarget

        font = _make_mock_font("RunFont")
        agent = ExportAgent(generate_specimen=False, generate_css=False, validate=False)

        with patch("aifont.agents.export_agent.export_ttf") as mock_ttf, \
             patch("aifont.agents.export_agent.export_woff2") as mock_woff2:

            # Make the mocks create the files
            def _ttf(f, p, **kw):
                Path(p).write_bytes(b"\x00\x01\x00\x00" + b"\x00" * 500)
                return Path(p)
            def _woff2(f, p, **kw):
                Path(p).write_bytes(b"wOF2" + b"\x00" * 100)
                return Path(p)

            mock_ttf.side_effect = _ttf
            mock_woff2.side_effect = _woff2

            result = agent.run(font, tmp_path, target=ExportTarget.WEB, family_name="RunFont")

        assert "ttf" in result.exported_files or "woff2" in result.exported_files

    def test_run_print_target_exports_otf(self, tmp_path):
        from aifont.agents.export_agent import ExportAgent, ExportTarget

        font = _make_mock_font("RunFont")
        agent = ExportAgent(generate_specimen=False, generate_css=False, validate=False)

        with patch("aifont.agents.export_agent.export_otf") as mock_otf:
            def _otf(f, p, **kw):
                Path(p).write_bytes(b"OTTO" + b"\x00" * 500)
                return Path(p)
            mock_otf.side_effect = _otf

            result = agent.run(font, tmp_path, target=ExportTarget.PRINT, family_name="RunFont")

        assert "otf" in result.exported_files

    def test_run_generates_css_when_enabled(self, tmp_path):
        from aifont.agents.export_agent import ExportAgent, ExportTarget

        font = _make_mock_font("RunFont")
        agent = ExportAgent(generate_specimen=False, generate_css=True, validate=False)

        with patch("aifont.agents.export_agent.export_otf") as mock_otf:
            def _otf(f, p, **kw):
                Path(p).write_bytes(b"OTTO" + b"\x00" * 500)
                return Path(p)
            mock_otf.side_effect = _otf

            result = agent.run(font, tmp_path, target=ExportTarget.PRINT, family_name="RunFont")

        assert "@font-face" in result.css_snippet

    def test_run_generates_specimen_when_enabled(self, tmp_path):
        from aifont.agents.export_agent import ExportAgent, ExportTarget

        font = _make_mock_font("RunFont")
        agent = ExportAgent(generate_specimen=True, generate_css=False, validate=False)

        with patch("aifont.agents.export_agent.export_otf") as mock_otf:
            def _otf(f, p, **kw):
                Path(p).write_bytes(b"OTTO" + b"\x00" * 500)
                return Path(p)
            mock_otf.side_effect = _otf

            result = agent.run(font, tmp_path, target=ExportTarget.PRINT, family_name="RunFont")

        assert result.specimen_path is not None
        assert result.specimen_path.exists()

    def test_run_validation_in_result(self, tmp_path):
        from aifont.agents.export_agent import ExportAgent, ExportTarget

        font = _make_mock_font("RunFont")
        agent = ExportAgent(generate_specimen=False, generate_css=False, validate=True)

        with patch("aifont.agents.export_agent.export_otf") as mock_otf:
            def _otf(f, p, **kw):
                Path(p).write_bytes(b"OTTO" + b"\x00" * 500)
                return Path(p)
            mock_otf.side_effect = _otf

            result = agent.run(font, tmp_path, target=ExportTarget.PRINT, family_name="RunFont")

        assert len(result.validation_report) > 0

    def test_run_accepts_string_target(self, tmp_path):
        from aifont.agents.export_agent import ExportAgent

        font = _make_mock_font("RunFont")
        agent = ExportAgent(generate_specimen=False, generate_css=False, validate=False)

        with patch("aifont.agents.export_agent.export_otf") as mock_otf:
            def _otf(f, p, **kw):
                Path(p).write_bytes(b"OTTO" + b"\x00" * 500)
                return Path(p)
            mock_otf.side_effect = _otf

            # Should not raise even though "print" is a string, not ExportTarget enum
            result = agent.run(font, tmp_path, target="print", family_name="RunFont")
        assert result is not None

    def test_run_all_passed_property(self, tmp_path):
        from aifont.agents.export_agent import ExportAgent, ExportTarget

        font = _make_mock_font("RunFont")
        agent = ExportAgent(generate_specimen=False, generate_css=False, validate=True)

        with patch("aifont.agents.export_agent.export_otf") as mock_otf:
            def _otf(f, p, **kw):
                Path(p).write_bytes(b"OTTO" + b"\x00" * 500)
                return Path(p)
            mock_otf.side_effect = _otf

            result = agent.run(font, tmp_path, target=ExportTarget.PRINT, family_name="RunFont")

        assert result.all_passed is True

    def test_run_export_exception_does_not_crash_pipeline(self, tmp_path):
        """Exceptions raised during a single format export must not abort the pipeline."""
        from aifont.agents.export_agent import ExportAgent, ExportTarget

        font = _make_mock_font("RunFont")
        agent = ExportAgent(generate_specimen=False, generate_css=False, validate=False)

        with patch("aifont.agents.export_agent.export_otf", side_effect=RuntimeError("boom")):
            # Should complete without raising
            result = agent.run(font, tmp_path, target=ExportTarget.PRINT, family_name="RunFont")

        # The failed format should not appear in exported_files
        assert "otf" not in result.exported_files


class TestExportTargetEnum:
    def test_string_values(self):
        from aifont.agents.export_agent import ExportTarget
        assert ExportTarget.WEB.value == "web"
        assert ExportTarget.PRINT.value == "print"
        assert ExportTarget.APP.value == "app"
        assert ExportTarget.VARIABLE.value == "variable"
        assert ExportTarget.FULL.value == "full"

    def test_from_string(self):
        from aifont.agents.export_agent import ExportTarget
        assert ExportTarget("web") is ExportTarget.WEB


class TestFormatValidationDataclass:
    def test_all_passed_empty(self):
        from aifont.agents.export_agent import ExportResult
        r = ExportResult()
        assert r.all_passed is True  # no validations = trivially true

    def test_all_passed_false_when_failure(self, tmp_path):
        from aifont.agents.export_agent import ExportResult, FormatValidation
        v = FormatValidation(
            format="otf",
            path=tmp_path / "x.otf",
            file_size_bytes=0,
            passed=False,
            issues=["File is empty"],
        )
        r = ExportResult(validation_report=[v])
        assert r.all_passed is False
