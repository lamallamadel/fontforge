"""AIFont FastAPI application entry point."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from aifont.auth.router import router as auth_router
from aifont.db import Base, engine

# ---------------------------------------------------------------------------
# Settings from environment variables
# ---------------------------------------------------------------------------

# Comma-separated list of allowed CORS origins.
# Example: ALLOWED_ORIGINS="https://app.example.com,https://www.example.com"
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS: list[str] = (
    [o.strip() for o in _raw_origins.split(",") if o.strip()]
    if _raw_origins
    else ["http://localhost:3000", "http://localhost:8000"]
)

# Comma-separated list of trusted hostnames (prevents HTTP Host header injection).
# Example: ALLOWED_HOSTS="api.example.com,www.example.com"
_raw_hosts = os.environ.get("ALLOWED_HOSTS", "")
ALLOWED_HOSTS: list[str] = (
    [h.strip() for h in _raw_hosts.split(",") if h.strip()]
    if _raw_hosts
    else ["localhost", "127.0.0.1"]
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create all database tables on startup (dev convenience)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="AIFont API",
    description="AI-powered font creation platform built on top of FontForge.",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Security middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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

# Prevent HTTP host header injection (OWASP A05)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS,
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth_router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"message": "AIFont API", "version": "0.1.0"}
