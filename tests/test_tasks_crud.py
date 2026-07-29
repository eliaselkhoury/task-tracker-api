"""CRUD behaviour for /tasks - the Module 1-2 contract."""


def test_create_task_returns_201_and_defaults(client):
    response = client.post("/tasks", json={"title": "Fix auth bug"})

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Fix auth bug"
    assert body["status"] == "todo"
    assert body["priority"] == "medium"
    assert body["description"] is None
    assert body["id"]
    assert body["created_at"] == body["updated_at"]


def test_create_task_rejects_blank_title(client):
    response = client.post("/tasks", json={"title": "   "})

    assert response.status_code == 422


def test_create_task_rejects_unknown_priority(client):
    response = client.post("/tasks", json={"title": "Nope", "priority": "urgent"})

    assert response.status_code == 422


def test_list_tasks_starts_empty(client):
    response = client.get("/tasks")

    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_returns_created_tasks(make_task, client):
    make_task(title="One")
    make_task(title="Two")

    body = client.get("/tasks").json()

    assert [task["title"] for task in body] == ["One", "Two"]


def test_list_tasks_filters_by_status(make_task, client):
    make_task(title="Backlog item")
    make_task(title="Active item", status="in_progress")

    body = client.get("/tasks", params={"status": "in_progress"}).json()

    assert [task["title"] for task in body] == ["Active item"]


def test_list_tasks_filters_by_priority(make_task, client):
    make_task(title="Low one", priority="low")
    make_task(title="High one", priority="high")

    body = client.get("/tasks", params={"priority": "high"}).json()

    assert [task["title"] for task in body] == ["High one"]


def test_get_task_returns_the_task(make_task, client):
    created = make_task(title="Readme")

    response = client.get(f"/tasks/{created['id']}")

    assert response.status_code == 200
    assert response.json()["title"] == "Readme"


def test_get_task_returns_404_for_unknown_id(client):
    response = client.get("/tasks/does-not-exist")

    assert response.status_code == 404


def test_patch_task_updates_only_supplied_fields(make_task, client):
    created = make_task(title="Original", description="Keep me", priority="low")

    response = client.patch(f"/tasks/{created['id']}", json={"title": "Renamed"})

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Renamed"
    assert body["description"] == "Keep me"
    assert body["priority"] == "low"


def test_patch_task_returns_404_for_unknown_id(client):
    response = client.patch("/tasks/nope", json={"title": "x"})

    assert response.status_code == 404


def test_delete_task_returns_204_then_404(make_task, client):
    created = make_task(title="Temporary")

    assert client.delete(f"/tasks/{created['id']}").status_code == 204
    assert client.get(f"/tasks/{created['id']}").status_code == 404


def test_delete_task_returns_404_for_unknown_id(client):
    response = client.delete("/tasks/nope")

    assert response.status_code == 404
