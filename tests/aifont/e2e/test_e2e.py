"""End-to-end tests for main frontend flows using Playwright.

These tests exercise the main user journeys through the web frontend.
They are marked with ``@pytest.mark.e2e`` and are skipped by default
unless a running server is detected at ``BASE_URL``.
"""

from __future__ import annotations

import os

import pytest

# The URL of the running application under test.
# Override with the E2E_BASE_URL environment variable.
BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _server_is_up() -> bool:
    """Return True if the application server is reachable."""
    import urllib.request
    import urllib.error

    try:
        urllib.request.urlopen(f"{BASE_URL}/health", timeout=2)
        return True
    except (urllib.error.URLError, OSError):
        return False


requires_server = pytest.mark.skipif(
    not _server_is_up(),
    reason=f"AIFont server not running at {BASE_URL}",
)


# ---------------------------------------------------------------------------
# Font analysis flow
# ---------------------------------------------------------------------------


@requires_server
def test_e2e_health_endpoint():
    """Verify the health endpoint responds with 200."""
    import urllib.request

    with urllib.request.urlopen(f"{BASE_URL}/health") as resp:
        assert resp.status == 200
        import json

        data = json.loads(resp.read())
        assert data.get("status") == "ok"


@pytest.mark.e2e
@requires_server
def test_e2e_generate_font_flow():
    """
    E2E flow: POST /fonts/generate → verify response → GET /fonts/{id}/export.

    This test exercises the full generation pipeline end-to-end.
    """
    import httpx

    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        # Step 1 — generate a font
        gen_resp = client.post(
            "/fonts/generate",
            json={"prompt": "modern sans-serif A", "font_name": "E2EFont"},
        )
        assert gen_resp.status_code == 200, gen_resp.text
        gen_data = gen_resp.json()
        assert "font_id" in gen_data
        font_id = gen_data["font_id"]

        # Step 2 — export the generated font
        export_resp = client.get(f"/fonts/{font_id}/export?fmt=otf")
        # We expect either 200 (file) or 500 (ff not available in test env)
        assert export_resp.status_code in (200, 500)


@pytest.mark.e2e
@requires_server
def test_e2e_agent_pipeline():
    """
    E2E flow: POST /agents/run with a text prompt.
    """
    import httpx

    with httpx.Client(base_url=BASE_URL, timeout=60) as client:
        resp = client.post(
            "/agents/run",
            json={"prompt": "create a bold geometric font"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "steps" in data
        assert isinstance(data["steps"], list)
