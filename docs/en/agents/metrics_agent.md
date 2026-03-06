# Metrics Agent

Auto-optimizes spacing and kerning.

## Class Reference

::: aifont.agents.metrics_agent.MetricsAgent

## Spacing Presets

| Keyword in prompt | Side-bearing ratio |
|---|---|
| `tight` | 8% of em |
| `normal` | 12% of em |
| `airy` | 18% of em |
| `display` | 10% of em |

## Usage

```python
from aifont import Font
from aifont.agents.metrics_agent import MetricsAgent

font = Font.open("MyFont.sfd")
agent = MetricsAgent()
font = agent.run("airy spacing for a poster font", font)
font.save("MyFont-spaced.otf")
```
