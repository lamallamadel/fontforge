# Exemples

## Créer une police d'icônes web à partir de SVGs

```python
from pathlib import Path
from aifont import Font
from aifont.core.svg_parser import svg_to_glyph
from aifont.core.export import export_woff2

# Créer une nouvelle police d'icônes
font = Font.new("MesIcones")

# Importer tous les SVGs d'un dossier
base_codepoint = 0xE000
for i, svg_path in enumerate(sorted(Path("icones/").glob("*.svg"))):
    svg_to_glyph(svg_path, font, unicode_point=base_codepoint + i)

# Exporter en WOFF2
export_woff2(font, "dist/MesIcones.woff2")
print(f"Police d'icônes avec {len(font.glyphs)} glyphes exportée !")
```

---

## Analyser et corriger une police

```python
from aifont import Font
from aifont.core.analyzer import analyze
from aifont.core.contour import remove_overlap, simplify

font = Font.open("PoliceBrouillon.ttf")
rapport = analyze(font)
print(rapport.summary())

# Corriger tous les glyphes problématiques
for probleme in rapport.issues:
    if probleme.issue_type in ("open_contour", "validation"):
        glyph = next(g for g in font.glyphs if g.name == probleme.glyph_name)
        remove_overlap(glyph)
        simplify(glyph, threshold=1.5)

rapport2 = analyze(font)
print(f"Score amélioré de {rapport.score:.0f} à {rapport2.score:.0f}")
font.save("PoliceCorrégée.ttf")
```

---

## Générer une police avec le pipeline IA

```python
from aifont.agents import Orchestrator
from aifont.core.export import export_otf, export_woff2
from pathlib import Path

orch = Orchestrator()
font = orch.run("Créer une sans-serif minimaliste aux proportions géométriques")

Path("dist/").mkdir(exist_ok=True)
export_otf(font, "dist/PolicéGénérée.otf")
export_woff2(font, "dist/PolicéGénérée.woff2")
print("Police générée et exportée !")
```
