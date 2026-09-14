"""Formalizes the Phase 9 manual verification into pytest: real
WebsocketCommunicator against the real ASGI app and the real Redis-backed
channel layer (no mocking) — connection authorization, then an actual
service call producing a live event on the socket."""

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import AccessToken

from apps.organizations.services import OrganizationService
from apps.projects.models import ProjectMembership
from apps.projects.services import ProjectService
from apps.tasks.services import TaskService
from config.asgi import application

# transaction=True: ActivityService.log()'s broadcast is deferred via
# transaction.on_commit() (Phase 9's on_commit reasoning), which never
# fires under pytest-django's default test wrapping (each test runs
# inside a transaction that's rolled back, not committed). Real commits
# are required here to actually exercise the live-broadcast path.
pytestmark = pytest.mark.django_db(transaction=True)


@database_sync_to_async
def _make_project_with_member(owner, member):
    org = OrganizationService.create_organization(owner=owner, name="Acme")
    OrganizationService.add_member(organization=org, user=member)
    project = ProjectService.create_project(organization=org, owner=owner, name="Proj")
    ProjectService.add_member(project=project, user=member, role=ProjectMembership.Role.DEVELOPER, actor=owner)
    return project


@database_sync_to_async
def _create_task(project, owner):
    return TaskService.create_task(project=project, created_by=owner, title="Realtime task")


async def test_non_member_websocket_connection_is_rejected(user_factory):
    owner = await database_sync_to_async(user_factory)()
    outsider = await database_sync_to_async(user_factory)()
    project = await _make_project_with_member(owner, await database_sync_to_async(user_factory)())

    token = str(AccessToken.for_user(outsider))
    communicator = WebsocketCommunicator(application, f"/ws/projects/{project.id}/?token={token}")
    connected, _ = await communicator.connect()
    assert connected is False


async def test_anonymous_websocket_connection_is_rejected(user_factory):
    owner = await database_sync_to_async(user_factory)()
    project = await _make_project_with_member(owner, await database_sync_to_async(user_factory)())

    communicator = WebsocketCommunicator(application, f"/ws/projects/{project.id}/")
    connected, _ = await communicator.connect()
    assert connected is False


async def test_member_receives_live_activity_event_on_task_creation(user_factory):
    owner = await database_sync_to_async(user_factory)()
    member = await database_sync_to_async(user_factory)()
    project = await _make_project_with_member(owner, member)

    token = str(AccessToken.for_user(member))
    communicator = WebsocketCommunicator(application, f"/ws/projects/{project.id}/?token={token}")
    connected, _ = await communicator.connect()
    assert connected is True

    await _create_task(project, owner)

    event = await communicator.receive_json_from(timeout=5)
    assert event["action"] == "task.created"

    await communicator.disconnect()
