# AI Agents

AIFont includes a multi-agent pipeline for automated font design and processing.

## Architecture

```
User Prompt
     │
     ▼
┌─────────────────┐
│  Orchestrator   │  ← Central coordinator
└────────┬────────┘
         │
    ┌────▼────┐
    │ Design  │  ← Generates glyph outlines from prompts
    └────┬────┘
         │
    ┌────▼────┐
    │  Style  │  ← Applies consistent visual style
    └────┬────┘
         │
    ┌────▼────┐
    │ Metrics │  ← Optimises spacing and kerning
    └────┬────┘
         │
    ┌────▼────┐
    │   QA    │  ← Validates and auto-fixes
    └────┬────┘
         │
    ┌────▼────┐
    │ Export  │  ← Generates output files
    └─────────┘
```

## Available Agents

| Agent | Module | Responsibility |
|---|---|---|
| `Orchestrator` | `aifont.agents.orchestrator` | Coordinates the pipeline |
| `DesignAgent` | `aifont.agents.design_agent` | Glyph generation |
| `StyleAgent` | `aifont.agents.style_agent` | Visual style transfer |
| `MetricsAgent` | `aifont.agents.metrics_agent` | Spacing & kerning |
| `QAAgent` | `aifont.agents.qa_agent` | Quality assurance |
| `ExportAgent` | `aifont.agents.export_agent` | Multi-format export |

## Quick Start

```python
from aifont.agents import Orchestrator

orch = Orchestrator()
font = orch.run("Create a bold geometric sans-serif")
font.save("output.otf")
```
