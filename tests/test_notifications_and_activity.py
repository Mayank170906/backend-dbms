import pytest

from apps.notifications.services import NotificationService

pytestmark = pytest.mark.django_db


def test_mark_single_notification_read(auth_client):
    client, user = auth_client()
    notification = NotificationService.notify(recipient=user, notification_type="task_assigned", message="msg")

    response = client.post(f"/api/v1/notifications/{notification.id}/read/")
    assert response.status_code == 200
    assert response.data["is_read"] is True


def test_mark_all_read_only_touches_unread_ones(auth_client):
    client, user = auth_client()
    first = NotificationService.notify(recipient=user, notification_type="task_assigned", message="first")
    second = NotificationService.notify(recipient=user, notification_type="task_assigned", message="second")
    NotificationService.mark_read(notification=first)

    response = client.post("/api/v1/notifications/read-all/")
    assert response.data["marked_read"] == 1  # only `second` was still unread

    second.refresh_from_db()
    assert second.is_read is True


def test_project_activity_feed_is_paginated_and_ordered_newest_first(auth_client):
    client, owner = auth_client()
    org = client.post("/api/v1/organizations/", {"name": "Acme"}, format="json").data
    project = client.post("/api/v1/projects/", {"organization": org["id"], "name": "Proj"}, format="json").data
    client.post("/api/v1/tasks/", {"project": project["id"], "title": "Task 1"}, format="json")
    client.post("/api/v1/tasks/", {"project": project["id"], "title": "Task 2"}, format="json")

    response = client.get(f"/api/v1/projects/{project['id']}/activity/")
    assert "results" in response.data
    timestamps = [entry["created_at"] for entry in response.data["results"]]
    assert timestamps == sorted(timestamps, reverse=True)
