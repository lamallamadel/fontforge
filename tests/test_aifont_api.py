"""Integration tests for the AIFont FastAPI server.

These tests exercise all major API endpoints using an in-memory SQLite
database and a mocked Celery layer so that neither PostgreSQL nor Redis
nor a running Celery worker is required in CI.

Run with:
    pytest tests/test_aifont_api.py -v
"""

from __future__ import annotations

import io
import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# App / DB wiring for tests
# ---------------------------------------------------------------------------

# Use an in-memory SQLite DB instead of PostgreSQL
TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="function")
async def test_app() -> AsyncGenerator[FastAPI, None]:
    """Yield a FastAPI app instance wired to an in-memory SQLite DB."""
    import os

    # Point config at SQLite before importing the app so that the engine
    # is created with the test URL.
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["SECRET_KEY"] = "test-secret-key-for-ci"
    os.environ["CELERY_BROKER_URL"] = "memory://"
    os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"

    # Clear the cached settings so that env vars take effect.
    from aifont.api.config import get_settings

    get_settings.cache_clear()

    # Re-create the engine with the SQLite URL
    import aifont.api.database as _db_module

    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    # Override the engine and session factory
    _db_module.engine = test_engine
    _db_module.AsyncSessionLocal = TestSessionLocal

    # Create tables
    from aifont.api.database import Base

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Build the app *after* patching
    from aifont.api.main import create_app

    app = create_app()

    yield app

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Celery task mock helpers
# ---------------------------------------------------------------------------


def _mock_task(task_id: str = "fake-task-id") -> MagicMock:
    mock = MagicMock()
    mock.id = task_id
    return mock


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


# ---------------------------------------------------------------------------
# Auth — register & login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient) -> None:
    # Register
    resp = await client.post(
        "/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "s3cr3tpass"},
    )
    assert resp.status_code == 201
    user = resp.json()
    assert user["username"] == "alice"
    assert "id" in user

    # Login
    resp = await client.post(
        "/auth/login",
        json={"username": "alice", "password": "s3cr3tpass"},
    )
    assert resp.status_code == 200
    token_data = resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient) -> None:
    for _ in range(2):
        resp = await client.post(
            "/auth/register",
            json={"username": "bob", "email": "bob@example.com", "password": "password1"},
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    await client.post(
        "/auth/register",
        json={"username": "carol", "email": "carol@example.com", "password": "realpass1"},
    )
    resp = await client.post(
        "/auth/login",
        json={"username": "carol", "password": "wrongpass"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_token(client: AsyncClient, username: str = "testuser") -> str:
    await client.post(
        "/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": "password1"},
    )
    resp = await client.post(
        "/auth/login",
        json={"username": username, "password": "password1"},
    )
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Fonts — CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_font(client: AsyncClient) -> None:
    token = await _get_token(client, "user_create")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/fonts",
        json={"name": "My Font", "family": "Sans", "style": "Regular"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Font"
    assert data["family"] == "Sans"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_fonts(client: AsyncClient) -> None:
    token = await _get_token(client, "user_list")
    headers = {"Authorization": f"Bearer {token}"}

    # Create two fonts
    for name in ("Alpha", "Beta"):
        await client.post("/fonts", json={"name": name}, headers=headers)

    resp = await client.get("/fonts", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_get_font(client: AsyncClient) -> None:
    token = await _get_token(client, "user_get")
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post("/fonts", json={"name": "Gamma"}, headers=headers)
    font_id = create_resp.json()["id"]

    resp = await client.get(f"/fonts/{font_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == font_id


@pytest.mark.asyncio
async def test_update_font(client: AsyncClient) -> None:
    token = await _get_token(client, "user_update")
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post("/fonts", json={"name": "Delta"}, headers=headers)
    font_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/fonts/{font_id}",
        json={"name": "Delta Updated", "description": "Updated description"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Delta Updated"


@pytest.mark.asyncio
async def test_delete_font(client: AsyncClient) -> None:
    token = await _get_token(client, "user_delete")
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post("/fonts", json={"name": "Epsilon"}, headers=headers)
    font_id = create_resp.json()["id"]

    resp = await client.delete(f"/fonts/{font_id}", headers=headers)
    assert resp.status_code == 204

    # Should now return 404
    resp = await client.get(f"/fonts/{font_id}", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_font_not_found(client: AsyncClient) -> None:
    token = await _get_token(client, "user_nf")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get(f"/fonts/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_requires_authentication(client: AsyncClient) -> None:
    resp = await client.get("/fonts")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_font_name_validation(client: AsyncClient) -> None:
    token = await _get_token(client, "user_val")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post("/fonts", json={"name": "   "}, headers=headers)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Font search / filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_fonts_filter_by_name(client: AsyncClient) -> None:
    token = await _get_token(client, "user_filter")
    headers = {"Authorization": f"Bearer {token}"}

    for name in ("Roboto", "Raleway", "Open Sans"):
        await client.post("/fonts", json={"name": name}, headers=headers)

    resp = await client.get("/fonts?name=Roboto", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert all("Roboto" in item["name"] for item in data["items"])


# ---------------------------------------------------------------------------
# Font upload — invalid type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_invalid_extension(client: AsyncClient) -> None:
    token = await _get_token(client, "user_upload")
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post("/fonts", json={"name": "Uploader"}, headers=headers)
    font_id = create_resp.json()["id"]

    resp = await client.post(
        f"/fonts/{font_id}/upload",
        headers=headers,
        files={"file": ("bad_file.exe", io.BytesIO(b"fake"), "application/octet-stream")},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Generation — async task dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_font_dispatches_task(client: AsyncClient) -> None:
    token = await _get_token(client, "user_gen")
    headers = {"Authorization": f"Bearer {token}"}

    with patch(
        "aifont.api.routers.generation._generate_task.delay",
        return_value=_mock_task("gen-task-123"),
    ):
        resp = await client.post(
            "/fonts/generate",
            json={"prompt": "Create a bold geometric sans-serif"},
            headers=headers,
        )
    assert resp.status_code == 202
    data = resp.json()
    assert data["task_id"] == "gen-task-123"
    assert data["status"] == "pending"


# ---------------------------------------------------------------------------
# Task status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_task_status_pending(client: AsyncClient) -> None:
    token = await _get_token(client, "user_ts")
    headers = {"Authorization": f"Bearer {token}"}

    mock_result = MagicMock()
    mock_result.status = "PENDING"
    mock_result.successful.return_value = False
    mock_result.failed.return_value = False

    with patch("aifont.api.routers.generation.celery_app") as mock_celery:
        mock_celery.AsyncResult.return_value = mock_result
        resp = await client.get("/tasks/some-task-id", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_task_status_success(client: AsyncClient) -> None:
    token = await _get_token(client, "user_ts2")
    headers = {"Authorization": f"Bearer {token}"}

    mock_result = MagicMock()
    mock_result.status = "SUCCESS"
    mock_result.successful.return_value = True
    mock_result.failed.return_value = False
    mock_result.result = {"font_id": "abc", "status": "completed"}

    with patch("aifont.api.routers.generation.celery_app") as mock_celery:
        mock_celery.AsyncResult.return_value = mock_result
        resp = await client.get("/tasks/done-task-id", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["result"]["font_id"] == "abc"


# ---------------------------------------------------------------------------
# Agents — run endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_run_dispatches_task(client: AsyncClient) -> None:
    token = await _get_token(client, "user_agent")
    headers = {"Authorization": f"Bearer {token}"}

    with patch(
        "aifont.api.routers.agents._run_agent_task.delay",
        return_value=_mock_task("agent-task-456"),
    ):
        resp = await client.post(
            "/agents/run",
            json={"agent": "design", "prompt": "A geometric letter A"},
            headers=headers,
        )
    assert resp.status_code == 202
    data = resp.json()
    assert data["task_id"] == "agent-task-456"
    assert data["agent"] == "design"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_agent_run_invalid_agent(client: AsyncClient) -> None:
    token = await _get_token(client, "user_agent2")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/agents/run",
        json={"agent": "unknown_agent", "prompt": "test"},
        headers=headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# OpenAPI schema
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openapi_schema_accessible(client: AsyncClient) -> None:
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["info"]["title"] == "AIFont API"
    # Verify key paths exist in the schema
    paths = schema["paths"]
    assert "/health" in paths
    assert "/auth/register" in paths
    assert "/auth/login" in paths
    assert "/fonts" in paths
    assert "/fonts/generate" in paths
    assert "/agents/run" in paths
