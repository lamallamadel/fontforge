# Metrics

Kerning and spacing utilities.

## Function Reference

::: aifont.core.metrics.get_kern_pairs

::: aifont.core.metrics.set_kern

::: aifont.core.metrics.auto_space

## Usage Examples

### Read kerning pairs

```python
from aifont import Font
from aifont.core.metrics import get_kern_pairs

font = Font.open("MyFont.otf")
pairs = get_kern_pairs(font)
for left, right, value in pairs[:10]:
    print(f"  {left} + {right} = {value}")
```

### Set a kern pair

```python
from aifont.core.metrics import set_kern

set_kern(font, "A", "V", -50)
```

### Auto-space all glyphs

```python
from aifont.core.metrics import auto_space

auto_space(font, target_ratio=0.15)
```
