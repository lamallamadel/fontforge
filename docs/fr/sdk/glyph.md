# Glyph (Glyphe)

La classe `Glyph` encapsule un objet glyphe FontForge, donnant accès aux contours, métriques et transformations.

## Référence de classe

::: aifont.core.glyph.Glyph

## Exemples d'utilisation

### Accéder aux glyphes

```python
from aifont import Font

font = Font.open("MaPolice.otf")
glyph_A = next(g for g in font.glyphs if g.name == "A")
print(glyph_A.width, glyph_A.unicode)
```

### Modifier les métriques

```python
glyph_A.set_width(600)
glyph_A.set_left_side_bearing(50)
```
