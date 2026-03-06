# Export Agent

Intelligent font export with format-specific optimisation.

## Class Reference

::: aifont.agents.export_agent.ExportAgent

## Use-case Keywords

| Keyword | Formats |
|---|---|
| `web` | WOFF2 |
| `print` | OTF |
| `app` | TTF + OTF |
| `variable` | TTF |

## Usage

```python
from aifont import Font
from aifont.agents.export_agent import ExportAgent

font = Font.open("MyFont.sfd")
agent = ExportAgent(output_dir="dist/")
agent.run("web font for mobile app", font)
# Creates dist/MyFont.woff2
```
