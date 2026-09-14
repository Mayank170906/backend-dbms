import pytest

from apps.organizations.services import OrganizationService
from apps.projects.models import ProjectMembership
from apps.projects.services import ProjectService
from apps.tasks.services import TaskService
from apps.workflows.services import WorkflowService

pytestmark = pytest.mark.django_db


@pytest.fixture
def workflow_setup(user_factory):
    manager = user_factory()
    developer = user_factory()
    org = OrganizationService.create_organization(owner=manager, name="Acme")
    project = ProjectService.create_project(organization=org, owner=manager, name="Proj")
    OrganizationService.add_member(organization=org, user=developer)
    ProjectService.add_member(project=project, user=developer, role=ProjectMembership.Role.DEVELOPER, actor=manager)

    workflow = WorkflowService.create_workflow(organization=org, name="WF", actor=manager)
    backlog = WorkflowService.add_state(workflow=workflow, name="Backlog", order=1, is_initial=True, actor=manager)
    review = WorkflowService.add_state(workflow=workflow, name="Review", order=2, actor=manager)
    done = WorkflowService.add_state(workflow=workflow, name="Done", order=3, is_terminal=True, actor=manager)
    WorkflowService.add_transition(workflow=workflow, from_state=backlog, to_state=review, allowed_roles=[], actor=manager)
    WorkflowService.add_transition(
        workflow=workflow, from_state=review, to_state=done, allowed_roles=["MANAGER"], actor=manager
    )
    project.workflow = workflow
    project.save(update_fields=["workflow"])

    task = TaskService.create_task(project=project, created_by=manager, title="Task 1")
    return manager, developer, project, task, backlog, review, done


def test_cannot_enter_at_a_non_initial_state(workflow_setup):
    manager, developer, project, task, backlog, review, done = workflow_setup
    with pytest.raises(ValueError):
        WorkflowService.transition_task(task=task, to_state=review, user=manager)


def test_can_enter_at_the_initial_state(workflow_setup):
    manager, developer, project, task, backlog, review, done = workflow_setup
    WorkflowService.transition_task(task=task, to_state=backlog, user=manager)
    task.refresh_from_db()
    assert task.workflow_state_id == backlog.id


def test_cannot_skip_a_state_with_no_transition(workflow_setup):
    manager, developer, project, task, backlog, review, done = workflow_setup
    WorkflowService.transition_task(task=task, to_state=backlog, user=manager)
    with pytest.raises(ValueError):
        WorkflowService.transition_task(task=task, to_state=done, user=manager)


def test_role_gated_transition_denied_for_wrong_role(workflow_setup):
    manager, developer, project, task, backlog, review, done = workflow_setup
    WorkflowService.transition_task(task=task, to_state=backlog, user=manager)
    WorkflowService.transition_task(task=task, to_state=review, user=developer)
    with pytest.raises(PermissionError):
        WorkflowService.transition_task(task=task, to_state=done, user=developer)
    task.refresh_from_db()
    assert task.workflow_state_id == review.id  # unchanged after the rejected attempt


def test_role_gated_transition_allowed_for_correct_role(workflow_setup):
    manager, developer, project, task, backlog, review, done = workflow_setup
    WorkflowService.transition_task(task=task, to_state=backlog, user=manager)
    WorkflowService.transition_task(task=task, to_state=review, user=manager)
    WorkflowService.transition_task(task=task, to_state=done, user=manager)
    task.refresh_from_db()
    assert task.workflow_state_id == done.id


def test_non_project_member_cannot_transition(workflow_setup, user_factory):
    manager, developer, project, task, backlog, review, done = workflow_setup
    outsider = user_factory()
    with pytest.raises(PermissionError):
        WorkflowService.transition_task(task=task, to_state=backlog, user=outsider)


def test_transition_to_state_of_a_different_workflow_rejected(workflow_setup):
    manager, developer, project, task, backlog, review, done = workflow_setup
    other_org = OrganizationService.create_organization(owner=manager, name="Other")
    other_workflow = WorkflowService.create_workflow(organization=other_org, name="Other WF", actor=manager)
    foreign_state = WorkflowService.add_state(
        workflow=other_workflow, name="Foreign", order=1, is_initial=True, actor=manager
    )
    with pytest.raises(ValueError):
        WorkflowService.transition_task(task=task, to_state=foreign_state, user=manager)
