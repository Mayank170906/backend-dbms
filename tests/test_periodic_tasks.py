import pytest
from django.utils import timezone

from apps.accounts.tasks import cleanup_expired_tokens
from apps.notifications.models import Notification
from apps.organizations.services import OrganizationService
from apps.projects.models import ProjectMembership
from apps.projects.services import ProjectService
from apps.projects.tasks import generate_daily_project_reports
from apps.tasks.services import TaskService
from apps.tasks.tasks import notify_tasks_due_tomorrow

pytestmark = pytest.mark.django_db


def test_notify_tasks_due_tomorrow_only_notifies_assignees_of_tasks_due_tomorrow(user_factory):
    owner = user_factory()
    developer = user_factory()
    org = OrganizationService.create_organization(owner=owner, name="Acme")
    OrganizationService.add_member(organization=org, user=developer)
    project = ProjectService.create_project(organization=org, owner=owner, name="Proj")
    ProjectService.add_member(project=project, user=developer, role=ProjectMembership.Role.DEVELOPER, actor=owner)

    tomorrow = timezone.localdate() + timezone.timedelta(days=1)
    next_week = timezone.localdate() + timezone.timedelta(days=7)

    due_tomorrow = TaskService.create_task(project=project, created_by=owner, title="Due tomorrow", due_date=tomorrow)
    TaskService.assign(task=due_tomorrow, user=developer, actor=owner)

    due_later = TaskService.create_task(project=project, created_by=owner, title="Due later", due_date=next_week)
    TaskService.assign(task=due_later, user=developer, actor=owner)

    count = notify_tasks_due_tomorrow()

    assert count == 1
    notification = Notification.objects.get(notification_type=Notification.NotificationType.TASK_DUE_SOON)
    assert notification.recipient == developer
    assert "Due tomorrow" in notification.message


def test_notify_tasks_due_tomorrow_skips_terminal_tasks(user_factory):
    from apps.workflows.services import WorkflowService

    owner = user_factory()
    developer = user_factory()
    org = OrganizationService.create_organization(owner=owner, name="Acme")
    OrganizationService.add_member(organization=org, user=developer)
    project = ProjectService.create_project(organization=org, owner=owner, name="Proj")
    ProjectService.add_member(project=project, user=developer, role=ProjectMembership.Role.DEVELOPER, actor=owner)
    workflow = WorkflowService.create_workflow(organization=org, name="WF", actor=owner)
    done = WorkflowService.add_state(workflow=workflow, name="Done", order=1, is_initial=True, is_terminal=True, actor=owner)
    project.workflow = workflow
    project.save(update_fields=["workflow"])

    tomorrow = timezone.localdate() + timezone.timedelta(days=1)
    task = TaskService.create_task(project=project, created_by=owner, title="Already done", due_date=tomorrow)
    TaskService.assign(task=task, user=developer, actor=owner)
    WorkflowService.transition_task(task=task, to_state=done, user=owner)

    count = notify_tasks_due_tomorrow()
    assert count == 0


def test_generate_daily_project_reports_notifies_each_active_projects_owner(user_factory):
    owner = user_factory()
    org = OrganizationService.create_organization(owner=owner, name="Acme")
    project = ProjectService.create_project(organization=org, owner=owner, name="Proj")
    TaskService.create_task(project=project, created_by=owner, title="Task 1")

    count = generate_daily_project_reports()

    assert count == 1
    assert Notification.objects.filter(
        recipient=owner, notification_type=Notification.NotificationType.PROJECT_REPORT
    ).exists()


def test_generate_daily_project_reports_skips_archived_projects(user_factory):
    owner = user_factory()
    org = OrganizationService.create_organization(owner=owner, name="Acme")
    project = ProjectService.create_project(organization=org, owner=owner, name="Proj")
    from apps.projects.models import Project

    Project.objects.filter(pk=project.pk).update(status="ARCHIVED")

    count = generate_daily_project_reports()
    assert count == 0


def test_cleanup_expired_tokens_runs_without_error(user_factory):
    # Nothing to assert on the row count without faking token expiry —
    # this just confirms the management command wrapper actually runs
    # cleanly against a real database.
    cleanup_expired_tokens()
