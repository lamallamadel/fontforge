# Examples

## Build a Web Icon Font from SVGs

```python
from pathlib import Path
from aifont import Font
from aifont.core.svg_parser import svg_to_glyph
from aifont.core.export import export_woff2

# Create a new icon font
font = Font.new("MyIcons")

# Import all SVGs from a folder
base_codepoint = 0xE000
for i, svg_path in enumerate(sorted(Path("icons/").glob("*.svg"))):
    svg_to_glyph(svg_path, font, unicode_point=base_codepoint + i)

# Export as WOFF2
export_woff2(font, "dist/MyIcons.woff2")
print(f"Icon font with {len(font.glyphs)} glyphs exported!")
```

---

## Analyse and Fix a Font

```python
from aifont import Font
from aifont.core.analyzer import analyze
from aifont.core.contour import remove_overlap, simplify

font = Font.open("RoughFont.ttf")
report = analyze(font)
print(report.summary())

# Fix all glyphs with issues
for issue in report.issues:
    if issue.issue_type in ("open_contour", "validation"):
        glyph = next(g for g in font.glyphs if g.name == issue.glyph_name)
        remove_overlap(glyph)
        simplify(glyph, threshold=1.5)

# Re-analyse
report2 = analyze(font)
print(f"Score improved from {report.score:.0f} to {report2.score:.0f}")
font.save("FixedFont.ttf")
```

---

## Generate a Font with the AI Pipeline

```python
from aifont.agents import Orchestrator
from aifont.core.export import export_otf, export_woff2
from pathlib import Path

# Run the full AI pipeline
orch = Orchestrator()
font = orch.run("Create a minimalist sans-serif with geometric proportions")

# Export multiple formats
Path("dist/").mkdir(exist_ok=True)
export_otf(font, "dist/GeneratedFont.otf")
export_woff2(font, "dist/GeneratedFont.woff2")
print("Font generated and exported!")
```

---

## Batch Kern Adjustment

```python
from aifont import Font
from aifont.core.metrics import get_kern_pairs, set_kern

font = Font.open("MyFont.otf")
pairs = get_kern_pairs(font)

# Tighten all AV-type pairs by 10 units
av_pairs = [(l, r, v) for l, r, v in pairs if l in "AVTY" and r in "AVTY"]
for left, right, value in av_pairs:
    set_kern(font, left, right, value - 10)

font.save("MyFont-kerned.otf")
```
