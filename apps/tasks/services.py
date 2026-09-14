from django.db import transaction

from apps.activity.models import ActivityLog
from apps.activity.services import ActivityService
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.projects.models import Project, ProjectMembership

from .models import Label, Task, TaskAssignment


class TaskService:
    @staticmethod
    def _ensure_project_member(*, project: Project, user) -> None:
        if not ProjectMembership.objects.filter(project=project, user=user).exists():
            raise ValueError(f"{user} is not a member of {project}.")

    @classmethod
    @transaction.atomic
    def create_task(
        cls,
        *,
        project: Project,
        created_by,
        title: str,
        description: str = "",
        priority: str = Task.Priority.MEDIUM,
        due_date=None,
        estimated_hours=None,
    ) -> Task:
        cls._ensure_project_member(project=project, user=created_by)
        task = Task.objects.create(
            project=project,
            title=title,
            description=description,
            created_by=created_by,
            priority=priority,
            due_date=due_date,
            estimated_hours=estimated_hours,
        )
        ActivityService.log(
            actor=created_by,
            action=ActivityLog.Action.TASK_CREATED,
            target=task,
            organization=project.organization,
            project=project,
            metadata={"title": task.title},
        )
        return task

    @classmethod
    @transaction.atomic
    def assign(cls, *, task: Task, user, actor) -> TaskAssignment:
        cls._ensure_project_member(project=task.project, user=user)
        assignment, created = TaskAssignment.objects.get_or_create(task=task, user=user)
        if created:
            ActivityService.log(
                actor=actor,
                action=ActivityLog.Action.TASK_ASSIGNED,
                target=task,
                organization=task.project.organization,
                project=task.project,
                metadata={"assignee": user.username},
            )
            NotificationService.notify(
                recipient=user,
                notification_type=Notification.NotificationType.TASK_ASSIGNED,
                message=f"You were assigned Task #{task.id}: {task.title}",
                target=task,
            )
        return assignment

    @staticmethod
    def add_label(*, task: Task, label: Label) -> None:
        # A label created under one project has no business being attached
        # to a task in a different project — this is the kind of
        # cross-tenant slip that's easy to introduce via a raw ID in an API
        # payload, so it's checked here rather than trusted from the caller.
        if label.project_id != task.project_id:
            raise ValueError("Label belongs to a different project than the task.")
        task.labels.add(label)
