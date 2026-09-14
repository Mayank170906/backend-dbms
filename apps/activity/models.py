from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.organizations.models import Organization
from apps.projects.models import Project


class ActivityLog(models.Model):
    class Action(models.TextChoices):
        TASK_CREATED = "task.created", "Task Created"
        TASK_ASSIGNED = "task.assigned", "Task Assigned"
        TASK_STATUS_CHANGED = "task.status_changed", "Task Status Changed"
        COMMENT_ADDED = "comment.added", "Comment Added"
        PROJECT_MEMBERSHIP_CHANGED = "project_membership.changed", "Project Membership Changed"
        WORKFLOW_CHANGED = "workflow.changed", "Workflow Changed"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
    )
    action = models.CharField(max_length=50, choices=Action.choices)
    # Generic target (Task, Comment, ProjectMembership, Workflow, ...)
    # instead of a separate FK per object type: the audit trail needs to
    # point at "whatever changed", and that set of types grows with the
    # app — a GenericForeignKey means adding a new loggable model never
    # requires a migration on ActivityLog itself.
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    target = GenericForeignKey("content_type", "object_id")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="activity_logs")
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, null=True, blank=True, related_name="activity_logs"
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # Supports the two real query patterns: an org- or
            # project-scoped activity feed ordered by time...
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["project", "created_at"]),
            # ...and "show the history of this specific object".
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} by {self.actor} at {self.created_at}"

    def save(self, *args, **kwargs):
        # Enforced here, not just by convention or admin config: an audit
        # log that can be quietly edited after the fact isn't an audit log.
        if self.pk is not None:
            raise ValueError("ActivityLog entries are immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("ActivityLog entries cannot be deleted; they are a permanent audit trail.")
