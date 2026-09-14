import re

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.activity.models import ActivityLog
from apps.activity.services import ActivityService
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.projects.models import ProjectMembership
from apps.tasks.models import Task

from .models import Comment

MENTION_RE = re.compile(r"@(\w+)")


class CommentService:
    @staticmethod
    @transaction.atomic
    def add_comment(*, task: Task, author, body: str) -> Comment:
        if not ProjectMembership.objects.filter(project=task.project, user=author).exists():
            raise ValueError(f"{author} is not a member of {task.project}.")
        comment = Comment.objects.create(task=task, author=author, body=body)
        ActivityService.log(
            actor=author,
            action=ActivityLog.Action.COMMENT_ADDED,
            target=comment,
            organization=task.project.organization,
            project=task.project,
            metadata={"task_id": task.id},
        )
        CommentService._notify_mentions(comment=comment, task=task, author=author)
        return comment

    @staticmethod
    def _notify_mentions(*, comment: Comment, task: Task, author) -> None:
        usernames = set(MENTION_RE.findall(comment.body))
        if not usernames:
            return
        User = get_user_model()
        mentioned_users = User.objects.filter(username__in=usernames).exclude(pk=author.pk)
        # Only notify mentions that resolve to an actual project member —
        # an "@username" typed in a comment body is untrusted text, not
        # proof the mentioned account has any standing on this task.
        member_ids = set(
            ProjectMembership.objects.filter(project=task.project, user__in=mentioned_users).values_list(
                "user_id", flat=True
            )
        )
        for user in mentioned_users:
            if user.id not in member_ids:
                continue
            NotificationService.notify(
                recipient=user,
                notification_type=Notification.NotificationType.COMMENT_MENTION,
                message=f"You were mentioned in a comment on Task #{task.id}: {task.title}",
                target=comment,
            )
