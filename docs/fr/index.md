# AIFont

**SDK Python de création de polices assistée par IA, construit sur FontForge**

AIFont est un SDK Python et un système multi-agents qui permet la création, la modification et l'analyse intelligentes de polices de caractères. Il s'appuie sur [FontForge](https://fontforge.org) — fournissant une API Python claire et idiomatique au-dessus du plus puissant éditeur de polices open source au monde.

## Fonctionnalités clés

- 🔤 **SDK Pythonique** — wrappers haut niveau autour des liaisons Python de FontForge
- 🤖 **Agents IA** — pipeline multi-agents pour la conception automatisée de polices
- 📐 **Métriques intelligentes** — optimisation automatique de l'espacement et du crénage
- 🔍 **Analyse de polices** — rapports qualité avec suggestions concrètes
- 🌐 **API REST** — API FastAPI avec documentation Swagger interactive
- 📦 **Export multi-format** — OTF, TTF, WOFF2, Variable Fonts

## Exemple rapide

```python
from aifont import Font

# Ouvrir une police existante
font = Font.open("MaPolice.otf")
print(font.metadata.family_name)  # MaPolice

# Parcourir les glyphes
for glyph in font.glyphs:
    print(glyph.name, glyph.width)

# Exporter en WOFF2
from aifont.core.export import export_woff2
export_woff2(font, "MaPolice.woff2")
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   SDK AIFont                         │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │  Agents  │  │   API    │  │    SDK Core        │ │
│  │   (IA)   │  │(FastAPI) │  │ (wrappers FontForge)│ │
│  └────┬─────┘  └────┬─────┘  └────────┬───────────┘ │
│       └─────────────┴─────────────────┘              │
│                      ↓                               │
│            Liaisons Python de FontForge              │
│                      ↓                               │
│          Moteur FontForge (non modifié)              │
└─────────────────────────────────────────────────────┘
```

!!! note "Contrainte d'architecture"
    FontForge est le moteur sous-jacent — AIFont **ne modifie pas** le code source de FontForge.
    Toutes les opérations passent par `import fontforge`.

## Installation

```bash
pip install aifont
```

Ou depuis les sources :

```bash
git clone https://github.com/lamallamadel/fontforge
cd fontforge
pip install -e ".[docs]"
```

## Étapes suivantes

- [Guide de démarrage rapide](quickstart.md) — opérationnel en 5 minutes
- [Référence SDK](sdk/font.md) — documentation API complète
- [API REST](api/overview.md) — API HTTP avec interface Swagger
