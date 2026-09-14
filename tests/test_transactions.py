"""Proves the transaction.atomic() blocks used throughout the service
layer actually roll back on failure, rather than leaving a partial write
behind — the property the spec's "Transactions" section asks to be tested,
not just implemented."""

import pytest

from apps.activity.services import ActivityService
from apps.organizations.models import Membership, Organization
from apps.organizations.services import OrganizationService
from apps.projects.services import ProjectService
from apps.tasks.models import Task
from apps.tasks.services import TaskService

pytestmark = pytest.mark.django_db


def test_organization_creation_rolls_back_if_membership_insert_fails(user_factory, monkeypatch):
    owner = user_factory()

    def boom(*args, **kwargs):
        raise RuntimeError("simulated membership insert failure")

    monkeypatch.setattr(Membership.objects, "create", boom)

    with pytest.raises(RuntimeError):
        OrganizationService.create_organization(owner=owner, name="Acme")

    # If the Organization row survived despite the Membership insert
    # failing, transaction.atomic() isn't actually wrapping both writes.
    assert Organization.objects.filter(name="Acme").count() == 0


def test_task_creation_rolls_back_if_activity_log_fails(user_factory, monkeypatch):
    owner = user_factory()
    org = OrganizationService.create_organization(owner=owner, name="Acme")
    project = ProjectService.create_project(organization=org, owner=owner, name="Proj")

    def boom(*args, **kwargs):
        raise RuntimeError("simulated activity log failure")

    monkeypatch.setattr(ActivityService, "log", boom)

    with pytest.raises(RuntimeError):
        TaskService.create_task(project=project, created_by=owner, title="Should not persist")

    # The Task insert happens before the ActivityLog call inside the same
    # atomic() block — if that block weren't atomic, the Task would exist
    # with no corresponding audit trail entry.
    assert Task.objects.filter(title="Should not persist").count() == 0


def test_task_assignment_rolls_back_if_notification_fails(user_factory, monkeypatch):
    owner = user_factory()
    developer = user_factory()
    org = OrganizationService.create_organization(owner=owner, name="Acme")
    OrganizationService.add_member(organization=org, user=developer)
    project = ProjectService.create_project(organization=org, owner=owner, name="Proj")
    from apps.projects.models import ProjectMembership

    ProjectService.add_member(project=project, user=developer, role=ProjectMembership.Role.DEVELOPER, actor=owner)
    task = TaskService.create_task(project=project, created_by=owner, title="Task 1")

    from apps.notifications.services import NotificationService

    def boom(*args, **kwargs):
        raise RuntimeError("simulated notification failure")

    monkeypatch.setattr(NotificationService, "notify", boom)

    with pytest.raises(RuntimeError):
        TaskService.assign(task=task, user=developer, actor=owner)

    from apps.tasks.models import TaskAssignment

    assert TaskAssignment.objects.filter(task=task, user=developer).count() == 0
