"""main.py - Application entry point.

Creates the FastAPI instance, loads config, and registers all routers.
Run with: uvicorn app.main:app --reload
"""

from typing import Optional

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app import storage
from app.business_rules import BusinessRuleError
from app.core.config import settings
from app.models import TaskCreate, TaskPriority, TaskResponse, TaskStatus, TaskUpdate
from app.api.routes.health import router as health_router

# Create the FastAPI application instance.
# The title and version appear in the auto-generated /docs (Swagger UI).
app = FastAPI(
    title="Task Tracker API",
    version="0.1.0",
    description="A learning-focused REST API built with FastAPI and JSON file storage.",
)

# The frontend is served from a different port (Live Server on 5500) than the
# API (8000), which makes every fetch a cross-origin request. Without this the
# browser blocks the response and the board silently stays empty.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers.
# All routes defined in health_router are mounted at the root path.
# Add future routers here (e.g., tasks, projects) as the app grows.
app.include_router(health_router)


@app.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["tasks"],
)
def create_task(payload: TaskCreate) -> TaskResponse:
    """Create a new task and return it with its server-assigned id."""
    return storage.add_task(payload)


@app.get("/tasks", response_model=list[TaskResponse], tags=["tasks"])
def list_tasks(
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    assignee: Optional[str] = None,
    overdue: Optional[bool] = None,
) -> list[TaskResponse]:
    """List tasks, optionally filtered. Filters combine with AND.

    `overdue=true` returns only tasks past their due date that are not done;
    `overdue=false` returns everything else, including tasks with no due date.
    Omit it to get all tasks.
    """
    return storage.list_tasks(
        status=status, priority=priority, assignee=assignee, overdue=overdue
    )


@app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
def get_task(task_id: str) -> TaskResponse:
    """Return a single task, or 404 if the id is unknown."""
    try:
        return storage.get_task(task_id)
    except storage.TaskNotFoundError:
        raise HTTPException(status_code=404, detail="task not found")


@app.patch("/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
def update_task_route(task_id: str, payload: TaskUpdate) -> TaskResponse:
    """Partially update a task.

    Returns 404 for an unknown id and 409 when the requested status change is
    not a legal transition.
    """
    try:
        return storage.update_task(task_id, payload)
    except storage.TaskNotFoundError:
        raise HTTPException(status_code=404, detail="task not found")
    except BusinessRuleError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["tasks"])
def delete_task_route(task_id: str) -> Response:
    """Delete a task. Returns 204 with no body, or 404 if the id is unknown."""
    try:
        storage.delete_task(task_id)
    except storage.TaskNotFoundError:
        raise HTTPException(status_code=404, detail="task not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
