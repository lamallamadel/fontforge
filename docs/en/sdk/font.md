# Font

The `Font` class is the primary entry point for working with font files in AIFont.

## Class Reference

::: aifont.core.font.Font
    options:
      show_source: true

::: aifont.core.font.FontMetadata

## Usage Examples

### Open an existing font

```python
from aifont import Font

font = Font.open("MyFont.otf")
print(font.metadata.family_name)
```

### Create a new font

```python
font = Font.new("MyNewFont")
```

### Update metadata

```python
from aifont.core.font import FontMetadata

font.metadata = FontMetadata(
    family_name="MyFont",
    full_name="MyFont Regular",
    weight="Regular",
    version="1.0",
)
```

### Save / export

```python
font.save("output.otf")        # OpenType
font.save("output.ttf")        # TrueType
```
