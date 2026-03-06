# Orchestrateur

Le coordinateur central multi-agents.

## Référence de classe

::: aifont.agents.orchestrator.Orchestrator

## Exemples d'utilisation

### Utilisation basique

```python
from aifont.agents import Orchestrator

orch = Orchestrator()
font = orch.run("Créer une police sans-serif géométrique en gras")
font.save("PolicéGénérée.otf")
```
