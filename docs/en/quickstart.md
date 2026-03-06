# Quick Start Guide

Get up and running with AIFont in under 5 minutes.

## Prerequisites

- Python 3.10+
- FontForge with Python bindings installed

```bash
# Install FontForge (Ubuntu / Debian)
sudo apt install fontforge python3-fontforge

# Install AIFont
pip install aifont
```

## Step 1 — Open a Font

```python
from aifont import Font

font = Font.open("path/to/MyFont.otf")
print(f"Family: {font.metadata.family_name}")
print(f"Glyphs: {len(font.glyphs)}")
```

## Step 2 — Inspect Glyphs

```python
for glyph in font.glyphs[:5]:
    print(f"  {glyph.name:20s}  width={glyph.width}  unicode={glyph.unicode}")
```

## Step 3 — Analyse the Font

```python
from aifont.core.analyzer import analyze

report = analyze(font)
print(report.summary())
# FontReport: 256 glyphs, 0 errors, 3 warnings, score=97.0/100

for issue in report.issues:
    print(f"  [{issue.severity.upper()}] {issue.glyph_name}: {issue.description}")
```

## Step 4 — Fix and Export

```python
from aifont.core.contour import remove_overlap
from aifont.core.export import export_woff2

# Fix overlapping paths
for glyph in font.glyphs:
    remove_overlap(glyph)

# Export as WOFF2 for the web
export_woff2(font, "MyFont.woff2")
print("Done! ✓")
```

## Step 5 — Use the AI Agent Pipeline

```python
from aifont.agents import Orchestrator

orch = Orchestrator()
font = orch.run("Create a modern geometric sans-serif font")
font.save("GeneratedFont.otf")
```

## Step 6 — Start the REST API

```bash
uvicorn aifont.api.main:app --reload
```

Then open [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive Swagger UI.

---

!!! tip "What's next?"
    - Read the full [SDK Reference](sdk/font.md) for detailed API documentation
    - Explore [Agents](agents/overview.md) to build custom pipelines
    - Deploy to production with the [REST API](api/overview.md)
