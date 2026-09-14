import pytest
from django.utils import timezone

from apps.organizations.services import OrganizationService
from apps.projects.models import ProjectMembership
from apps.projects.services import ProjectService
from apps.projects.statistics import get_project_statistics
from apps.tasks.models import Task
from apps.tasks.services import TaskService
from apps.workflows.services import WorkflowService

pytestmark = pytest.mark.django_db


def test_statistics_computed_from_scratch_without_a_workflow(user_factory):
    owner = user_factory()
    org = OrganizationService.create_organization(owner=owner, name="Acme")
    project = ProjectService.create_project(organization=org, owner=owner, name="Proj")
    TaskService.create_task(project=project, created_by=owner, title="Task 1", priority=Task.Priority.HIGH)
    TaskService.create_task(project=project, created_by=owner, title="Task 2", priority=Task.Priority.LOW)

    stats = get_project_statistics(project=project)
    assert stats["total_tasks"] == 2
    assert stats["completed_tasks"] == 0
    assert stats["pending_tasks"] == 2
    assert stats["tasks_by_priority"] == {"HIGH": 1, "LOW": 1}
    assert stats["average_completion_hours"] is None  # no workflow yet, nothing can be "completed"
    assert stats["cache_hit"] is False


def test_statistics_second_call_is_a_cache_hit(user_factory):
    owner = user_factory()
    org = OrganizationService.create_organization(owner=owner, name="Acme")
    project = ProjectService.create_project(organization=org, owner=owner, name="Proj")
    TaskService.create_task(project=project, created_by=owner, title="Task 1")

    first = get_project_statistics(project=project)
    second = get_project_statistics(project=project)
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert second["generated_at"] == first["generated_at"]  # identical cached payload, not recomputed


def test_statistics_invalidated_after_a_task_changes(user_factory):
    owner = user_factory()
    org = OrganizationService.create_organization(owner=owner, name="Acme")
    project = ProjectService.create_project(organization=org, owner=owner, name="Proj")
    TaskService.create_task(project=project, created_by=owner, title="Task 1")
    get_project_statistics(project=project)  # populates the cache

    TaskService.create_task(project=project, created_by=owner, title="Task 2")
    stats = get_project_statistics(project=project)
    assert stats["cache_hit"] is False  # the post_save signal cleared the cache
    assert stats["total_tasks"] == 2


def test_overdue_tasks_counted_correctly(user_factory):
    owner = user_factory()
    org = OrganizationService.create_organization(owner=owner, name="Acme")
    project = ProjectService.create_project(organization=org, owner=owner, name="Proj")
    yesterday = timezone.localdate() - timezone.timedelta(days=1)
    tomorrow = timezone.localdate() + timezone.timedelta(days=1)
    TaskService.create_task(project=project, created_by=owner, title="Overdue", due_date=yesterday)
    TaskService.create_task(project=project, created_by=owner, title="Not due yet", due_date=tomorrow)

    stats = get_project_statistics(project=project)
    assert stats["overdue_tasks"] == 1


def test_completion_metrics_after_a_task_reaches_a_terminal_state(user_factory):
    owner = user_factory()
    org = OrganizationService.create_organization(owner=owner, name="Acme")
    project = ProjectService.create_project(organization=org, owner=owner, name="Proj")
    workflow = WorkflowService.create_workflow(organization=org, name="WF", actor=owner)
    backlog = WorkflowService.add_state(workflow=workflow, name="Backlog", order=1, is_initial=True, actor=owner)
    done = WorkflowService.add_state(workflow=workflow, name="Done", order=2, is_terminal=True, actor=owner)
    WorkflowService.add_transition(workflow=workflow, from_state=backlog, to_state=done, allowed_roles=[], actor=owner)
    project.workflow = workflow
    project.save(update_fields=["workflow"])

    task = TaskService.create_task(project=project, created_by=owner, title="Task 1")
    WorkflowService.transition_task(task=task, to_state=backlog, user=owner)
    WorkflowService.transition_task(task=task, to_state=done, user=owner)

    stats = get_project_statistics(project=project)
    assert stats["completed_tasks"] == 1
    assert stats["average_completion_hours"] is not None
    assert sum(stats["tasks_completed_per_day"].values()) == 1


def test_workload_by_member_counts_assigned_tasks(user_factory):
    owner = user_factory()
    developer = user_factory()
    org = OrganizationService.create_organization(owner=owner, name="Acme")
    OrganizationService.add_member(organization=org, user=developer)
    project = ProjectService.create_project(organization=org, owner=owner, name="Proj")
    ProjectService.add_member(project=project, user=developer, role=ProjectMembership.Role.DEVELOPER, actor=owner)

    task1 = TaskService.create_task(project=project, created_by=owner, title="Task 1")
    task2 = TaskService.create_task(project=project, created_by=owner, title="Task 2")
    TaskService.assign(task=task1, user=developer, actor=owner)
    TaskService.assign(task=task2, user=developer, actor=owner)

    stats = get_project_statistics(project=project)
    assert stats["workload_by_member"] == {developer.username: 2}
