import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def project_setup(auth_client):
    client, owner = auth_client()
    org = client.post("/api/v1/organizations/", {"name": "Acme"}, format="json").data
    project = client.post("/api/v1/projects/", {"organization": org["id"], "name": "Proj"}, format="json").data
    return client, owner, org, project


def test_create_and_list_tasks(project_setup):
    client, owner, org, project = project_setup
    client.post("/api/v1/tasks/", {"project": project["id"], "title": "Task 1", "priority": "HIGH"}, format="json")
    client.post("/api/v1/tasks/", {"project": project["id"], "title": "Task 2", "priority": "LOW"}, format="json")

    response = client.get(f"/api/v1/tasks/?project={project['id']}")
    assert response.data["count"] == 2


def test_filter_by_priority(project_setup):
    client, owner, org, project = project_setup
    client.post("/api/v1/tasks/", {"project": project["id"], "title": "Task 1", "priority": "HIGH"}, format="json")
    client.post("/api/v1/tasks/", {"project": project["id"], "title": "Task 2", "priority": "LOW"}, format="json")

    response = client.get("/api/v1/tasks/?priority=HIGH")
    assert response.data["count"] == 1
    assert response.data["results"][0]["title"] == "Task 1"


def test_search_uses_postgres_full_text_search(project_setup):
    client, owner, org, project = project_setup
    client.post("/api/v1/tasks/", {"project": project["id"], "title": "Fix invoice rendering bug"}, format="json")
    client.post("/api/v1/tasks/", {"project": project["id"], "title": "Completely unrelated"}, format="json")

    response = client.get("/api/v1/tasks/?search=invoice")
    assert response.data["count"] == 1


def test_ordering(project_setup):
    client, owner, org, project = project_setup
    client.post("/api/v1/tasks/", {"project": project["id"], "title": "B task"}, format="json")
    client.post("/api/v1/tasks/", {"project": project["id"], "title": "A task"}, format="json")

    response = client.get("/api/v1/tasks/?ordering=title")
    titles = [t["title"] for t in response.data["results"]]
    assert titles == sorted(titles)


def test_assign_rejects_non_project_member(project_setup, user_factory):
    client, owner, org, project = project_setup
    task = client.post("/api/v1/tasks/", {"project": project["id"], "title": "Task 1"}, format="json").data
    outsider = user_factory()

    response = client.post(f"/api/v1/tasks/{task['id']}/assign/", {"user_id": outsider.id}, format="json")
    assert response.status_code == 403


def test_workflow_state_is_read_only_on_task_serializer(project_setup):
    client, owner, org, project = project_setup
    task = client.post("/api/v1/tasks/", {"project": project["id"], "title": "Task 1"}, format="json").data

    response = client.patch(f"/api/v1/tasks/{task['id']}/", {"workflow_state": 999}, format="json")
    assert response.status_code == 200
    assert response.data["workflow_state"] is None


def test_task_project_cannot_be_changed_after_creation(project_setup):
    client, owner, org, project = project_setup
    project2 = client.post("/api/v1/projects/", {"organization": org["id"], "name": "Proj2"}, format="json").data
    task = client.post("/api/v1/tasks/", {"project": project["id"], "title": "Task 1"}, format="json").data

    response = client.patch(f"/api/v1/tasks/{task['id']}/", {"project": project2["id"]}, format="json")
    assert response.status_code == 400


def test_label_from_another_project_rejected_on_patch(project_setup):
    client, owner, org, project = project_setup
    project2 = client.post("/api/v1/projects/", {"organization": org["id"], "name": "Proj2"}, format="json").data
    label2 = client.post("/api/v1/labels/", {"project": project2["id"], "name": "urgent"}, format="json").data
    task = client.post("/api/v1/tasks/", {"project": project["id"], "title": "Task 1"}, format="json").data

    response = client.patch(f"/api/v1/tasks/{task['id']}/", {"labels": [label2["id"]]}, format="json")
    assert response.status_code == 400
