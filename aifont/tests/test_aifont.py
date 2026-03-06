"""Smoke tests for the aifont package — run without a live FontForge install."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_ff_font(family: str = "Test") -> MagicMock:
    """Return a minimal mock that looks like a fontforge.font object."""
    ff = MagicMock()
    ff.familyname = family
    ff.fullname = f"{family} Regular"
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


def _make_mock_ff_glyph(name: str = "A", unicode_val: int = 65) -> MagicMock:
    g = MagicMock()
    g.glyphname = name
    g.unicode = unicode_val
    g.width = 600
    g.left_side_bearing = 50
    g.right_side_bearing = 50
    g.foreground = []
    return g


# ---------------------------------------------------------------------------
# aifont.core.font
# ---------------------------------------------------------------------------


def test_font_metadata_read():
    from aifont.core.font import Font

    ff = _make_mock_ff_font("MyFamily")
    font = Font(ff)
    meta = font.metadata
    assert meta["family"] == "MyFamily"
    assert meta["em_size"] == "1000"


def test_font_metadata_write():
    from aifont.core.font import Font

    ff = _make_mock_ff_font()
    font = Font(ff)
    font.metadata = {"family": "NewFamily", "weight": "Bold"}
    assert ff.familyname == "NewFamily"
    assert ff.weight == "Bold"


def test_font_glyphs_empty():
    from aifont.core.font import Font

    ff = _make_mock_ff_font()
    font = Font(ff)
    assert list(font.glyphs) == []


def test_font_raw():
    from aifont.core.font import Font

    ff = _make_mock_ff_font()
    font = Font(ff)
    assert font._raw is ff


# ---------------------------------------------------------------------------
# aifont.core.glyph
# ---------------------------------------------------------------------------


def test_glyph_name_and_unicode():
    from aifont.core.glyph import Glyph

    g = Glyph(_make_mock_ff_glyph("A", 65))
    assert g.name == "A"
    assert g.unicode == 65


def test_glyph_width_setter():
    from aifont.core.glyph import Glyph

    ff_g = _make_mock_ff_glyph()
    g = Glyph(ff_g)
    g.set_width(700)
    assert ff_g.width == 700


def test_glyph_set_width():
    from aifont.core.glyph import Glyph

    ff_g = _make_mock_ff_glyph()
    g = Glyph(ff_g)
    g.width = 800
    assert ff_g.width == 800


# ---------------------------------------------------------------------------
# aifont.core.analyzer
# ---------------------------------------------------------------------------


def test_analyze_empty_font():
    from aifont.core.analyzer import analyze
    from aifont.core.font import Font

    ff = _make_mock_ff_font()
    ff.__iter__ = lambda self: iter([])
    font = Font(ff)
    report = analyze(font)
    assert report.glyph_count == 0
    assert report.passed
    assert report.missing_unicodes == []


def test_analyze_font_with_glyph_no_unicode():
    from aifont.core.analyzer import analyze
    from aifont.core.font import Font

    ff = _make_mock_ff_font()
    ff_g = _make_mock_ff_glyph(".notdef", -1)
    ff.__iter__ = lambda self: iter([".notdef"])
    ff.__getitem__ = lambda self, key: ff_g
    font = Font(ff)
    report = analyze(font)
    assert report.glyph_count == 1
    assert ".notdef" in report.missing_unicodes


def test_font_report_passed_flag():
    from aifont.core.analyzer import FontReport

    r = FontReport(validation_errors=[])
    assert r.passed is True

    r2 = FontReport(validation_errors=["open_paths"])
    assert r2.passed is False


# ---------------------------------------------------------------------------
# aifont.core.contour
# ---------------------------------------------------------------------------


def test_simplify_delegates_to_fontforge():
    from aifont.core import contour
    from aifont.core.glyph import Glyph

    ff_g = _make_mock_ff_glyph()
    g = Glyph(ff_g)
    contour.simplify(g, threshold=2.0)
    ff_g.simplify.assert_called_once_with(2.0)


def test_remove_overlap_delegates():
    from aifont.core import contour
    from aifont.core.glyph import Glyph

    ff_g = _make_mock_ff_glyph()
    g = Glyph(ff_g)
    contour.remove_overlap(g)
    ff_g.removeOverlap.assert_called_once()


def test_transform_bad_matrix_raises():
    from aifont.core import contour
    from aifont.core.glyph import Glyph

    ff_g = _make_mock_ff_glyph()
    g = Glyph(ff_g)
    try:
        contour.transform(g, [1, 0, 0, 1])  # only 4 elements
        assert False, "Expected ValueError"  # noqa: B011
    except ValueError:
        pass


def test_transform_good_matrix():
    from aifont.core import contour
    from aifont.core.glyph import Glyph

    ff_g = _make_mock_ff_glyph()
    g = Glyph(ff_g)
    contour.transform(g, [1, 0, 0, 1, 0, 0])
    ff_g.transform.assert_called_once_with((1, 0, 0, 1, 0, 0))


# ---------------------------------------------------------------------------
# aifont.agents.orchestrator
# ---------------------------------------------------------------------------


def test_orchestrator_run_succeeds():
    """Orchestrator should return a Font when all agents succeed."""
    from aifont.agents.orchestrator import AgentResult, Orchestrator
    from aifont.core.font import Font

    ff = _make_mock_ff_font("Orchestrated")
    mock_font = Font(ff)

    class _OkAgent:
        def run(self, prompt, font):
            return AgentResult(agent_name="OkAgent", success=True, confidence=1.0)

    orch = Orchestrator()

    # Agents are imported locally inside Orchestrator.run() via
    # "from aifont.agents.X import Y", so we patch at the source module.
    with (
        patch("aifont.agents.design_agent.DesignAgent", _OkAgent),
        patch("aifont.agents.style_agent.StyleAgent", _OkAgent),
        patch("aifont.agents.metrics_agent.MetricsAgent", _OkAgent),
        patch("aifont.agents.qa_agent.QAAgent", _OkAgent),
        patch("aifont.agents.export_agent.ExportAgent", _OkAgent),
        patch("aifont.core.font.Font.new", return_value=mock_font),
    ):
        result = orch.run("test prompt")

    assert result is mock_font


def test_orchestrator_raises_on_agent_failure():
    from aifont.agents.orchestrator import AgentResult, Orchestrator
    from aifont.core.font import Font

    ff = _make_mock_ff_font()
    mock_font = Font(ff)

    class _FailAgent:
        def run(self, prompt, font):
            return AgentResult(
                agent_name="FailAgent",
                success=False,
                message="intentional failure",
            )

    orch = Orchestrator(max_retries=0)

    with (
        patch("aifont.agents.design_agent.DesignAgent", _FailAgent),
        patch("aifont.agents.style_agent.StyleAgent", _FailAgent),
        patch("aifont.agents.metrics_agent.MetricsAgent", _FailAgent),
        patch("aifont.agents.qa_agent.QAAgent", _FailAgent),
        patch("aifont.agents.export_agent.ExportAgent", _FailAgent),
        patch("aifont.core.font.Font.new", return_value=mock_font),
    ):
        try:
            orch.run("bad prompt")
            assert False, "Expected RuntimeError"  # noqa: B011
        except RuntimeError as exc:
            assert "intentional failure" in str(exc)
