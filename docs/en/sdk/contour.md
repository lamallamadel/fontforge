# Contour

Bézier curve and path manipulation utilities.

## Function Reference

::: aifont.core.contour.simplify

::: aifont.core.contour.remove_overlap

::: aifont.core.contour.transform

::: aifont.core.contour.reverse_direction

## Usage Examples

### Remove overlapping paths

```python
from aifont import Font
from aifont.core.contour import remove_overlap

font = Font.open("MyFont.otf")
for glyph in font.glyphs:
    remove_overlap(glyph)
```

### Scale a glyph by 80%

```python
from aifont.core.contour import transform

# [xx, xy, yx, yy, dx, dy]
transform(glyph, [0.8, 0, 0, 0.8, 0, 0])
```

### Simplify paths

```python
from aifont.core.contour import simplify

simplify(glyph, threshold=2.0)
```
