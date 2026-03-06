# Contour

Utilitaires de manipulation de courbes de Bézier et de chemins.

## Référence des fonctions

::: aifont.core.contour.simplify

::: aifont.core.contour.remove_overlap

::: aifont.core.contour.transform

::: aifont.core.contour.reverse_direction

## Exemples d'utilisation

### Supprimer les superpositions

```python
from aifont import Font
from aifont.core.contour import remove_overlap

font = Font.open("MaPolice.otf")
for glyph in font.glyphs:
    remove_overlap(glyph)
```

### Mise à l'échelle d'un glyphe à 80%

```python
from aifont.core.contour import transform

# [xx, xy, yx, yy, dx, dy]
transform(glyph, [0.8, 0, 0, 0.8, 0, 0])
```
