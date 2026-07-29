"""Shared pytest fixtures.

Every test gets its own empty JSON store in a temporary directory, so tests
never see each other's tasks and never touch the developer's real data file.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    """Point the storage layer at a fresh temp file for the duration of a test."""
    monkeypatch.setattr(settings, "data_file", tmp_path / "tasks.json")
    yield tmp_path / "tasks.json"


@pytest.fixture
def client() -> TestClient:
    """An HTTP client that calls the app in-process (no server needed)."""
    return TestClient(app)


@pytest.fixture
def make_task(client):
    """Create a task via the API and return its response body.

    Keeps tests short: `make_task(title="X", priority="high")`.
    """

    def _make_task(**overrides):
        payload = {"title": "Sample task"}
        payload.update(overrides)
        response = client.post("/tasks", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _make_task
