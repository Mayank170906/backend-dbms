from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from .models import ActivityLog
from .realtime import broadcast_activity_event


class ActivityService:
    @staticmethod
    def log(*, actor, action: str, target, organization, project=None, metadata=None) -> ActivityLog:
        entry = ActivityLog.objects.create(
            actor=actor,
            action=action,
            content_type=ContentType.objects.get_for_model(target),
            object_id=target.pk,
            organization=organization,
            project=project,
            metadata=metadata or {},
        )
        if project is not None:
            payload = {
                "id": entry.id,
                "action": entry.action,
                "actor": actor.username if actor else None,
                "object_type": entry.content_type.model,
                "object_id": entry.object_id,
                "metadata": entry.metadata,
                "created_at": entry.created_at.isoformat(),
            }
            # Deferred until the enclosing transaction actually commits:
            # every caller of ActivityService.log() runs inside
            # transaction.atomic() alongside the write it's logging, and
            # broadcasting before commit would mean a live event fires for
            # a change that a later failure in the same transaction rolls
            # back. on_commit() runs immediately if there is no open
            # transaction (e.g. called from a shell), so this is a no-op
            # difference outside a transaction.
            transaction.on_commit(lambda: broadcast_activity_event(project_id=project.id, payload=payload))
        return entry
