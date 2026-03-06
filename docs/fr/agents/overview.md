# Agents IA

AIFont inclut un pipeline multi-agents pour la conception et le traitement automatisés de polices.

## Architecture

```
Invite utilisateur
        │
        ▼
┌─────────────────┐
│  Orchestrateur  │  ← Coordinateur central
└────────┬────────┘
         │
    ┌────▼────┐
    │ Design  │  ← Génère les contours depuis les invites
    └────┬────┘
         │
    ┌────▼────┐
    │  Style  │  ← Applique un style visuel cohérent
    └────┬────┘
         │
    ┌────▼────┐
    │Métriques│  ← Optimise espacement et crénage
    └────┬────┘
         │
    ┌────▼────┐
    │   QA    │  ← Valide et corrige automatiquement
    └────┬────┘
         │
    ┌────▼────┐
    │ Export  │  ← Génère les fichiers de sortie
    └─────────┘
```

## Agents disponibles

| Agent | Module | Responsabilité |
|---|---|---|
| `Orchestrator` | `aifont.agents.orchestrator` | Coordonne le pipeline |
| `DesignAgent` | `aifont.agents.design_agent` | Génération de glyphes |
| `StyleAgent` | `aifont.agents.style_agent` | Transfert de style visuel |
| `MetricsAgent` | `aifont.agents.metrics_agent` | Espacement et crénage |
| `QAAgent` | `aifont.agents.qa_agent` | Assurance qualité |
| `ExportAgent` | `aifont.agents.export_agent` | Export multi-format |

## Démarrage rapide

```python
from aifont.agents import Orchestrator

orch = Orchestrator()
font = orch.run("Créer une police sans-serif géométrique en gras")
font.save("sortie.otf")
```
