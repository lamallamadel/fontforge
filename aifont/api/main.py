"""FastAPI application for the AIFont REST API."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AIFont API",
    description="REST API for AI-powered font generation and analysis",
    version="0.1.0",
)

# Restrict CORS to explicitly configured origins.
# In production set CORS_ORIGINS to a comma-separated list, e.g.:
#   CORS_ORIGINS=https://app.example.com,https://admin.example.com
_cors_origins_raw = os.getenv("CORS_ORIGINS", "")
cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"message": "AIFont API", "version": "0.1.0"}
