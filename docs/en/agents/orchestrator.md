# Orchestrator

The central multi-agent coordinator.

## Class Reference

::: aifont.agents.orchestrator.Orchestrator

## Usage Examples

### Basic usage

```python
from aifont.agents import Orchestrator

orch = Orchestrator()
font = orch.run("Create a bold geometric sans-serif")
font.save("GeneratedFont.otf")
```

### Modify an existing font

```python
from aifont import Font
from aifont.agents import Orchestrator

base_font = Font.open("BaseFont.otf")
orch = Orchestrator()
modified = orch.run("Make it bolder and add more contrast", font=base_font)
modified.save("ModifiedFont.otf")
```
