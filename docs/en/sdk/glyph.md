# Glyph

The `Glyph` class wraps a FontForge glyph object, providing access to outlines, metrics, and transformations.

## Class Reference

::: aifont.core.glyph.Glyph

## Usage Examples

### Access glyphs

```python
from aifont import Font

font = Font.open("MyFont.otf")
glyph_A = next(g for g in font.glyphs if g.name == "A")
print(glyph_A.width, glyph_A.unicode)
```

### Modify metrics

```python
glyph_A.set_width(600)
glyph_A.set_left_side_bearing(50)
```

### Copy from another glyph

```python
glyph_a = next(g for g in font.glyphs if g.name == "a")
glyph_A.copy_from(glyph_a)
```
