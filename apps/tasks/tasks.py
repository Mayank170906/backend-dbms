from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.services import NotificationService

from .models import Task


@shared_task
def notify_tasks_due_tomorrow() -> int:
    # The one Phase 6 notification example that needs a recurring check
    # rather than an event hook — nothing about "tomorrow" changes as the
    # result of a write, so it has to be evaluated on a schedule.
    tomorrow = timezone.localdate() + timedelta(days=1)
    tasks = (
        Task.objects.filter(due_date=tomorrow)
        .exclude(workflow_state__is_terminal=True)
        .prefetch_related("assignees")
    )
    count = 0
    for task in tasks:
        for user in task.assignees.all():
            NotificationService.notify(
                recipient=user,
                notification_type=Notification.NotificationType.TASK_DUE_SOON,
                message=f"Task #{task.id} is due tomorrow: {task.title}",
                target=task,
            )
            count += 1
    return count
