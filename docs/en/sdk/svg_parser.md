# SVG Parser

Import SVG files as font glyphs.

## Function Reference

::: aifont.core.svg_parser.svg_to_glyph

## Usage Examples

### Import a single SVG

```python
from aifont import Font
from aifont.core.svg_parser import svg_to_glyph

font = Font.new("IconFont")
svg_to_glyph("icon-star.svg", font, unicode_point=0xE001)
font.save("IconFont.otf")
```

### Batch import a folder of SVGs

```python
from pathlib import Path
from aifont import Font
from aifont.core.svg_parser import svg_to_glyph

font = Font.new("IconSet")
base_codepoint = 0xE000

for i, svg_file in enumerate(sorted(Path("icons/").glob("*.svg"))):
    svg_to_glyph(svg_file, font, unicode_point=base_codepoint + i)

font.save("IconSet.otf")
```
