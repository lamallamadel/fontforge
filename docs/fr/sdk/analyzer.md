# Analyseur

Analyse et diagnostic de polices.

## Référence de classe

::: aifont.core.analyzer.FontReport

::: aifont.core.analyzer.GlyphIssue

## Référence des fonctions

::: aifont.core.analyzer.analyze

## Exemples d'utilisation

### Analyse basique

```python
from aifont import Font
from aifont.core.analyzer import analyze

font = Font.open("MaPolice.otf")
rapport = analyze(font)

print(rapport.summary())
print(f"Score : {rapport.score}/100")
print(f"Erreurs : {rapport.error_count}")
print(f"Avertissements : {rapport.warning_count}")
```
