# Vue d'ensemble de l'API REST

AIFont fournit une API REST basée sur FastAPI qui expose le SDK et les agents via HTTP.

## Démarrer le serveur

```bash
# Installer les dépendances
pip install aifont[api]

# Démarrer le serveur de développement
uvicorn aifont.api.main:app --reload --port 8000
```

## Documentation interactive

Une fois démarré, visitez :

- **Swagger UI** : [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc** : [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **JSON OpenAPI** : [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

## URL de base

| Environnement | URL de base |
|---|---|
| Développement local | `http://localhost:8000` |
| Docker | `http://api:8000` |
| Production | `https://api.aifont.io` |
