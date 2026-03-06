# QA Agent

Validates font quality and auto-fixes common issues.

## Class Reference

::: aifont.agents.qa_agent.QAAgent

::: aifont.agents.qa_agent.QAResult

## Usage

```python
from aifont import Font
from aifont.agents.qa_agent import QAAgent

font = Font.open("MyFont.sfd")
agent = QAAgent()
font = agent.run("", font)

result = agent.last_result
print(result.report.summary())
print(f"Fixes applied: {result.fixes_applied}")
```
