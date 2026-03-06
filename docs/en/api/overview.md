# REST API Overview

AIFont provides a FastAPI-based REST API that exposes the SDK and agents over HTTP.

## Starting the Server

```bash
# Install dependencies
pip install aifont[api]

# Start the development server
uvicorn aifont.api.main:app --reload --port 8000
```

## Interactive Documentation

Once running, visit:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

## Authentication

!!! info "Coming Soon"
    Authentication (API keys / OAuth2) is planned for a future release.

## Rate Limiting

The API does not currently enforce rate limits. Add a reverse proxy (nginx, Caddy) for production deployments.

## Base URL

| Environment | Base URL |
|---|---|
| Local dev | `http://localhost:8000` |
| Docker | `http://api:8000` |
| Production | `https://api.aifont.io` |
