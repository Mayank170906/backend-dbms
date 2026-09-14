import pytest

from apps.notifications.models import Notification
from apps.projects.models import ProjectExport
from config.celery import app as celery_app

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _celery_eager():
    # Run the export task synchronously, in-process, instead of requiring
    # a live worker — this tests the task's actual logic (CSV generation,
    # status transitions, notification) rather than just that .delay() was
    # called. Mutating the already-instantiated Celery app's conf directly
    # (not django.conf.settings via the `settings` fixture): Celery reads
    # CELERY_* Django settings once at app.config_from_object() time during
    # startup, so overriding django.conf.settings afterward has no effect
    # on an app object that already exists.
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = False
    celery_app.conf.task_eager_propagates = False


def test_export_endpoint_returns_immediately_with_pending_then_completes(auth_client):
    client, owner = auth_client()
    org = client.post("/api/v1/organizations/", {"name": "Acme"}, format="json").data
    project = client.post("/api/v1/projects/", {"organization": org["id"], "name": "Proj"}, format="json").data
    client.post("/api/v1/tasks/", {"project": project["id"], "title": "Exportable task", "priority": "HIGH"}, format="json")

    response = client.post(f"/api/v1/projects/{project['id']}/export/", {}, format="json")
    assert response.status_code == 202

    export = ProjectExport.objects.get(pk=response.data["id"])
    assert export.status == ProjectExport.Status.COMPLETED
    assert export.file.name

    content = export.file.read().decode("utf-8")
    assert "Exportable task" in content
    assert "HIGH" in content


def test_export_ready_notification_sent_to_requester(auth_client):
    client, owner = auth_client()
    org = client.post("/api/v1/organizations/", {"name": "Acme"}, format="json").data
    project = client.post("/api/v1/projects/", {"organization": org["id"], "name": "Proj"}, format="json").data

    client.post(f"/api/v1/projects/{project['id']}/export/", {}, format="json")

    assert Notification.objects.filter(
        recipient=owner, notification_type=Notification.NotificationType.EXPORT_READY
    ).exists()


def test_exports_list_scoped_to_project_membership(auth_client):
    client_a, _ = auth_client()
    client_b, _ = auth_client()
    org = client_a.post("/api/v1/organizations/", {"name": "Acme"}, format="json").data
    project = client_a.post("/api/v1/projects/", {"organization": org["id"], "name": "Proj"}, format="json").data
    client_a.post(f"/api/v1/projects/{project['id']}/export/", {}, format="json")

    response = client_b.get(f"/api/v1/projects/{project['id']}/exports/")
    assert response.status_code == 404  # B isn't a member of this project at all
