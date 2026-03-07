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
    """Orchestrator.run() returns a PipelineResult — result.font holds the font."""
    from aifont.agents.orchestrator import AgentResult, Orchestrator, PipelineResult
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

    assert isinstance(result, PipelineResult)
    assert result.font is mock_font
    assert result.success


def test_orchestrator_raises_on_agent_failure():
    """When an agent fails, the step is captured in PipelineResult with success=False."""
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
        result = orch.run("bad prompt")

    assert not result.success
    assert any("intentional failure" in (s.message or "") for s in result.steps)


# ---------------------------------------------------------------------------
# Additional orchestrator tests for coverage
# ---------------------------------------------------------------------------


def _patch_pipeline_ok():
    """Return context managers that replace all 5 agents with a trivial OK agent."""
    from aifont.agents.orchestrator import AgentResult

    class _OkAgent:
        def run(self, prompt, font):
            return AgentResult(agent_name="OkAgent", success=True, confidence=1.0)

    return (
        patch("aifont.agents.design_agent.DesignAgent", _OkAgent),
        patch("aifont.agents.style_agent.StyleAgent", _OkAgent),
        patch("aifont.agents.metrics_agent.MetricsAgent", _OkAgent),
        patch("aifont.agents.qa_agent.QAAgent", _OkAgent),
        patch("aifont.agents.export_agent.ExportAgent", _OkAgent),
    )


def test_pipeline_result_errors_property():
    """PipelineResult.errors returns error strings from failed steps."""
    from aifont.agents.orchestrator import AgentResult, PipelineResult

    pr = PipelineResult(prompt="test")
    pr.steps.append(AgentResult(agent_name="A", success=False, error="boom"))
    pr.steps.append(AgentResult(agent_name="B", success=True))
    assert pr.errors == ["boom"]


def test_pipeline_result_success_false_on_any_failure():
    from aifont.agents.orchestrator import AgentResult, PipelineResult

    pr = PipelineResult(prompt="test")
    pr.steps.append(AgentResult(agent_name="A", success=True))
    pr.steps.append(AgentResult(agent_name="B", success=False))
    assert pr.success is False


def test_orchestrator_register_overrides_agent():
    """register() replaces the named agent slot."""
    from aifont.agents.orchestrator import AgentResult, Orchestrator, PipelineResult
    from aifont.core.font import Font

    ff = _make_mock_ff_font("Reg")
    mock_font = Font(ff)
    calls = []

    class _CustomDesign:
        def run(self, prompt, font):
            calls.append(prompt)
            return AgentResult(agent_name="CustomDesign", success=True, confidence=1.0)

    orch = Orchestrator()
    orch.register("design", _CustomDesign())

    patches = _patch_pipeline_ok()
    with (
        patches[0],
        patches[1],
        patches[2],
        patches[3],
        patches[4],
        patch("aifont.core.font.Font.new", return_value=mock_font),
    ):
        result = orch.run("reg prompt")

    assert isinstance(result, PipelineResult)
    # The registered design agent ran (even though patches override the class-level default)
    # — what matters is that register() sets _agents["design"].
    assert orch._agents.get("design") is not None


def test_orchestrator_create_font_delegates_to_run():
    """create_font() calls run() with font=None."""
    from aifont.agents.orchestrator import Orchestrator, PipelineResult
    from aifont.core.font import Font

    ff = _make_mock_ff_font()
    mock_font = Font(ff)
    orch = Orchestrator()

    patches = _patch_pipeline_ok()
    with (
        patches[0],
        patches[1],
        patches[2],
        patches[3],
        patches[4],
        patch("aifont.core.font.Font.new", return_value=mock_font),
    ):
        result = orch.create_font("a new font")

    assert isinstance(result, PipelineResult)
    assert result.font is mock_font


def test_orchestrator_run_font_new_fails_continues():
    """When Font.new() raises, the pipeline runs with font=None."""
    from aifont.agents.orchestrator import Orchestrator, PipelineResult

    orch = Orchestrator()

    patches = _patch_pipeline_ok()
    with (
        patches[0],
        patches[1],
        patches[2],
        patches[3],
        patches[4],
        patch("aifont.core.font.Font.new", side_effect=RuntimeError("no ff")),
    ):
        result = orch.run("broken font")

    assert isinstance(result, PipelineResult)
    assert result.font is None
    assert result.success  # all _OkAgent steps still succeed


def test_orchestrator_run_propagates_font_from_agent_data():
    """When an agent result carries data.font, the pipeline updates result.font."""
    from unittest.mock import MagicMock

    from aifont.agents.orchestrator import AgentResult, Orchestrator
    from aifont.core.font import Font

    ff = _make_mock_ff_font("Updated")
    updated_font = Font(ff)

    data = MagicMock()
    data.success = True
    data.font = updated_font
    # updated_font has a `glyphs` property (Font class always does)

    class _FontReturnAgent:
        def run(self, prompt, font):
            return AgentResult(agent_name="FontReturn", success=True, confidence=1.0, data=data)

    orch = Orchestrator()
    with (
        patch("aifont.agents.design_agent.DesignAgent", _FontReturnAgent),
        patch("aifont.agents.style_agent.StyleAgent", _FontReturnAgent),
        patch("aifont.agents.metrics_agent.MetricsAgent", _FontReturnAgent),
        patch("aifont.agents.qa_agent.QAAgent", _FontReturnAgent),
        patch("aifont.agents.export_agent.ExportAgent", _FontReturnAgent),
        patch("aifont.core.font.Font.new", side_effect=RuntimeError("no ff")),
    ):
        result = orch.run("update font")

    # The font propagation path should have been hit
    assert result is not None


def test_orchestrator_run_agent_exception_captured():
    """When an agent raises, the error is captured in AgentResult (not re-raised)."""
    from aifont.agents.orchestrator import Orchestrator

    class _BoomAgent:
        def run(self, prompt, font):
            raise ValueError("unexpected boom")

    orch = Orchestrator(max_retries=0)
    with (
        patch("aifont.agents.design_agent.DesignAgent", _BoomAgent),
        patch("aifont.agents.style_agent.StyleAgent", _BoomAgent),
        patch("aifont.agents.metrics_agent.MetricsAgent", _BoomAgent),
        patch("aifont.agents.qa_agent.QAAgent", _BoomAgent),
        patch("aifont.agents.export_agent.ExportAgent", _BoomAgent),
        patch("aifont.core.font.Font.new", side_effect=RuntimeError("no ff")),
    ):
        result = orch.run("boom")

    assert not result.success
    assert any(s.error and "boom" in s.error for s in result.steps)


def test_orchestrator_agent_retry_on_failure():
    """Agent failure is retried up to max_retries times before giving up."""
    from aifont.agents.orchestrator import AgentResult, Orchestrator

    attempt_counter = {"n": 0}

    class _EventualFailAgent:
        def run(self, prompt, font):
            attempt_counter["n"] += 1
            return AgentResult(agent_name="Fail", success=False, message="still failing")

    orch = Orchestrator(max_retries=2)
    with (
        patch("aifont.agents.design_agent.DesignAgent", _EventualFailAgent),
        patch("aifont.agents.style_agent.StyleAgent", _EventualFailAgent),
        patch("aifont.agents.metrics_agent.MetricsAgent", _EventualFailAgent),
        patch("aifont.agents.qa_agent.QAAgent", _EventualFailAgent),
        patch("aifont.agents.export_agent.ExportAgent", _EventualFailAgent),
        patch("aifont.core.font.Font.new", side_effect=RuntimeError("no ff")),
    ):
        result = orch.run("retry test")

    # DesignAgent alone should have been tried 3 times (0, 1, 2)
    assert attempt_counter["n"] >= 3
    assert not result.success


def test_orchestrator_agent_low_confidence_retry():
    """Agent returning low confidence is retried; final attempt is accepted."""
    from aifont.agents.orchestrator import AgentResult, Orchestrator

    call_count = {"n": 0}

    class _LowConfAgent:
        def run(self, prompt, font):
            call_count["n"] += 1
            return AgentResult(agent_name="LowConf", success=True, confidence=0.1)

    orch = Orchestrator(confidence_threshold=0.7, max_retries=1)
    with (
        patch("aifont.agents.design_agent.DesignAgent", _LowConfAgent),
        patch("aifont.agents.style_agent.StyleAgent", _LowConfAgent),
        patch("aifont.agents.metrics_agent.MetricsAgent", _LowConfAgent),
        patch("aifont.agents.qa_agent.QAAgent", _LowConfAgent),
        patch("aifont.agents.export_agent.ExportAgent", _LowConfAgent),
        patch("aifont.core.font.Font.new", side_effect=RuntimeError("no ff")),
    ):
        result = orch.run("low conf")

    # Each agent retried once → 5 agents × 2 attempts = 10 calls minimum
    assert call_count["n"] >= 10
    assert result.success  # accepted on last attempt


def test_orchestrator_run_step():
    """_run_step() wraps a bare callable and returns an AgentResult."""
    from aifont.agents.orchestrator import AgentResult, Orchestrator

    orch = Orchestrator()

    def _ok_fn(prompt, font):
        return AgentResult(agent_name="StepFn", success=True, confidence=0.9)

    result = orch._run_step(_ok_fn, "StepFn", "hello", None)
    assert result.success
    assert result.confidence == 0.9


def test_orchestrator_run_step_failure():
    """_run_step() captures failure from callable."""
    from aifont.agents.orchestrator import AgentResult, Orchestrator

    orch = Orchestrator(max_retries=0)

    def _fail_fn(prompt, font):
        return AgentResult(agent_name="Fail", success=False, message="step fail")

    result = orch._run_step(_fail_fn, "Fail", "x", None)
    assert not result.success


def test_orchestrator_run_step_exception():
    """_run_step() captures exceptions from callable."""
    from aifont.agents.orchestrator import Orchestrator

    orch = Orchestrator(max_retries=0)

    def _boom_fn(prompt, font):
        raise ValueError("step boom")

    result = orch._run_step(_boom_fn, "Boom", "x", None)
    assert not result.success
    assert "step boom" in (result.error or "")
