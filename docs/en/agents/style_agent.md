# Style Agent

Transfers visual style between fonts.

## Class Reference

::: aifont.agents.style_agent.StyleAgent

## Usage

```python
from aifont import Font
from aifont.agents.style_agent import StyleAgent

source = Font.open("ReferenceStyle.otf")
target = Font.open("TargetFont.sfd")

agent = StyleAgent(source_font=source)
result = agent.run("match the style", target)
result.save("Styled.otf")
```
