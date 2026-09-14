import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from apps.activity.models import ActivityLog
from apps.organizations.models import Membership
from apps.organizations.services import OrganizationService
from apps.projects.services import ProjectService
from apps.tasks.services import TaskService

pytestmark = pytest.mark.django_db


def test_membership_unique_per_organization_and_user(user_factory):
    owner = user_factory()
    org = OrganizationService.create_organization(owner=owner, name="Acme")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Membership.objects.create(organization=org, user=owner, role=Membership.Role.MEMBER)


def test_organization_owner_is_protected_on_delete(user_factory):
    owner = user_factory()
    OrganizationService.create_organization(owner=owner, name="Acme")
    with pytest.raises(ProtectedError):
        owner.delete()


def test_project_slug_unique_per_organization_not_globally(user_factory):
    owner = user_factory()
    org_a = OrganizationService.create_organization(owner=owner, name="Org A")
    org_b = OrganizationService.create_organization(owner=owner, name="Org B")
    # Same name -> same slug in two different organizations must not collide.
    project_a = ProjectService.create_project(organization=org_a, owner=owner, name="Backend")
    project_b = ProjectService.create_project(organization=org_b, owner=owner, name="Backend")
    assert project_a.slug == project_b.slug == "backend"


def test_task_created_by_set_null_on_user_delete(user_factory):
    owner = user_factory()
    other = user_factory()
    org = OrganizationService.create_organization(owner=owner, name="Acme")
    OrganizationService.add_member(organization=org, user=other)
    project = ProjectService.create_project(organization=org, owner=owner, name="Proj")
    from apps.projects.models import ProjectMembership

    ProjectService.add_member(project=project, user=other, role=ProjectMembership.Role.DEVELOPER, actor=owner)
    task = TaskService.create_task(project=project, created_by=other, title="Task 1")

    other.delete()
    task.refresh_from_db()
    assert task.created_by_id is None
    assert task.title == "Task 1"  # the task itself survives, unlike Organization.owner


def test_activity_log_cannot_be_updated(user_factory):
    owner = user_factory()
    org = OrganizationService.create_organization(owner=owner, name="Acme")
    project = ProjectService.create_project(organization=org, owner=owner, name="Proj")
    TaskService.create_task(project=project, created_by=owner, title="Task 1")

    entry = ActivityLog.objects.filter(project=project).first()
    assert entry is not None
    entry.action = "tampered"
    with pytest.raises(ValueError):
        entry.save()


def test_activity_log_cannot_be_deleted(user_factory):
    owner = user_factory()
    org = OrganizationService.create_organization(owner=owner, name="Acme")
    project = ProjectService.create_project(organization=org, owner=owner, name="Proj")
    TaskService.create_task(project=project, created_by=owner, title="Task 1")

    entry = ActivityLog.objects.filter(project=project).first()
    with pytest.raises(ValueError):
        entry.delete()
