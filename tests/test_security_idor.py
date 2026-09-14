"""Dedicated IDOR/cross-tenant tests: for every major resource, a user who
is not a member of the owning organization/project must not be able to
read it by guessing or incrementing its id — regardless of endpoint."""

import pytest

from apps.notifications.services import NotificationService

pytestmark = pytest.mark.django_db


def test_cannot_read_other_organizations_project(auth_client):
    client_a, _ = auth_client()
    client_b, _ = auth_client()
    org = client_a.post("/api/v1/organizations/", {"name": "Acme"}, format="json").data
    project = client_a.post("/api/v1/projects/", {"organization": org["id"], "name": "Proj"}, format="json").data

    response = client_b.get(f"/api/v1/projects/{project['id']}/")
    assert response.status_code == 404


def test_cannot_read_other_projects_task(auth_client):
    client_a, _ = auth_client()
    client_b, _ = auth_client()
    org = client_a.post("/api/v1/organizations/", {"name": "Acme"}, format="json").data
    project = client_a.post("/api/v1/projects/", {"organization": org["id"], "name": "Proj"}, format="json").data
    task = client_a.post("/api/v1/tasks/", {"project": project["id"], "title": "Secret task"}, format="json").data

    response = client_b.get(f"/api/v1/tasks/{task['id']}/")
    assert response.status_code == 404


def test_incrementing_a_known_id_does_not_reach_another_tenants_project(auth_client):
    client_a, _ = auth_client()
    org_a = client_a.post("/api/v1/organizations/", {"name": "Acme"}, format="json").data
    project_a = client_a.post("/api/v1/projects/", {"organization": org_a["id"], "name": "Proj A"}, format="json").data

    client_b, _ = auth_client()
    org_b = client_b.post("/api/v1/organizations/", {"name": "Beta"}, format="json").data
    project_b = client_b.post("/api/v1/projects/", {"organization": org_b["id"], "name": "Proj B"}, format="json").data

    assert client_b.get(f"/api/v1/projects/{project_a['id']}/").status_code == 404
    assert client_b.get(f"/api/v1/projects/{project_b['id']}/").status_code == 200


def test_cannot_read_other_projects_activity_feed(auth_client):
    client_a, _ = auth_client()
    client_b, _ = auth_client()
    org = client_a.post("/api/v1/organizations/", {"name": "Acme"}, format="json").data
    project = client_a.post("/api/v1/projects/", {"organization": org["id"], "name": "Proj"}, format="json").data

    response = client_b.get(f"/api/v1/projects/{project['id']}/activity/")
    assert response.status_code == 404


def test_cannot_read_other_projects_statistics(auth_client):
    client_a, _ = auth_client()
    client_b, _ = auth_client()
    org = client_a.post("/api/v1/organizations/", {"name": "Acme"}, format="json").data
    project = client_a.post("/api/v1/projects/", {"organization": org["id"], "name": "Proj"}, format="json").data

    response = client_b.get(f"/api/v1/projects/{project['id']}/statistics/")
    assert response.status_code == 404


def test_cannot_comment_on_a_task_outside_ones_projects(auth_client):
    client_a, _ = auth_client()
    client_b, _ = auth_client()
    org = client_a.post("/api/v1/organizations/", {"name": "Acme"}, format="json").data
    project = client_a.post("/api/v1/projects/", {"organization": org["id"], "name": "Proj"}, format="json").data
    task = client_a.post("/api/v1/tasks/", {"project": project["id"], "title": "Task 1"}, format="json").data

    response = client_b.post(f"/api/v1/tasks/{task['id']}/comments/", {"body": "sneaky"}, format="json")
    assert response.status_code == 404  # task isn't even visible to B


def test_notifications_are_scoped_to_their_recipient(auth_client):
    client_a, user_a = auth_client()
    client_b, _ = auth_client()
    NotificationService.notify(recipient=user_a, notification_type="task_assigned", message="For A's eyes only")

    response = client_b.get("/api/v1/notifications/")
    assert response.data["count"] == 0


def test_search_results_are_scoped_to_caller(auth_client):
    client_a, _ = auth_client()
    client_b, _ = auth_client()
    org = client_a.post("/api/v1/organizations/", {"name": "Acme"}, format="json").data
    project = client_a.post("/api/v1/projects/", {"organization": org["id"], "name": "Proj"}, format="json").data
    client_a.post("/api/v1/tasks/", {"project": project["id"], "title": "Unique searchable phrase"}, format="json")

    response = client_b.get("/api/v1/search/?q=unique searchable phrase")
    assert response.data["tasks"] == []
