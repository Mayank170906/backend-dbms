from django.db import transaction
from django.utils.text import slugify

from apps.activity.models import ActivityLog
from apps.activity.services import ActivityService
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.organizations.models import Membership, Organization

from .models import Project, ProjectMembership


class ProjectService:
    @staticmethod
    def _ensure_organization_member(*, organization: Organization, user) -> None:
        if not Membership.objects.filter(organization=organization, user=user).exists():
            raise ValueError(f"{user} is not a member of {organization}.")

    @staticmethod
    def _unique_slug(*, organization: Organization, name: str) -> str:
        base_slug = slugify(name)[:250] or "project"
        slug = base_slug
        suffix = 1
        while Project.objects.filter(organization=organization, slug=slug).exists():
            suffix += 1
            slug = f"{base_slug}-{suffix}"
        return slug

    @classmethod
    @transaction.atomic
    def create_project(cls, *, organization: Organization, owner, name: str, description: str = "") -> Project:
        # A project's owner must already belong to the organization it's
        # being created in — otherwise a user with no org affiliation could
        # end up "owning" a project inside a tenant they have no standing in.
        cls._ensure_organization_member(organization=organization, user=owner)
        project = Project.objects.create(
            organization=organization,
            name=name,
            slug=cls._unique_slug(organization=organization, name=name),
            description=description,
            owner=owner,
        )
        ProjectMembership.objects.create(
            project=project,
            user=owner,
            role=ProjectMembership.Role.MANAGER,
        )
        return project

    @classmethod
    @transaction.atomic
    def add_member(
        cls, *, project: Project, user, actor, role: str = ProjectMembership.Role.DEVELOPER
    ) -> ProjectMembership:
        cls._ensure_organization_member(organization=project.organization, user=user)
        membership, created = ProjectMembership.objects.update_or_create(
            project=project,
            user=user,
            defaults={"role": role},
        )
        ActivityService.log(
            actor=actor,
            action=ActivityLog.Action.PROJECT_MEMBERSHIP_CHANGED,
            target=membership,
            organization=project.organization,
            project=project,
            metadata={"user": user.username, "role": role},
        )
        if created:
            NotificationService.notify(
                recipient=user,
                notification_type=Notification.NotificationType.PROJECT_MEMBERSHIP_CHANGED,
                message=f"You were added to project {project.name}",
                target=project,
            )
        return membership
