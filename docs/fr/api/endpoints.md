# Points de terminaison de l'API

## Polices

### `POST /fonts/analyze`

Analyser un fichier de police téléversé.

**Requête** (multipart/form-data) :
- `file` : Fichier de police OTF ou TTF

**Réponse** :
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

**Exemple** :
```bash
curl -X POST http://localhost:8000/fonts/analyze \
  -F "file=@MaPolice.otf"
```

---

### `POST /fonts/generate`

Générer une police à partir d'une invite en langage naturel.

**Requête** (JSON) :
```json
{
  "prompt": "Créer une police sans-serif géométrique en gras",
  "family_name": "PolicéGénérée"
}
```

---

### `POST /fonts/export`

Exporter une police dans le format spécifié.

**Requête** (multipart/form-data) :
- `file` : Fichier de police à convertir
- `format` : Format cible (`otf`, `ttf`, `woff2`)

**Exemple** :
```bash
curl -X POST "http://localhost:8000/fonts/export?format=woff2" \
  -F "file=@MaPolice.ttf" \
  --output MaPolice.woff2
```
