from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        TASK_ASSIGNED = "task_assigned", "Task Assigned"
        TASK_TRANSITIONED = "task_transitioned", "Task Transitioned"
        COMMENT_MENTION = "comment_mention", "Mentioned in Comment"
        TASK_DUE_SOON = "task_due_soon", "Task Due Soon"
        PROJECT_MEMBERSHIP_CHANGED = "project_membership_changed", "Added to Project"
        EXPORT_READY = "export_ready", "Export Ready"
        PROJECT_REPORT = "project_report", "Project Report"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    message = models.CharField(max_length=255)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        # The overwhelmingly common query is "this user's unread
        # notifications" (the notification bell badge count and list) —
        # indexing (recipient, is_read) directly supports it.
        indexes = [models.Index(fields=["recipient", "is_read"])]

    def __str__(self) -> str:
        return f"{self.message} -> {self.recipient}"
