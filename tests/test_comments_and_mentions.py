import pytest

from apps.comments.services import CommentService
from apps.notifications.models import Notification
from apps.organizations.services import OrganizationService
from apps.projects.models import ProjectMembership
from apps.projects.services import ProjectService
from apps.tasks.services import TaskService

pytestmark = pytest.mark.django_db


@pytest.fixture
def task_with_members(user_factory):
    owner = user_factory(username="alice")
    member = user_factory(username="bob")
    outsider = user_factory(username="carol")
    org = OrganizationService.create_organization(owner=owner, name="Acme")
    OrganizationService.add_member(organization=org, user=member)
    project = ProjectService.create_project(organization=org, owner=owner, name="Proj")
    ProjectService.add_member(project=project, user=member, role=ProjectMembership.Role.DEVELOPER, actor=owner)
    task = TaskService.create_task(project=project, created_by=owner, title="Task 1")
    return owner, member, outsider, task


def test_mentioning_a_project_member_sends_a_notification(task_with_members):
    owner, member, outsider, task = task_with_members
    CommentService.add_comment(task=task, author=owner, body="Hey @bob can you look at this?")

    assert Notification.objects.filter(
        recipient=member, notification_type=Notification.NotificationType.COMMENT_MENTION
    ).exists()


def test_mentioning_a_non_member_sends_no_notification(task_with_members):
    owner, member, outsider, task = task_with_members
    CommentService.add_comment(task=task, author=owner, body="Hey @carol take a look")

    # "carol" is a real user but not a project member — an @mention is
    # untrusted text typed into a comment, not proof of standing on the
    # task, so it must not become a delivery target.
    assert not Notification.objects.filter(recipient=outsider).exists()


def test_mentioning_a_nonexistent_username_does_not_error(task_with_members):
    owner, member, outsider, task = task_with_members
    comment = CommentService.add_comment(task=task, author=owner, body="Hey @nobody_by_this_name")
    assert comment.body == "Hey @nobody_by_this_name"


def test_author_does_not_get_a_self_mention_notification(task_with_members):
    owner, member, outsider, task = task_with_members
    CommentService.add_comment(task=task, author=owner, body="Note to self @alice")
    assert not Notification.objects.filter(recipient=owner, notification_type=Notification.NotificationType.COMMENT_MENTION).exists()


def test_non_member_cannot_comment(task_with_members):
    owner, member, outsider, task = task_with_members
    with pytest.raises(ValueError):
        CommentService.add_comment(task=task, author=outsider, body="sneaking in")
