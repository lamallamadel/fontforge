# AIFont

**AI-powered font design SDK built on FontForge**

AIFont is a Python SDK and multi-agent system that enables intelligent font creation, modification, and analysis. It wraps [FontForge](https://fontforge.org) — providing a clean, Pythonic API on top of the world's most powerful open-source font editor.

## Key Features

- 🔤 **Pythonic SDK** — high-level wrappers around FontForge's Python bindings
- 🤖 **AI Agents** — multi-agent pipeline for automated font design
- 📐 **Smart Metrics** — automatic spacing and kerning optimisation
- 🔍 **Font Analysis** — quality reports with actionable suggestions
- 🌐 **REST API** — FastAPI-based API with interactive Swagger docs
- 📦 **Multi-format export** — OTF, TTF, WOFF2, Variable Fonts

## Quick Example

```python
from aifont import Font

# Open an existing font
font = Font.open("MyFont.otf")
print(font.metadata.family_name)  # MyFont

# Inspect glyphs
for glyph in font.glyphs:
    print(glyph.name, glyph.width)

# Save as WOFF2
from aifont.core.export import export_woff2
export_woff2(font, "MyFont.woff2")
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   AIFont SDK                         │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │  Agents  │  │  API     │  │  Core SDK          │ │
│  │ (AI)     │  │ (FastAPI)│  │  (FontForge wraps) │ │
│  └────┬─────┘  └────┬─────┘  └────────┬───────────┘ │
│       └─────────────┴─────────────────┘              │
│                      ↓                               │
│              fontforge Python bindings               │
│                      ↓                               │
│              FontForge Engine (frozen)               │
└─────────────────────────────────────────────────────┘
```

!!! note "Architecture Constraint"
    FontForge is the underlying engine — AIFont does **not** modify FontForge source code.
    All operations go through `import fontforge`.

## Installation

```bash
pip install aifont
```

Or from source:

```bash
git clone https://github.com/lamallamadel/fontforge
cd fontforge
pip install -e ".[docs]"
```

## Next Steps

- [Quick Start Guide](quickstart.md) — get up and running in 5 minutes
- [SDK Reference](sdk/font.md) — complete API documentation
- [REST API](api/overview.md) — HTTP API with Swagger UI
