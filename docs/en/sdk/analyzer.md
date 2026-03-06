# Analyzer

Font analysis and diagnostics.

## Class Reference

::: aifont.core.analyzer.FontReport

::: aifont.core.analyzer.GlyphIssue

## Function Reference

::: aifont.core.analyzer.analyze

## Usage Examples

### Basic analysis

```python
from aifont import Font
from aifont.core.analyzer import analyze

font = Font.open("MyFont.otf")
report = analyze(font)

print(report.summary())
print(f"Score: {report.score}/100")
print(f"Errors: {report.error_count}")
print(f"Warnings: {report.warning_count}")
```

### Iterate over issues

```python
for issue in report.issues:
    severity_icon = "🔴" if issue.severity == "error" else "🟡"
    print(f"  {severity_icon} [{issue.issue_type}] {issue.glyph_name}: {issue.description}")
```

### Check if font is ready to publish

```python
if report.has_errors:
    print("Font has errors — fix before publishing!")
elif report.score >= 90:
    print("Font quality is excellent ✓")
```
