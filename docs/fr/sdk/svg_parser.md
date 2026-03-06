# Parseur SVG

Importer des fichiers SVG comme glyphes de police.

## Référence des fonctions

::: aifont.core.svg_parser.svg_to_glyph

## Exemples d'utilisation

### Importer un SVG unique

```python
from aifont import Font
from aifont.core.svg_parser import svg_to_glyph

font = Font.new("PoliceIcones")
svg_to_glyph("icone-etoile.svg", font, unicode_point=0xE001)
font.save("PoliceIcones.otf")
```

### Import en lot d'un dossier de SVGs

```python
from pathlib import Path
from aifont import Font
from aifont.core.svg_parser import svg_to_glyph

font = Font.new("SetIcones")
base_codepoint = 0xE000

for i, svg_file in enumerate(sorted(Path("icones/").glob("*.svg"))):
    svg_to_glyph(svg_file, font, unicode_point=base_codepoint + i)

font.save("SetIcones.otf")
```
