from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from .models import Notification
from .realtime import broadcast_notification


class NotificationService:
    @staticmethod
    def notify(*, recipient, notification_type: str, message: str, target=None) -> Notification:
        notification = Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            message=message,
            content_type=ContentType.objects.get_for_model(target) if target is not None else None,
            object_id=target.pk if target is not None else None,
        )
        payload = {
            "id": notification.id,
            "notification_type": notification.notification_type,
            "message": notification.message,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat(),
        }
        # Deferred to commit for the same reason as ActivityService.log()
        # — see its comment. Every existing caller (TaskService, CommentService,
        # ProjectService, WorkflowService) already wraps this in
        # transaction.atomic(), so this line is the only Phase 9 change
        # needed to make every one of them real-time.
        transaction.on_commit(lambda: broadcast_notification(user_id=recipient.id, payload=payload))
        return notification

    @staticmethod
    def mark_read(*, notification: Notification) -> Notification:
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
        return notification

    @staticmethod
    def mark_all_read(*, user) -> int:
        return Notification.objects.filter(recipient=user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
