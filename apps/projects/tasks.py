import csv
import io

from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.services import NotificationService

from .models import Project, ProjectExport


@shared_task
def export_project_tasks_csv(export_id: int) -> None:
    export = ProjectExport.objects.select_related("project", "requested_by").get(pk=export_id)
    export.status = ProjectExport.Status.PROCESSING
    export.save(update_fields=["status"])

    try:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["id", "title", "priority", "workflow_state", "assignees", "due_date", "created_at"])
        tasks = export.project.tasks.select_related("workflow_state").prefetch_related("assignees")
        for task in tasks:
            writer.writerow(
                [
                    task.id,
                    task.title,
                    task.priority,
                    task.workflow_state.name if task.workflow_state else "",
                    ";".join(user.username for user in task.assignees.all()),
                    task.due_date or "",
                    task.created_at.isoformat(),
                ]
            )

        filename = f"project-{export.project_id}-tasks-{export.id}.csv"
        export.file.save(filename, ContentFile(buffer.getvalue().encode("utf-8")), save=False)
        export.status = ProjectExport.Status.COMPLETED
        export.completed_at = timezone.now()
        export.save(update_fields=["file", "status", "completed_at"])

        if export.requested_by is not None:
            NotificationService.notify(
                recipient=export.requested_by,
                notification_type=Notification.NotificationType.EXPORT_READY,
                message=f"Your export of {export.project.name} is ready.",
                target=export,
            )
    except Exception as exc:
        # Recorded on the row (visible via GET .../exports/) instead of
        # just raised — the requester has no other way to find out an
        # async job failed, since there's no request left to return an
        # error response on.
        export.status = ProjectExport.Status.FAILED
        export.error_message = str(exc)
        export.save(update_fields=["status", "error_message"])
        raise


@shared_task
def generate_daily_project_reports() -> int:
    from .statistics import get_project_statistics

    count = 0
    for project in Project.objects.filter(status=Project.Status.ACTIVE).select_related("owner"):
        if project.owner is None:
            continue
        stats = get_project_statistics(project=project)
        NotificationService.notify(
            recipient=project.owner,
            notification_type=Notification.NotificationType.PROJECT_REPORT,
            message=(
                f"Daily report for {project.name}: {stats['total_tasks']} total, "
                f"{stats['completed_tasks']} completed, {stats['overdue_tasks']} overdue."
            ),
            target=project,
        )
        count += 1
    return count
