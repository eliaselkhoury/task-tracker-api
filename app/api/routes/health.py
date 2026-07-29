"""Health-check route.

A tiny endpoint that proves the process is up and configured. Useful as the
first thing to hit after starting the server and as a smoke test in pytest.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Report that the API is running."""
    return {"status": "ok", "service": "task-tracker-api"}
