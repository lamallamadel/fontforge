# Export

Générer des sorties OTF, TTF, WOFF2 et Variable Font.

## Référence des fonctions

::: aifont.core.export.export_otf

::: aifont.core.export.export_ttf

::: aifont.core.export.export_woff2

::: aifont.core.export.export_variable

## Exemples d'utilisation

### Exporter tous les formats

```python
from aifont import Font
from aifont.core import export

font = Font.open("MaPolice.sfd")

export.export_otf(font, "dist/MaPolice.otf")
export.export_ttf(font, "dist/MaPolice.ttf")
export.export_woff2(font, "dist/MaPolice.woff2")
```
