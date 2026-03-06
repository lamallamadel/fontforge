# Font (Police)

La classe `Font` est le point d'entrée principal pour travailler avec des fichiers de polices dans AIFont.

## Référence de classe

::: aifont.core.font.Font

::: aifont.core.font.FontMetadata

## Exemples d'utilisation

### Ouvrir une police existante

```python
from aifont import Font

font = Font.open("MaPolice.otf")
print(font.metadata.family_name)
```

### Créer une nouvelle police

```python
font = Font.new("MaNouvellePolice")
```

### Mettre à jour les métadonnées

```python
from aifont.core.font import FontMetadata

font.metadata = FontMetadata(
    family_name="MaPolice",
    full_name="MaPolice Regular",
    weight="Regular",
    version="1.0",
)
```

### Sauvegarder / exporter

```python
font.save("sortie.otf")   # OpenType
font.save("sortie.ttf")   # TrueType
```
