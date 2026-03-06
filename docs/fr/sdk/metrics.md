# Métriques

Utilitaires de crénage et d'espacement.

## Référence des fonctions

::: aifont.core.metrics.get_kern_pairs

::: aifont.core.metrics.set_kern

::: aifont.core.metrics.auto_space

## Exemples d'utilisation

### Lire les paires de crénage

```python
from aifont import Font
from aifont.core.metrics import get_kern_pairs

font = Font.open("MaPolice.otf")
pairs = get_kern_pairs(font)
for gauche, droite, valeur in pairs[:10]:
    print(f"  {gauche} + {droite} = {valeur}")
```

### Définir un crénage

```python
from aifont.core.metrics import set_kern

set_kern(font, "A", "V", -50)
```
