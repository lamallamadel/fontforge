# Guide de démarrage rapide

Opérationnel avec AIFont en moins de 5 minutes.

## Prérequis

- Python 3.10+
- FontForge avec les liaisons Python installées

```bash
# Installer FontForge (Ubuntu / Debian)
sudo apt install fontforge python3-fontforge

# Installer AIFont
pip install aifont
```

## Étape 1 — Ouvrir une police

```python
from aifont import Font

font = Font.open("chemin/vers/MaPolice.otf")
print(f"Famille : {font.metadata.family_name}")
print(f"Glyphes : {len(font.glyphs)}")
```

## Étape 2 — Inspecter les glyphes

```python
for glyph in font.glyphs[:5]:
    print(f"  {glyph.name:20s}  largeur={glyph.width}  unicode={glyph.unicode}")
```

## Étape 3 — Analyser la police

```python
from aifont.core.analyzer import analyze

rapport = analyze(font)
print(rapport.summary())
# FontReport: 256 glyphs, 0 errors, 3 warnings, score=97.0/100

for probleme in rapport.issues:
    print(f"  [{probleme.severity.upper()}] {probleme.glyph_name}: {probleme.description}")
```

## Étape 4 — Corriger et exporter

```python
from aifont.core.contour import remove_overlap
from aifont.core.export import export_woff2

# Corriger les chemins superposés
for glyph in font.glyphs:
    remove_overlap(glyph)

# Exporter en WOFF2 pour le web
export_woff2(font, "MaPolice.woff2")
print("Terminé ! ✓")
```

## Étape 5 — Utiliser le pipeline d'agents IA

```python
from aifont.agents import Orchestrator

orch = Orchestrator()
font = orch.run("Créer une police sans-serif géométrique moderne")
font.save("PolicéGénérée.otf")
```

## Étape 6 — Démarrer l'API REST

```bash
uvicorn aifont.api.main:app --reload
```

Puis ouvrir [http://localhost:8000/docs](http://localhost:8000/docs) pour l'interface Swagger interactive.

---

!!! tip "Et ensuite ?"
    - Lire la [Référence SDK](sdk/font.md) pour la documentation API complète
    - Explorer les [Agents](agents/overview.md) pour créer des pipelines personnalisés
    - Déployer en production avec l'[API REST](api/overview.md)
