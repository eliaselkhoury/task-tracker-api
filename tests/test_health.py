"""Smoke tests: the app starts and answers."""


def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_schema_is_available(client):
    """If the schema builds, every route's models are internally consistent."""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/tasks" in response.json()["paths"]
