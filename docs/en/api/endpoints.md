# API Endpoints

## Font Endpoints

### `POST /fonts/analyze`

Analyze an uploaded font file.

**Request** (multipart/form-data):
- `file`: OTF or TTF font file

**Response**:
```json
{
  "glyph_count": 256,
  "missing_unicodes": [],
  "kern_pair_count": 142,
  "error_count": 0,
  "warning_count": 3,
  "score": 97.0,
  "summary": "FontReport: 256 glyphs, 0 errors, 3 warnings, score=97.0/100"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/fonts/analyze \
  -F "file=@MyFont.otf"
```

---

### `POST /fonts/generate`

Generate a font from a natural language prompt.

**Request** (JSON):
```json
{
  "prompt": "Create a bold geometric sans-serif",
  "family_name": "GeneratedFont"
}
```

**Response**:
```json
{
  "status": "success",
  "family_name": "GeneratedFont",
  "prompt": "Create a bold geometric sans-serif"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/fonts/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a bold geometric sans-serif"}'
```

---

### `POST /fonts/export`

Export an uploaded font in a specific format.

**Request** (multipart/form-data):
- `file`: Font file to convert
- `format`: Target format (`otf`, `ttf`, `woff2`)

**Response**: Binary font file download.

**Example**:
```bash
curl -X POST "http://localhost:8000/fonts/export?format=woff2" \
  -F "file=@MyFont.ttf" \
  --output MyFont.woff2
```
