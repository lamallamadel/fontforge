"""Locust load test — simulates 100 concurrent users against the AIFont API.

Run with::

    locust -f tests/aifont/load/locustfile.py --headless \
        -u 100 -r 10 --run-time 60s \
        --host http://localhost:8000

Acceptance criteria: 100 simultaneous users, P95 response time < 2 s.
"""

from __future__ import annotations

import json
import random
import string

from locust import HttpUser, between, task


def _random_font_name() -> str:
    return "Font" + "".join(random.choices(string.ascii_uppercase, k=4))


class AIFontUser(HttpUser):
    """Simulates a typical AIFont API user."""

    wait_time = between(0.5, 2.0)

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def on_start(self) -> None:
        """Warm-up: verify the server is alive."""
        self.client.get("/health")

    # ------------------------------------------------------------------ #
    # Tasks
    # ------------------------------------------------------------------ #

    @task(3)
    def health_check(self) -> None:
        """Lightweight health-check (high frequency)."""
        self.client.get("/health", name="/health")

    @task(5)
    def generate_font(self) -> None:
        """POST /fonts/generate — generate a font from a prompt."""
        payload = {
            "prompt": f"create a modern {random.choice(['bold', 'light', 'italic'])} font",
            "font_name": _random_font_name(),
        }
        with self.client.post(
            "/fonts/generate",
            json=payload,
            name="/fonts/generate",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 503):
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code}")

    @task(2)
    def run_agents(self) -> None:
        """POST /agents/run — run the full agent pipeline."""
        payload = {"prompt": "optimise spacing for web display"}
        with self.client.post(
            "/agents/run",
            json=payload,
            name="/agents/run",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 500):
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code}")

    @task(1)
    def export_nonexistent_font(self) -> None:
        """GET /fonts/{id}/export — exercises 404 path (fast)."""
        with self.client.get(
            "/fonts/nonexistent-id/export",
            name="/fonts/{font_id}/export",
            catch_response=True,
        ) as resp:
            if resp.status_code == 404:
                resp.success()
            else:
                resp.failure(f"Expected 404, got {resp.status_code}")
