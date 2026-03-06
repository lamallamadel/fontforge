# Export

Generate OTF, TTF, WOFF2, and Variable Font outputs.

## Function Reference

::: aifont.core.export.export_otf

::: aifont.core.export.export_ttf

::: aifont.core.export.export_woff2

::: aifont.core.export.export_variable

## Usage Examples

### Export all formats

```python
from aifont import Font
from aifont.core import export

font = Font.open("MyFont.sfd")

export.export_otf(font, "dist/MyFont.otf")
export.export_ttf(font, "dist/MyFont.ttf")
export.export_woff2(font, "dist/MyFont.woff2")
```

### WOFF2 for web

```python
export.export_woff2(font, "static/fonts/MyFont.woff2")
```

Then reference in your CSS:

```css
@font-face {
  font-family: 'MyFont';
  src: url('fonts/MyFont.woff2') format('woff2');
}
```
