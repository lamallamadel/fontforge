# Design Agent

Generates glyph outlines from natural language prompts.

## Class Reference

::: aifont.agents.design_agent.DesignAgent

## How It Works

1. Receives a text prompt (e.g. *"bold geometric A with flat terminals"*)
2. Sends the prompt to an LLM to generate SVG path descriptions
3. Uses `aifont.core.svg_parser` to convert SVG into FontForge contours
4. Injects the contours into the target font

## Usage

```python
from aifont import Font
from aifont.agents.design_agent import DesignAgent

agent = DesignAgent()
font = Font.new("MyFont")
font = agent.run("Bold geometric uppercase letters", font)
```
