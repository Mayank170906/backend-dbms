from django.db import transaction
from django.utils.text import slugify

from apps.activity.models import ActivityLog
from apps.activity.services import ActivityService
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.projects.models import ProjectMembership

from .models import Workflow, WorkflowState, WorkflowTransition


class WorkflowService:
    @staticmethod
    @transaction.atomic
    def create_workflow(*, organization, name: str, description: str = "", actor=None) -> Workflow:
        workflow = Workflow.objects.create(organization=organization, name=name, description=description)
        ActivityService.log(
            actor=actor,
            action=ActivityLog.Action.WORKFLOW_CHANGED,
            target=workflow,
            organization=organization,
            metadata={"change": "created", "name": name},
        )
        return workflow

    @staticmethod
    def _unique_slug(*, workflow: Workflow, name: str) -> str:
        base_slug = slugify(name)[:90] or "state"
        slug = base_slug
        suffix = 1
        while WorkflowState.objects.filter(workflow=workflow, slug=slug).exists():
            suffix += 1
            slug = f"{base_slug}-{suffix}"
        return slug

    @classmethod
    @transaction.atomic
    def add_state(
        cls,
        *,
        workflow: Workflow,
        name: str,
        order: int,
        is_initial: bool = False,
        is_terminal: bool = False,
        actor=None,
    ) -> WorkflowState:
        state = WorkflowState.objects.create(
            workflow=workflow,
            name=name,
            slug=cls._unique_slug(workflow=workflow, name=name),
            order=order,
            is_initial=is_initial,
            is_terminal=is_terminal,
        )
        ActivityService.log(
            actor=actor,
            action=ActivityLog.Action.WORKFLOW_CHANGED,
            target=workflow,
            organization=workflow.organization,
            metadata={"change": "state_added", "state": name},
        )
        return state

    @staticmethod
    @transaction.atomic
    def add_transition(
        *,
        workflow: Workflow,
        from_state: WorkflowState,
        to_state: WorkflowState,
        allowed_roles: list[str],
        actor=None,
    ) -> WorkflowTransition:
        if from_state.workflow_id != workflow.id or to_state.workflow_id != workflow.id:
            raise ValueError("from_state and to_state must belong to the given workflow.")
        valid_roles = set(ProjectMembership.Role.values)
        invalid_roles = set(allowed_roles) - valid_roles
        if invalid_roles:
            raise ValueError(f"Unknown role(s): {sorted(invalid_roles)}")
        transition = WorkflowTransition.objects.create(
            workflow=workflow,
            from_state=from_state,
            to_state=to_state,
            allowed_roles=list(allowed_roles),
        )
        ActivityService.log(
            actor=actor,
            action=ActivityLog.Action.WORKFLOW_CHANGED,
            target=workflow,
            organization=workflow.organization,
            metadata={"change": "transition_added", "from": from_state.name, "to": to_state.name},
        )
        return transition

    @staticmethod
    @transaction.atomic
    def transition_task(*, task, to_state: WorkflowState, user):
        # The backend is the sole authority here: every rule below is
        # re-derived from the database on every call, never trusted from
        # whatever state the frontend claims the task is in.
        project = task.project
        if project.workflow_id is None or project.workflow_id != to_state.workflow_id:
            raise ValueError("Target state does not belong to this project's workflow.")

        membership = ProjectMembership.objects.filter(project=project, user=user).first()
        if membership is None:
            raise PermissionError(f"{user} is not a member of {project}.")

        current_state = task.workflow_state

        if current_state is None:
            # No prior state: entering the workflow only makes sense at a
            # designated initial state, and any project member may do it —
            # there is no from_state to gate this move with a role list.
            if not to_state.is_initial:
                raise ValueError("A task with no current state can only move to an initial state.")
        else:
            try:
                transition = WorkflowTransition.objects.get(
                    workflow=project.workflow,
                    from_state=current_state,
                    to_state=to_state,
                )
            except WorkflowTransition.DoesNotExist:
                raise ValueError(f"No transition defined from '{current_state}' to '{to_state}'.")

            if transition.allowed_roles and membership.role not in transition.allowed_roles:
                raise PermissionError(
                    f"Role '{membership.role}' is not permitted to perform this transition."
                )

        task.workflow_state = to_state
        task.save(update_fields=["workflow_state", "updated_at"])

        ActivityService.log(
            actor=user,
            action=ActivityLog.Action.TASK_STATUS_CHANGED,
            target=task,
            organization=project.organization,
            project=project,
            metadata={"from": current_state.name if current_state else None, "to": to_state.name},
        )
        # Notify every other assignee — not the actor, who already knows —
        # that the task they're on moved. Phase 9's real-time broadcast
        # joins this same atomic block once Channels is wired up: a
        # transition either fully succeeds (state, audit trail,
        # notifications, broadcast) or none of it does.
        for assignee in task.assignees.exclude(pk=user.pk):
            NotificationService.notify(
                recipient=assignee,
                notification_type=Notification.NotificationType.TASK_TRANSITIONED,
                message=f"Task #{task.id} was moved to {to_state.name}",
                target=task,
            )
        return task
